import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QProgressBar,
)

from views.dashboard.components.stat_card import StatCard


# TODO: remplacer par session_repository.statistiques_journalieres()
_ACTIVITE_PAR_HEURE = [
    0, 0, 0, 1, 0, 3, 8, 15, 22, 28, 32, 30,
    25, 28, 30, 27, 22, 18, 12, 8, 5, 3, 1, 0,
]

_TOP_APPAREILS = [
    ("Jean Dupont — iPhone 14",   47),
    ("Marie A. — MacBook Pro",    38),
    ("PC Bureau — Windows 11",    22),
    ("Appareil inconnu",          15),
    ("Tablette Samsung",           8),
]

_COULEURS_BARRE = [
    "#5b6ee8", "#6ee8c0", "#e8c45b", "#e85b6e", "#5b9ee8",
]


class StatistiquesPage(QWidget):
    """Page de visualisation des statistiques réseau."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construire_interface()

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
        for icone, nom, valeur, sous in [
            ("fa5s.user-check",   "Sessions aujourd'hui",  "24",     "utilisateurs uniques"),
            ("fa5s.cloud-download-alt", "Volume téléchargé", "1,2 GB", "total journalier"),
            ("fa5s.clock",        "Durée moy. session",    "47 min", "par utilisateur"),
        ]:
            rangee.addWidget(StatCard(icone, nom, valeur, sous))
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
        layout.setSpacing(14)

        titre = QLabel("ACTIVITÉ SUR 24 HEURES")
        titre.setObjectName("titreSectionSessions")
        layout.addWidget(titre)

        max_val = max(_ACTIVITE_PAR_HEURE) or 1

        for heure, val in enumerate(_ACTIVITE_PAR_HEURE):
            ligne = QHBoxLayout()
            ligne.setSpacing(10)

            lbl_h = QLabel(f"{heure:02d}h")
            lbl_h.setObjectName("labelHeure")
            lbl_h.setFixedWidth(30)
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

            layout.addLayout(ligne)

        return card

    def _carte_top_appareils(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        titre = QLabel("TOP 5 APPAREILS  ·  SESSION EN COURS")
        titre.setObjectName("titreSectionSessions")
        layout.addWidget(titre)

        max_val = _TOP_APPAREILS[0][1] if _TOP_APPAREILS else 1

        for i, (nom, val) in enumerate(_TOP_APPAREILS):
            ligne = QHBoxLayout()
            ligne.setSpacing(12)

            # Rang
            rang = QLabel(f"#{i + 1}")
            rang.setObjectName("labelHeure")
            rang.setFixedWidth(24)
            rang.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(rang)

            # Nom
            lbl_nom = QLabel(nom)
            lbl_nom.setObjectName("nomUtilisateur")
            lbl_nom.setFixedWidth(220)
            ligne.addWidget(lbl_nom)

            # Barre colorée
            barre = QProgressBar()
            barre.setObjectName("barreTop")
            barre.setRange(0, max_val)
            barre.setValue(val)
            barre.setTextVisible(False)
            barre.setFixedHeight(10)
            barre.setStyleSheet(
                f"QProgressBar {{ background-color: #2f3340; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background-color: {_COULEURS_BARRE[i % len(_COULEURS_BARRE)]}; border-radius: 5px; }}"
            )
            ligne.addWidget(barre, stretch=1)

            lbl_v = QLabel(f"{val} MB")
            lbl_v.setObjectName("labelValeurBarre")
            lbl_v.setFixedWidth(50)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_v)

            layout.addLayout(ligne)

        return card
