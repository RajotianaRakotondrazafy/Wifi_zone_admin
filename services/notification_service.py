import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon

logger = logging.getLogger(__name__)

_SEUIL_MINUTES  = 30
_INTERVALLE_MS  = 5 * 60 * 1000   # vérification toutes les 5 minutes


class NotificationService:
    """Surveille les tickets qui expirent bientôt et affiche une notification système."""

    def __init__(self, icon_path: str, parent=None):
        self._tray = QSystemTrayIcon(parent)
        if os.path.exists(icon_path):
            self._tray.setIcon(QIcon(icon_path))
        self._tray.setToolTip("E-Konnekta")

        self._timer = QTimer(parent)
        self._timer.setInterval(_INTERVALLE_MS)
        self._timer.timeout.connect(self._verifier)

        # Codes déjà notifiés — évite de répéter la même alerte
        self._notifies: set[str] = set()

    def demarrer(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("Barre système non disponible — notifications désactivées.")
            return
        self._tray.show()
        self._verifier()
        self._timer.start()

    def arreter(self):
        self._timer.stop()
        self._tray.hide()

    def _nettoyer_expires(self):
        """Supprime les tickets expirés de tous les routeurs et les marque 'epuise' en DB."""
        try:
            from repositories.ticket_repository import TicketRepository
            from repositories.router_repository import RouterRepository
            from services.mikrotik_service import MikroTikService

            repo    = TicketRepository()
            tickets = repo.lister_expires_actifs()
            if not tickets:
                return

            routers = RouterRepository().lister_tous()
            for ticket in tickets:
                for router in routers:
                    svc = MikroTikService()
                    connecte = svc.connecter_routeur(
                        router.adresse_ip,
                        router.username,
                        router.password_chiffre,
                        router.port_api or 8728,
                    )
                    if connecte:
                        try:
                            svc.supprimer_utilisateur_hotspot(ticket.code)
                        except Exception as exc:
                            logger.warning(
                                "Nettoyage MikroTik %s / ticket %s : %s",
                                router.adresse_ip, ticket.code, exc,
                            )
                        finally:
                            svc.deconnecter()
                repo.marquer_cloture(ticket.id)
                logger.info("Ticket expiré nettoyé du routeur : %s", ticket.code)
        except Exception as exc:
            logger.warning("NotificationService._nettoyer_expires : %s", exc)

    def _verifier(self):
        self._nettoyer_expires()
        try:
            from repositories.ticket_repository import TicketRepository
            tickets = TicketRepository().lister_expirant_bientot(_SEUIL_MINUTES)
        except Exception as exc:
            logger.warning("NotificationService._verifier : %s", exc)
            return

        codes_actuels = {t.code for t in tickets}
        # Retirer les codes qui ne sont plus dans la fenêtre d'expiration
        self._notifies &= codes_actuels

        nouveaux = [t for t in tickets if t.code not in self._notifies]
        if not nouveaux:
            return

        for t in nouveaux:
            self._notifies.add(t.code)

        if len(nouveaux) == 1:
            message = (
                f"Le ticket « {nouveaux[0].code} » expire "
                f"dans moins de {_SEUIL_MINUTES} minutes."
            )
        else:
            codes_str = ", ".join(t.code for t in nouveaux[:3])
            suite = f" et {len(nouveaux) - 3} autre(s)" if len(nouveaux) > 3 else ""
            message = f"{codes_str}{suite} expirent dans moins de {_SEUIL_MINUTES} min."

        self._tray.showMessage(
            "⚠ Tickets expirant bientôt",
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            8_000,
        )
        logger.info("Notification expiration envoyée : %s", message)
