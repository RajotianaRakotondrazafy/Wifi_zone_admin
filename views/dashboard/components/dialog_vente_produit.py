import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QSpinBox, QButtonGroup,
)

_METHODES = {
    "especes":      "Espèces",
    "mobile_money": "Mobile Money",
    "carte":        "Carte",
}


class DialogVenteProduit(QDialog):
    """Vente d'un produit du multiservice (prix fixe ou variable)."""

    vente_confirmee = pyqtSignal(dict)

    def __init__(self, produits: list[dict], parent=None):
        super().__init__(parent)
        self._produits = produits
        self._methode = "especes"

        self.setWindowTitle("Vendre un produit")
        self.setModal(True)
        self.setFixedWidth(440)
        self.setObjectName("dialogStock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(14)

        # ── En-tête ────────────────────────────────────────────────────
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.shopping-basket", color="#5b6ee8").pixmap(18, 18))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Vendre un produit")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()
        lay.addLayout(h_titre)
        lay.addWidget(self._sep())
        lay.addSpacing(6)

        # ── Produit ────────────────────────────────────────────────────
        lay.addWidget(self._lbl_section("PRODUIT"))
        lay.addSpacing(6)

        self._combo_produit = QComboBox()
        self._combo_produit.setObjectName("comboParametres")
        self._combo_produit.setFixedHeight(42)
        self._combo_produit.setCursor(Qt.CursorShape.PointingHandCursor)
        for p in self._produits:
            self._combo_produit.addItem(
                f"{p['nom']}  —  {p['categorie_label']}",
                userData=p,
            )
        self._combo_produit.currentIndexChanged.connect(self._on_produit_change)
        lay.addWidget(self._combo_produit)
        lay.addSpacing(4)

        # ── Quantité + prix ─────────────────────────────────────────────
        h_prix = QHBoxLayout()
        h_prix.setSpacing(12)

        col_q = QVBoxLayout()
        col_q.setSpacing(4)
        lbl_q = QLabel("Quantité")
        lbl_q.setObjectName("labelParametre")
        col_q.addWidget(lbl_q)
        self._spin_quantite = QSpinBox()
        self._spin_quantite.setObjectName("comboParametres")
        self._spin_quantite.setRange(1, 999)
        self._spin_quantite.setValue(1)
        self._spin_quantite.valueChanged.connect(self._maj_total)
        col_q.addWidget(self._spin_quantite)
        h_prix.addLayout(col_q)

        col_p = QVBoxLayout()
        col_p.setSpacing(4)
        lbl_p = QLabel("Prix unitaire (Ar)")
        lbl_p.setObjectName("labelParametre")
        col_p.addWidget(lbl_p)
        self._spin_prix = QSpinBox()
        self._spin_prix.setObjectName("comboParametres")
        self._spin_prix.setRange(0, 50_000_000)
        self._spin_prix.setSingleStep(100)
        self._spin_prix.setValue(0)
        self._spin_prix.valueChanged.connect(self._maj_total)
        col_p.addWidget(self._spin_prix)
        h_prix.addLayout(col_p)

        lay.addLayout(h_prix)

        # ── Mode de paiement ────────────────────────────────────────────
        lay.addSpacing(6)
        lay.addWidget(self._lbl_section("MODE DE PAIEMENT"))
        lay.addSpacing(6)

        h_pay = QHBoxLayout()
        h_pay.setSpacing(8)
        self._grp_pay = QButtonGroup(self)
        self._grp_pay.setExclusive(True)
        for label, valeur, icone_id in [
            ("Espèces",      "especes",      "fa5s.money-bill-wave"),
            ("Mobile Money", "mobile_money", "fa5s.mobile-alt"),
            ("Carte",        "carte",        "fa5s.credit-card"),
        ]:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("boutonPaiement")
            btn.setCheckable(True)
            btn.setIcon(qta.icon(icone_id, color="#8b8d98"))
            btn.setProperty("valeur", valeur)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grp_pay.addButton(btn)
            h_pay.addWidget(btn)
        self._grp_pay.buttons()[0].setChecked(True)
        self._grp_pay.buttonClicked.connect(
            lambda b: setattr(self, "_methode", b.property("valeur"))
        )
        lay.addLayout(h_pay)

        lay.addStretch()
        lay.addWidget(self._sep())
        lay.addSpacing(10)

        # ── Actions ─────────────────────────────────────────────────────
        h_act = QHBoxLayout()
        h_act.setSpacing(10)

        btn_ann = QPushButton("Annuler")
        btn_ann.setObjectName("boutonActionHistorique")
        btn_ann.setFixedHeight(44)
        btn_ann.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ann.clicked.connect(self.reject)
        h_act.addWidget(btn_ann)
        h_act.addStretch()

        self._btn_confirmer = QPushButton()
        self._btn_confirmer.setObjectName("boutonVendre")
        self._btn_confirmer.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        self._btn_confirmer.setFixedHeight(44)
        self._btn_confirmer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_confirmer.clicked.connect(self._confirmer)
        h_act.addWidget(self._btn_confirmer)

        lay.addLayout(h_act)

        self._on_produit_change(0)

    # ── Logique ─────────────────────────────────────────────────────────

    def _on_produit_change(self, idx: int):
        produit = self._combo_produit.itemData(idx)
        if produit is None:
            return
        if produit.get("prix_fixe") and produit.get("prix_unitaire"):
            self._spin_prix.blockSignals(True)
            self._spin_prix.setValue(int(produit["prix_unitaire"]))
            self._spin_prix.blockSignals(False)
        self._maj_total()

    def _maj_total(self):
        total = self._spin_quantite.value() * self._spin_prix.value()
        self._btn_confirmer.setText(f"  Confirmer — {total:,} Ar".replace(",", " "))

    def _confirmer(self):
        produit = self._combo_produit.currentData()
        if produit is None:
            return
        self.vente_confirmee.emit({
            "produit_id":  produit["id"],
            "produit":     produit["nom"],
            "quantite":    self._spin_quantite.value(),
            "prix_unitaire": self._spin_prix.value(),
            "methode":     self._methode,
        })
        self.accept()

    # ── Helpers UI ──────────────────────────────────────────────────────

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setObjectName("separateurSession")
        return f

    @staticmethod
    def _lbl_section(texte: str) -> QLabel:
        l = QLabel(texte)
        l.setObjectName("titreSectionSessions")
        return l
