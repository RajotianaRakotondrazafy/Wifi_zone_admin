import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox,
)

from models.user import RoleUtilisateur


class DialogUtilisateur(QDialog):
    """Dialog d'ajout ou de modification d'un compte utilisateur."""

    utilisateur_modifie = pyqtSignal()

    def __init__(self, utilisateur: dict | None = None, parent=None):
        super().__init__(parent)
        self._utilisateur = utilisateur

        self.setWindowTitle("Modifier le compte" if utilisateur else "Nouveau compte")
        self.setModal(True)
        self.setFixedSize(460, 620)
        self.setObjectName("dialogVente")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        page = self._construire_formulaire()
        layout.addWidget(page)

    def _champ(self, label: str, widget) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("titreSectionSessions")
        vbox.addWidget(lbl)
        widget.setFixedHeight(40)
        widget.setObjectName("comboParametres")
        vbox.addWidget(widget)
        return vbox

    def _construire_formulaire(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("pageDialogProfil")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        # ── Titre ────────────────────────────────────────────────────
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.user", color="#5b6ee8").pixmap(20, 20))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Modifier le compte" if self._utilisateur else "Nouveau compte")
        titre.setObjectName("titreDialog")
        h_titre.addWidget(titre)
        h_titre.addStretch()

        if self._utilisateur:
            actif = self._utilisateur["actif"]
            badge = QLabel("  Actif  " if actif else "  Inactif  ")
            badge.setObjectName("badgeStatutDialog")
            badge.setProperty("actif", actif)
            h_titre.addWidget(badge)

        lay.addLayout(h_titre)

        lay.addSpacing(8)
        lay.addWidget(self._sep())
        lay.addSpacing(12)

        # ── Nom ──────────────────────────────────────────────────────
        self._input_nom = QLineEdit()
        self._input_nom.setPlaceholderText("Ex : Jean Dupont")
        if self._utilisateur:
            self._input_nom.setText(self._utilisateur["nom"])
        lay.addLayout(self._champ("NOM COMPLET", self._input_nom))
        lay.addSpacing(12)

        # ── Identifiant ──────────────────────────────────────────────
        self._input_login = QLineEdit()
        self._input_login.setPlaceholderText("Ex : jean.dupont")
        if self._utilisateur:
            self._input_login.setText(self._utilisateur["login"])
        lay.addLayout(self._champ("IDENTIFIANT DE CONNEXION", self._input_login))
        lay.addSpacing(12)

        # ── Mot de passe ─────────────────────────────────────────────
        self._input_mdp = QLineEdit()
        self._input_mdp.setPlaceholderText(
            "Nouveau mot de passe…" if self._utilisateur else "Mot de passe"
        )
        self._input_mdp.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addLayout(self._champ("MOT DE PASSE", self._input_mdp))
        lay.addSpacing(12)

        # ── Rôle ─────────────────────────────────────────────────────
        self._combo_role = QComboBox()
        role_actuel = self._utilisateur["role"] if self._utilisateur else "caissier"
        roles = [(r.value, r.name.capitalize()) for r in RoleUtilisateur]
        for valeur, libelle in roles:
            self._combo_role.addItem(libelle, userData=valeur)
        for i, (valeur, _) in enumerate(roles):
            if valeur == role_actuel:
                self._combo_role.setCurrentIndex(i)
                break
        lay.addLayout(self._champ("RÔLE", self._combo_role))
        lay.addSpacing(8)

        # ── Statut ───────────────────────────────────────────────────
        self._combo_actif = QComboBox()
        self._combo_actif.addItem("Actif (peut se connecter)", userData=True)
        self._combo_actif.addItem("Inactif (désactivé)",       userData=False)
        if self._utilisateur and not self._utilisateur["actif"]:
            self._combo_actif.setCurrentIndex(1)
        lay.addLayout(self._champ("STATUT", self._combo_actif))
        lay.addSpacing(8)

        encart = QFrame()
        encart.setObjectName("encartStatut")
        encart_lay = QHBoxLayout(encart)
        encart_lay.setContentsMargins(12, 8, 12, 8)
        lbl_encart = QLabel(
            "Un compte inactif ne peut plus se connecter, mais son historique "
            "de ventes est conservé."
        )
        lbl_encart.setObjectName("encartStatutTexte")
        lbl_encart.setWordWrap(True)
        encart_lay.addWidget(lbl_encart)
        lay.addWidget(encart)

        lay.addStretch()

        # ── Boutons ──────────────────────────────────────────────────
        lay.addWidget(self._sep())
        lay.addSpacing(16)
        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)

        btn_annuler = QPushButton("Annuler")
        btn_annuler.setObjectName("boutonActionHistorique")
        btn_annuler.setFixedHeight(44)
        btn_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_annuler.clicked.connect(self.reject)
        h_btn.addWidget(btn_annuler)

        h_btn.addStretch()

        btn_sauvegarder = QPushButton("  Enregistrer")
        btn_sauvegarder.setObjectName("boutonVendre")
        btn_sauvegarder.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        btn_sauvegarder.setFixedHeight(44)
        btn_sauvegarder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sauvegarder.clicked.connect(self._sauvegarder)
        h_btn.addWidget(btn_sauvegarder)

        lay.addLayout(h_btn)
        return frame

    def _sauvegarder(self):
        data = self._collecter_donnees()
        if data is None:
            return

        if self._utilisateur:
            data["id"] = self._utilisateur["id"]

        self._donnees = data
        self.utilisateur_modifie.emit()
        self.accept()

    def _collecter_donnees(self) -> dict | None:
        nom = self._input_nom.text().strip()
        if not nom:
            self._input_nom.setFocus()
            return None

        login = self._input_login.text().strip()
        if not login:
            self._input_login.setFocus()
            return None

        if not self._utilisateur and not self._input_mdp.text():
            self._input_mdp.setFocus()
            return None

        return {
            "nom":           nom,
            "login":         login,
            "mot_de_passe":  self._input_mdp.text(),
            "role":          self._combo_role.currentData(),
            "actif":         bool(self._combo_actif.currentData()),
        }

    @property
    def donnees(self) -> dict:
        return getattr(self, "_donnees", None)

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setObjectName("separateurSession")
        return f
