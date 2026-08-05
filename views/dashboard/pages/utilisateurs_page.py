import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QMessageBox,
)

from controllers.utilisateurs.utilisateurs_controller import UtilisateursController
from views.dashboard.components.dialog_utilisateur import DialogUtilisateur
from views.dashboard.components.session_row import AvatarCirculaire


class LigneUtilisateur(QWidget):
    """Ligne d'utilisateur dans la liste."""

    def __init__(self, donnees: dict, on_modifier, on_basculer, on_supprimer, parent=None):
        super().__init__(parent)
        self._donnees = donnees
        self.setObjectName("ligneUtilisateur")
        self.setProperty("inactif", not donnees["actif"])

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

        # Badge rôle — largeur fixe pour alignement
        badge_role = QLabel("Admin" if donnees["role"] == "admin" else "Caissier")
        badge_role.setObjectName("badgeAdmin" if donnees["role"] == "admin" else "badgeCaissier")
        badge_role.setFixedWidth(72)
        badge_role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge_role)

        layout.addSpacing(10)

        # Badge statut — largeur fixe pour alignement
        badge_statut = QLabel("Actif" if donnees["actif"] else "Inactif")
        badge_statut.setObjectName("badgeActif" if donnees["actif"] else "badgeInactif")
        badge_statut.setFixedWidth(60)
        badge_statut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge_statut)

        layout.addSpacing(16)

        # Boutons actions — largeurs fixes
        btn_modifier = self._btn("Modifier", "boutonActionLimiter", 90)
        btn_modifier.clicked.connect(lambda: on_modifier(donnees))
        layout.addWidget(btn_modifier)

        libelle_toggle = "Désactiver" if donnees["actif"] else "Activer"
        style_toggle = "boutonActionBloquer" if donnees["actif"] else "boutonActionActiver"
        btn_toggle = self._btn(libelle_toggle, style_toggle, 96)
        btn_toggle.clicked.connect(lambda: on_basculer(donnees))
        layout.addWidget(btn_toggle)

        btn_supprimer = self._btn("Supprimer", "boutonActionBloquer", 90)
        btn_supprimer.clicked.connect(lambda: on_supprimer(donnees))
        layout.addWidget(btn_supprimer)

    @staticmethod
    def _btn(texte: str, obj: str, largeur: int = 90) -> QPushButton:
        b = QPushButton(texte)
        b.setObjectName(obj)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(32)
        b.setFixedWidth(largeur)
        return b


class UtilisateursPage(QWidget):
    """Page de gestion des comptes utilisateurs."""

    def __init__(self, controller: UtilisateursController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._recherche = ""
        self._construire_interface()
        self._remplir()

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

        self._badge_nb = QLabel("  0 comptes  ")
        self._badge_nb.setObjectName("badgeNeutre")
        header.addWidget(self._badge_nb)
        header.addSpacing(12)

        btn_ajouter = QPushButton("  Nouveau compte")
        btn_ajouter.setObjectName("boutonActionPage")
        btn_ajouter.setIcon(qta.icon("fa5s.user-plus", color="#ffffff"))
        btn_ajouter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ajouter.setFixedHeight(38)
        btn_ajouter.clicked.connect(self._ajouter)
        header.addWidget(btn_ajouter)
        layout.addLayout(header)

        # ── Recherche ────────────────────────────────────────────────────
        barre = QLineEdit()
        barre.setObjectName("barreRecherche")
        barre.setPlaceholderText("   Rechercher un utilisateur…")
        barre.setFixedHeight(40)
        barre.textChanged.connect(self._filtrer)
        layout.addWidget(barre)

        # ── Liste ────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("cardSessions")
        self._card_layout = QVBoxLayout(card)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(0)
        self._card_layout.addStretch()
        layout.addWidget(card, stretch=1)

    def _vider_card(self):
        while self._card_layout.count():
            item = self._card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _filtrer(self, texte: str):
        self._recherche = texte.strip().lower()
        self._remplir()

    def _remplir(self):
        self._vider_card()

        utilisateurs = self._controller.obtenir_utilisateurs()

        if self._recherche:
            utilisateurs = [
                u for u in utilisateurs
                if self._recherche in u["nom"].lower() or self._recherche in u["login"].lower()
            ]

        self._badge_nb.setText(f"  {len(utilisateurs)} comptes  ")

        titre_section = QLabel(
            "COMPTES ENREGISTRÉS" + (f"  ·  « {self._recherche} »" if self._recherche else "")
        )
        titre_section.setObjectName("titreSectionSessions")
        titre_section.setContentsMargins(20, 16, 20, 12)
        self._card_layout.addWidget(titre_section)

        if not utilisateurs:
            lbl_vide = QLabel(
                "Aucun utilisateur trouvé."
                if self._recherche else "Aucun compte. Cliquez sur « Nouveau compte »."
            )
            lbl_vide.setObjectName("loginUtilisateur")
            lbl_vide.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_vide.setContentsMargins(0, 30, 0, 30)
            self._card_layout.addWidget(lbl_vide)
        else:
            for i, u in enumerate(utilisateurs):
                if i > 0:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setObjectName("separateurSession")
                    self._card_layout.addWidget(sep)
                self._card_layout.addWidget(LigneUtilisateur(
                    u, self._modifier, self._basculer, self._supprimer,
                ))

        self._card_layout.addStretch()

    # ── Actions ──────────────────────────────────────────────────────────

    def _ajouter(self):
        dialog = DialogUtilisateur(utilisateur=None, parent=self)
        if not dialog.exec():
            return
        try:
            self._controller.creer_utilisateur(dialog.donnees)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()

    def _modifier(self, utilisateur: dict):
        dialog = DialogUtilisateur(utilisateur=utilisateur, parent=self)
        if not dialog.exec():
            return
        try:
            self._controller.modifier_utilisateur(dialog.donnees)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()

    def _basculer(self, utilisateur: dict):
        try:
            self._controller.basculer_actif(utilisateur["id"])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()

    def _supprimer(self, utilisateur: dict):
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer le compte de « {utilisateur['nom']} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._controller.supprimer_utilisateur(utilisateur["id"])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._remplir()
