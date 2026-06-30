from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QScrollArea,
)

from controllers.dashboard.dashboard_controller import DashboardController
from models.user import User
from views.dashboard.components.sidebar import Sidebar
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.session_row import SessionRow


CHEMIN_QSS = Path(__file__).resolve().parent.parent / "assets" / "styles" / "dark_theme.qss"


class DashboardView(QWidget):
    def __init__(self, current_user: User, dashboard_controller: DashboardController, parent=None):
        super().__init__(parent)
        self._utilisateur = current_user
        self._controller = dashboard_controller

        self.setWindowTitle("WiFi-Zone Manager — Tableau de bord")
        self.setMinimumSize(1000, 650)

        self._construire_interface()
        self._appliquer_theme()
        self._centrer_sur_ecran()

        # Rafraîchissement automatique toutes les 5 secondes
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.rafraichir_donnees)
        self._timer.start()

        # Chargement initial
        self.rafraichir_donnees()

    def _construire_interface(self):
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- Sidebar ---
        self._sidebar = Sidebar()
        self._sidebar.item_selectionne.connect(self._on_navigation)
        layout_principal.addWidget(self._sidebar)

        # --- Zone de contenu ---
        zone_contenu = QWidget()
        zone_contenu.setObjectName("zoneContenu")
        layout_contenu = QVBoxLayout(zone_contenu)
        layout_contenu.setContentsMargins(32, 28, 32, 28)
        layout_contenu.setSpacing(24)

        # 1. Header
        layout_contenu.addLayout(self._construire_header())

        # 2. Rangée de StatCards
        layout_contenu.addLayout(self._construire_rangee_stats())

        # 3. Card sessions actives
        layout_contenu.addWidget(self._construire_card_sessions(), stretch=1)

        layout_principal.addWidget(zone_contenu)

    def _construire_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(0)

        titre = QLabel("Tableau de bord réseau")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        # Badge "Routeur connecté"
        badge = QWidget()
        badge.setObjectName("badgeConnexion")
        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(12, 6, 14, 6)
        badge_layout.setSpacing(6)

        pastille = QLabel()
        pastille.setFixedSize(8, 8)
        pastille.setObjectName("pastilleConnexion")
        badge_layout.addWidget(pastille)

        texte_badge = QLabel("Routeur connecté")
        texte_badge.setObjectName("texteBadgeConnexion")
        badge_layout.addWidget(texte_badge)

        header.addWidget(badge)
        return header

    def _construire_rangee_stats(self) -> QHBoxLayout:
        rangee = QHBoxLayout()
        rangee.setSpacing(16)

        self._card_appareils = StatCard(
            "fa5s.laptop", "Appareils connectés", "—", "sur — max"
        )
        self._card_debit_down = StatCard(
            "fa5s.arrow-down", "Débit descendant", "— Mb/s", "moyen actuel"
        )
        self._card_debit_up = StatCard(
            "fa5s.arrow-up", "Débit montant", "— Mb/s", "moyen actuel"
        )
        self._card_latence = StatCard(
            "fa5s.signal", "Latence", "— ms", "ping moyen"
        )

        for card in (
            self._card_appareils,
            self._card_debit_down,
            self._card_debit_up,
            self._card_latence,
        ):
            rangee.addWidget(card)

        return rangee

    def _construire_card_sessions(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Titre de section
        titre_section = QLabel("SESSIONS ACTIVES")
        titre_section.setObjectName("titreSectionSessions")
        titre_section.setContentsMargins(20, 16, 20, 12)
        layout.addWidget(titre_section)

        # Zone défilable pour les lignes de session
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._conteneur_sessions = QWidget()
        self._layout_sessions = QVBoxLayout(self._conteneur_sessions)
        self._layout_sessions.setContentsMargins(0, 0, 0, 0)
        self._layout_sessions.setSpacing(0)
        self._layout_sessions.addStretch()

        scroll.setWidget(self._conteneur_sessions)
        layout.addWidget(scroll)

        return card

    def _vider_sessions(self):
        """Supprime toutes les SessionRow existantes."""
        while self._layout_sessions.count() > 1:  # garde le stretch final
            item = self._layout_sessions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_navigation(self, section: str):
        # Seul le tableau de bord est implémenté pour l'instant
        pass

    def rafraichir_donnees(self):
        """Appelle le controller et met à jour l'UI."""
        donnees = self._controller.obtenir_donnees_dashboard()
        stats = donnees["statistiques"]
        sessions = donnees["sessions_actives"]

        # Mise à jour des StatCards
        self._card_appareils.mettre_a_jour(
            str(stats["appareils_connectes"]),
            f"sur {stats['appareils_max']} max",
        )
        self._card_debit_down.mettre_a_jour(
            f"{stats['debit_descendant']} Mb/s"
        )
        self._card_debit_up.mettre_a_jour(
            f"{stats['debit_montant']} Mb/s"
        )
        self._card_latence.mettre_a_jour(
            f"{stats['latence']} ms"
        )

        # Reconstruction de la liste des sessions
        self._vider_sessions()
        for i, session in enumerate(sessions):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                # insertWidget(-1) insère avant le stretch final
                self._layout_sessions.insertWidget(
                    self._layout_sessions.count() - 1, sep
                )
            ligne = SessionRow(session)
            self._layout_sessions.insertWidget(
                self._layout_sessions.count() - 1, ligne
            )

    def _appliquer_theme(self):
        try:
            with open(CHEMIN_QSS, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def _centrer_sur_ecran(self):
        ecran = self.screen().availableGeometry()
        x = (ecran.width() - self.width()) // 2
        y = (ecran.height() - self.height()) // 2
        self.move(x, y)
