import logging
from datetime import datetime

from models.blocage import Blocage
from repositories.blocage_repository import BlocageRepository
from repositories.router_repository import RouterRepository
from services.mikrotik_service import MikroTikService

logger = logging.getLogger(__name__)


class BlocagesController:
    """Blocage/déblocage d'appareils : persistance + application sur le routeur."""

    def __init__(self):
        self._blocage_repo = BlocageRepository()
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

    def _connecter(self, svc: MikroTikService) -> bool:
        routeur = self._routeur_actif()
        if routeur is None or not (
            routeur.adresse_ip and routeur.username and routeur.password_chiffre
        ):
            return False
        return svc.connecter_routeur(
            routeur.adresse_ip, routeur.username, routeur.password_chiffre,
            routeur.port_api or 8728,
        )

    # ── Actions ───────────────────────────────────────────────────────────

    def bloquer_appareil(self, donnees: dict) -> dict:
        """Bloque un appareil : règle ip-binding sur le routeur puis persistance.

        Retourne un dict avec ``ok`` et ``message``.
        """
        mac = (donnees.get("mac_address") or "").strip().upper()
        if not mac:
            return {"ok": False, "message": "Adresse MAC manquante — blocage impossible."}

        svc = MikroTikService()
        if not self._connecter(svc):
            return {
                "ok": False,
                "message": "Routeur injoignable. Vérifiez la configuration de la zone active.",
            }
        try:
            if not svc.bloquer_appareil(mac):
                return {"ok": False, "message": "Le routeur a refusé le blocage."}
        finally:
            svc.deconnecter()

        if self._blocage_repo.trouver_par_mac(mac) is None:
            nom = (
                donnees.get("nom_hote")
                or donnees.get("nom_appareil")
                or "Appareil inconnu"
            )
            self._blocage_repo.creer(Blocage(
                mac_address=mac,
                nom=nom,
                ip_assignee=donnees.get("adresse_ip", ""),
                raison="Bloqué manuellement",
                date_blocage=datetime.now(),
            ))
        return {"ok": True, "message": f"Appareil {mac} bloqué."}

    def debloquer_appareil(self, blocage_id: int) -> dict:
        """Retire le blocage du routeur puis supprime la ligne."""
        blocage = self._blocage_repo.obtenir_par_id(blocage_id)
        if blocage is None:
            return {"ok": False, "message": "Blocage introuvable."}

        svc = MikroTikService()
        if not self._connecter(svc):
            return {
                "ok": False,
                "message": "Routeur injoignable — le blocage est conservé.",
            }
        try:
            svc.debloquer_appareil(blocage.mac_address)
        finally:
            svc.deconnecter()

        self._blocage_repo.supprimer(blocage.id)
        return {"ok": True, "message": f"Appareil {blocage.mac_address} débloqué."}

    # ── Lecture ───────────────────────────────────────────────────────────

    def lister(self) -> list[dict]:
        return [b.to_dict() for b in self._blocage_repo.lister_tous()]
