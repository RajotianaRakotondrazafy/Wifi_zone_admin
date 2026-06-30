import qtawesome as qta
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)

from controllers.auth.auth_controller import AuthController
from models.user import User


CHEMIN_QSS = Path(__file__).resolve().parent.parent / "assets" / "styles" / "dark_theme.qss"


class LoginView(QWidget):
    connexion_reussie = pyqtSignal(object)  # object = User

    def __init__(self, auth_controller: AuthController):
        super().__init__()
        self.auth_controller = auth_controller
        self._mot_de_passe_visible = False

        self.setWindowTitle("Connexion - WiFi-Zone Manager")
        self.setFixedSize(400, 500)

        self._construire_interface()
        self._appliquer_theme()
        self._centrer_sur_ecran()

    def _construire_interface(self):
        layout_general = QVBoxLayout(self)
        layout_general.setContentsMargins(0, 0, 0, 0)

        # --- Carte centrale ---
        self.carte = QFrame()
        self.carte.setObjectName("cardLogin")
        self.carte.setFixedWidth(320)

        layout_carte = QVBoxLayout(self.carte)
        layout_carte.setContentsMargins(32, 32, 32, 32)
        layout_carte.setSpacing(16)

        # Icône WiFi
        icone = QLabel("📶")
        icone.setObjectName("iconeWifi")
        layout_carte.addWidget(icone)

        # Titre + sous-titre
        titre = QLabel("WiFi-Zone Manager")
        titre.setObjectName("titreApp")
        layout_carte.addWidget(titre)

        sous_titre = QLabel("Connexion à votre espace")
        sous_titre.setObjectName("sousTitre")
        layout_carte.addWidget(sous_titre)

        layout_carte.addSpacing(8)

        # Champ login
        self.champ_login = QLineEdit()
        self.champ_login.setPlaceholderText("Identifiant")
        self.champ_login.returnPressed.connect(self._tenter_connexion)
        layout_carte.addWidget(self.champ_login)

        # Champ mot de passe + bouton toggle (afficher/masquer)
        conteneur_mdp = QHBoxLayout()
        conteneur_mdp.setSpacing(0)

        self.champ_mot_de_passe = QLineEdit()
        self.champ_mot_de_passe.setPlaceholderText("Mot de passe")
        self.champ_mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self.champ_mot_de_passe.returnPressed.connect(self._tenter_connexion)
        conteneur_mdp.addWidget(self.champ_mot_de_passe)

        self.bouton_toggle_mdp = QPushButton()
        self.bouton_toggle_mdp.setIcon(qta.icon('fa5s.eye', color='#8b8d98'))
        self.bouton_toggle_mdp.setObjectName("boutonToggleMdp")
        self.bouton_toggle_mdp.setFixedWidth(36)
        self.bouton_toggle_mdp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_toggle_mdp.clicked.connect(self._basculer_visibilite_mdp)
        conteneur_mdp.addWidget(self.bouton_toggle_mdp)

        layout_carte.addLayout(conteneur_mdp)

        # Message d'erreur (caché par défaut)
        self.label_erreur = QLabel("Identifiant ou mot de passe incorrect.")
        self.label_erreur.setObjectName("labelErreur")
        self.label_erreur.setVisible(False)
        layout_carte.addWidget(self.label_erreur)

        layout_carte.addSpacing(8)

        # Bouton de connexion
        self.bouton_connexion = QPushButton("Se connecter")
        self.bouton_connexion.setObjectName("boutonConnexion")
        self.bouton_connexion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_connexion.setFixedHeight(42)
        self.bouton_connexion.clicked.connect(self._tenter_connexion)
        layout_carte.addWidget(self.bouton_connexion)

        # --- Centrage de la carte dans la fenêtre ---
        layout_general.addStretch()
        ligne_centrale = QHBoxLayout()
        ligne_centrale.addStretch()
        ligne_centrale.addWidget(self.carte)
        ligne_centrale.addStretch()
        layout_general.addLayout(ligne_centrale)
        layout_general.addStretch()

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

    def _basculer_visibilite_mdp(self):
        self._mot_de_passe_visible = not self._mot_de_passe_visible
        if self._mot_de_passe_visible:
            self.champ_mot_de_passe.setEchoMode(QLineEdit.EchoMode.Normal)
            self.bouton_toggle_mdp.setIcon(qta.icon('fa5s.eye-slash', color='#8b8d98'))
        else:
            self.champ_mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
            self.bouton_toggle_mdp.setIcon(qta.icon('fa5s.eye', color='#8b8d98'))

    def _tenter_connexion(self):
        login = self.champ_login.text().strip()
        mot_de_passe = self.champ_mot_de_passe.text()

        self.bouton_connexion.setEnabled(False)
        self.label_erreur.setVisible(False)

        try:
            user: User | None = self.auth_controller.authentifier(login, mot_de_passe)
        finally:
            self.bouton_connexion.setEnabled(True)

        if user is not None:
            self.connexion_reussie.emit(user)
        else:
            self.label_erreur.setVisible(True)
            self.champ_mot_de_passe.clear()
            self.champ_mot_de_passe.setFocus()
