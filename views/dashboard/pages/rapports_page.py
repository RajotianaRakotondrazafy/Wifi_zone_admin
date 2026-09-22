import qtawesome as qta
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QScrollArea, QProgressBar,
    QFileDialog, QMessageBox,
)

from controllers.rapports.rapports_controller import RapportsController, PERIODES
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.montant_masquable import MontantMasquable


_COULEURS_BARRE = ["#5b6ee8", "#6ee8c0", "#e8c45b", "#e85b6e", "#5b9ee8"]


def _echelle_secure(max_val, valeurs) -> tuple[int, list[int]]:
    max_val = max(0, int(max_val or 0))
    valeurs = [max(0, int(v or 0)) for v in valeurs]
    while max_val > 2_000_000_000:
        max_val //= 1_000
        valeurs = [v // 1_000 for v in valeurs]
    if max_val == 0:
        max_val = 1
    return max_val, valeurs


def _fmt_ar(montant: int) -> str:
    return f"{montant:,}".replace(",", " ")


def _fmt_date_fr(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


class RapportsPage(QWidget):

    def __init__(self, controller: RapportsController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._par_jour: list[dict] = []
        self._date_debut = ""
        self._date_fin   = ""
        self._construire_interface()
        self._charger()

        self._timer_rafraichir = QTimer(self)
        self._timer_rafraichir.setInterval(60_000)
        self._timer_rafraichir.timeout.connect(self._charger)
        self._timer_rafraichir.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._charger()

    # ── Construction ──────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        # ── Header ──────────────────────────────────────────────────
        header = QHBoxLayout()

        titre = QLabel("Rapports")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        self._combo_periode = QComboBox()
        self._combo_periode.setObjectName("comboPeriode")
        self._combo_periode.setFixedHeight(36)
        self._combo_periode.setMinimumWidth(180)
        for p in PERIODES:
            self._combo_periode.addItem(p)
        self._combo_periode.currentTextChanged.connect(self._charger)
        header.addWidget(self._combo_periode)

        btn_export = QPushButton("  Exporter CSV")
        btn_export.setObjectName("boutonActionPage")
        btn_export.setIcon(qta.icon("fa5s.file-csv", color="#ffffff"))
        btn_export.setFixedHeight(36)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._exporter_csv)
        header.addWidget(btn_export)

        layout.addLayout(header)

        # ── Cards synthèse ───────────────────────────────────────────
        rangee = QHBoxLayout()
        rangee.setSpacing(16)
        self._card_ca             = StatCard("fa5s.coins",          "CA de la période",   "—", "Ar", masquable=True)
        self._card_ca_tickets     = StatCard("fa5s.wifi",           "CA Tickets WiFi",    "—", "Ar", masquable=True)
        self._card_ca_accessoires = StatCard("fa5s.shopping-basket","CA Accessoires",     "—", "Ar", masquable=True)
        self._card_ca_autres      = StatCard("fa5s.box",            "CA Autres produits", "—", "Ar", masquable=True)
        for c in (self._card_ca, self._card_ca_tickets, self._card_ca_accessoires, self._card_ca_autres):
            rangee.addWidget(c)
        layout.addLayout(rangee)

        rangee2 = QHBoxLayout()
        rangee2.setSpacing(16)
        self._card_ventes    = StatCard("fa5s.receipt",    "Ventes",         "—", "tickets")
        self._card_moyenne   = StatCard("fa5s.chart-line", "Ticket moyen",   "—", "Ar", masquable=True)
        self._card_depenses  = StatCard("fa5s.money-bill-wave-alt", "Total dépenses", "—", "Ar", masquable=True)
        self._card_benefice  = StatCard("fa5s.hand-holding-usd",    "Bénéfice net",   "—", "Ar", masquable=True)
        for c in (self._card_ventes, self._card_moyenne, self._card_depenses, self._card_benefice):
            rangee2.addWidget(c)
        layout.addLayout(rangee2)

        # ── Zone défilable ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        self._contenu_layout = QVBoxLayout(contenu)
        self._contenu_layout.setSpacing(20)
        self._contenu_layout.setContentsMargins(0, 0, 0, 0)

        self._carte_evolution        = self._creer_carte("ÉVOLUTION JOURNALIÈRE")
        self._carte_top_profils      = self._creer_carte("TOP FORFAITS VENDUS")
        self._carte_produits_cat     = self._creer_carte("VENTES PRODUITS PAR CATÉGORIE")

        self._contenu_layout.addWidget(self._carte_evolution)
        self._contenu_layout.addWidget(self._carte_top_profils)
        self._contenu_layout.addWidget(self._carte_produits_cat)
        self._contenu_layout.addStretch()

        scroll.setWidget(contenu)
        layout.addWidget(scroll, stretch=1)

    def _creer_carte(self, titre_texte: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(0)

        titre = QLabel(titre_texte)
        titre.setObjectName("titreSectionSessions")
        titre.setContentsMargins(0, 0, 0, 12)
        lay.addWidget(titre)

        contenu = QWidget()
        contenu.setStyleSheet("background: transparent;")
        contenu_lay = QVBoxLayout(contenu)
        contenu_lay.setContentsMargins(0, 0, 0, 0)
        contenu_lay.setSpacing(0)
        lay.addWidget(contenu)

        card._contenu      = contenu
        card._contenu_lay  = contenu_lay
        return card

    # ── Chargement ────────────────────────────────────────────────────

    def _charger(self):
        periode = self._combo_periode.currentText()
        self._date_debut, self._date_fin = self._controller.plage_pour_periode(periode)
        donnees = self._controller.rapport_complet(self._date_debut, self._date_fin)

        synthese    = donnees["synthese"]
        self._par_jour = donnees["par_jour"]

        # Cards
        self._card_ca.mettre_a_jour(_fmt_ar(donnees["ca_total"]), "Ar")
        self._card_ca_tickets.mettre_a_jour(_fmt_ar(donnees["ca_tickets"]), "Ar")
        self._card_ca_accessoires.mettre_a_jour(_fmt_ar(donnees["ca_accessoires"]), "Ar")
        self._card_ca_autres.mettre_a_jour(_fmt_ar(donnees["ca_autres_produits"]), "Ar")
        self._card_ventes.mettre_a_jour(str(synthese["nb_ventes"]), "tickets")
        self._card_moyenne.mettre_a_jour(_fmt_ar(synthese["ticket_moyen"]), "Ar")
        self._card_depenses.mettre_a_jour(_fmt_ar(donnees["depenses_total"]), "Ar")
        self._card_benefice.mettre_a_jour(_fmt_ar(donnees["benefice_net"]), "Ar")

        self._construire_evolution(self._par_jour)
        self._construire_top_profils(donnees["top_profils"])
        self._construire_produits_categorie(donnees["par_categorie"])

    # ── Sections ──────────────────────────────────────────────────────

    def _construire_evolution(self, par_jour: list[dict]):
        self._vider(self._carte_evolution._contenu_lay)

        if not par_jour:
            lbl = QLabel("Aucune vente sur cette période.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(0, 4, 0, 4)
            self._carte_evolution._contenu_lay.addWidget(lbl)
            return

        # En-tête colonnes
        entete = QHBoxLayout()
        entete.setContentsMargins(0, 0, 0, 8)
        for texte, largeur in [("Date", 100), ("Nb ventes", 80), ("CA (Ar)", 110)]:
            lbl = QLabel(texte)
            lbl.setObjectName("titreSectionSessions")
            lbl.setFixedWidth(largeur)
            entete.addWidget(lbl)
        entete.addStretch()
        entete_widget = QWidget()
        entete_widget.setStyleSheet("background: transparent;")
        entete_widget.setLayout(entete)
        self._carte_evolution._contenu_lay.addWidget(entete_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        self._carte_evolution._contenu_lay.addWidget(sep)

        ca_values = [int(r["ca"]) for r in par_jour]
        max_ca, ca_values = _echelle_secure(max(ca_values) if ca_values else 0, ca_values)

        for i, r in enumerate(par_jour):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            ligne = QHBoxLayout(row)
            ligne.setContentsMargins(0, 6, 0, 6)
            ligne.setSpacing(0)

            lbl_date = QLabel(_fmt_date_fr(r["jour"]))
            lbl_date.setObjectName("loginUtilisateur")
            lbl_date.setFixedWidth(100)
            ligne.addWidget(lbl_date)

            lbl_nb = QLabel(str(r["nb_ventes"]))
            lbl_nb.setObjectName("nomUtilisateur")
            lbl_nb.setFixedWidth(80)
            ligne.addWidget(lbl_nb)

            lbl_ca = MontantMasquable(
                _fmt_ar(int(r["ca"])) + " Ar",
                object_name="montantVente",
            )
            lbl_ca.setFixedWidth(124)
            ligne.addWidget(lbl_ca)

            barre = QProgressBar()
            barre.setObjectName("barreActivite")
            barre.setRange(0, max_ca)
            barre.setValue(ca_values[i])
            barre.setTextVisible(False)
            barre.setFixedHeight(8)
            ligne.addWidget(barre, stretch=1)

            self._carte_evolution._contenu_lay.addWidget(row)

            sep_r = QFrame()
            sep_r.setFrameShape(QFrame.Shape.HLine)
            sep_r.setObjectName("separateurSession")
            self._carte_evolution._contenu_lay.addWidget(sep_r)

    def _construire_top_profils(self, top: list[dict]):
        self._vider(self._carte_top_profils._contenu_lay)

        if not top:
            lbl = QLabel("Aucune vente sur cette période.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(0, 4, 0, 4)
            self._carte_top_profils._contenu_lay.addWidget(lbl)
            return

        max_val = max(r["nb_ventes"] for r in top) or 1

        for i, r in enumerate(top):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            ligne = QHBoxLayout(row)
            ligne.setContentsMargins(0, 6, 0, 6)
            ligne.setSpacing(12)

            rang = QLabel(f"#{i + 1}")
            rang.setObjectName("labelHeure")
            rang.setFixedWidth(24)
            rang.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(rang)

            lbl_nom = QLabel(r["profil"])
            lbl_nom.setObjectName("nomUtilisateur")
            lbl_nom.setFixedWidth(180)
            ligne.addWidget(lbl_nom)

            barre = QProgressBar()
            barre.setObjectName("barreTop")
            barre.setRange(0, max_val)
            barre.setValue(r["nb_ventes"])
            barre.setTextVisible(False)
            barre.setFixedHeight(10)
            barre.setStyleSheet(
                f"QProgressBar {{ background-color: #2f3340; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background-color: {_COULEURS_BARRE[i % len(_COULEURS_BARRE)]}; border-radius: 5px; }}"
            )
            ligne.addWidget(barre, stretch=1)

            lbl_nb = QLabel(f"{r['nb_ventes']} ticket{'s' if r['nb_ventes'] > 1 else ''}")
            lbl_nb.setObjectName("labelValeurBarre")
            lbl_nb.setFixedWidth(80)
            lbl_nb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_nb)

            lbl_ca = MontantMasquable(
                _fmt_ar(int(r["ca"])) + " Ar",
                object_name="montantVente",
            )
            lbl_ca.setFixedWidth(114)
            ligne.addWidget(lbl_ca)

            self._carte_top_profils._contenu_lay.addWidget(row)

    def _construire_produits_categorie(self, categories: list[dict]):
        self._vider(self._carte_produits_cat._contenu_lay)

        if not categories:
            lbl = QLabel("Aucune vente de produit sur cette période.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(0, 4, 0, 4)
            self._carte_produits_cat._contenu_lay.addWidget(lbl)
            return

        entete = QHBoxLayout()
        entete.setContentsMargins(0, 0, 0, 8)
        for texte, largeur in [("Catégorie", 140), ("Qté", 60), ("CA (Ar)", 110)]:
            lbl = QLabel(texte)
            lbl.setObjectName("titreSectionSessions")
            lbl.setFixedWidth(largeur)
            entete.addWidget(lbl)
        entete.addStretch()
        entete_widget = QWidget()
        entete_widget.setStyleSheet("background: transparent;")
        entete_widget.setLayout(entete)
        self._carte_produits_cat._contenu_lay.addWidget(entete_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        self._carte_produits_cat._contenu_lay.addWidget(sep)

        max_val = int(max((r["ca"] for r in categories), default=1) or 1)

        for i, r in enumerate(categories):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            ligne = QHBoxLayout(row)
            ligne.setContentsMargins(0, 6, 0, 6)
            ligne.setSpacing(0)

            lbl_cat = QLabel(r["categorie"].capitalize())
            lbl_cat.setObjectName("nomUtilisateur")
            lbl_cat.setFixedWidth(140)
            ligne.addWidget(lbl_cat)

            lbl_qte = QLabel(str(r["quantite"]))
            lbl_qte.setObjectName("loginUtilisateur")
            lbl_qte.setFixedWidth(60)
            ligne.addWidget(lbl_qte)

            lbl_ca = MontantMasquable(
                _fmt_ar(int(r["ca"])) + " Ar",
                object_name="montantVente",
            )
            lbl_ca.setFixedWidth(124)
            ligne.addWidget(lbl_ca)

            barre = QProgressBar()
            barre.setObjectName("barreTop")
            barre.setRange(0, max_val)
            barre.setValue(int(r["ca"]))
            barre.setTextVisible(False)
            barre.setFixedHeight(10)
            barre.setStyleSheet(
                f"QProgressBar {{ background-color: #2f3340; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background-color: {_COULEURS_BARRE[i % len(_COULEURS_BARRE)]}; border-radius: 5px; }}"
            )
            ligne.addWidget(barre, stretch=1)

            self._carte_produits_cat._contenu_lay.addWidget(row)

            sep_r = QFrame()
            sep_r.setFrameShape(QFrame.Shape.HLine)
            sep_r.setObjectName("separateurSession")
            self._carte_produits_cat._contenu_lay.addWidget(sep_r)

    # ── Export CSV ────────────────────────────────────────────────────

    def _exporter_csv(self):
        if not self._par_jour:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return
        periode = self._combo_periode.currentText().replace(" ", "_").replace("é", "e")
        suggestion = f"rapport_{periode}_{datetime.now().strftime('%Y%m%d')}.csv"
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport", suggestion,
            "Fichiers CSV (*.csv);;Tous les fichiers (*)"
        )
        if not chemin:
            return
        nb = self._controller.exporter_csv(
            chemin, self._date_debut, self._date_fin, self._par_jour
        )
        QMessageBox.information(self, "Export réussi", f"{nb} lignes exportées vers :\n{chemin}")

    # ── Utilitaire ────────────────────────────────────────────────────

    @staticmethod
    def _vider(lay: QVBoxLayout):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # vider le sous-layout récursivement
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
