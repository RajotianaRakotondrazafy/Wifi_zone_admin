import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QScrollArea,
)

from views.dashboard.components.session_row import AvatarCirculaire


# TODO: remplacer par user_repository.lister_tous()
UTILISATEURS_FACTICES = [
    {"nom": "Jean Dupont",        "login": "jean.dupont", "role": "admin",    "actif": True},
    {"nom": "Marie Andriantsoa",  "login": "marie.a",     "role": "caissier", "actif": True},
    {"nom": "Robert Rakoto",      "login": "r.rakoto",    "role": "caissier", "actif": False},
    {"nom": "Fara Koto",          "login": "fara.k",      "role": "caissier", "actif": True},
]


class LigneUtilisateur(QWidget):
    """Ligne d'utilisateur dans la liste."""

    def __init__(self, donnees: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneUtilisateur")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(14)

        # Avatar circulaire
        layout.addWidget(AvatarCirculaire(donnees["nom"], donnees["login"]))

        # Nom + identifiant
        bloc = QVBoxLayout()
        bloc.setSpacing(2)
        nom = QLabel(donnees["nom"])
        nom.setObjectName("nomUtilisateur")
        bloc.addWidget(nom)
        login = QLabel(donnees["login"])
        login.setObjectName("loginUtilisateur")
        bloc.addWidget(login)
        layout.addLayout(bloc)

        layout.addStretch()

        # Badge rôle
        badge_role = QLabel(" Admin " if donnees["role"] == "admin" else " Caissier ")
        badge_role.setObjectName("badgeAdmin" if donnees["role"] == "admin" else "badgeCaissier")
        layout.addWidget(badge_role)

        layout.addSpacing(8)

        # Badge statut
        badge_statut = QLabel(" Actif " if donnees["actif"] else " Inactif ")
        badge_statut.setObjectName("badgeActif" if donnees["actif"] else "badgeInactif")
        layout.addWidget(badge_statut)

        layout.addSpacing(12)

        # Boutons actions
        btn_modifier = self._btn("Modifier", "boutonActionLimiter")
        layout.addWidget(btn_modifier)

        libelle_toggle = "Désactiver" if donnees["actif"] else "Activer"
        style_toggle = "boutonActionBloquer" if donnees["actif"] else "boutonActionIdentifier"
        layout.addWidget(self._btn(libelle_toggle, style_toggle))

    @staticmethod
    def _btn(texte: str, obj: str) -> QPushButton:
        b = QPushButton(texte)
        b.setObjectName(obj)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(32)
        return b


class UtilisateursPage(QWidget):
    """Page de gestion des comptes utilisateurs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        titre = QLabel("Gestion des utilisateurs")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        badge_nb = QLabel(f"  {len(UTILISATEURS_FACTICES)} comptes  ")
        badge_nb.setObjectName("badgeNeutre")
        header.addWidget(badge_nb)
        header.addSpacing(12)

        btn_ajouter = QPushButton("  Nouveau compte")
        btn_ajouter.setObjectName("boutonActionPage")
        btn_ajouter.setIcon(qta.icon("fa5s.user-plus", color="#ffffff"))
        btn_ajouter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ajouter.setFixedHeight(38)
        header.addWidget(btn_ajouter)
        layout.addLayout(header)

        # ── Recherche ────────────────────────────────────────────────────
        barre = QLineEdit()
        barre.setObjectName("barreRecherche")
        barre.setPlaceholderText("   Rechercher un utilisateur…")
        barre.setFixedHeight(40)
        layout.addWidget(barre)

        # ── Liste ────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("cardSessions")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        titre_section = QLabel(f"COMPTES ENREGISTRÉS  ·  {len(UTILISATEURS_FACTICES)}")
        titre_section.setObjectName("titreSectionSessions")
        titre_section.setContentsMargins(20, 16, 20, 12)
        card_layout.addWidget(titre_section)

        for i, u in enumerate(UTILISATEURS_FACTICES):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                card_layout.addWidget(sep)
            card_layout.addWidget(LigneUtilisateur(u))

        card_layout.addStretch()
        layout.addWidget(card, stretch=1)
