import qtawesome as qta
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QScrollArea, QProgressBar,
    QFileDialog, QMessageBox,
)

from controllers.rapports.rapports_controller import RapportsController, PERIODES
from views.dashboard.components.stat_card import StatCard


_COULEURS_BARRE = ["#5b6ee8", "#6ee8c0", "#e8c45b", "#e85b6e", "#5b9ee8"]


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
        self._card_ca      = StatCard("fa5s.coins",       "CA de la période",  "—", "Ar")
        self._card_ventes  = StatCard("fa5s.receipt",     "Ventes",            "—", "tickets")
        self._card_moyenne = StatCard("fa5s.chart-line",  "Ticket moyen",      "—", "Ar")
        for c in (self._card_ca, self._card_ventes, self._card_moyenne):
            rangee.addWidget(c)
        layout.addLayout(rangee)

        # ── Zone défilable ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        self._contenu_layout = QVBoxLayout(contenu)
        self._contenu_layout.setSpacing(20)
        self._contenu_layout.setContentsMargins(0, 0, 0, 0)

        self._carte_evolution   = self._creer_carte("ÉVOLUTION JOURNALIÈRE")
        self._carte_top_profils = self._creer_carte("TOP FORFAITS VENDUS")

        self._contenu_layout.addWidget(self._carte_evolution)
        self._contenu_layout.addWidget(self._carte_top_profils)
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
        self._card_ca.mettre_a_jour(_fmt_ar(synthese["ca_total"]), "Ar")
        self._card_ventes.mettre_a_jour(str(synthese["nb_ventes"]), "tickets")
        self._card_moyenne.mettre_a_jour(_fmt_ar(synthese["ticket_moyen"]), "Ar")

        self._construire_evolution(self._par_jour)
        self._construire_top_profils(donnees["top_profils"])

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

        max_ca = max((int(r["ca"]) for r in par_jour), default=1) or 1

        for r in par_jour:
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

            lbl_ca = QLabel(_fmt_ar(int(r["ca"])) + " Ar")
            lbl_ca.setObjectName("montantVente")
            lbl_ca.setFixedWidth(110)
            ligne.addWidget(lbl_ca)

            barre = QProgressBar()
            barre.setObjectName("barreActivite")
            barre.setRange(0, max_ca)
            barre.setValue(int(r["ca"]))
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

            lbl_ca = QLabel(_fmt_ar(int(r["ca"])) + " Ar")
            lbl_ca.setObjectName("montantVente")
            lbl_ca.setFixedWidth(100)
            lbl_ca.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            ligne.addWidget(lbl_ca)

            self._carte_top_profils._contenu_lay.addWidget(row)

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
