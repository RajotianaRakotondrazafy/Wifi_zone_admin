from datetime import date as _date, timedelta

import qtawesome as qta
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QDateEdit, QComboBox,
    QDialog, QDialogButtonBox,
)

from controllers.depenses.depenses_controller import DepensesController
from models.user import User
from utils.formatage import formater_montant
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.elide_label import LabelElide
from views.dashboard.components.dialog_depense import DialogDepense


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("separateurSession")
    return f


class LigneDepense(QWidget):
    """Ligne d'une dépense dans l'historique du jour."""

    annulation_demande = pyqtSignal(dict)

    def __init__(self, depense: dict, annulable: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneVente")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(0)

        # Heure
        lbl_h = QLabel(depense["heure"])
        lbl_h.setObjectName("heureVente")
        lbl_h.setFixedWidth(48)
        lay.addWidget(lbl_h)

        lay.addSpacing(12)

        # Motif
        lbl_motif = LabelElide(depense["motif"], largeur_min=120)
        lbl_motif.setObjectName("nomUtilisateur")
        lay.addWidget(lbl_motif, stretch=1)

        lay.addSpacing(16)

        # Badge catégorie
        badge_cat = QLabel(depense["categorie_label"])
        badge_cat.setObjectName("badgeNeutre")
        badge_cat.setFixedWidth(150)
        badge_cat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_cat)

        lay.addSpacing(16)

        # Montant
        lbl_montant = QLabel(f"{formater_montant(depense['montant'])} Ar")
        lbl_montant.setObjectName("montantVente")
        lbl_montant.setFixedWidth(110)
        lay.addWidget(lbl_montant)

        lay.addSpacing(16)

        # Méthode
        badge_m = QLabel(depense["methode_label"])
        badge_m.setObjectName("badgeActif")
        badge_m.setFixedWidth(104)
        badge_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_m)

        lay.addSpacing(8)

        if depense.get("annule"):
            lbl_montant.setStyleSheet(
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
            self.btn_annuler.clicked.connect(lambda: self.annulation_demande.emit(depense))
            lay.addWidget(self.btn_annuler)
        else:
            lay.addSpacing(84)


class DepensesPage(QWidget):
    """Gestion des dépenses du multiservice."""

    def __init__(self, controller: DepensesController, current_user: User, parent=None):
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

        corps_lay.addWidget(self._card_depenses())
        corps_lay.addStretch()

        scroll.setWidget(corps)
        layout.addWidget(scroll, stretch=1)

    def _header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        titre = QLabel("Dépenses")
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

        self._btn_ajouter = QPushButton("  Ajouter une dépense")
        self._btn_ajouter.setObjectName("boutonVendre")
        self._btn_ajouter.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self._btn_ajouter.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ajouter.setFixedHeight(42)
        self._btn_ajouter.clicked.connect(self._ouvrir_ajout)
        h.addWidget(self._btn_ajouter)
        return h

    def _rangee_cards(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._stat_total    = StatCard("fa5s.money-bill-wave", "Dépenses du jour", "0 Ar", "aujourd'hui", masquable=True)
        self._stat_nb       = StatCard("fa5s.receipt",         "Dépenses enregistrées", "0", "aujourd'hui")
        self._stat_annulees = StatCard("fa5s.times-circle",    "Dépenses annulées", "0 Ar", "aujourd'hui", masquable=True)
        for c in (self._stat_total, self._stat_nb, self._stat_annulees):
            r.addWidget(c)
        r.addStretch()
        return r

    def _card_depenses(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titre_depenses = QLabel("DÉPENSES DU JOUR  ·  0")
        self._titre_depenses.setObjectName("titreSectionSessions")
        self._titre_depenses.setContentsMargins(20, 16, 20, 12)
        lay.addWidget(self._titre_depenses)

        self._conteneur_depenses = QWidget()
        self._lay_depenses = QVBoxLayout(self._conteneur_depenses)
        self._lay_depenses.setContentsMargins(0, 0, 0, 0)
        self._lay_depenses.setSpacing(0)

        lay.addWidget(self._conteneur_depenses)
        return card

    # ── Données ──────────────────────────────────────────────────────────

    def rafraichir_donnees(self):
        qdate = self._date_combo.currentData()
        if qdate is None:
            return
        date_str = qdate.toString("yyyy-MM-dd")
        est_aujourd_hui = qdate == QDate.currentDate()

        totaux   = self._controller.total_du_jour(date_str)
        depenses = self._controller.obtenir_depenses_du_jour(date_str)

        self._stat_total.mettre_a_jour(f"{formater_montant(totaux['total'])} Ar")
        self._stat_nb.mettre_a_jour(str(totaux["nb_depenses"]))
        self._stat_annulees.mettre_a_jour(f"{formater_montant(totaux['total_annulees'])} Ar")
        self._btn_ajouter.setVisible(est_aujourd_hui)

        # ── Liste du jour ────────────────────────────────────────────
        self._titre_depenses.setText(f"DÉPENSES DU JOUR  ·  {len(depenses)}")
        self._vider(self._lay_depenses)
        if not depenses:
            lbl = QLabel("Aucune dépense ce jour-là.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(20, 14, 20, 14)
            self._lay_depenses.addWidget(lbl)
        else:
            for i, d in enumerate(depenses):
                if i > 0:
                    self._lay_depenses.addWidget(_sep())
                ligne = LigneDepense(d, annulable=est_aujourd_hui)
                ligne.annulation_demande.connect(self._on_annuler)
                self._lay_depenses.addWidget(ligne)

    # ── Actions ──────────────────────────────────────────────────────────

    def _ouvrir_ajout(self):
        dlg = DialogDepense(self._controller, user_id=self._current_user.id or 1, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.rafraichir_donnees()

    def _on_annuler(self, depense: dict):
        rep = QMessageBox.question(
            self,
            "Annuler la dépense",
            f"Annuler la dépense de <b>{formater_montant(depense['montant'])} Ar</b> "
            f"— {depense['motif']} ?<br><br>"
            "La dépense sera exclue du total mais restera visible "
            "dans l'historique comme « Annulée ».",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if rep != QMessageBox.StandardButton.Yes:
            return
        resultat = self._controller.annuler_depense(depense["depense_id"])
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