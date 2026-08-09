import glob
import logging
import os
import shutil
from datetime import datetime

from PyQt6.QtCore import QTimer

from config.settings import DATABASE_PATH, _chemin_donnees

logger = logging.getLogger(__name__)

_DOSSIER_BACKUPS = _chemin_donnees("backups")
_MAX_BACKUPS     = 7
_INTERVALLE_MS   = 24 * 60 * 60 * 1000  # 24 heures


class BackupService:
    """Sauvegarde automatique de la base toutes les 24h."""

    def __init__(self, parent=None):
        self._timer = QTimer(parent)
        self._timer.setInterval(_INTERVALLE_MS)
        self._timer.timeout.connect(self._executer)

    def demarrer(self) -> None:
        self._executer()   # sauvegarde immédiate au démarrage de session
        self._timer.start()
        logger.info("BackupService : sauvegarde automatique activée (toutes les 24h).")

    def arreter(self) -> None:
        self._timer.stop()

    def _executer(self) -> None:
        try:
            chemin = self._sauvegarder()
            self._nettoyer_anciens()
            logger.info("BackupService : sauvegarde créée → %s", chemin)
        except Exception as exc:
            logger.error("BackupService : échec de la sauvegarde automatique : %s", exc)

    def _sauvegarder(self) -> str:
        os.makedirs(_DOSSIER_BACKUPS, exist_ok=True)
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        chemin = os.path.join(_DOSSIER_BACKUPS, f"auto_{horodatage}.db")
        shutil.copy2(DATABASE_PATH, chemin)
        return chemin

    def _nettoyer_anciens(self) -> None:
        fichiers = sorted(
            glob.glob(os.path.join(_DOSSIER_BACKUPS, "auto_*.db"))
        )
        for vieux in fichiers[:-_MAX_BACKUPS]:
            try:
                os.remove(vieux)
                logger.debug("BackupService : ancien backup supprimé → %s", vieux)
            except OSError:
                pass
