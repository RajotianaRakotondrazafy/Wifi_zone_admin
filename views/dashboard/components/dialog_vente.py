import random
import string

import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QButtonGroup, QStackedWidget, QWidget,
)


def _generer_code() -> str:
    """Génère un code lisible en évitant les caractères ambigus (O, I, 0, 1)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    chiffres = "23456789"
    lettres = ''.join(random.choices(alphabet, k=3))
    nums    = ''.join(random.choices(chiffres, k=4))
    return f"{lettres}-{nums}"


def _generer_password() -> str:
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=6))


class DialogVente(QDialog):
    """Dialog 2 étapes : sélection profil/paiement → affichage du ticket généré."""

    ticket_vendu = pyqtSignal(dict)

    def __init__(self, profils: list[dict], vendeur_id: int, parent=None):
        super().__init__(parent)
        self._profils      = profils
        self._vendeur_id   = vendeur_id
        self._methode      = "especes"
        self._ticket: dict | None = None

        self.setWindowTitle("Vendre un ticket")
        self.setModal(True)
        self.setFixedSize(500, 530)
        self.setObjectName("dialogVente")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stacked = QStackedWidget()
        self._stacked.addWidget(self._page_selection())
        self._stacked.addWidget(self._page_resultat())
        layout.addWidget(self._stacked)

    # ── Page 1 : sélection ──────────────────────────────────────────────

    def _page_selection(self) -> QWidget:
        page = QWidget()
        page.setObjectName("pageDialogVente")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 26)
        lay.setSpacing(18)

        # Titre
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.cash-register", color="#5b6ee8").pixmap(20, 20))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Vendre un ticket")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()
        lay.addLayout(h_titre)

        lay.addWidget(self._sep())

        # Profil
        lay.addWidget(self._lbl_section("CHOISIR UN PROFIL"))

        self._combo = QComboBox()
        self._combo.setObjectName("comboParametres")
        self._combo.setFixedHeight(42)
        for p in self._profils:
            self._combo.addItem(f"{p['nom']}  —  {int(p['prix'])} Ar", userData=p)
        self._combo.currentIndexChanged.connect(self._actualiser_detail)
        lay.addWidget(self._combo)

        # Carte détail profil
        self._carte_detail = QFrame()
        self._carte_detail.setObjectName("carteDetailProfil")
        cd_lay = QHBoxLayout(self._carte_detail)
        cd_lay.setContentsMargins(16, 14, 16, 14)
        cd_lay.setSpacing(0)

        self._d_duree    = self._bloc_info("Durée")
        self._d_validite = self._bloc_info("Validité")
        self._d_debit    = self._bloc_info("Débit")
        self._d_prix     = self._bloc_info("Prix")
        for b in (self._d_duree, self._d_validite, self._d_debit, self._d_prix):
            cd_lay.addLayout(b["lay"], stretch=1)

        lay.addWidget(self._carte_detail)
        self._actualiser_detail(0)

        # Paiement
        lay.addWidget(self._lbl_section("MODE DE PAIEMENT"))

        h_pay = QHBoxLayout()
        h_pay.setSpacing(10)
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
            btn.setFixedHeight(40)
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

        # Boutons
        h_act = QHBoxLayout()
        h_act.setSpacing(10)

        btn_annuler = QPushButton("Annuler")
        btn_annuler.setObjectName("boutonActionHistorique")
        btn_annuler.setFixedHeight(44)
        btn_annuler.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_annuler.clicked.connect(self.reject)
        h_act.addWidget(btn_annuler)

        h_act.addStretch()

        btn_vendre = QPushButton("  Confirmer la vente")
        btn_vendre.setObjectName("boutonVendre")
        btn_vendre.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        btn_vendre.setFixedHeight(44)
        btn_vendre.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_vendre.clicked.connect(self._effectuer_vente)
        h_act.addWidget(btn_vendre)

        lay.addLayout(h_act)
        return page

    # ── Page 2 : ticket généré ─────────────────────────────────────────

    def _page_resultat(self) -> QWidget:
        page = QWidget()
        page.setObjectName("pageDialogVente")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 26)
        lay.setSpacing(16)

        # Badge succès centré
        self._badge_ok = QLabel("  ✓  Ticket vendu avec succès  ")
        self._badge_ok.setObjectName("badgeSuccesVente")
        self._badge_ok.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._badge_ok)

        # Carte ticket
        carte = QFrame()
        carte.setObjectName("carteTicketGenere")
        ct_lay = QVBoxLayout(carte)
        ct_lay.setContentsMargins(20, 22, 20, 22)
        ct_lay.setSpacing(10)

        lbl_c = QLabel("CODE D'ACCÈS")
        lbl_c.setObjectName("titreSectionSessions")
        lbl_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct_lay.addWidget(lbl_c)

        self._lbl_code = QLabel("———")
        self._lbl_code.setObjectName("codeTicketGenere")
        self._lbl_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct_lay.addWidget(self._lbl_code)

        sep_c = QFrame()
        sep_c.setFrameShape(QFrame.Shape.HLine)
        sep_c.setObjectName("separateurSession")
        ct_lay.addWidget(sep_c)

        lbl_p = QLabel("MOT DE PASSE")
        lbl_p.setObjectName("titreSectionSessions")
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct_lay.addWidget(lbl_p)

        self._lbl_mdp = QLabel("———")
        self._lbl_mdp.setObjectName("passwordTicketGenere")
        self._lbl_mdp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct_lay.addWidget(self._lbl_mdp)

        lay.addWidget(carte)

        # Récap
        self._lbl_recap = QLabel()
        self._lbl_recap.setObjectName("recapTicket")
        self._lbl_recap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl_recap)

        lay.addStretch()
        lay.addWidget(self._sep())

        # Boutons
        h_act = QHBoxLayout()
        h_act.setSpacing(10)

        btn_imp = QPushButton("  Imprimer")
        btn_imp.setObjectName("boutonActionHistorique")
        btn_imp.setIcon(qta.icon("fa5s.print", color="#5c5f6e"))
        btn_imp.setFixedHeight(44)
        btn_imp.setEnabled(False)
        btn_imp.setToolTip("Impression — bientôt disponible")
        h_act.addWidget(btn_imp)

        h_act.addStretch()

        btn_nouveau = QPushButton("  Nouveau")
        btn_nouveau.setObjectName("boutonActionLimiter")
        btn_nouveau.setIcon(qta.icon("fa5s.plus", color="#8b8d98"))
        btn_nouveau.setFixedHeight(44)
        btn_nouveau.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nouveau.clicked.connect(self._reinitialiser)
        h_act.addWidget(btn_nouveau)

        btn_fermer = QPushButton("  Fermer")
        btn_fermer.setObjectName("boutonVendre")
        btn_fermer.setIcon(qta.icon("fa5s.times", color="#ffffff"))
        btn_fermer.setFixedHeight(44)
        btn_fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fermer.clicked.connect(self.accept)
        h_act.addWidget(btn_fermer)

        lay.addLayout(h_act)
        return page

    # ── Logique ─────────────────────────────────────────────────────────

    def _effectuer_vente(self):
        profil = self._combo.currentData()
        if not profil:
            return

        code     = _generer_code()
        password = _generer_password()

        methodes_label = {
            "especes":      "Espèces",
            "mobile_money": "Mobile Money",
            "carte":        "Carte",
        }

        self._ticket = {
            "code":      code,
            "password":  password,
            "profil":    profil["nom"],
            "prix":      profil["prix"],
            "methode":   self._methode,
            "validite":  profil["validite"],
        }

        self._lbl_code.setText(code)
        self._lbl_mdp.setText(password)
        self._lbl_recap.setText(
            f"Profil : {profil['nom']}  ·  "
            f"Validité : {profil['validite']}h après connexion  ·  "
            f"{int(profil['prix'])} Ar  ·  {methodes_label.get(self._methode, '')}"
        )

        self.ticket_vendu.emit(self._ticket)
        self._stacked.setCurrentIndex(1)

    def _reinitialiser(self):
        self._stacked.setCurrentIndex(0)
        self._ticket = None

    def _actualiser_detail(self, index: int):
        if index < 0 or index >= len(self._profils):
            return
        p = self._profils[index]
        min_tot = p["duree_session_max"]
        duree = f"{min_tot} min" if min_tot < 60 else f"{min_tot // 60}h"
        self._d_duree["val"].setText(duree)
        self._d_validite["val"].setText(f"{p['validite']}h")
        self._d_debit["val"].setText(f"{p['debit_max'] // 1024} Mbps")
        self._d_prix["val"].setText(f"{int(p['prix'])} Ar")

    # ── Helpers UI ───────────────────────────────────────────────────────

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

    @staticmethod
    def _bloc_info(etiquette: str) -> dict:
        lay = QVBoxLayout()
        lay.setSpacing(4)
        lbl_et = QLabel(etiquette)
        lbl_et.setObjectName("labelParametre")
        lbl_et.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_val = QLabel("—")
        lbl_val.setObjectName("valeurDetailProfil")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_et)
        lay.addWidget(lbl_val)
        return {"lay": lay, "val": lbl_val}
