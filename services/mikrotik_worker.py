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
        try:
            donnees = self._controller.obtenir_donnees_dashboard()
        except Exception as exc:
            donnees = {
                "connecte": False,
                "statistiques": {},
                "sessions_actives": [],
                "ventes": {"nb_ventes": 0, "ca_total": 0},
                "erreur": str(exc),
            }
        self.donnees_prete.emit(donnees)


class WorkerZones(QThread):
    """Thread de fond : vérifie l'état de connexion réel de chaque zone.

    Émet ``connexions_prete`` avec le dict {router_id: bool} dès la fin du test.
    Un seul worker tourne à la fois (la page vérifie ``isRunning()`` avant
    d'en démarrer un nouveau).
    """

    connexions_prete = pyqtSignal(dict)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller

    def run(self):
        try:
            etats = self._controller.verifier_connexions()
        except Exception as exc:
            etats = {"erreur": str(exc)}
        self.connexions_prete.emit(etats)
