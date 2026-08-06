import logging
from datetime import datetime, timedelta

from models.session import Session
from repositories.router_repository import RouterRepository
from repositories.session_repository import SessionRepository
from repositories.ticket_repository import TicketRepository
from services.mikrotik_service import MikroTikService, _parse_uptime

logger = logging.getLogger(__name__)


class StatistiquesController:
    """Statistiques réseau : enregistrement des sessions depuis le routeur + agrégats."""

    def __init__(self):
        self._session_repo = SessionRepository()
        self._ticket_repo = TicketRepository()
        self._router_repo = RouterRepository()

    # ── Routeur ───────────────────────────────────────────────────────────

    def _routeur_actif(self):
        try:
            routeurs = self._router_repo.lister_tous()
        except Exception:
            return None
        for r in routeurs:
            if getattr(r, "statut", "") == "actif":
                return r
        return routeurs[0] if routeurs else None

    # ── Enregistrement ────────────────────────────────────────────────────

    def enregistrer_sessions_actives(self) -> dict:
        """Capture les sessions actives du routeur dans la table sessions.

        Crée une session ouverte, met à jour les volumes/durée à chaque scan,
        et clôture les sessions disparues de /ip/hotspot/active.
        """
        routeur = self._routeur_actif()
        if routeur is None or not (
            routeur.adresse_ip and routeur.username and routeur.password_chiffre
        ):
            return {"connecte": False, "sessions": 0}

        svc = MikroTikService()
        try:
            if not svc.connecter_routeur(
                routeur.adresse_ip, routeur.username, routeur.password_chiffre,
                routeur.port_api or 8728,
            ):
                return {"connecte": False, "sessions": 0}
            actives = svc.obtenir_sessions_actives()
            hostnames = svc.obtenir_hostnames()
        except Exception as exc:
            logger.warning("Capture des sessions échouée : %s", exc)
            return {"connecte": False, "sessions": 0}
        finally:
            svc.deconnecter()

        conserves: list[int] = []
        for s in actives:
            code = s.get("user")
            if not code:
                continue
            ticket = self._ticket_repo.get_ticket_by_code(code)
            if ticket is None:
                continue

            mac      = (s.get("mac-address") or "").upper()
            if not mac:
                continue

            octets_envoyes = max(0, int(s.get("bytes-in", 0)))
            octets_recus   = max(0, int(s.get("bytes-out", 0)))
            duree_reelle   = _parse_uptime(s.get("uptime"))
            nom_hote       = hostnames.get(mac, "")

            existante = self._session_repo.obtenir_ouverte(ticket.id, mac)
            if existante is not None:
                existante.ip_assignee    = s.get("address", "")
                existante.octets_envoyes = max(existante.octets_envoyes, octets_envoyes)
                existante.octets_recus   = max(existante.octets_recus, octets_recus)
                existante.duree_reelle   = duree_reelle
                existante.nom_hote       = nom_hote or existante.nom_hote
                self._session_repo.mettre_a_jour(existante)
                conserves.append(existante.id)
            else:
                session = Session(
                    ticket_id=ticket.id,
                    mac_address=mac,
                    ip_assignee=s.get("address", ""),
                    date_debut=datetime.now() - timedelta(seconds=duree_reelle),
                    octets_envoyes=octets_envoyes,
                    octets_recus=octets_recus,
                    duree_reelle=duree_reelle,
                    nom_hote=nom_hote,
                )
                self._session_repo.creer(session)
                conserves.append(session.id)

        self._session_repo.fermer_les_autres(conserves, date_fin=datetime.now())
        return {"connecte": True, "sessions": len(actives)}

    # ── Agrégats ──────────────────────────────────────────────────────────

    def stats_du_jour(self) -> dict:
        jour = datetime.now().date().isoformat()
        s = self._session_repo.statistiques_journalieres(jour)
        return {
            "nb_sessions":        s["nb_sessions"],
            "volume_recu_octets": s["volume_recu"],
            "duree_moyenne_min":  round(s["duree_moyenne"] / 60.0, 1),
        }

    def activite_du_jour(self) -> list[int]:
        return self._session_repo.activite_du_jour(datetime.now().date().isoformat())

    def top_consommateurs(self, limite: int = 5) -> list[dict]:
        return self._session_repo.top_consommateurs(
            datetime.now().date().isoformat(), limite
        )

    def snapshot_complet(self) -> dict:
        """Enregistre puis renvoie toutes les données de la page Statistiques."""
        capture = self.enregistrer_sessions_actives()
        return {
            "connecte": capture["connecte"],
            "sessions_actives": capture["sessions"],
            "stats":  self.stats_du_jour(),
            "activite": self.activite_du_jour(),
            "top":    self.top_consommateurs(),
        }
