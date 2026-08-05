import time
import logging
from typing import Any

from repositories.router_repository import RouterRepository
from services.mikrotik_service import MikroTikService

logger = logging.getLogger(__name__)

# Délai minimum entre deux tentatives de connexion échouées
_BACKOFF = 30.0


class DashboardController:
    def __init__(self):
        self._mikrotik    = MikroTikService()
        self._router_repo = RouterRepository()
        self._echec_ts    = 0.0   # timestamp du dernier échec de connexion

    def _routeur_actif(self):
        try:
            routeurs = self._router_repo.lister_tous()
        except Exception:
            return None
        for r in routeurs:
            if getattr(r, "statut", "") == "actif":
                return r
        return routeurs[0] if routeurs else None

    def _tenter_connexion(self) -> bool:
        if time.monotonic() - self._echec_ts < _BACKOFF:
            return False

        routeur = self._routeur_actif()
        if routeur is None:
            logger.warning("Aucun routeur configuré dans Zones WiFi.")
            self._echec_ts = time.monotonic()
            return False

        if not (routeur.adresse_ip and routeur.username and routeur.password_chiffre):
            logger.warning(
                "Routeur « %s » incomplet (IP/user/password manquants).", routeur.nom
            )
            self._echec_ts = time.monotonic()
            return False

        ok = self._mikrotik.connecter_routeur(
            routeur.adresse_ip,
            routeur.username,
            routeur.password_chiffre,
            routeur.port_api or 8728,
        )
        if not ok:
            self._echec_ts = time.monotonic()
        return ok

    def obtenir_donnees_dashboard(self) -> dict[str, Any]:
        """Retourne un snapshot en temps réel depuis le MikroTik actif."""
        if not self._mikrotik.connecte:
            self._tenter_connexion()

        snap = self._mikrotik.obtenir_stats_dashboard()

        return {
            "connecte": snap["connecte"],
            "statistiques": {
                "appareils_connectes": snap["appareils_connectes"],
                "appareils_max":       0,
                "debit_descendant":    snap["debit_descendant"],
                "debit_montant":       snap["debit_montant"],
                "latence":             snap["latence"],
            },
            "sessions_actives": snap["sessions"],
        }
