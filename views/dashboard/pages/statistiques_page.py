from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QProgressBar,
)

from controllers.statistiques.statistiques_controller import StatistiquesController
from views.dashboard.components.stat_card import StatCard


class WorkerStatistiques(QThread):
    """Enregistre les sessions depuis le routeur puis agrège les données en arrière-plan."""

    donnees_prete = pyqtSignal(dict)

    def __init__(self, controller: StatistiquesController, parent=None):
        super().__init__(parent)
        self._controller = controller

    def run(self):
        try:
            donnees = self._controller.snapshot_complet()
        except Exception as exc:
            donnees = {
                "connecte": False,
                "sessions_actives": 0,
                "stats": {"nb_sessions": 0, "volume_recu_octets": 0, "duree_moyenne_min": 0},
                "activite": [],
                "top": [],
                "erreur": str(exc),
            }
        self.donnees_prete.emit(donnees)


_COULEURS_BARRE = [
    "#5b6ee8", "#6ee8c0", "#e8c45b", "#e85b6e", "#5b9ee8",
]


def _formater_volume(octets) -> str:
    """Formate un volume en octets (ex : '1,2 GB', '840 MB')."""
    try:
        octets = int(octets)
    except (TypeError, ValueError):
        octets = 0
    if octets >= 1_000_000_000:
        return f"{octets / 1_000_000_000:.1f}".replace(".", ",") + " GB"
    if octets >= 1_000_000:
        return f"{octets / 1_000_000:.1f}".replace(".", ",") + " MB"
    if octets >= 1_000:
        return f"{octets / 1_000:.0f}" + " Ko"
    return f"{octets} o"


class StatistiquesPage(QWidget):
    """Page de visualisation des statistiques réseau (données réelles)."""

    def __init__(self, controller: StatistiquesController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._worker: WorkerStatistiques | None = None

        self._construire_interface()

        # Rafraîchissement toutes les 60 s en arrière-plan
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self._lancer_rafraichissement)
        self._timer.start()

        self._lancer_rafraichissement()

    # ── Construction ──────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        # ── Header ──────────────────────────────────────────────────────
        titre = QLabel("Statistiques réseau")
        titre.setObjectName("titreDashboard")
        layout.addWidget(titre)

        # ── Tuiles de synthèse ──────────────────────────────────────────
        rangee = QHBoxLayout()
        rangee.setSpacing(16)
        self._card_sessions = StatCard("fa5s.user-check", "Sessions aujourd'hui", "—", "utilisateurs uniques")
        self._card_volume   = StatCard("fa5s.cloud-download-alt", "Volume téléchargé", "—", "total journalier")
        self._card_duree    = StatCard("fa5s.clock", "Durée moy. session", "—", "par utilisateur")
        for c in (self._card_sessions, self._card_volume, self._card_duree):
            rangee.addWidget(c)
        layout.addLayout(rangee)

        # ── Zone défilable pour les graphes ─────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        contenu_layout = QVBoxLayout(contenu)
        contenu_layout.setSpacing(20)
        contenu_layout.setContentsMargins(0, 0, 0, 0)

        contenu_layout.addWidget(self._carte_activite_24h())
        contenu_layout.addWidget(self._carte_top_appareils())
        contenu_layout.addStretch()

        scroll.setWidget(contenu)
        layout.addWidget(scroll, stretch=1)

    def _carte_activite_24h(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(0)

        titre = QLabel("ACTIVITÉ DU JOUR · PAR HEURE")
        titre.setObjectName("titreSectionSessions")
        titre.setContentsMargins(0, 0, 0, 12)
        layout.addWidget(titre)

        self._conteneur_activite = QWidget()
        self._layout_activite = QVBoxLayout(self._conteneur_activite)
        self._layout_activite.setContentsMargins(0, 0, 0, 0)
        self._layout_activite.setSpacing(6)
        layout.addWidget(self._conteneur_activite)
        return card

    def _carte_top_appareils(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(0)

        titre = QLabel("TOP 5 CONSOMMATEURS · AUJOURD'HUI")
        titre.setObjectName("titreSectionSessions")
        titre.setContentsMargins(0, 0, 0, 12)
        layout.addWidget(titre)

        self._conteneur_top = QWidget()
        self._layout_top = QVBoxLayout(self._conteneur_top)
        self._layout_top.setContentsMargins(0, 0, 0, 0)
        self._layout_top.setSpacing(10)
        layout.addWidget(self._conteneur_top)
        return card

    # ── Rafraîchissement ────────────────────────────────────────────────

    def _lancer_rafraichissement(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = WorkerStatistiques(self._controller, parent=self)
        self._worker.donnees_prete.connect(self.rafraichir_donnees)
        self._worker.start()

    def rafraichir_donnees(self, donnees: dict):
        connecte = donnees.get("connecte", False)
        stats    = donnees.get("stats", {})

        # ── Tuiles de synthèse ──────────────────────────────────────────
        self._card_sessions.mettre_a_jour(
            str(stats.get("nb_sessions", 0)), "utilisateurs uniques"
        )
        self._card_volume.mettre_a_jour(
            _formater_volume(stats.get("volume_recu_octets", 0)), "total journalier"
        )
        duree = stats.get("duree_moyenne_min", 0) or 0
        self._card_duree.mettre_a_jour(
            f"{duree:.1f}".replace(".", ","), "min par utilisateur"
        )

        # ── Activité par heure ──────────────────────────────────────────
        activite = donnees.get("activite") or []
        if len(activite) < 24:
            activite = [0] * 24
        self._construire_activite(activite)

        # ── Top consommateurs ───────────────────────────────────────────
        self._construire_top(donnees.get("top") or [], connecte)

    def _construire_activite(self, activite: list[int]):
        self._vider_layout(self._layout_activite)
        max_val = max(activite) or 1

        for heure, val in enumerate(activite):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            ligne = QHBoxLayout(row)
            ligne.setContentsMargins(0, 0, 0, 0)
            ligne.setSpacing(8)

            lbl_h = QLabel(f"{heure:02d}h")
            lbl_h.setObjectName("labelHeure")
            lbl_h.setFixedWidth(36)
            lbl_h.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_h)

            barre = QProgressBar()
            barre.setObjectName("barreActivite")
            barre.setRange(0, max_val)
            barre.setValue(val)
            barre.setTextVisible(False)
            barre.setFixedHeight(10)
            ligne.addWidget(barre, stretch=1)

            lbl_v = QLabel(str(val) if val > 0 else "")
            lbl_v.setObjectName("labelValeurBarre")
            lbl_v.setFixedWidth(28)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_v)

            self._layout_activite.addWidget(row)

    def _construire_top(self, top: list[dict], connecte: bool):
        self._vider_layout(self._layout_top)

        if not top:
            lbl = QLabel(
                "Routeur non connecté — aucune donnée pour l'instant."
                if not connecte else
                "Aucune session enregistrée aujourd'hui."
            )
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(0, 4, 0, 4)
            self._layout_top.addWidget(lbl)
            return

        max_val = max((c.get("octets") or 0) for c in top) or 1

        for i, c in enumerate(top):
            nom = c.get("nom_hote") or c.get("code") or "Inconnu"
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            ligne = QHBoxLayout(row)
            ligne.setContentsMargins(0, 0, 0, 0)
            ligne.setSpacing(12)

            rang = QLabel(f"#{i + 1}")
            rang.setObjectName("labelHeure")
            rang.setFixedWidth(24)
            rang.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(rang)

            lbl_nom = QLabel(nom)
            lbl_nom.setObjectName("nomUtilisateur")
            lbl_nom.setFixedWidth(220)
            ligne.addWidget(lbl_nom)

            barre = QProgressBar()
            barre.setObjectName("barreTop")
            barre.setRange(0, max_val)
            barre.setValue(c.get("octets") or 0)
            barre.setTextVisible(False)
            barre.setFixedHeight(10)
            barre.setStyleSheet(
                f"QProgressBar {{ background-color: #2f3340; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background-color: {_COULEURS_BARRE[i % len(_COULEURS_BARRE)]}; border-radius: 5px; }}"
            )
            ligne.addWidget(barre, stretch=1)

            lbl_v = QLabel(_formater_volume(c.get("octets") or 0))
            lbl_v.setObjectName("labelValeurBarre")
            lbl_v.setFixedWidth(64)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_v)

            self._layout_top.addWidget(row)

    @staticmethod
    def _vider_layout(lay: QVBoxLayout):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
