from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)

from controllers.dashboard.dashboard_controller import DashboardController
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.session_row import SessionRow


class TableauDeBordPage(QWidget):
    """Page principale : statistiques réseau + sessions actives."""

    def __init__(self, dashboard_controller: DashboardController, parent=None):
        super().__init__(parent)
        self._controller = dashboard_controller
        self._construire_interface()

        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.rafraichir_donnees)
        self._timer.start()

        self.rafraichir_donnees()

    # ── Construction ────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)
        layout.addLayout(self._construire_header())
        layout.addLayout(self._construire_rangee_stats())
        layout.addWidget(self._construire_card_sessions(), stretch=1)

    def _construire_header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        titre = QLabel("Tableau de bord réseau")
        titre.setObjectName("titreDashboard")
        h.addWidget(titre)
        h.addStretch()

        badge = QWidget()
        badge.setObjectName("badgeConnexion")
        bl = QHBoxLayout(badge)
        bl.setContentsMargins(12, 6, 14, 6)
        bl.setSpacing(6)
        pastille = QLabel()
        pastille.setFixedSize(8, 8)
        pastille.setObjectName("pastilleConnexion")
        bl.addWidget(pastille)
        bl.addWidget(self._lbl("Routeur connecté", "texteBadgeConnexion"))
        h.addWidget(badge)
        return h

    def _construire_rangee_stats(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._card_appareils  = StatCard("fa5s.laptop",     "Appareils connectés", "—",      "sur — max")
        self._card_debit_down = StatCard("fa5s.arrow-down", "Débit descendant",    "— Mb/s", "moyen actuel")
        self._card_debit_up   = StatCard("fa5s.arrow-up",   "Débit montant",       "— Mb/s", "moyen actuel")
        self._card_latence    = StatCard("fa5s.signal",      "Latence",             "— ms",   "ping moyen")
        for c in (self._card_appareils, self._card_debit_down, self._card_debit_up, self._card_latence):
            r.addWidget(c)
        return r

    def _construire_card_sessions(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        titre = QLabel("SESSIONS ACTIVES")
        titre.setObjectName("titreSectionSessions")
        titre.setContentsMargins(20, 16, 20, 12)
        layout.addWidget(titre)

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

    # ── Données ─────────────────────────────────────────────────────────

    def rafraichir_donnees(self):
        donnees = self._controller.obtenir_donnees_dashboard()
        stats   = donnees["statistiques"]
        sessions = donnees["sessions_actives"]

        self._card_appareils.mettre_a_jour(
            str(stats["appareils_connectes"]), f"sur {stats['appareils_max']} max"
        )
        self._card_debit_down.mettre_a_jour(f"{stats['debit_descendant']} Mb/s")
        self._card_debit_up.mettre_a_jour(f"{stats['debit_montant']} Mb/s")
        self._card_latence.mettre_a_jour(f"{stats['latence']} ms")

        # Vider puis reconstruire les lignes de session
        while self._layout_sessions.count() > 1:
            item = self._layout_sessions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, session in enumerate(sessions):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                self._layout_sessions.insertWidget(self._layout_sessions.count() - 1, sep)
            self._layout_sessions.insertWidget(
                self._layout_sessions.count() - 1, SessionRow(session)
            )

    @staticmethod
    def _lbl(texte: str, obj: str) -> QLabel:
        l = QLabel(texte)
        l.setObjectName(obj)
        return l
