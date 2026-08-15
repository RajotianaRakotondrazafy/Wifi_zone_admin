import qtawesome as qta
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QSpinBox, QListWidget, QMessageBox,
)


_STATUTS = [
    ("actif",   "Actif"),
    ("inactif", "Inactif"),
    ("erreur",  "Erreur"),
]


class DetectionMikrotikThread(QThread):
    """Scanne le réseau local en arrière-plan pour trouver les MikroTik."""

    terminee = pyqtSignal(list)
    echouee = pyqtSignal(str)

    def run(self):
        try:
            from services.mikrotik_service import detecter_mikrotiks
            self.terminee.emit(detecter_mikrotiks())
        except Exception as exc:
            self.echouee.emit(str(exc))


class DialogChoixMikrotik(QDialog):
    """Sélection d'un MikroTik détecté sur le réseau."""

    def __init__(self, appareils: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("MikroTik détectés")
        self.setModal(True)
        self.setObjectName("dialogVente")
        self._adresse: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        titre = QLabel("Choisir un routeur détecté :")
        titre.setObjectName("titreSectionSessions")
        lay.addWidget(titre)

        self._liste = QListWidget()
        self._liste.setObjectName("comboParametres")
        for a in appareils:
            self._liste.addItem(a["adresse_ip"])
        self._liste.setCurrentRow(0)
        hauteur = min(220, 34 * len(appareils) + 8)
        self._liste.setFixedHeight(hauteur)
        lay.addWidget(self._liste)

        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)
        h_btn.addStretch()

        btn_annuler = QPushButton("Annuler")
        btn_annuler.setObjectName("boutonActionHistorique")
        btn_annuler.setFixedHeight(40)
        btn_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_annuler.clicked.connect(self.reject)
        h_btn.addWidget(btn_annuler)

        btn_ok = QPushButton("  Utiliser cette IP")
        btn_ok.setObjectName("boutonVendre")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self._valider)
        h_btn.addWidget(btn_ok)

        lay.addLayout(h_btn)

    def _valider(self):
        item = self._liste.currentItem()
        if item is not None:
            self._adresse = item.text()
        self.accept()

    @property
    def adresse_selectionnee(self) -> str | None:
        return self._adresse


class DialogZone(QDialog):
    """Dialog d'ajout ou de modification d'une zone WiFi (routeur MikroTik)."""

    zone_modifiee = pyqtSignal()

    def __init__(self, zone: dict | None = None, parent=None):
        super().__init__(parent)
        self._zone = zone
        self._thread: DetectionMikrotikThread | None = None

        self.setWindowTitle("Modifier la zone" if zone else "Ajouter une zone")
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
        frame.setObjectName("pageDialogZone")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        # ── Titre ────────────────────────────────────────────────────
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.wifi", color="#5b6ee8").pixmap(20, 20))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Modifier la zone" if self._zone else "Nouvelle zone")
        titre.setObjectName("titreDialog")
        h_titre.addWidget(titre)
        h_titre.addStretch()

        if self._zone:
            statut_actif = self._zone.get("statut") == "actif"
            badge = QLabel("  Actif  " if statut_actif else "  Inactif  ")
            badge.setObjectName("badgeStatutDialog")
            badge.setProperty("actif", statut_actif)
            h_titre.addWidget(badge)

        lay.addLayout(h_titre)

        lay.addSpacing(8)
        lay.addWidget(self._sep())
        lay.addSpacing(12)

        # ── Nom ──────────────────────────────────────────────────────
        self._input_nom = QLineEdit()
        self._input_nom.setPlaceholderText("Ex : Zone A — Salle d'attente")
        if self._zone:
            self._input_nom.setText(self._zone["nom"])
        lay.addLayout(self._champ("NOM DE LA ZONE", self._input_nom))
        lay.addSpacing(12)

        # ── Adresse IP ───────────────────────────────────────────────
        v_ip = QVBoxLayout()
        v_ip.setSpacing(4)
        lbl_ip = QLabel("ADRESSE IP DU ROUTEUR")
        lbl_ip.setObjectName("titreSectionSessions")
        v_ip.addWidget(lbl_ip)

        h_ip = QHBoxLayout()
        h_ip.setSpacing(8)
        self._input_ip = QLineEdit()
        self._input_ip.setPlaceholderText("192.168.1.1")
        if self._zone:
            self._input_ip.setText(self._zone["adresse_ip"])
        self._input_ip.setFixedHeight(40)
        self._input_ip.setObjectName("comboParametres")
        h_ip.addWidget(self._input_ip, stretch=1)

        self._btn_detecter = QPushButton(" Détecter")
        self._btn_detecter.setObjectName("boutonActionHistorique")
        self._btn_detecter.setIcon(qta.icon("fa5s.broadcast-tower", color="#8b8d98"))
        self._btn_detecter.setFixedHeight(40)
        self._btn_detecter.setFixedWidth(96)
        self._btn_detecter.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_detecter.setToolTip("Scanner le réseau local (port API 8728)")
        self._btn_detecter.clicked.connect(self._detecter_mikrotik)
        h_ip.addWidget(self._btn_detecter)

        v_ip.addLayout(h_ip)
        lay.addLayout(v_ip)
        lay.addSpacing(12)

        # ── Port API ─────────────────────────────────────────────────
        self._spin_port = QSpinBox()
        self._spin_port.setRange(1, 65535)
        self._spin_port.setValue(self._zone["port_api"] if self._zone else 8728)
        lay.addLayout(self._champ("PORT API ROUTEROS", self._spin_port))
        lay.addSpacing(12)

        # ── Nom d'utilisateur ────────────────────────────────────────
        self._input_username = QLineEdit()
        self._input_username.setPlaceholderText("admin")
        if self._zone:
            self._input_username.setText(self._zone["username"])
        lay.addLayout(self._champ("NOM D'UTILISATEUR", self._input_username))
        lay.addSpacing(12)

        # ── Mot de passe ─────────────────────────────────────────────
        self._input_password = QLineEdit()
        self._input_password.setPlaceholderText(
            "Nouveau mot de passe…" if self._zone else "Mot de passe API"
        )
        self._input_password.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addLayout(self._champ("MOT DE PASSE API", self._input_password))
        lay.addSpacing(12)

        # ── Statut ───────────────────────────────────────────────────
        self._combo_statut = QComboBox()
        statut_actuel = self._zone["statut"] if self._zone else "inactif"
        for valeur, libelle in _STATUTS:
            self._combo_statut.addItem(libelle, userData=valeur)
        for i, (valeur, _) in enumerate(_STATUTS):
            if valeur == statut_actuel:
                self._combo_statut.setCurrentIndex(i)
                break
        lay.addLayout(self._champ("STATUT", self._combo_statut))
        lay.addSpacing(8)

        encart = QFrame()
        encart.setObjectName("encartStatut")
        encart_lay = QHBoxLayout(encart)
        encart_lay.setContentsMargins(12, 8, 12, 8)
        lbl_encart = QLabel("Une zone inactive est marquée hors ligne et ne propose plus de profils à la vente.")
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

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            thread = self._thread
            thread.setParent(None)
            try:
                thread.terminee.disconnect(self._on_detection_ok)
                thread.echouee.disconnect(self._on_detection_erreur)
            except TypeError:
                pass
            thread.finished.connect(thread.deleteLater)
        super().closeEvent(event)

    def _detecter_mikrotik(self):
        if self._thread is not None and self._thread.isRunning():
            return
        self._btn_detecter.setEnabled(False)
        self._btn_detecter.setText(" Scan…")
        self._thread = DetectionMikrotikThread(self)
        self._thread.terminee.connect(self._on_detection_ok)
        self._thread.echouee.connect(self._on_detection_erreur)
        self._thread.start()

    def _on_detection_ok(self, appareils: list):
        self._btn_detecter.setEnabled(True)
        self._btn_detecter.setText(" Détecter")
        if not appareils:
            QMessageBox.information(
                self, "Aucun routeur détecté",
                "Aucun équipement avec le port API RouterOS (8728) ouvert.\n"
                "Vérifiez dans Winbox : IP → Services → api doit être activé.",
            )
            return
        choix = DialogChoixMikrotik(appareils, self)
        if choix.exec():
            ip = choix.adresse_selectionnee
            if ip:
                self._input_ip.setText(ip)
                self._input_ip.setFocus()

    def _on_detection_erreur(self, message: str):
        self._btn_detecter.setEnabled(True)
        self._btn_detecter.setText(" Détecter")
        QMessageBox.critical(self, "Erreur", f"Échec de la détection : {message}")

    def _sauvegarder(self):
        data = self._collecter_donnees()
        if data is None:
            return

        if self._zone:
            data["id"] = self._zone["id"]

        self._donnees = data
        self.zone_modifiee.emit()
        self.accept()

    def _collecter_donnees(self) -> dict | None:
        nom = self._input_nom.text().strip()
        if not nom:
            self._input_nom.setFocus()
            return None

        adresse_ip = self._input_ip.text().strip()
        if not adresse_ip:
            self._input_ip.setFocus()
            return None

        username = self._input_username.text().strip()
        if not username:
            self._input_username.setFocus()
            return None

        return {
            "nom":        nom,
            "adresse_ip": adresse_ip,
            "port_api":   self._spin_port.value(),
            "username":   username,
            "password":   self._input_password.text(),
            "statut":     self._combo_statut.currentData(),
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
