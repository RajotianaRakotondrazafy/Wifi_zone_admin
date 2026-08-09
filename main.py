import sys, os, logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from database.connection import DatabaseConnection
from database.init_db import initialiser_base
from controllers.auth.auth_controller import AuthController
from controllers.dashboard.dashboard_controller import DashboardController
from views.login.login_view import LoginView
from views.dashboard.dashboard_view import DashboardView
from models.user import User
from services.session import charger_session
from services.backup_service import BackupService

_APP_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_APP_DIR, "app.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class ApplicationManager:
    def __init__(self):
        self.app = QApplication(sys.argv)

        _logo = os.path.join(
            getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
            "assets", "logo.png",
        )
        if os.path.exists(_logo):
            self.app.setWindowIcon(QIcon(_logo))

        self.auth_controller = AuthController()
        self.dashboard_controller = DashboardController()
        self._backup_service = BackupService(parent=self.app)

        self.login_view: LoginView | None = None
        self.dashboard_view: DashboardView | None = None

    def demarrer(self):
        # Mode dev : si une session existe, on repart directement sur le
        # tableau de bord sans repasser par le login (hot-reload).
        if "--dev" in sys.argv:
            user = charger_session()
            if user is not None:
                self.afficher_dashboard(user)
                sys.exit(self.app.exec())
                return
        self.afficher_login()
        sys.exit(self.app.exec())

    def afficher_login(self):
        self.login_view = LoginView(auth_controller=self.auth_controller)
        self.login_view.connexion_reussie.connect(self.afficher_dashboard)
        self.login_view.show()

    def afficher_dashboard(self, user: User):
        from services.session import sauvegarder_session
        sauvegarder_session(user)
        if self.login_view is not None:
            self.login_view.close()
        self.dashboard_view = DashboardView(
            current_user=user,
            dashboard_controller=self.dashboard_controller,
        )
        self.dashboard_view.deconnexion_demandee.connect(self.deconnecter)
        self.dashboard_view.show()
        self._backup_service.demarrer()

    def deconnecter(self):
        from services.session import effacer_session
        self._backup_service.arreter()
        effacer_session()
        if self.dashboard_view is not None:
            self.dashboard_view.close()
            self.dashboard_view = None
        self.afficher_login()


def _initialiser_admin_si_absent() -> None:
    from repositories.user_repository import UserRepository
    from scripts.creer_admin import creer_ou_mettre_a_jour_admin
    try:
        if not UserRepository().lister_tous():
            logger.info("Premier démarrage : création du compte admin par défaut.")
            creer_ou_mettre_a_jour_admin("admin@Ekonnekta", "admin.ekonnekta.2025")
            logger.info("Compte admin créé : admin@Ekonnekta / admin.ekonnekta.2025")
    except Exception as e:
        logger.warning(f"Impossible de créer le compte admin par défaut : {e}")


def main():
    logger.info("Démarrage de l'application WiFi-Zone Manager...")

    try:
        DatabaseConnection()
        initialiser_base()
        _initialiser_admin_si_absent()
        logger.info("Base de données prête.")
    except Exception as e:
        logger.critical(f"Erreur critique lors de l'initialisation de la base : {e}")
        sys.exit(1)

    gestionnaire = ApplicationManager()
    gestionnaire.demarrer()


if __name__ == "__main__":
    main()
