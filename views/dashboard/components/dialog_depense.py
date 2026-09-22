import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QDoubleSpinBox, QMessageBox,
)

from controllers.depenses.depenses_controller import DepensesController
from models.depense import CATEGORIES_DEPENSES


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("separateurSession")
    return f


class DialogDepense(QDialog):
    """Formulaire d'ajout d'une dépense."""

    def __init__(self, controller: DepensesController, user_id: int, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._user_id = user_id

        self.setWindowTitle("Ajouter une dépense")
        self.setModal(True)
        self.setFixedWidth(400)
        self.setObjectName("dialogStock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.money-bill-wave", color="#5b6ee8").pixmap(18, 18))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Ajouter une dépense")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()
        lay.addLayout(h_titre)
        lay.addWidget(_sep())
        lay.addSpacing(6)

        # ── Montant ───────────────────────────────────────────────────
        lbl_montant = QLabel("Montant (Ar)")
        lbl_montant.setObjectName("labelParametre")
        lay.addWidget(lbl_montant)

        self._spin_montant = QDoubleSpinBox()
        self._spin_montant.setObjectName("comboParametres")
        self._spin_montant.setRange(1, 9_999_999_999)
        self._spin_montant.setSingleStep(1000)
        self._spin_montant.setDecimals(0)
        self._spin_montant.setFixedHeight(38)
        lay.addWidget(self._spin_montant)

        # ── Motif ─────────────────────────────────────────────────────
        lbl_motif = QLabel("Motif / désignation")
        lbl_motif.setObjectName("labelParametre")
        lay.addWidget(lbl_motif)

        self._champ_motif = QLineEdit()
        self._champ_motif.setObjectName("champParametres")
        self._champ_motif.setFixedHeight(38)
        self._champ_motif.setPlaceholderText("Ex. : Achat papier, facture électricité…")
        lay.addWidget(self._champ_motif)

        # ── Catégorie ─────────────────────────────────────────────────
        lbl_cat = QLabel("Catégorie")
        lbl_cat.setObjectName("labelParametre")
        lay.addWidget(lbl_cat)

        self._combo_categorie = QComboBox()
        self._combo_categorie.setObjectName("comboParametres")
        self._combo_categorie.setFixedHeight(38)
        self._combo_categorie.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, label in CATEGORIES_DEPENSES:
            self._combo_categorie.addItem(label, code)
        lay.addWidget(self._combo_categorie)

        # ── Méthode de paiement ───────────────────────────────────────
        lbl_methode = QLabel("Méthode de paiement")
        lbl_methode.setObjectName("labelParametre")
        lay.addWidget(lbl_methode)

        self._combo_methode = QComboBox()
        self._combo_methode.setObjectName("comboParametres")
        self._combo_methode.setFixedHeight(38)
        self._combo_methode.setCursor(Qt.CursorShape.PointingHandCursor)
        self._combo_methode.addItem("Espèces",      "especes")
        self._combo_methode.addItem("Mobile Money", "mobile_money")
        self._combo_methode.addItem("Carte",        "carte")
        lay.addWidget(self._combo_methode)

        lay.addSpacing(6)

        # ── Actions ───────────────────────────────────────────────────
        h_act = QHBoxLayout()
        h_act.setSpacing(10)
        btn_ann = QPushButton("Annuler")
        btn_ann.setObjectName("boutonActionHistorique")
        btn_ann.setFixedHeight(42)
        btn_ann.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ann.clicked.connect(self.reject)
        h_act.addWidget(btn_ann)
        h_act.addStretch()

        btn_save = QPushButton("  Enregistrer")
        btn_save.setObjectName("boutonVendre")
        btn_save.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        btn_save.setFixedHeight(42)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._enregistrer)
        h_act.addWidget(btn_save)

        lay.addLayout(h_act)

    def _enregistrer(self):
        montant = self._spin_montant.value()
        resultat = self._controller.creer_depense(
            montant=montant,
            motif=self._champ_motif.text(),
            categorie=self._combo_categorie.currentData(),
            methode=self._combo_methode.currentData(),
            user_id=self._user_id,
        )
        if resultat.get("ok"):
            self.accept()
        else:
            QMessageBox.warning(self, "Erreur", resultat.get("message", "Erreur inconnue."))