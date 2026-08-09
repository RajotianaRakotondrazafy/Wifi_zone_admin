from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget

from controllers.blocages.blocages_controller import BlocagesController
from controllers.dashboard.dashboard_controller import DashboardController
from controllers.parametres.parametres_controller import ParametresController
from controllers.rapports.rapports_controller import RapportsController
from controllers.statistiques.statistiques_controller import StatistiquesController
from controllers.utilisateurs.utilisateurs_controller import UtilisateursController
from controllers.ventes.ventes_controller import VentesController
from controllers.zones.zones_controller import ZonesController
from models.user import User
from services.theme import charger_theme
from views.dashboard.components.sidebar import Sidebar
from views.dashboard.pages.tableau_de_bord_page import TableauDeBordPage
from views.dashboard.pages.ventes_page import VentesPage
from views.dashboard.pages.utilisateurs_page import UtilisateursPage
from views.dashboard.pages.zones_wifi_page import ZonesWifiPage
from views.dashboard.pages.statistiques_page import StatistiquesPage
from views.dashboard.pages.rapports_page import RapportsPage
from views.dashboard.pages.blocages_page import BlocagesPage
from views.dashboard.pages.parametres_page import ParametresPage


class DashboardView(QWidget):
    deconnexion_demandee = pyqtSignal()

    def __init__(self, current_user: User, dashboard_controller: DashboardController, parent=None):
        super().__init__(parent)
        self._utilisateur        = current_user
        self._controller         = dashboard_controller
        self._ventes_controller  = VentesController()
        self._zones_controller   = ZonesController()
        self._utilisateurs_controller = UtilisateursController()
        self._statistiques_controller = StatistiquesController()
        self._rapports_controller     = RapportsController()
        self._blocages_controller     = BlocagesController()
        self._parametres_controller   = ParametresController()

        self.setWindowTitle("E-Konnekta — Tableau de bord")
        self.setMinimumSize(1100, 680)

        self._construire_interface()
        self._appliquer_theme()
        self._centrer_sur_ecran()

    def _construire_interface(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ─────────────────────────────────────────────────────
        self._sidebar = Sidebar()
        self._sidebar.item_selectionne.connect(self._naviguer)
        self._sidebar.deconnexion_demandee.connect(self.deconnexion_demandee.emit)
        layout.addWidget(self._sidebar)

        # ── Pages ───────────────────────────────────────────────────────
        self._stacked = QStackedWidget()
        self._stacked.setObjectName("zoneContenu")

        self._pages: dict[str, QWidget] = {
            "Tableau de bord": TableauDeBordPage(self._controller, self._blocages_controller),
            "Ventes":          VentesPage(self._ventes_controller, self._utilisateur),
            "Utilisateurs":    UtilisateursPage(self._utilisateurs_controller, self._utilisateur),
            "Zones WiFi":      ZonesWifiPage(self._zones_controller),
            "Statistiques":    StatistiquesPage(self._statistiques_controller),
            "Rapports":        RapportsPage(self._rapports_controller),
            "Blocages":        BlocagesPage(self._blocages_controller),
            "Paramètres":      ParametresPage(self._parametres_controller),
        }

        for page in self._pages.values():
            self._stacked.addWidget(page)

        layout.addWidget(self._stacked)

    def _naviguer(self, section: str):
        if section in self._pages:
            self._stacked.setCurrentWidget(self._pages[section])
            self.setWindowTitle(f"E-Konnekta — {section}")

    def _appliquer_theme(self):
        try:
            self.setStyleSheet(charger_theme())
        except FileNotFoundError:
            pass

    def _centrer_sur_ecran(self):
        ecran = self.screen().availableGeometry()
        x = (ecran.width() - self.width()) // 2
        y = (ecran.height() - self.height()) // 2
        self.move(x, y)
