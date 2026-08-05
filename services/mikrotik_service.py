from __future__ import annotations

import ipaddress
import logging
import re
import select
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

try:
    import routeros_api
    _DISPONIBLE = True
except ImportError:
    _DISPONIBLE = False

from config import settings

logger = logging.getLogger(__name__)


def _minutes_vers_timeout(minutes: int) -> str:
    """Convertit des minutes en format RouterOS hh:mm:ss."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}:00"


_DUREE_UNITE = {"w": 7 * 86400, "d": 86400, "h": 3600, "m": 60, "s": 1}


def _parse_uptime(texte: str | None) -> int:
    """Convertit un uptime RouterOS ('1w2d3h4m5s', '45s', '1h30m') en secondes."""
    if not texte:
        return 0
    total = 0
    for montant, unite in re.findall(r"(\d+)\s*([wdhms])", texte):
        total += int(montant) * _DUREE_UNITE.get(unite, 0)
    return total


class MikroTikErreur(Exception):
    """Erreur levée par MikroTikService."""


class MikroTikService:
    """Interface haut niveau avec un routeur MikroTik.

    Usage recommandé :
        svc = MikroTikService()
        if svc.connecter():
            svc.ajouter_utilisateur_hotspot(...)
            svc.deconnecter()
    """

    def __init__(self):
        self._pool: Any = None
        self._api: Any = None
        # {nom_interface: (rx_bytes, tx_bytes, monotonic_ts)} pour calcul débit
        self._prev_stats: dict[str, tuple[int, int, float]] = {}

    # ── Connexion ─────────────────────────────────────────────────────────────

    def connecter(self) -> bool:
        """Ouvre la connexion au routeur (configuration globale). Retourne True si réussi."""
        if not _DISPONIBLE:
            logger.error("routeros-api n'est pas installé (pip install routeros-api)")
            return False

        host = getattr(settings, "MIKROTIK_HOST", None)
        port = getattr(settings, "MIKROTIK_PORT", 8728)
        user = getattr(settings, "MIKROTIK_USER", None)
        pwd  = getattr(settings, "MIKROTIK_PASSWORD", None)

        if not all([host, user, pwd]):
            logger.error(
                "Configuration MikroTik incomplète (MIKROTIK_HOST/USER/PASSWORD manquants)"
            )
            return False

        return self.connecter_routeur(host, user, pwd, port)

    def connecter_routeur(
        self,
        adresse_ip: str,
        username: str,
        password: str,
        port: int = 8728,
    ) -> bool:
        """Ouvre une connexion à un routeur précis (identifiants de la zone)."""
        if not _DISPONIBLE:
            logger.error("routeros-api n'est pas installé (pip install routeros-api)")
            return False

        try:
            self._pool = routeros_api.RouterOsApiPool(
                host=adresse_ip,
                username=username,
                password=password,
                port=int(port),
                plaintext_login=True,
            )
            self._api = self._pool.get_api()
            logger.info("Connexion MikroTik établie (%s:%s)", adresse_ip, port)
            return True
        except Exception as exc:
            logger.error("Connexion MikroTik échouée (%s): %s", adresse_ip, exc)
            self._pool = None
            self._api = None
            return False

    def deconnecter(self):
        """Ferme proprement la connexion."""
        try:
            if self._pool is not None:
                self._pool.disconnect()
        except Exception:
            pass
        finally:
            self._pool = None
            self._api = None

    @property
    def connecte(self) -> bool:
        return self._api is not None

    def _api_ou_erreur(self):
        if self._api is None:
            raise MikroTikErreur("Non connecté au routeur MikroTik")
        return self._api

    # ── Utilisateurs hotspot ──────────────────────────────────────────────────

    def ajouter_utilisateur_hotspot(
        self,
        code: str,
        password: str,
        profil: str,
        duree_min: int | None = None,
        *,
        server: str = "all",
    ) -> dict:
        """Crée un compte hotspot sur le routeur.

        Args:
            code        — login de connexion (ex : "ABC-1234")
            password    — mot de passe
            profil      — nom du profil hotspot sur le routeur
            duree_min   — durée de session max en minutes (None = illimité)
            server      — nom du serveur hotspot ("all" par défaut)

        Returns:
            dict avec l'id RouterOS du compte créé
        """
        api = self._api_ou_erreur()
        kwargs: dict[str, str] = {
            "name":     code,
            "password": password,
            "profile":  profil,
            "server":   server,
        }
        if duree_min is not None:
            kwargs["limit-uptime"] = _minutes_vers_timeout(duree_min)

        try:
            ressource = api.get_resource("/ip/hotspot/user")
            result = ressource.add(**kwargs)
            logger.info("Utilisateur hotspot créé : %s (profil=%s)", code, profil)
            return {"id": result, "code": code}
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de créer l'utilisateur '{code}': {exc}") from exc

    def supprimer_utilisateur_hotspot(self, code: str) -> bool:
        """Supprime un compte hotspot par son login. Retourne True si trouvé et supprimé."""
        api = self._api_ou_erreur()
        try:
            ressource = api.get_resource("/ip/hotspot/user")
            utilisateurs = ressource.get(name=code)
            if not utilisateurs:
                logger.warning("Utilisateur hotspot introuvable : %s", code)
                return False
            ressource.remove(id=utilisateurs[0]["id"])
            logger.info("Utilisateur hotspot supprimé : %s", code)
            return True
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de supprimer '{code}': {exc}") from exc

    # ── Sessions actives ─────────────────────────────────────────────────────

    def obtenir_sessions_actives(self) -> list[dict]:
        """Retourne la liste des sessions hotspot actuellement actives.

        Chaque dict contient les clés RouterOS : id, user, address,
        mac-address, uptime, session-time, server, etc.
        """
        api = self._api_ou_erreur()
        try:
            return api.get_resource("/ip/hotspot/active").get()
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de lire les sessions actives: {exc}") from exc

    def obtenir_connexions_actives_par_code(self) -> dict[str, int]:
        """Retourne {code utilisateur: secondes_connectees} pour les sessions actives."""
        sessions = self.obtenir_sessions_actives()
        return {
            s.get("user"): _parse_uptime(s.get("uptime"))
            for s in sessions
            if s.get("user")
        }

    def deconnecter_utilisateur(self, mac_address: str) -> bool:
        """Force la déconnexion d'un utilisateur par son adresse MAC.

        Retourne True si une session a été trouvée et supprimée.
        """
        api = self._api_ou_erreur()
        try:
            actifs = api.get_resource("/ip/hotspot/active").get()
            sessions = [s for s in actifs if s.get("mac-address") == mac_address]
            if not sessions:
                return False
            ressource = api.get_resource("/ip/hotspot/active")
            for s in sessions:
                ressource.remove(id=s["id"])
            logger.info("Session déconnectée : %s", mac_address)
            return True
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de déconnecter {mac_address}: {exc}") from exc

    # ── Profils ───────────────────────────────────────────────────────────────

    def lister_profils(self) -> list[dict]:
        """Retourne les profils hotspot définis sur le routeur."""
        api = self._api_ou_erreur()
        try:
            return api.get_resource("/ip/hotspot/user/profile").get()
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de lister les profils: {exc}") from exc

    def creer_profil(
        self,
        nom: str,
        debit_max_kbps: int | None = None,
        *,
        session_timeout_min: int | None = None,
    ) -> dict:
        """Crée un profil hotspot sur le routeur.

        Args:
            nom               — nom du profil (doit être unique)
            debit_max_kbps    — limite de bande passante en Kbps (None = illimité)
            session_timeout_min — durée max de session en minutes (None = illimité)
        """
        api = self._api_ou_erreur()
        kwargs: dict[str, str] = {"name": nom}
        if debit_max_kbps is not None:
            rate = f"{debit_max_kbps}k"
            kwargs["rate-limit"] = f"{rate}/{rate}"
        if session_timeout_min is not None:
            kwargs["session-timeout"] = _minutes_vers_timeout(session_timeout_min)

        try:
            ressource = api.get_resource("/ip/hotspot/user/profile")
            result = ressource.add(**kwargs)
            logger.info("Profil hotspot créé : %s", nom)
            return {"id": result, "nom": nom}
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de créer le profil '{nom}': {exc}") from exc

    def supprimer_profil(self, nom: str) -> bool:
        """Supprime un profil hotspot par son nom."""
        api = self._api_ou_erreur()
        try:
            ressource = api.get_resource("/ip/hotspot/user/profile")
            profils = ressource.get(name=nom)
            if not profils:
                return False
            ressource.remove(id=profils[0]["id"])
            logger.info("Profil hotspot supprimé : %s", nom)
            return True
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de supprimer le profil '{nom}': {exc}") from exc

    # ── Snapshot tableau de bord ──────────────────────────────────────────────

    def obtenir_stats_dashboard(self) -> dict:
        """Snapshot complet pour le tableau de bord.

        Ne tente PAS de se reconnecter — c'est la responsabilité du
        DashboardController (qui connaît les credentials de la zone active).
        Retourne un snapshot vide si non connecté.
        """
        if not self.connecte:
            return self._snapshot_vide()

        try:
            api = self._api_ou_erreur()
            sessions_raw = api.get_resource("/ip/hotspot/active").get()
            debit_down, debit_up = self._calculer_debit(api)
            latence = self._mesurer_latence()

            return {
                "connecte":           True,
                "appareils_connectes": len(sessions_raw),
                "debit_descendant":   debit_down,
                "debit_montant":      debit_up,
                "latence":            latence,
                "sessions":           [self._formater_session(s) for s in sessions_raw],
            }
        except Exception as exc:
            logger.error("Dashboard snapshot échoué : %s", exc)
            self._api = None
            self._pool = None
            return self._snapshot_vide()

    @staticmethod
    def _snapshot_vide() -> dict:
        return {
            "connecte":           False,
            "appareils_connectes": 0,
            "debit_descendant":   0.0,
            "debit_montant":      0.0,
            "latence":            -1,
            "sessions":           [],
        }

    @staticmethod
    def _formater_session(s: dict) -> dict:
        user    = s.get("user", "")
        address = s.get("address", "")
        uptime  = s.get("uptime", "")
        detail  = f"IP {address}"
        if uptime:
            detail += f"  ·  {uptime}"
        return {
            "nom_appareil":  user if user else "Inconnu",
            "mac_address":   s.get("mac-address", ""),
            "type_appareil": detail,
            "debit_actuel":  0,
            "est_connecte":  True,
            "est_identifie": bool(user),
        }

    def _calculer_debit(self, api, interface: str = "ether1") -> tuple[float, float]:
        """Débit instantané sur l'interface WAN en Mb/s (megabits/s).

        Premier appel retourne (0, 0) — le delta se calcule au suivant.
        """
        try:
            ifaces = api.get_resource("/interface").get(name=interface)
            if not ifaces:
                return 0.0, 0.0
            rx = int(ifaces[0].get("rx-byte", 0))
            tx = int(ifaces[0].get("tx-byte", 0))
            now = time.monotonic()

            prev = self._prev_stats.get(interface)
            self._prev_stats[interface] = (rx, tx, now)

            if prev is None:
                return 0.0, 0.0

            prev_rx, prev_tx, prev_ts = prev
            dt = now - prev_ts
            if dt <= 0:
                return 0.0, 0.0

            # bytes/s → megabits/s (* 8 / 1_000_000)
            down = max(0.0, (rx - prev_rx) * 8 / dt / 1_000_000)
            up   = max(0.0, (tx - prev_tx) * 8 / dt / 1_000_000)
            return round(down, 1), round(up, 1)
        except Exception:
            return 0.0, 0.0

    def _mesurer_latence(self) -> int:
        """Latence de l'API RouterOS en millisecondes.

        Mesure le temps d'un appel réel (/system/identity) sur la connexion
        existante — plus fiable qu'une nouvelle connexion TCP sur le port 8728.
        """
        if self._api is None:
            return -1
        try:
            t0 = time.monotonic()
            self._api.get_resource("/system/identity").get()
            return int((time.monotonic() - t0) * 1000)
        except Exception:
            return -1


# ── Détection des MikroTik sur le réseau local ──────────────────────────────

_PORT_API_DEFAUT = 8728


def detecter_mikrotiks(timeout: float = 0.4, duree_max: float = 8.0) -> list[dict]:
    """Scanne le réseau local et retourne les équipements avec le port API RouterOS ouvert.

    Chaque dict retourné contient la clé ``adresse_ip``. Le scan ne dépasse pas
    ``duree_max`` secondes, même si certains hôtes ne répondent pas.
    """
    candidats: set[str] = set()
    for ip, masque in _adresses_ip_locales():
        if not _adresse_scannable(ip):
            continue
        candidats.update(_hotes_du_sous_reseau(ip, masque))

    ip_sortante = _ip_locale_sortante()
    if ip_sortante:
        candidats.discard(ip_sortante)

    resultats: list[dict] = []
    if not candidats:
        return resultats

    nb_travailleurs = min(96, len(candidats))
    with ThreadPoolExecutor(max_workers=nb_travailleurs) as pool:
        futures = {
            pool.submit(_port_ouvert, h, _PORT_API_DEFAUT, timeout): h
            for h in candidats
        }
        try:
            for future in as_completed(futures, timeout=duree_max):
                if future.result():
                    resultats.append({"adresse_ip": futures[future]})
        except TimeoutError:
            pass

    return sorted(resultats, key=lambda d: tuple(int(p) for p in d["adresse_ip"].split(".")))


def _adresses_ip_locales() -> list[tuple[str, str]]:
    """Retourne les couples (ip, masque) des interfaces locales, sans dépendre de la langue."""

    def _ip_sortante() -> str | None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return None
        finally:
            s.close()

    adresses: list[tuple[str, str]] = []
    try:
        sortie = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=5
        ).stdout
    except Exception:
        sortie = ""

    ip_actuel: str | None = None
    for ligne in sortie.splitlines():
        m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ligne)
        if not m:
            continue
        valeur = m.group(1)
        bas = ligne.lower()
        if any(mot in bas for mot in ("ipv4", "adresse ip", "ip address")):
            ip_actuel = valeur
        elif any(mot in bas for mot in ("masque", "mask")):
            if ip_actuel:
                adresses.append((ip_actuel, valeur))
            ip_actuel = None

    if not adresses:
        ip = _ip_sortante()
        if ip:
            adresses.append((ip, "255.255.255.0"))
    return adresses


def _ip_locale_sortante() -> str | None:
    """IP de la machine vue depuis le réseau (passerelle par défaut)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def _hotes_du_sous_reseau(ip: str, netmask: str, max_hotes: int = 4096) -> list[str]:
    """Toutes les adresses hôtes (hors réseau/broadcast) du sous-réseau.

    Pour les grands sous-réseaux (> 4096 hôtes), seules les premières adresses
    sont scannées afin de borner la durée de détection.
    """
    try:
        reseau = ipaddress.ip_network(f"{ip}/{netmask}", strict=False)
    except ValueError:
        return []
    hotes = reseau.hosts()
    if reseau.prefixlen < 20:
        hotes = list(hotes)[:max_hotes]
    return [str(h) for h in hotes]


def _adresse_scannable(ip: str) -> bool:
    """Vraie si l'adresse est privée et susceptible d'héberger un routeur LAN."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if a.is_loopback or a.is_link_local or a.is_multicast or a.is_unspecified:
        return False
    return a.is_private


def _port_ouvert(ip: str, port: int, timeout: float) -> bool:
    """Connecte en non-bloquant : ne dépasse jamais `timeout` sur Windows."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(False)
    try:
        s.connect_ex((ip, port))
        _, pret, _ = select.select([], [s], [], timeout)
        if not pret:
            return False
        return s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) == 0
    except Exception:
        return False
    finally:
        s.close()
