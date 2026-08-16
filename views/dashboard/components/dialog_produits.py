import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QScrollArea, QWidget,
)

from controllers.stock.stock_controller import StockController
from models.produit import CATEGORIES_PRODUITS, libelle_categorie
from utils.formatage import formater_montant
from views.dashboard.components.elide_label import LabelElide


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("separateurSession")
    return f


class DialogProduit(QDialog):
    """Formulaire d'ajout / modification d'un produit."""

    def __init__(self, controller: StockController, produit: dict | None = None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._produit = produit

        self.setWindowTitle("Modifier le produit" if produit else "Ajouter un produit")
        self.setModal(True)
        self.setFixedWidth(380)
        self.setObjectName("dialogStock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.box", color="#5b6ee8").pixmap(18, 18))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Modifier le produit" if produit else "Ajouter un produit")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()
        lay.addLayout(h_titre)
        lay.addWidget(self._sep())
        lay.addSpacing(6)

        # ── Nom ─────────────────────────────────────────────────────────
        lbl_nom = QLabel("Nom du produit")
        lbl_nom.setObjectName("labelParametre")
        lay.addWidget(lbl_nom)

        self._champ_nom = QLineEdit()
        self._champ_nom.setObjectName("champParametres")
        self._champ_nom.setFixedHeight(38)
        self._champ_nom.setPlaceholderText("Ex. : Film, Câble USB-C…")
        lay.addWidget(self._champ_nom)

        # ── Catégorie ───────────────────────────────────────────────────
        lbl_cat = QLabel("Catégorie")
        lbl_cat.setObjectName("labelParametre")
        lay.addWidget(lbl_cat)

        self._combo_categorie = QComboBox()
        self._combo_categorie.setObjectName("comboParametres")
        self._combo_categorie.setFixedHeight(38)
        self._combo_categorie.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, label in CATEGORIES_PRODUITS:
            self._combo_categorie.addItem(label, code)
        lay.addWidget(self._combo_categorie)

        # ── Prix ────────────────────────────────────────────────────────
        lbl_prix = QLabel("Prix par défaut (Ar)")
        lbl_prix.setObjectName("labelParametre")
        lay.addWidget(lbl_prix)

        self._champ_prix = QLineEdit()
        self._champ_prix.setObjectName("champParametres")
        self._champ_prix.setFixedHeight(38)
        self._champ_prix.setPlaceholderText("Laisser vide pour un prix variable")
        lay.addWidget(self._champ_prix)

        lay.addSpacing(6)

        # ── Actions ─────────────────────────────────────────────────────
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
        btn_save.setIcon(qta.icon("fa5s.save", color="#ffffff"))
        btn_save.setFixedHeight(42)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._enregistrer)
        h_act.addWidget(btn_save)

        lay.addLayout(h_act)

        if produit:
            self._champ_nom.setText(produit["nom"])
            idx = self._combo_categorie.findData(produit["categorie"])
            if idx >= 0:
                self._combo_categorie.setCurrentIndex(idx)
            if produit.get("prix_unitaire"):
                self._champ_prix.setText(str(int(produit["prix_unitaire"])))

    def _enregistrer(self):
        prix_texte = self._champ_prix.text().strip()
        prix = None
        if prix_texte:
            try:
                prix = float(prix_texte)
                if prix < 0:
                    raise ValueError
            except ValueError:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Prix invalide", "Le prix doit être un nombre positif.")
                return

        if self._produit:
            resultat = self._controller.modifier_produit(
                self._produit["id"],
                self._champ_nom.text(),
                self._combo_categorie.currentData(),
                prix,
            )
        else:
            resultat = self._controller.creer_produit(
                self._champ_nom.text(),
                self._combo_categorie.currentData(),
                prix,
            )

        from PyQt6.QtWidgets import QMessageBox
        if resultat.get("ok"):
            self.accept()
        else:
            QMessageBox.warning(self, "Erreur", resultat.get("message", "Erreur inconnue."))

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setObjectName("separateurSession")
        return f


class DialogGestionProduits(QDialog):
    """Liste des produits avec ajout, modification et activation."""

    produits_modifies = pyqtSignal()

    def __init__(self, controller: StockController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._rows: list[QWidget] = []

        self.setWindowTitle("Gérer les produits")
        self.setModal(True)
        self.setFixedSize(700, 500)
        self.setObjectName("dialogStock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(14)

        # ── En-tête ─────────────────────────────────────────────────────
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.boxes", color="#5b6ee8").pixmap(18, 18))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Gérer les produits")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()

        btn_ajouter = QPushButton("  Ajouter un produit")
        btn_ajouter.setObjectName("boutonActionLimiter")
        btn_ajouter.setIcon(qta.icon("fa5s.plus", color="#5b6ee8"))
        btn_ajouter.setFixedHeight(34)
        btn_ajouter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ajouter.clicked.connect(self._ajouter)
        h_titre.addWidget(btn_ajouter)

        lay.addLayout(h_titre)

        # ── Liste ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._conteneur = QWidget()
        self._layout_liste = QVBoxLayout(self._conteneur)
        self._layout_liste.setContentsMargins(0, 0, 0, 0)
        self._layout_liste.setSpacing(0)

        scroll.setWidget(self._conteneur)
        lay.addWidget(scroll, stretch=1)

        lay.addWidget(_sep())
        lay.addSpacing(4)

        h_fermer = QHBoxLayout()
        h_fermer.addStretch()
        btn_fermer = QPushButton("  Fermer")
        btn_fermer.setObjectName("boutonVendre")
        btn_fermer.setIcon(qta.icon("fa5s.times", color="#ffffff"))
        btn_fermer.setFixedWidth(140)
        btn_fermer.setFixedHeight(40)
        btn_fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fermer.clicked.connect(self.accept)
        h_fermer.addWidget(btn_fermer)
        h_fermer.addStretch()
        lay.addLayout(h_fermer)

        self._charger()

    def _charger(self):
        while self._layout_liste.count():
            item = self._layout_liste.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        produits = self._controller.obtenir_produits(actif_seulement=False)
        if not produits:
            lbl = QLabel("Aucun produit. Cliquez sur « Ajouter un produit ».")
            lbl.setObjectName("loginUtilisateur")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setContentsMargins(20, 18, 20, 18)
            self._layout_liste.addWidget(lbl, stretch=1)
            return

        for i, p in enumerate(produits):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                self._layout_liste.addWidget(sep)
            self._layout_liste.addWidget(self._ligne_produit(p))

        self._layout_liste.addStretch()

    def _ligne_produit(self, produit: dict) -> QWidget:
        ligne = QWidget()
        ligne.setObjectName("ligneVente")
        lay = QHBoxLayout(ligne)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # Nom
        lbl_nom = LabelElide(produit["nom"], largeur_min=120)
        lbl_nom.setObjectName("nomUtilisateur")
        lbl_nom.setStyleSheet("font-size:12px;")
        lbl_nom.setFixedWidth(160)
        lay.addWidget(lbl_nom)

        # Badge catégorie
        badge_cat = QLabel(libelle_categorie(produit["categorie"]))
        badge_cat.setObjectName("badgeNeutre")
        badge_cat.setFixedWidth(90)
        badge_cat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_cat)

        lay.addStretch()

        # Prix
        if produit.get("prix_fixe"):
            lbl_prix = QLabel(f"{formater_montant(produit['prix_unitaire'])} Ar")
            lbl_prix.setObjectName("montantVente")
        else:
            lbl_prix = QLabel("Prix variable")
            lbl_prix.setObjectName("prixVariableProduit")
        lbl_prix.setStyleSheet("font-size:13px;")
        lbl_prix.setFixedWidth(100)
        lbl_prix.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(lbl_prix)

        lay.addSpacing(6)

        # Modifier
        btn_edit = QPushButton("Modifier")
        btn_edit.setObjectName("boutonActionLimiter")
        btn_edit.setFixedHeight(28)
        btn_edit.setFixedWidth(92)
        btn_edit.setStyleSheet("font-size:11px;")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(lambda _, p=produit: self._modifier(p))
        lay.addWidget(btn_edit)

        # Activer / Désactiver
        if produit.get("actif"):
            btn_toggle = QPushButton("Désactiver")
            btn_toggle.setObjectName("boutonActionBloquer")
            btn_toggle.setFixedHeight(28)
            btn_toggle.setFixedWidth(100)
            btn_toggle.setStyleSheet("font-size:11px;")
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_toggle.clicked.connect(lambda _, p=produit: self._toggle(p))
        else:
            btn_toggle = QPushButton("Activer")
            btn_toggle.setObjectName("boutonActionLimiter")
            btn_toggle.setFixedHeight(28)
            btn_toggle.setFixedWidth(100)
            btn_toggle.setStyleSheet("font-size:11px;")
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_toggle.clicked.connect(lambda _, p=produit: self._toggle(p))
        lay.addWidget(btn_toggle)

        return ligne

    def _ajouter(self):
        dlg = DialogProduit(self._controller, parent=self)
        if dlg.exec() == DialogProduit.DialogCode.Accepted:
            self._charger()
            self.produits_modifies.emit()

    def _modifier(self, produit: dict):
        dlg = DialogProduit(self._controller, produit=produit, parent=self)
        if dlg.exec() == DialogProduit.DialogCode.Accepted:
            self._charger()
            self.produits_modifies.emit()

    def _toggle(self, produit: dict):
        from PyQt6.QtWidgets import QMessageBox
        actif = not produit.get("actif")
        resultat = self._controller.definir_actif(produit["id"], actif)
        if resultat.get("ok"):
            self._charger()
            self.produits_modifies.emit()
        else:
            QMessageBox.warning(self, "Erreur", resultat.get("message", "Erreur inconnue."))
