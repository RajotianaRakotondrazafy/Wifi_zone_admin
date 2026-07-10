import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit,
)


# TODO: remplacer par blocage_repository.lister_tous()
BLOCAGES_FACTICES = [
    {
        "mac": "DC:A6:32:F5:88:21",
        "nom": "Appareil inconnu",
        "ip": "192.168.1.45",
        "raison": "Abus de bande passante",
        "date": "28/06/2025",
    },
    {
        "mac": "FF:12:34:56:78:90",
        "nom": "PC Salle de réunion",
        "ip": "192.168.1.78",
        "raison": "Tentative d'intrusion détectée",
        "date": "07/07/2026",
    },
]


class LigneBlocage(QWidget):
    """Ligne représentant un appareil bloqué."""

    def __init__(self, donnees: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneBlocage")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(16)

        # Icône bloc
        icone = QLabel()
        icone.setPixmap(qta.icon("fa5s.ban", color="#f87171").pixmap(16, 16))
        layout.addWidget(icone)

        # Bloc texte
        bloc = QVBoxLayout()
        bloc.setSpacing(3)

        ligne1 = QHBoxLayout()
        ligne1.setSpacing(10)
        nom = QLabel(donnees["nom"])
        nom.setObjectName("nomUtilisateur")
        ligne1.addWidget(nom)
        mac = QLabel(donnees["mac"])
        mac.setObjectName("macBlocage")
        ligne1.addWidget(mac)
        ligne1.addStretch()
        bloc.addLayout(ligne1)

        ligne2 = QHBoxLayout()
        ligne2.setSpacing(10)
        raison = QLabel(f"Raison : {donnees['raison']}")
        raison.setObjectName("raisonBlocage")
        ligne2.addWidget(raison)
        date = QLabel(f"· Bloqué le {donnees['date']}")
        date.setObjectName("dateBlocage")
        ligne2.addWidget(date)
        ligne2.addStretch()
        bloc.addLayout(ligne2)

        layout.addLayout(bloc)
        layout.addStretch()

        # IP
        lbl_ip = QLabel(donnees["ip"])
        lbl_ip.setObjectName("ipZone")
        layout.addWidget(lbl_ip)

        layout.addSpacing(8)

        # Bouton débloquer
        btn = QPushButton("Débloquer")
        btn.setObjectName("boutonActionIdentifier")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)
        layout.addWidget(btn)


class BlocagesPage(QWidget):
    """Page de gestion des appareils bloqués."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        titre = QLabel("Appareils bloqués")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        badge = QLabel(f"  {len(BLOCAGES_FACTICES)} bloqué(s)  ")
        badge.setObjectName("badgeBlocage")
        header.addWidget(badge)
        layout.addLayout(header)

        # ── Recherche ────────────────────────────────────────────────────
        barre = QLineEdit()
        barre.setObjectName("barreRecherche")
        barre.setPlaceholderText("   Rechercher par MAC, nom ou IP…")
        barre.setFixedHeight(40)
        layout.addWidget(barre)

        if not BLOCAGES_FACTICES:
            vide = QLabel("Aucun appareil bloqué.")
            vide.setObjectName("loginUtilisateur")
            vide.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(vide, stretch=1)
            return

        # ── Liste ────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("cardSessions")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        titre_section = QLabel(f"LISTE DES BLOCAGES  ·  {len(BLOCAGES_FACTICES)}")
        titre_section.setObjectName("titreSectionSessions")
        titre_section.setContentsMargins(20, 16, 20, 12)
        card_layout.addWidget(titre_section)

        for i, b in enumerate(BLOCAGES_FACTICES):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                card_layout.addWidget(sep)
            card_layout.addWidget(LigneBlocage(b))

        card_layout.addStretch()
        layout.addWidget(card, stretch=1)
