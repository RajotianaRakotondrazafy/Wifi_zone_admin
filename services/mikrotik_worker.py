from PyQt6.QtCore import QThread, pyqtSignal


class WorkerDashboard(QThread):
    """Thread de fond : passe par le contrôleur (backoff + connexion inclus).

    Émet ``donnees_prete`` avec le dict snapshot dès que la requête est terminée.
    Un seul worker tourne à la fois (le dashboard vérifie ``isRunning()`` avant
    d'en démarrer un nouveau).
    """

    donnees_prete = pyqtSignal(dict)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller

    def run(self):
        donnees = self._controller.obtenir_donnees_dashboard()
        self.donnees_prete.emit(donnees)
