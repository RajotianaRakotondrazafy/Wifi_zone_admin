import time
import logging
from datetime import datetime
from typing import Any

from repositories.router_repository import RouterRepository
from repositories.sale_repository import SaleRepository
from services.mikrotik_service import MikroTikService
from controllers.stock.stock_controller import StockController

logger = logging.getLogger(__name__)

# Délai minimum entre deux tentatives de connexion échouées
_BACKOFF = 30.0


class DashboardController:
    def __init__(self):
        self._mikrotik    = MikroTikService()
        self._router_repo = RouterRepository()
        self._sale_repo   = SaleRepository()
        self._stock_ctrl  = StockController()
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

    def bloquer_session(self, session_id: str) -> bool:
        return self._mikrotik.bloquer_session(session_id)

    def limiter_session(self, adresse_ip: str, debit_ko: int) -> bool:
        return self._mikrotik.limiter_session(adresse_ip, debit_ko)

    def _totaux_du_jour(self) -> dict:
        try:
            return self._sale_repo.agreger_par_date(datetime.now().date().isoformat())
        except Exception:
            return {"nb_ventes": 0, "ca_total": 0, "nb_actifs": 0}

    def _produits_du_jour(self) -> dict:
        try:
            return self._stock_ctrl.total_du_jour()
        except Exception:
            return {"nb_ventes": 0, "nb_articles": 0, "ca_total": 0}

    def obtenir_donnees_dashboard(self) -> dict[str, Any]:
        """Retourne un snapshot en temps réel depuis le MikroTik actif."""
        if not self._mikrotik.connecte:
            self._tenter_connexion()

        snap    = self._mikrotik.obtenir_stats_dashboard()
        totaux  = self._totaux_du_jour()
        produits = self._produits_du_jour()

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
            "ventes": {
                "nb_ventes": totaux["nb_ventes"],
                "ca_total":  int(totaux["ca_total"]),
            },
            "produits": {
                "nb_ventes":   produits["nb_ventes"],
                "nb_articles": produits["nb_articles"],
                "ca_total":    int(produits["ca_total"]),
            },
        }
