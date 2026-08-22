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


def _parse_temps_restant(texte: str | None) -> int:
    """Convertit session-time-left RouterOS en secondes.

    Gère les formats : '00:05:00' (HH:MM:SS), '5:30' (MM:SS),
    '5m30s' (uptime) et '0s'.
    """
    if not texte:
        return 0
    if ":" in texte:
        parties = texte.split(":")
        try:
            valeurs = [int(p) for p in parties]
            if len(valeurs) == 3:
                return valeurs[0] * 3600 + valeurs[1] * 60 + valeurs[2]
            if len(valeurs) == 2:
                return valeurs[0] * 60 + valeurs[1]
        except ValueError:
            pass
    return _parse_uptime(texte)


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
        # {nom_interface: (rx_bytes, tx_bytes, monotonic_ts)} pour calcul débit interface
        self._prev_stats: dict[str, tuple[int, int, float]] = {}
        # {mac_address: (bytes_in, bytes_out, monotonic_ts)} pour calcul débit par session
        self._prev_sessions: dict[str, tuple[int, int, float]] = {}

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
        if duree_min:   # 0 ou None = pas de limite (session libre)
            kwargs["limit-uptime"] = _minutes_vers_timeout(duree_min)

        try:
            ressource = api.get_resource("/ip/hotspot/user")
            result = ressource.add(**kwargs)
            logger.info("Utilisateur hotspot créé : %s (profil=%s)", code, profil)
            return {"id": result, "code": code}
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de créer l'utilisateur '{code}': {exc}") from exc

    def lister_utilisateurs_hotspot(self) -> list[str]:
        """Retourne les noms de tous les comptes hotspot présents sur le routeur."""
        api = self._api_ou_erreur()
        try:
            users = api.get_resource("/ip/hotspot/user").get()
            return [u.get("name", "") for u in users if u.get("name")]
        except Exception as exc:
            raise MikroTikErreur(f"Impossible de lister les utilisateurs: {exc}") from exc

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

    def obtenir_hostnames(self) -> dict[str, str]:
        """Retourne {MAC_UPPER: hostname} depuis les baux DHCP actifs."""
        api = self._api_ou_erreur()
        return self._obtenir_hostnames(api)

    def obtenir_temps_restants_sessions(self) -> dict[str, int]:
        if not self.connecte:
            return {}
        try:
            api = self._api_ou_erreur()
            sessions = api.get_resource("/ip/hotspot/active").get()
            result = {}
            for s in sessions:
                user      = s.get("user", "")
                time_left = s.get("session-time-left", "")
                if user and time_left:
                    secondes = _parse_temps_restant(time_left)
                    if secondes > 0:
                        result[user] = secondes
            return result
        except Exception as exc:
            logger.warning("Impossible de lire session-time-left : %s", exc)
            return {}

    def deconnecter_par_username(self, username: str) -> bool:
        """Déconnecte la session active ET supprime l'user hotspot (empêche reconnexion).

        Note : routeros_api décode '.id' → 'id' dans les réponses.
        La clé correcte dans les dicts retournés par get() est donc 'id', pas '.id'.
        La méthode remove(id=...) ré-encode 'id' → '.id' avant d'envoyer à RouterOS.
        """
        if not self.connecte:
            logger.warning("deconnecter_par_username(%s) : pas connecté", username)
            return False
        try:
            api = self._api_ou_erreur()

            # 1. Retirer la session active en cours
            toutes_sessions = api.get_resource("/ip/hotspot/active").get()
            cibles = [s for s in toutes_sessions if s.get("user") == username]
            logger.info("Sessions actives trouvées pour '%s' : %d / %d",
                        username, len(cibles), len(toutes_sessions))
            res_active = api.get_resource("/ip/hotspot/active")
            for s in cibles:
                sid = s.get("id", "")
                logger.info("Suppression session active id=%s", sid)
                res_active.remove(id=sid)

            # 2. Supprimer l'entrée dans /ip/hotspot/user pour bloquer la reconnexion
            all_users = api.get_resource("/ip/hotspot/user").get()
            cibles_user = [u for u in all_users if u.get("name") == username]
            logger.info("Users hotspot trouvés pour '%s' : %d", username, len(cibles_user))
            res_user = api.get_resource("/ip/hotspot/user")
            for u in cibles_user:
                uid = u.get("id", "")
                logger.info("Suppression user hotspot id=%s", uid)
                res_user.remove(id=uid)

            return True
        except Exception as exc:
            logger.error("Déconnexion %s échouée : %s", username, exc)
            return False

    def deconnecter_utilisateur(self, mac_address: str) -> bool:
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
        shared_users: int = 1,
    ) -> dict:
        """Crée un profil hotspot sur le routeur.

        Args:
            nom                 — nom du profil (doit être unique)
            debit_max_kbps      — limite de bande passante en Kbps (None = illimité)
            session_timeout_min — durée max de session en minutes (None = illimité)
            shared_users        — nb max d'appareils simultanés sur le même identifiant
        """
        api = self._api_ou_erreur()
        kwargs: dict[str, str] = {"name": nom}
        if debit_max_kbps is not None:
            rate = f"{debit_max_kbps}k"
            kwargs["rate-limit"] = f"{rate}/{rate}"
        if session_timeout_min is not None and session_timeout_min > 0:
            kwargs["session-timeout"] = _minutes_vers_timeout(session_timeout_min)
        if shared_users > 1:
            kwargs["shared-users"] = str(shared_users)

        try:
            ressource = api.get_resource("/ip/hotspot/user/profile")
            result = ressource.add(**kwargs)
            logger.info("Profil hotspot créé : %s (shared-users=%d)", nom, shared_users)
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
            now = time.monotonic()

            hostnames = self._obtenir_hostnames(api)
            sessions = []
            for s in sessions_raw:
                mac = s.get("mac-address", "")
                b_in  = int(s.get("bytes-in",  0))
                b_out = int(s.get("bytes-out", 0))
                prev = self._prev_sessions.get(mac)
                self._prev_sessions[mac] = (b_in, b_out, now)
                if prev is not None:
                    p_in, p_out, p_ts = prev
                    dt = now - p_ts
                    s_down = max(0.0, (b_out - p_out) / dt) if dt > 0 else 0.0
                    s_up   = max(0.0, (b_in  - p_in)  / dt) if dt > 0 else 0.0
                else:
                    s_down = s_up = 0.0
                nom_hote = hostnames.get(mac.upper(), "")
                sessions.append(self._formater_session(s, s_down, s_up, nom_hote))

            return {
                "connecte":           True,
                "appareils_connectes": len(sessions_raw),
                "debit_descendant":   debit_down,
                "debit_montant":      debit_up,
                "latence":            latence,
                "sessions":           sessions,
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
    def _formater_session(
        s: dict,
        debit_down: float = 0.0,
        debit_up: float = 0.0,
        nom_hote: str = "",
    ) -> dict:
        user    = s.get("user", "")
        address = s.get("address", "")
        uptime  = s.get("uptime", "")
        detail  = f"IP {address}"
        if uptime:
            detail += f"  ·  {uptime}"
        return {
            "nom_appareil":  user if user else "Inconnu",
            "nom_hote":      nom_hote,
            "mac_address":   s.get("mac-address", ""),
            "adresse_ip":    address,
            "session_id":    s.get("id", ""),
            "type_appareil": detail,
            "debit_down":    debit_down,
            "debit_up":      debit_up,
            "est_connecte":  True,
            "est_identifie": bool(user),
        }

    def _obtenir_hostnames(self, api) -> dict[str, str]:
        """Retourne {MAC_UPPER: hostname} depuis les baux DHCP actifs."""
        try:
            leases = api.get_resource("/ip/dhcp-server/lease").get()
            return {
                lease.get("mac-address", "").upper(): lease.get("host-name", "")
                for lease in leases
                if lease.get("host-name")
            }
        except Exception:
            return {}

    def bloquer_session(self, session_id: str) -> bool:
        """Déconnecte une session hotspot active (par son .id RouterOS)."""
        try:
            api = self._api_ou_erreur()
            api.get_resource("/ip/hotspot/active").remove(id=session_id)
            return True
        except Exception as exc:
            logger.error("Blocage session %s échoué : %s", session_id, exc)
            return False

    def bloquer_appareil(self, mac_address: str) -> bool:
        """Bloque durablement un appareil au hotspot.

        Ajoute une règle /ip/hotspot/ip-binding type=blocked (empêche toute
        reconnexion) puis déconnecte ses sessions actives.
        """
        if not mac_address:
            return False
        try:
            api = self._api_ou_erreur()
            binding = api.get_resource("/ip/hotspot/ip-binding")
            existants = binding.get(mac_address=mac_address)
            if not existants:
                binding.add(mac_address=mac_address, type="blocked")
            actifs = api.get_resource("/ip/hotspot/active").get()
            ressource_active = api.get_resource("/ip/hotspot/active")
            for s in actifs:
                if s.get("mac-address") == mac_address:
                    ressource_active.remove(id=s.get("id", ""))
            logger.info("Appareil bloqué au hotspot : %s", mac_address)
            return True
        except Exception as exc:
            logger.error("Blocage appareil %s échoué : %s", mac_address, exc)
            return False

    def debloquer_appareil(self, mac_address: str) -> bool:
        """Retire le blocage /ip/hotspot/ip-binding d'un appareil."""
        if not mac_address:
            return False
        try:
            api = self._api_ou_erreur()
            binding = api.get_resource("/ip/hotspot/ip-binding")
            existants = binding.get(mac_address=mac_address)
            for e in existants:
                binding.remove(id=e["id"])
            logger.info("Appareil débloqué au hotspot : %s", mac_address)
            return bool(existants)
        except Exception as exc:
            logger.error("Déblocage appareil %s échoué : %s", mac_address, exc)
            return False

    def limiter_session(self, adresse_ip: str, debit_ko: int) -> bool:
        """Applique ou met à jour une Simple Queue sur l'IP cliente (Ko/s symétrique)."""
        try:
            api = self._api_ou_erreur()
            queues = api.get_resource("/queue/simple")
            nom   = f"ekonnekta-{adresse_ip}"
            rate  = f"{debit_ko}k/{debit_ko}k"
            existantes = queues.get(name=nom)
            if existantes:
                queues.set(id=existantes[0]["id"], max_limit=rate)
            else:
                queues.add(name=nom, target=f"{adresse_ip}/32", max_limit=rate)
            return True
        except Exception as exc:
            logger.error("Limitation %s à %dKo/s échouée : %s", adresse_ip, debit_ko, exc)
            return False

    def _calculer_debit(self, api, interface: str = "ether1") -> tuple[float, float]:
        """Débit instantané sur l'interface WAN en octets/s.

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

            down = max(0.0, (rx - prev_rx) / dt)
            up   = max(0.0, (tx - prev_tx) / dt)
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
