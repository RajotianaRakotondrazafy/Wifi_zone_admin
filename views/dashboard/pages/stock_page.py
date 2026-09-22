from datetime import date as _date, timedelta

import qtawesome as qta
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QDateEdit, QComboBox,
    QDialog, QDialogButtonBox,
)

from controllers.stock.stock_controller import StockController
from models.user import User
from utils.formatage import formater_montant
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.montant_masquable import MontantMasquable
from views.dashboard.components.elide_label import LabelElide
from views.dashboard.components.dialog_vente_produit import DialogVenteProduit
from views.dashboard.components.dialog_produits import DialogGestionProduits

_METHODES = {
    "especes":      ("Espèces",      "badgeActif"),
    "mobile_money": ("Mobile Money", "badgeCaissier"),
    "carte":        ("Carte",        "badgeAdmin"),
}


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("separateurSession")
    return f


class LigneVenteProduit(QWidget):
    """Ligne d'une vente produit dans l'historique du jour."""

    annulation_demande = pyqtSignal(dict)

    def __init__(self, vente: dict, annulable: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneVente")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(0)

        # Heure
        lbl_h = QLabel(vente["heure"])
        lbl_h.setObjectName("heureVente")
        lbl_h.setFixedWidth(48)
        lay.addWidget(lbl_h)

        lay.addSpacing(12)

        # Produit
        lbl_produit = LabelElide(vente["produit"], largeur_min=120)
        lbl_produit.setObjectName("nomUtilisateur")
        lay.addWidget(lbl_produit, stretch=1)

        lay.addSpacing(16)

        # Badge catégorie
        badge_cat = QLabel(vente["categorie_label"])
        badge_cat.setObjectName("badgeNeutre")
        badge_cat.setFixedWidth(90)
        badge_cat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_cat)

        lay.addSpacing(16)

        # Quantité × prix
        lbl_detail = MontantMasquable(
            f"{vente['quantite']} × {formater_montant(vente['prix_unitaire'])} Ar",
            object_name="labelHeure",
        )
        lbl_detail.setFixedWidth(118)
        lay.addWidget(lbl_detail)

        lay.addSpacing(16)

        # Montant
        lbl_montant = MontantMasquable(
            f"{formater_montant(vente['montant'])} Ar",
            object_name="montantVente",
        )
        lbl_montant.setFixedWidth(98)
        lay.addWidget(lbl_montant)

        lay.addSpacing(16)

        # Méthode
        label_m, style_m = _METHODES.get(vente["methode"], ("—", "badgeNeutre"))
        badge_m = QLabel(label_m)
        badge_m.setObjectName(style_m)
        badge_m.setFixedWidth(104)
        badge_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_m)

        lay.addSpacing(8)

        if vente.get("annule"):
            lbl_montant.label.setStyleSheet(
                "color:#5c5f6e;font-size:15px;font-weight:bold;text-decoration:line-through;"
            )
            badge_a = QLabel("Annulé")
            badge_a.setObjectName("badgeExpire")
            badge_a.setFixedWidth(84)
            badge_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(badge_a)
        elif annulable:
            self.btn_annuler = QPushButton("Annuler")
            self.btn_annuler.setObjectName("boutonActionBloquer")
            self.btn_annuler.setFixedHeight(28)
            self.btn_annuler.setFixedWidth(84)
            self.btn_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_annuler.clicked.connect(lambda: self.annulation_demande.emit(vente))
            lay.addWidget(self.btn_annuler)
        else:
            lay.addSpacing(84)


class LigneCategorieStock(QWidget):
    """Ligne du récapitulatif par catégorie."""

    def __init__(self, ligne: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneCategorieStock")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(0)

        lbl_cat = QLabel(ligne["categorie_label"])
        lbl_cat.setObjectName("nomUtilisateur")
        lay.addWidget(lbl_cat)

        lay.addSpacing(16)

        lbl_detail = QLabel(
            f"{ligne['nb_ventes']} vente{'s' if ligne['nb_ventes'] > 1 else ''}"
            f"  ·  {ligne['quantite']} article{'s' if ligne['quantite'] > 1 else ''}"
        )
        lbl_detail.setObjectName("loginUtilisateur")
        lay.addWidget(lbl_detail)

        lay.addStretch()

        lbl_ca = MontantMasquable(
            f"{formater_montant(ligne['ca'])} Ar",
            object_name="montantCategorieStock",
        )
        lay.addWidget(lbl_ca)


class StockPage(QWidget):
    """Boutique / stock du multiservice : ventes de produits et CA par catégorie."""

    def __init__(self, controller: StockController, current_user: User, parent=None):
        super().__init__(parent)
        self._controller   = controller
        self._current_user = current_user
        self._derniere_index_valide = 0

        self._construire_interface()
        self.rafraichir_donnees()

    # ── Construction ─────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        layout.addLayout(self._header())
        layout.addLayout(self._rangee_cards())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        corps = QWidget()
        corps_lay = QVBoxLayout(corps)
        corps_lay.setContentsMargins(0, 0, 0, 0)
        corps_lay.setSpacing(20)

        corps_lay.addWidget(self._card_ventes())
        corps_lay.addWidget(self._card_categories())
        corps_lay.addStretch()

        scroll.setWidget(corps)
        layout.addWidget(scroll, stretch=1)

    def _header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        titre = QLabel("Stock & Boutique")
        titre.setObjectName("titreDashboard")
        h.addWidget(titre)
        h.addStretch()

        self._date_combo = QComboBox()
        self._date_combo.setObjectName("dateComboVentes")
        self._date_combo.setFixedSize(162, 42)
        today = _date.today()
        for i in range(5):
            d = today - timedelta(days=i)
            qd = QDate(d.year, d.month, d.day)
            if i == 0:
                label = "Aujourd'hui"
            elif i == 1:
                label = "Hier"
            else:
                label = d.strftime("%d/%m/%Y")
            self._date_combo.addItem(label, qd)
        self._date_combo.addItem("Choisir une date...", None)
        self._date_combo.currentIndexChanged.connect(self._on_date_combo_changed)
        h.addWidget(self._date_combo)
        h.addSpacing(10)

        btn_produits = QPushButton("  Gérer les produits")
        btn_produits.setObjectName("boutonActionLimiter")
        btn_produits.setIcon(qta.icon("fa5s.box", color="#5b6ee8"))
        btn_produits.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_produits.setFixedHeight(42)
        btn_produits.clicked.connect(self._ouvrir_gestion_produits)
        h.addWidget(btn_produits)
        h.addSpacing(8)

        self._btn_vendre = QPushButton("  Vendre un produit")
        self._btn_vendre.setObjectName("boutonVendre")
        self._btn_vendre.setIcon(qta.icon("fa5s.shopping-basket", color="#ffffff"))
        self._btn_vendre.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_vendre.setFixedHeight(42)
        self._btn_vendre.clicked.connect(self._ouvrir_vente)
        h.addWidget(self._btn_vendre)
        return h

    def _rangee_cards(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._stat_ca        = StatCard("fa5s.coins",           "CA produits du jour", "0 Ar", "aujourd'hui", masquable=True)
        self._stat_nb_ventes = StatCard("fa5s.receipt",         "Ventes produits",     "0",    "aujourd'hui")
        self._stat_articles  = StatCard("fa5s.box-open",        "Articles vendus",     "0",    "aujourd'hui")
        for c in (self._stat_ca, self._stat_nb_ventes, self._stat_articles):
            r.addWidget(c)
        return r

    def _card_ventes(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titre_ventes = QLabel("VENTES DU JOUR  ·  0")
        self._titre_ventes.setObjectName("titreSectionSessions")
        self._titre_ventes.setContentsMargins(20, 16, 20, 12)
        lay.addWidget(self._titre_ventes)

        self._conteneur_ventes = QWidget()
        self._lay_ventes = QVBoxLayout(self._conteneur_ventes)
        self._lay_ventes.setContentsMargins(0, 0, 0, 0)
        self._lay_ventes.setSpacing(0)

        lay.addWidget(self._conteneur_ventes)
        return card

    def _card_categories(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titre_categories = QLabel("CA PAR CATÉGORIE  ·  0")
        self._titre_categories.setObjectName("titreSectionSessions")
        self._titre_categories.setContentsMargins(20, 16, 20, 12)
        lay.addWidget(self._titre_categories)

        self._conteneur_categories = QWidget()
        self._lay_categories = QVBoxLayout(self._conteneur_categories)
        self._lay_categories.setContentsMargins(0, 0, 0, 0)
        self._lay_categories.setSpacing(0)

        lay.addWidget(self._conteneur_categories)
        return card

    # ── Données ──────────────────────────────────────────────────────────

    def rafraichir_donnees(self):
        qdate = self._date_combo.currentData()
        if qdate is None:
            return
        date_str = qdate.toString("yyyy-MM-dd")
        est_aujourd_hui = qdate == QDate.currentDate()

        totaux   = self._controller.total_du_jour(date_str)
        ventes   = self._controller.obtenir_ventes_du_jour(date_str)
        categories = self._controller.ventes_par_categorie_du_jour(date_str)

        self._stat_ca.mettre_a_jour(f"{formater_montant(totaux['ca_total'])} Ar")
        self._stat_nb_ventes.mettre_a_jour(str(totaux["nb_ventes"]))
        self._stat_articles.mettre_a_jour(str(totaux["nb_articles"]))
        self._btn_vendre.setVisible(est_aujourd_hui)

        # ── Ventes du jour ────────────────────────────────────────────
        self._titre_ventes.setText(f"VENTES DU JOUR  ·  {len(ventes)}")
        self._vider(self._lay_ventes)
        if not ventes:
            lbl = QLabel("Aucune vente produit ce jour-là.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(20, 14, 20, 14)
            self._lay_ventes.addWidget(lbl)
        else:
            for i, v in enumerate(ventes):
                if i > 0:
                    self._lay_ventes.addWidget(_sep())
                ligne = LigneVenteProduit(v, annulable=est_aujourd_hui)
                ligne.annulation_demande.connect(self._on_annuler)
                self._lay_ventes.addWidget(ligne)

        # ── CA par catégorie ─────────────────────────────────────────
        self._titre_categories.setText(f"CA PAR CATÉGORIE  ·  {len(categories)}")
        self._vider(self._lay_categories)
        if not categories:
            lbl = QLabel("Aucune vente produit ce jour-là.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(20, 14, 20, 14)
            self._lay_categories.addWidget(lbl)
        else:
            for i, ligne in enumerate(categories):
                if i > 0:
                    self._lay_categories.addWidget(_sep())
                self._lay_categories.addWidget(LigneCategorieStock(ligne))

    # ── Actions ──────────────────────────────────────────────────────────

    def _ouvrir_gestion_produits(self):
        dlg = DialogGestionProduits(self._controller, parent=self)
        dlg.produits_modifies.connect(self.rafraichir_donnees)
        dlg.exec()

    def _ouvrir_vente(self):
        produits = self._controller.obtenir_produits(actif_seulement=True)
        if not produits:
            QMessageBox.information(
                self, "Aucun produit",
                "Ajoutez d'abord des produits dans « Gérer les produits ».",
            )
            return
        dialog = DialogVenteProduit(produits, parent=self)
        dialog.vente_confirmee.connect(self._on_vente_confirmee)
        dialog.exec()

    def _on_vente_confirmee(self, donnees: dict):
        resultat = self._controller.enregistrer_vente(
            produit_id=donnees["produit_id"],
            quantite=donnees["quantite"],
            prix_unitaire=donnees["prix_unitaire"],
            methode=donnees["methode"],
            user_id=self._current_user.id or 1,
        )
        if not resultat.get("ok"):
            QMessageBox.critical(
                self, "Erreur",
                f"La vente n'a pas pu être enregistrée.\n{resultat.get('message', 'Erreur inconnue.')}",
            )
            return
        self.rafraichir_donnees()

    def _on_annuler(self, vente: dict):
        rep = QMessageBox.question(
            self,
            "Annuler la vente",
            f"Annuler la vente de <b>{vente['produit']}</b> "
            f"({vente['quantite']} × {formater_montant(vente['prix_unitaire'])} Ar) ?<br><br>"
            "La vente sera exclue du chiffre d'affaires mais restera visible "
            "dans l'historique comme « Annulée ».",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if rep != QMessageBox.StandardButton.Yes:
            return
        resultat = self._controller.annuler_vente(vente["vente_id"])
        if not resultat.get("ok"):
            QMessageBox.warning(self, "Erreur", resultat.get("message", "Annulation impossible."))
        self.rafraichir_donnees()

    def _on_date_combo_changed(self, index: int):
        data = self._date_combo.currentData()
        if data is None:
            self._choisir_date_autre()
        else:
            self._derniere_index_valide = index
            self.rafraichir_donnees()

    def _choisir_date_autre(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Choisir une date")
        dlg.setFixedWidth(300)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        picker = QDateEdit()
        picker.setCalendarPopup(True)
        picker.setDisplayFormat("dd/MM/yyyy")
        picker.setMaximumDate(QDate.currentDate())
        current_data = self._date_combo.itemData(self._derniere_index_valide)
        picker.setDate(current_data if current_data else QDate.currentDate())
        lay.addWidget(picker)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            self._date_combo.blockSignals(True)
            self._date_combo.setCurrentIndex(self._derniere_index_valide)
            self._date_combo.blockSignals(False)
            return

        chosen = picker.date()

        for i in range(5):
            if self._date_combo.itemData(i) == chosen:
                self._date_combo.blockSignals(True)
                self._date_combo.setCurrentIndex(i)
                self._date_combo.blockSignals(False)
                self._derniere_index_valide = i
                self.rafraichir_donnees()
                return

        self._date_combo.blockSignals(True)
        sentinel = self._date_combo.count() - 1
        if self._date_combo.count() > 6:
            self._date_combo.removeItem(5)
            sentinel = self._date_combo.count() - 1
        label = chosen.toString("dd/MM/yyyy")
        self._date_combo.insertItem(sentinel, label, chosen)
        self._date_combo.setCurrentIndex(sentinel)
        self._date_combo.blockSignals(False)
        self._derniere_index_valide = sentinel
        self.rafraichir_donnees()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _vider(lay: QVBoxLayout):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
