import qtawesome as qta

from PyQt6.QtCore import Qt, QEvent, QTimer, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QCheckBox,
)

from controllers.auth.auth_controller import AuthController
from models.user import User
from services.theme import charger_theme


class _ChampIcone(QFrame):
    """Conteneur (icône + QLineEdit) qui simule un seul champ unifié.
    La bordure accent s'active quand le champ interne prend le focus.
    """

    def __init__(self, icone_id: str, placeholder: str, parent=None):
        super().__init__(parent)
        self.setObjectName("conteneurChamp")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._icone_label = QLabel()
        self._icone_label.setObjectName("iconeChamp")
        self._icone_label.setFixedSize(40, 42)
        self._icone_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icone_label.setPixmap(
            qta.icon(icone_id, color="#5c5f6e").pixmap(14, 14)
        )
        layout.addWidget(self._icone_label)

        self.champ = QLineEdit()
        self.champ.setObjectName("champAvecIcone")
        self.champ.setPlaceholderText(placeholder)
        self.champ.setFixedHeight(42)
        self.champ.installEventFilter(self)
        layout.addWidget(self.champ)

    def eventFilter(self, obj, event):
        if obj is self.champ:
            if event.type() == QEvent.Type.FocusIn:
                self.setProperty("actif", True)
                self._repolish()
            elif event.type() == QEvent.Type.FocusOut:
                self.setProperty("actif", False)
                self._repolish()
        return super().eventFilter(obj, event)

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)


class LoginView(QWidget):
    connexion_reussie = pyqtSignal(object, bool)  # (User, souvenir)

    def __init__(self, auth_controller: AuthController):
        super().__init__()
        self.auth_controller = auth_controller
        self._mot_de_passe_visible = False

        self.setWindowTitle("E-Konnekta — Connexion")
        self.setFixedSize(440, 600)

        self._construire_interface()
        self._appliquer_theme()
        self._centrer_sur_ecran()

    def _construire_interface(self):
        layout_general = QVBoxLayout(self)
        layout_general.setContentsMargins(0, 0, 0, 0)
        layout_general.setSpacing(0)

        # ── Carte centrale ──────────────────────────────────────────────
        self.carte = QFrame()
        self.carte.setObjectName("cardLogin")
        self.carte.setFixedWidth(368)

        layout_carte = QVBoxLayout(self.carte)
        layout_carte.setContentsMargins(36, 36, 36, 32)
        layout_carte.setSpacing(0)

        # ── Branding ────────────────────────────────────────────────────
        # Cercle avec icône WiFi
        cercle = QLabel()
        cercle.setObjectName("cercleIconeLogin")
        cercle.setFixedSize(68, 68)
        cercle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cercle.setPixmap(qta.icon("fa5s.wifi", color="#5b6ee8").pixmap(QSize(30, 30)))
        layout_carte.addWidget(cercle, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_carte.addSpacing(14)

        titre = QLabel("E-Konnekta")
        titre.setObjectName("titreApp")
        layout_carte.addWidget(titre, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_carte.addSpacing(4)

        badge_zone = QLabel("WiFi-Zone")
        badge_zone.setObjectName("badgeZoneLogin")
        layout_carte.addWidget(badge_zone, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_carte.addSpacing(20)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurLogin")
        layout_carte.addWidget(sep)

        layout_carte.addSpacing(20)

        sous_titre = QLabel("Connectez-vous à votre espace")
        sous_titre.setObjectName("sousTitre")
        layout_carte.addWidget(sous_titre, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_carte.addSpacing(24)

        # ── Champ identifiant ───────────────────────────────────────────
        layout_carte.addWidget(self._label_champ("Identifiant"))
        layout_carte.addSpacing(5)

        self._champ_login_frame = _ChampIcone("fa5s.user", "Votre identifiant")
        self.champ_login = self._champ_login_frame.champ
        self.champ_login.returnPressed.connect(self._tenter_connexion)
        layout_carte.addWidget(self._champ_login_frame)

        layout_carte.addSpacing(16)

        # ── Champ mot de passe ──────────────────────────────────────────
        layout_carte.addWidget(self._label_champ("Mot de passe"))
        layout_carte.addSpacing(5)

        self._champ_mdp_frame = _ChampIcone("fa5s.lock", "Votre mot de passe")
        self.champ_mot_de_passe = self._champ_mdp_frame.champ
        self.champ_mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self.champ_mot_de_passe.returnPressed.connect(self._tenter_connexion)

        # Bouton afficher/masquer injecté à droite du champ mdp
        self.bouton_toggle_mdp = QPushButton()
        self.bouton_toggle_mdp.setIcon(qta.icon("fa5s.eye", color="#5c5f6e"))
        self.bouton_toggle_mdp.setObjectName("boutonToggleMdp")
        self.bouton_toggle_mdp.setFixedSize(40, 42)
        self.bouton_toggle_mdp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_toggle_mdp.clicked.connect(self._basculer_visibilite_mdp)
        self._champ_mdp_frame.layout().addWidget(self.bouton_toggle_mdp)

        layout_carte.addWidget(self._champ_mdp_frame)

        # ── Se souvenir de moi ──────────────────────────────────────────
        layout_carte.addSpacing(6)
        self._checkbox_souvenir = QCheckBox("Se souvenir de moi")
        self._checkbox_souvenir.setObjectName("checkboxSouvenir")
        self._checkbox_souvenir.setChecked(True)
        layout_carte.addWidget(self._checkbox_souvenir)

        # ── Message d'erreur ────────────────────────────────────────────
        self.label_erreur = QLabel("Identifiant ou mot de passe incorrect.")
        self.label_erreur.setObjectName("labelErreur")
        self.label_erreur.setStyleSheet(
            "color: #f87171;"
            "background-color: rgba(248,113,113,0.10);"
            "border: 1px solid rgba(248,113,113,0.25);"
            "border-radius: 6px;"
            "padding: 6px 10px;"
            "font-size: 12px;"
        )
        self.label_erreur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_erreur.setVisible(False)
        layout_carte.addSpacing(10)
        layout_carte.addWidget(self.label_erreur)

        layout_carte.addSpacing(22)

        # ── Bouton connexion ────────────────────────────────────────────
        self.bouton_connexion = QPushButton("  Se connecter")
        self.bouton_connexion.setObjectName("boutonConnexion")
        self.bouton_connexion.setIcon(qta.icon("fa5s.sign-in-alt", color="#ffffff"))
        self.bouton_connexion.setIconSize(QSize(16, 16))
        self.bouton_connexion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bouton_connexion.setFixedHeight(46)
        self.bouton_connexion.clicked.connect(self._tenter_connexion)
        layout_carte.addWidget(self.bouton_connexion)

        # ── Centrage de la carte ────────────────────────────────────────
        layout_general.addStretch(2)
        ligne = QHBoxLayout()
        ligne.addStretch()
        ligne.addWidget(self.carte)
        ligne.addStretch()
        layout_general.addLayout(ligne)
        layout_general.addStretch(1)

        # ── Pied de page ────────────────────────────────────────────────
        footer = QLabel("© 2025 E-Konnekta · Gestion WiFi Hotspot")
        footer.setObjectName("footerLogin")
        layout_general.addWidget(footer, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_general.addSpacing(14)

    @staticmethod
    def _label_champ(texte: str) -> QLabel:
        lbl = QLabel(texte)
        lbl.setObjectName("labelChamp")
        return lbl

    def _appliquer_theme(self):
        try:
            self.setStyleSheet(charger_theme())
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
            self.bouton_toggle_mdp.setIcon(qta.icon("fa5s.eye-slash", color="#5c5f6e"))
        else:
            self.champ_mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
            self.bouton_toggle_mdp.setIcon(qta.icon("fa5s.eye", color="#5c5f6e"))

    def _tenter_connexion(self):
        login = self.champ_login.text().strip()
        mot_de_passe = self.champ_mot_de_passe.text()

        self.bouton_connexion.setEnabled(False)
        self.label_erreur.setVisible(False)

        try:
            user: User | None = self.auth_controller.authentifier(login, mot_de_passe)
        except RuntimeError as exc:
            self._afficher_erreur(str(exc))
            restant = self.auth_controller.restant_blocage(login)
            if restant > 0:
                self._demarrer_countdown(login, restant)
            else:
                self.bouton_connexion.setEnabled(True)
            self.champ_mot_de_passe.clear()
            return
        finally:
            pass  # activation gérée ci-dessus ou après succès

        if user is not None:
            self.bouton_connexion.setEnabled(True)
            souvenir = self._checkbox_souvenir.isChecked()
            self.connexion_reussie.emit(user, souvenir)
        else:
            self.bouton_connexion.setEnabled(True)
            self._afficher_erreur("Identifiant ou mot de passe incorrect.")
            self.champ_mot_de_passe.clear()
            self.champ_mot_de_passe.setFocus()

    def _afficher_erreur(self, message: str):
        self.label_erreur.setText(message)
        self.label_erreur.setVisible(True)
        self.champ_mot_de_passe.setFocus()

    def _demarrer_countdown(self, login: str, secondes: int):
        """Désactive le bouton et affiche un compte à rebours pendant le blocage."""
        self._countdown_restant = secondes
        self._countdown_login   = login

        self._timer_countdown = QTimer(self)
        self._timer_countdown.setInterval(1000)
        self._timer_countdown.timeout.connect(self._tick_countdown)
        self._timer_countdown.start()
        self._tick_countdown()

    def _tick_countdown(self):
        restant = self.auth_controller.restant_blocage(self._countdown_login)
        if restant > 0:
            self._afficher_erreur(
                f"Trop de tentatives. Réessayez dans {restant} seconde(s)."
            )
            self.bouton_connexion.setEnabled(False)
        else:
            self._timer_countdown.stop()
            self.bouton_connexion.setEnabled(True)
            self.label_erreur.setVisible(False)
            self.champ_mot_de_passe.setFocus()
