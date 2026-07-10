import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QScrollArea, QComboBox,
)


class ParametresPage(QWidget):
    """Page de configuration de l'application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        titre = QLabel("Paramètres")
        titre.setObjectName("titreDashboard")
        layout.addWidget(titre)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        cl = QVBoxLayout(contenu)
        cl.setSpacing(16)
        cl.setContentsMargins(0, 0, 0, 0)

        cl.addWidget(self._section(
            "fa5s.server", "CONNEXION ROUTEUR MIKROTIK",
            [
                ("Adresse IP du routeur", "192.168.1.1", False),
                ("Port API RouterOS",     "8728",        False),
                ("Nom d'utilisateur",     "admin",       False),
                ("Mot de passe API",      "",            True),
            ]
        ))

        cl.addWidget(self._section(
            "fa5s.wifi", "CONFIGURATION HOTSPOT",
            [
                ("Nom du hotspot (SSID)", "E-Konnekta", False),
                ("Interface réseau",      "bridge1",    False),
                ("Profil par défaut",     "default",    False),
            ]
        ))

        cl.addWidget(self._section_application())

        btn = QPushButton("  Sauvegarder les paramètres")
        btn.setObjectName("boutonSauvegarder")
        btn.setIcon(qta.icon("fa5s.save", color="#ffffff"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(46)
        cl.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        cl.addStretch()
        scroll.setWidget(contenu)
        layout.addWidget(scroll, stretch=1)

    def _section(self, icone_id: str, titre: str, champs: list) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # En-tête
        header = QHBoxLayout()
        icone = QLabel()
        icone.setPixmap(qta.icon(icone_id, color="#5b6ee8").pixmap(14, 14))
        header.addWidget(icone)
        header.addSpacing(6)
        lbl_titre = QLabel(titre)
        lbl_titre.setObjectName("titreSectionParametres")
        header.addWidget(lbl_titre)
        header.addStretch()
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        layout.addWidget(sep)

        # Champs en 2 colonnes
        cols = [QVBoxLayout(), QVBoxLayout()]
        cols[0].setSpacing(12)
        cols[1].setSpacing(12)

        for i, (label, valeur, est_mdp) in enumerate(champs):
            bloc = QVBoxLayout()
            bloc.setSpacing(4)
            bloc.addWidget(self._label_param(label))
            champ = QLineEdit()
            champ.setFixedHeight(38)
            if est_mdp:
                champ.setPlaceholderText("Nouveau mot de passe…")
                champ.setEchoMode(QLineEdit.EchoMode.Password)
            else:
                champ.setText(valeur)
            bloc.addWidget(champ)
            cols[i % 2].addLayout(bloc)

        grille = QHBoxLayout()
        grille.setSpacing(16)
        grille.addLayout(cols[0])
        grille.addLayout(cols[1])
        layout.addLayout(grille)

        return card

    def _section_application(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionParametres")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        icone = QLabel()
        icone.setPixmap(qta.icon("fa5s.sliders-h", color="#5b6ee8").pixmap(14, 14))
        header.addWidget(icone)
        header.addSpacing(6)
        lbl = QLabel("APPLICATION")
        lbl.setObjectName("titreSectionParametres")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        layout.addWidget(sep)

        grille = QHBoxLayout()
        grille.setSpacing(16)

        col1 = QVBoxLayout()
        col1.setSpacing(4)
        col1.addWidget(self._label_param("Intervalle de rafraîchissement (s)"))
        champ = QLineEdit("5")
        champ.setFixedHeight(38)
        col1.addWidget(champ)
        grille.addLayout(col1)

        col2 = QVBoxLayout()
        col2.setSpacing(4)
        col2.addWidget(self._label_param("Langue de l'interface"))
        combo = QComboBox()
        combo.setObjectName("comboParametres")
        combo.addItems(["Français", "English", "Malagasy"])
        combo.setFixedHeight(38)
        col2.addWidget(combo)
        grille.addLayout(col2)

        layout.addLayout(grille)
        return card

    @staticmethod
    def _label_param(texte: str) -> QLabel:
        lbl = QLabel(texte)
        lbl.setObjectName("labelParametre")
        return lbl
