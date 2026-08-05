import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox,
)

from config.settings import TARIFICATION_PRIX_PAR_HEURE, TARIFICATION_DEBIT_DEFAUT_MBPS
from views.dashboard.components.spin_duree import SpinDuree


class DialogProfil(QDialog):
    """Dialog d'ajout ou de modification d'un profil hotspot."""

    profil_modifie = pyqtSignal()

    def __init__(self, routers: list[dict], profil: dict | None = None, parent=None):
        super().__init__(parent)
        self._routers = routers
        self._profil = profil

        self.setWindowTitle("Modifier le profil" if profil else "Ajouter un profil")
        self.setModal(True)
        self.setFixedSize(460, 620)
        self.setObjectName("dialogVente")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        page = self._construire_formulaire()
        layout.addWidget(page)

    def _champ(self, label: str, widget, auto_style: bool = True) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("titreSectionSessions")
        vbox.addWidget(lbl)
        if auto_style:
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
        ico.setPixmap(qta.icon("fa5s.wifi", color="#5b6ee8").pixmap(20, 20))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Modifier le profil" if self._profil else "Nouveau profil")
        titre.setObjectName("titreDialog")
        h_titre.addWidget(titre)
        h_titre.addStretch()

        if self._profil:
            statut_actif = self._profil.get("statut") == "actif"
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
        self._input_nom.setPlaceholderText("Ex : 1h — 2 Mbps")
        if self._profil:
            self._input_nom.setText(self._profil["nom"])
        lay.addLayout(self._champ("NOM DU PROFIL", self._input_nom))
        lay.addSpacing(12)

        # ── Routeur ──────────────────────────────────────────────────
        self._combo_router = QComboBox()
        for r in self._routers:
            self._combo_router.addItem(r["nom"], userData=r["id"])
        if self._profil:
            for i, r in enumerate(self._routers):
                if r["id"] == self._profil["router_id"]:
                    self._combo_router.setCurrentIndex(i)
                    break
        lay.addLayout(self._champ("ROUTEUR", self._combo_router))
        lay.addSpacing(12)

        # ── Débit max ────────────────────────────────────────────────
        self._spin_debit = QSpinBox()
        self._spin_debit.setRange(1, 1000)
        self._spin_debit.setSuffix(" Mbps")
        if self._profil:
            self._spin_debit.setValue(self._profil["debit_max"] // 1024)
        else:
            self._spin_debit.setValue(TARIFICATION_DEBIT_DEFAUT_MBPS)
        lay.addLayout(self._champ("DÉBIT MAX", self._spin_debit))
        lay.addSpacing(12)

        # ── Durée session ────────────────────────────────────────────
        duree_init = self._profil["duree_session_max"] if self._profil else 60
        self._spin_duree = SpinDuree(duree_init)
        self._spin_duree.changed.connect(lambda _: self._calculer_prix())
        lay.addLayout(self._champ("DURÉE SESSION", self._spin_duree, auto_style=False))
        lay.addSpacing(12)

        # ── Validité (stockée en heures, SpinDuree travaille en minutes) ─
        validite_init = (self._profil["validite"] * 60) if self._profil else 1440  # 24h par défaut
        self._spin_validite = SpinDuree(validite_init)
        lay.addLayout(self._champ("VALIDITÉ (après connexion)", self._spin_validite, auto_style=False))
        lay.addSpacing(12)

        # ── Statut ───────────────────────────────────────────────────
        self._combo_statut = QComboBox()
        self._combo_statut.addItem("Actif (vendu)",   userData="actif")
        self._combo_statut.addItem("Inactif (masqué)", userData="inactif")
        if self._profil and self._profil.get("statut") == "inactif":
            self._combo_statut.setCurrentIndex(1)
        lay.addLayout(self._champ("STATUT", self._combo_statut))
        lay.addSpacing(8)

        encart = QFrame()
        encart.setObjectName("encartStatut")
        encart_lay = QHBoxLayout(encart)
        encart_lay.setContentsMargins(12, 8, 12, 8)
        lbl_encart = QLabel("Un profil inactif est masqué de la vente, mais son historique est conservé.")
        lbl_encart.setObjectName("encartStatutTexte")
        lbl_encart.setWordWrap(True)
        encart_lay.addWidget(lbl_encart)
        lay.addWidget(encart)
        lay.addSpacing(12)

        # ── Prix ─────────────────────────────────────────────────────
        lbl_prix = QLabel("PRIX")
        lbl_prix.setObjectName("titreSectionSessions")

        self._spin_prix = QDoubleSpinBox()
        self._spin_prix.setRange(0, 9999999)
        self._spin_prix.setSuffix(" Ar")
        self._spin_prix.setDecimals(0)
        self._spin_prix.setReadOnly(True)
        self._spin_prix.setFixedHeight(40)
        self._spin_prix.setObjectName("comboParametres")
        self._spin_prix.setStyleSheet("background-color: #1a1b26; color: #a9b1d6;")

        self._chk_prix_manuel = QCheckBox("Manuel")
        self._chk_prix_manuel.setObjectName("labelParametre")
        self._chk_prix_manuel.toggled.connect(self._toggle_prix_manuel)

        vbox_prix = QVBoxLayout()
        vbox_prix.setSpacing(4)
        vbox_prix.addWidget(lbl_prix)

        h_prix_input = QHBoxLayout()
        h_prix_input.setSpacing(8)
        h_prix_input.addWidget(self._spin_prix, stretch=1)
        h_prix_input.addWidget(self._chk_prix_manuel)
        vbox_prix.addLayout(h_prix_input)

        lay.addLayout(vbox_prix)

        if self._profil:
            self._spin_prix.setValue(self._profil["prix"])
            # Si le prix ne correspond pas au calcul auto, activer le mode manuel
            duree_h = self._profil["duree_session_max"] / 60
            prix_calcule = round(duree_h * TARIFICATION_PRIX_PAR_HEURE)
            if self._profil["prix"] != prix_calcule:
                self._chk_prix_manuel.setChecked(True)
        else:
            self._calculer_prix()

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

    def _toggle_prix_manuel(self, coche: bool):
        self._spin_prix.setReadOnly(not coche)
        if coche:
            self._spin_prix.setStyleSheet("background-color: #1a1b26; color: #c0caf5;")
        else:
            self._spin_prix.setStyleSheet("background-color: #1a1b26; color: #a9b1d6;")
            self._calculer_prix()

    def _calculer_prix(self):
        if not hasattr(self, "_spin_prix"):
            return
        if self._chk_prix_manuel.isChecked():
            return
        duree_h = self._spin_duree.valeur_minutes / 60
        prix = round(duree_h * TARIFICATION_PRIX_PAR_HEURE)
        self._spin_prix.setValue(prix)

    def _sauvegarder(self):
        data = self._collecter_donnees()
        if data is None:
            return

        if self._profil:
            data["id"] = self._profil["id"]

        self._donnees = data
        self.profil_modifie.emit()
        self.accept()

    def _collecter_donnees(self) -> dict | None:
        nom = self._input_nom.text().strip()
        if not nom:
            self._input_nom.setFocus()
            return None

        return {
            "router_id":         self._combo_router.currentData(),
            "nom":               nom,
            "debit_max":         self._spin_debit.value() * 1024,
            "duree_session_max": self._spin_duree.valeur_minutes,
            "validite":          self._spin_validite.valeur_minutes // 60,
            "prix":              self._spin_prix.value(),
            "statut":            self._combo_statut.currentData(),
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
