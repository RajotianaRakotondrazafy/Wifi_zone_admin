import random
import string

import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QStackedWidget, QWidget, QComboBox, QSpinBox,
)

from config.settings import (
    TARIFICATION_PRIX_PAR_HEURE,
    TARIFICATION_LIBRE_MIN_AR,
    TARIFICATION_LIBRE_MIN_MIN,
)
from services.qr_service import generer_pixmap, url_connexion_hotspot
from utils.formatage import formater_montant
from views.dashboard.components.spin_duree import SpinDuree


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generer_username() -> str:
    return f"User{random.randint(1, 9999)}"


def _generer_code_unique() -> str:
    """Génère un code unique vérifié en base (900 000 combinaisons, 20 tentatives)."""
    from repositories.ticket_repository import TicketRepository
    repo = TicketRepository()
    for _ in range(20):
        candidate = _generer_username()
        if repo.get_ticket_by_code(candidate) is None:
            return candidate
    import uuid
    return f"User{uuid.uuid4().hex[:6].upper()}"


def _generer_password() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _fmt_duree(minutes: int) -> str:
    if minutes >= 1440:
        j = minutes // 1440
        h = (minutes % 1440) // 60
        return f"{j}j{f' {h}h' if h else ''}"
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h}h{f' {m:02d}' if m else ''}"
    return f"{minutes} min"


def _fmt_validite(heures: int) -> str:
    return f"{heures // 24}j" if heures >= 24 else f"{heures}h"


VITESSES = [
    {"label": "2 Mbps",  "debit_max": 2048},
    {"label": "5 Mbps",  "debit_max": 5120},
    {"label": "10 Mbps", "debit_max": 10240},
]

_METHODES = {
    "especes":      "Espèces",
    "mobile_money": "Mobile Money",
    "carte":        "Carte",
}

_IDX_PERSO   = -1       # sentinel pour l'option personnalisée
_FORFAIT_TAG = "forfait" # userData du combo pour l'option forfait


# ── Dialog principal ──────────────────────────────────────────────────────────

class DialogVente(QDialog):
    """Dialog 2 étapes : sélection forfait/paiement → ticket généré."""

    ticket_vendu = pyqtSignal(dict)

    def __init__(self, profils: list[dict], vendeur_id: int, parent=None):
        super().__init__(parent)
        self._profils         = profils
        self._vendeur_id      = vendeur_id
        self._methode         = "especes"
        self._vitesse_idx     = 0
        self._ticket_en_cours: dict = {}

        self.setWindowTitle("Vendre un ticket")
        self.setModal(True)
        self.setFixedSize(520, 660)
        self.setObjectName("dialogVente")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stacked = QStackedWidget()
        self._stacked.addWidget(self._page_selection())
        self._stacked.addWidget(self._page_resultat())
        outer.addWidget(self._stacked)

    # ── Page 1 : sélection ───────────────────────────────────────────────────

    def _page_selection(self) -> QWidget:
        page = QWidget()
        page.setObjectName("pageDialogVente")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 22, 26, 18)
        lay.setSpacing(0)

        # Header
        h_titre = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.cash-register", color="#5b6ee8").pixmap(18, 18))
        h_titre.addWidget(ico)
        h_titre.addSpacing(8)
        titre = QLabel("Vendre un ticket")
        titre.setObjectName("titreDashboard")
        h_titre.addWidget(titre)
        h_titre.addStretch()
        lay.addLayout(h_titre)
        lay.addSpacing(6)
        lay.addWidget(self._sep())
        lay.addSpacing(16)

        # ── Forfait ──────────────────────────────────────────────────
        lay.addWidget(self._lbl_section("FORFAIT"))
        lay.addSpacing(8)

        self._combo = QComboBox()
        self._combo.setObjectName("comboParametres")
        self._combo.setFixedHeight(42)
        self._combo.setCursor(Qt.CursorShape.PointingHandCursor)

        for p in self._profils:
            self._combo.addItem(
                f"{p['nom']}  —  {formater_montant(p['prix'])} Ar",
                userData=p,
            )
        self._combo.addItem("🔗  Forfait mensuel — partage d'appareils", userData=_FORFAIT_TAG)
        self._combo.addItem("✏  Personnalisé (durée libre)", userData=None)

        self._combo.currentIndexChanged.connect(self._on_combo_change)
        lay.addWidget(self._combo)
        lay.addSpacing(10)

        # Zone de détail (stacked: détail profil / forfait / personnalisé)
        self._zone_detail = QStackedWidget()
        self._zone_detail.setFixedHeight(108)
        self._zone_detail.addWidget(self._w_detail_profil())  # 0
        self._zone_detail.addWidget(self._w_forfait())        # 1
        self._zone_detail.addWidget(self._w_custom())         # 2
        lay.addWidget(self._zone_detail)
        lay.addSpacing(14)
        lay.addWidget(self._sep())
        lay.addSpacing(12)

        # ── Paiement ─────────────────────────────────────────────────
        lay.addWidget(self._lbl_section("MODE DE PAIEMENT"))
        lay.addSpacing(8)

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

        # ── Boutons ──────────────────────────────────────────────────
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
        self._btn_confirmer.clicked.connect(self._effectuer_vente)
        h_act.addWidget(self._btn_confirmer)

        lay.addLayout(h_act)

        # Initialiser avec le premier item
        self._on_combo_change(0)
        return page

    def _w_detail_profil(self) -> QFrame:
        """Ligne de détails du profil sélectionné."""
        w = QFrame()
        w.setObjectName("carteDetailProfil")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(0)

        def _col(etiq: str) -> QLabel:
            col = QVBoxLayout()
            col.setSpacing(3)
            e = QLabel(etiq)
            e.setObjectName("titreSectionSessions")
            col.addWidget(e)
            v = QLabel("—")
            v.setObjectName("valeurDetailProfil")
            col.addWidget(v)
            lay.addLayout(col)
            lay.addSpacing(28)
            return v

        self._d_duree    = _col("DURÉE")
        self._d_debit    = _col("DÉBIT")
        self._d_validite = _col("VALIDITÉ")
        lay.addStretch()
        self._d_prix     = _col("PRIX")
        return w

    def _w_forfait(self) -> QFrame:
        """Forfait mensuel partagé : 30 jours · 5 Mbps · N appareils max."""
        w = QFrame()
        w.setObjectName("carteDetailProfil")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(8)

        # Ligne 1 : description fixe
        lbl_info = QLabel("30 jours · 5 Mbps · Appareils simultanés limités")
        lbl_info.setObjectName("detailSessionRow")
        lay.addWidget(lbl_info)

        # Ligne 2 : nb appareils + prix
        h = QHBoxLayout()
        h.setSpacing(12)

        lbl_app = QLabel("Appareils max :")
        lbl_app.setObjectName("labelParametre")
        h.addWidget(lbl_app)

        self._spin_appareils = QSpinBox()
        self._spin_appareils.setRange(1, 20)
        self._spin_appareils.setValue(5)
        self._spin_appareils.setFixedWidth(90)
        self._spin_appareils.setFixedHeight(30)
        self._spin_appareils.valueChanged.connect(self._on_appareils_change)
        h.addWidget(self._spin_appareils)

        h.addStretch()

        lbl_px = QLabel("Prix :")
        lbl_px.setObjectName("labelParametre")
        h.addWidget(lbl_px)

        self._spin_prix_forfait = QSpinBox()
        self._spin_prix_forfait.setRange(0, 9_999_999)
        self._spin_prix_forfait.setSingleStep(1000)
        self._spin_prix_forfait.setSuffix(" Ar")
        self._spin_prix_forfait.setFixedWidth(150)
        self._spin_prix_forfait.setFixedHeight(30)
        self._spin_prix_forfait.valueChanged.connect(self._maj_prix_forfait)
        h.addWidget(self._spin_prix_forfait)
        # Initialiser avec la valeur calculée pour 5 appareils
        self._spin_prix_forfait.setValue(self._prix_forfait_pour(5))

        lay.addLayout(h)
        return w

    @staticmethod
    def _prix_forfait_pour(n_appareils: int) -> int:
        """75 000 Ar pour 5 appareils, +15 000 Ar par appareil supplémentaire."""
        BASE, PALIER, REF = 75_000, 15_000, 5
        return max(PALIER, BASE + (n_appareils - REF) * PALIER)

    def _on_appareils_change(self, n: int):
        self._spin_prix_forfait.blockSignals(True)
        self._spin_prix_forfait.setValue(self._prix_forfait_pour(n))
        self._spin_prix_forfait.blockSignals(False)
        self._maj_prix_forfait()

    def _maj_prix_forfait(self):
        if not hasattr(self, "_btn_confirmer"):
            return
        prix = self._spin_prix_forfait.value()
        self._btn_confirmer.setText(f"  Confirmer — {formater_montant(prix)} Ar")

    def _w_custom(self) -> QFrame:
        """Configuration personnalisée : vitesse + durée (2 lignes)."""
        w = QFrame()
        w.setObjectName("carteDetailProfil")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(8)

        # ── Ligne 1 : boutons vitesse ─────────────────────────────────
        h_vit = QHBoxLayout()
        h_vit.setSpacing(8)
        self._grp_vitesse = QButtonGroup(self)
        self._grp_vitesse.setExclusive(True)
        for i, v in enumerate(VITESSES):
            btn = QPushButton(v["label"])
            btn.setObjectName("boutonPaiement")
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            self._grp_vitesse.addButton(btn, i)
            h_vit.addWidget(btn)
        h_vit.addStretch()
        # Bouton "∞ Libre" dans la même rangée que les vitesses
        self._btn_libre = QPushButton("∞ Libre")
        self._btn_libre.setObjectName("boutonPaiement")
        self._btn_libre.setCheckable(True)
        self._btn_libre.setFixedHeight(30)
        self._btn_libre.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_libre.toggled.connect(self._on_libre_toggle)
        h_vit.addSpacing(8)
        h_vit.addWidget(self._btn_libre)

        self._grp_vitesse.buttons()[0].setChecked(True)
        self._grp_vitesse.buttonClicked.connect(
            lambda b: (
                setattr(self, "_vitesse_idx", self._grp_vitesse.id(b)),
                self._maj_prix_perso(),
            )
        )
        lay.addLayout(h_vit)

        # ── Ligne 2 : durée + prix ────────────────────────────────────
        h_dur = QHBoxLayout()
        h_dur.setSpacing(10)

        lbl_d = QLabel("Durée :")
        lbl_d.setObjectName("labelParametre")
        h_dur.addWidget(lbl_d)

        self._spin_duree = SpinDuree(60)
        self._spin_duree.changed.connect(lambda _: self._maj_prix_perso())
        h_dur.addWidget(self._spin_duree)

        self._lbl_prix_perso = QLabel()
        self._lbl_prix_perso.setObjectName("prixCarteProfil")
        self._lbl_prix_perso.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h_dur.addWidget(self._lbl_prix_perso)

        lay.addLayout(h_dur)
        return w

    def _on_libre_toggle(self, checked: bool):
        self._spin_duree.setVisible(not checked)
        for btn in self._grp_vitesse.buttons():
            btn.setEnabled(not checked)
        if checked:
            # Défaut 5 Mbps (index 1) pour session libre
            self._grp_vitesse.button(1).setChecked(True)
            self._vitesse_idx = 1
            self._lbl_prix_perso.setText(
                f"{formater_montant(TARIFICATION_LIBRE_MIN_AR)} Ar min. (<{TARIFICATION_LIBRE_MIN_MIN} min)"
            )
            self._btn_confirmer.setText("  Ouvrir la session")
        else:
            self._maj_prix_perso()

    # ── Page 2 : ticket généré ────────────────────────────────────────────────

    def _page_resultat(self) -> QWidget:
        page = QWidget()
        page.setObjectName("pageDialogVente")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 26)
        lay.setSpacing(16)

        badge = QLabel("  ✓  Ticket vendu avec succès  ")
        badge.setObjectName("badgeSuccesVente")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge)

        carte = QFrame()
        carte.setObjectName("carteTicketGenere")
        ct = QVBoxLayout(carte)
        ct.setContentsMargins(20, 22, 20, 22)
        ct.setSpacing(10)

        # QR code de connexion
        self._lbl_qr = QLabel()
        self._lbl_qr.setFixedSize(160, 160)
        self._lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_qr.setStyleSheet(
            "background-color:#ffffff;border-radius:10px;padding:6px;"
        )
        ct.addWidget(self._lbl_qr, alignment=Qt.AlignmentFlag.AlignHCenter)

        lbl_qr_txt = QLabel("Scannez pour vous connecter au WiFi")
        lbl_qr_txt.setObjectName("detailSessionRow")
        lbl_qr_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(lbl_qr_txt)

        ct.addWidget(self._sep())

        lbl_c = QLabel("UTILISATEUR")
        lbl_c.setObjectName("titreSectionSessions")
        lbl_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(lbl_c)

        self._lbl_code = QLabel("———")
        self._lbl_code.setObjectName("codeTicketGenere")
        self._lbl_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(self._lbl_code)

        ct.addWidget(self._sep())

        lbl_p = QLabel("MOT DE PASSE")
        lbl_p.setObjectName("titreSectionSessions")
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(lbl_p)

        self._lbl_mdp = QLabel("———")
        self._lbl_mdp.setObjectName("passwordTicketGenere")
        self._lbl_mdp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ct.addWidget(self._lbl_mdp)

        lay.addWidget(carte)

        self._lbl_recap = QLabel()
        self._lbl_recap.setObjectName("recapTicket")
        self._lbl_recap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl_recap)

        lay.addStretch()
        lay.addWidget(self._sep())

        h_act = QHBoxLayout()
        h_act.setSpacing(10)

        self._btn_imp = QPushButton("  Imprimer")
        self._btn_imp.setObjectName("boutonActionHistorique")
        self._btn_imp.setIcon(qta.icon("fa5s.print", color="#5c5f6e"))
        self._btn_imp.setFixedHeight(44)
        self._btn_imp.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_imp.clicked.connect(self._imprimer)
        h_act.addWidget(self._btn_imp)
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

    # ── Logique ───────────────────────────────────────────────────────────────

    def _on_combo_change(self, idx: int):
        profil = self._combo.itemData(idx)
        if profil == _FORFAIT_TAG:
            self._zone_detail.setCurrentIndex(1)
            self._maj_prix_forfait()
        elif profil is not None:
            self._d_duree.setText(_fmt_duree(profil["duree_session_max"]))
            self._d_debit.setText(f"{profil['debit_max'] // 1024} Mbps")
            self._d_validite.setText(_fmt_validite(profil["validite"]))
            self._d_prix.setText(f"{formater_montant(profil['prix'])} Ar")
            self._zone_detail.setCurrentIndex(0)
            self._btn_confirmer.setText(f"  Confirmer — {formater_montant(profil['prix'])} Ar")
        else:
            self._zone_detail.setCurrentIndex(2)
            self._maj_prix_perso()

    def _maj_prix_perso(self):
        duree_min = self._spin_duree.valeur_minutes
        prix = round((duree_min / 60) * TARIFICATION_PRIX_PAR_HEURE)
        self._lbl_prix_perso.setText(f"{formater_montant(prix)} Ar")
        profil = self._combo.currentData()
        if profil is None:
            self._btn_confirmer.setText(f"  Confirmer — {formater_montant(prix)} Ar")

    def _effectuer_vente(self):
        code     = _generer_code_unique()
        password = _generer_password()
        profil   = self._combo.currentData()

        # ── Forfait mensuel partagé ───────────────────────────────────
        if profil == _FORFAIT_TAG:
            n_app  = self._spin_appareils.value()
            prix   = self._spin_prix_forfait.value()
            nom_profil = f"Forfait 5 Mbps - {n_app} app"
            ticket = {
                "code":              code,
                "password":          password,
                "profil":            nom_profil,
                "profil_id":         None,
                "debit_max":         5120,          # 5 Mbps
                "duree_session_max": 43200,          # 30 jours en minutes (DB uniquement)
                "validite":          720,            # 30 jours en heures
                "prix":              prix,
                "methode":           self._methode,
                "utilisateurs_max":  n_app,
            }
            recap = (
                f"Forfait 1 mois · 5 Mbps · {n_app} appareils max  ·  "
                f"{formater_montant(prix)} Ar  ·  {_METHODES.get(self._methode, '')}"
            )
            self._lbl_code.setText(code)
            self._lbl_mdp.setText(password)
            self._afficher_qr(code, password)
            self._lbl_recap.setText(recap)
            self._ticket_en_cours = ticket
            self.ticket_vendu.emit(ticket)
            self._stacked.setCurrentIndex(1)
            return

        # ── Session libre (sans durée fixe) ──────────────────────────
        if profil is None and self._btn_libre.isChecked():
            v = VITESSES[self._vitesse_idx]
            ticket = {
                "code":              code,
                "password":          password,
                "profil":            f"Libre - {v['label']}",
                "profil_id":         None,
                "debit_max":         v["debit_max"],
                "duree_session_max": 0,
                "validite":          24,
                "prix":              0,
                "methode":           self._methode,
                "libre":             True,
            }
            recap = f"Session libre · {v['label']} · Paiement à la fin"
            self._lbl_code.setText(code)
            self._lbl_mdp.setText(password)
            self._afficher_qr(code, password)
            self._lbl_recap.setText(recap)
            self._ticket_en_cours = ticket
            self.ticket_vendu.emit(ticket)
            self._stacked.setCurrentIndex(1)
            return

        if profil is not None:
            ticket = {
                "code":              code,
                "password":          password,
                "profil":            profil["nom"],
                "profil_id":         profil.get("id"),
                "debit_max":         profil["debit_max"],
                "duree_session_max": profil["duree_session_max"],
                "validite":          profil["validite"],
                "prix":              profil["prix"],
                "methode":           self._methode,
            }
            recap = (
                f"{profil['nom']}  ·  {_fmt_duree(profil['duree_session_max'])}  ·  "
                f"Validité {_fmt_validite(profil['validite'])}  ·  "
                f"{formater_montant(profil['prix'])} Ar  ·  {_METHODES.get(self._methode, '')}"
            )
        else:
            duree_min = self._spin_duree.valeur_minutes
            prix      = round((duree_min / 60) * TARIFICATION_PRIX_PAR_HEURE)
            v         = VITESSES[self._vitesse_idx]
            validite = max(1, (duree_min + 59) // 60)  # durée en heures (min 1 h)
            ticket = {
                "code":              code,
                "password":          password,
                "profil":            f"Perso - {v['label']}",
                "profil_id":         None,
                "debit_max":         v["debit_max"],
                "duree_session_max": duree_min,
                "validite":          validite,
                "prix":              prix,
                "methode":           self._methode,
            }
            recap = (
                f"Personnalisé {v['label']}  ·  {_fmt_duree(duree_min)}  ·  "
                f"{formater_montant(prix)} Ar  ·  {_METHODES.get(self._methode, '')}"
            )

        self._lbl_code.setText(code)
        self._lbl_mdp.setText(password)
        self._afficher_qr(code, password)
        self._lbl_recap.setText(recap)
        self._ticket_en_cours = ticket
        self.ticket_vendu.emit(ticket)
        self._stacked.setCurrentIndex(1)

    def _afficher_qr(self, code: str, password: str):
        """Affiche le QR code de connexion correspondant au ticket."""
        pix = generer_pixmap(url_connexion_hotspot(code, password))
        if pix is None:
            self._lbl_qr.setText("QR indisponible")
            self._lbl_qr.setStyleSheet("color:#5c5f6e;")
        else:
            self._lbl_qr.setText("")
            self._lbl_qr.setStyleSheet(
                "background-color:#ffffff;border-radius:10px;padding:6px;"
            )
            self._lbl_qr.setPixmap(pix)

    def _imprimer(self):
        if not self._ticket_en_cours:
            return
        from datetime import datetime as _dt
        from services.impression_service import imprimer_ticket
        data = {
            "code":     self._ticket_en_cours.get("code", ""),
            "password": self._ticket_en_cours.get("password", ""),
            "profil":   self._ticket_en_cours.get("profil", ""),
            "duree_min": self._ticket_en_cours.get("duree_session_max", 0),
            "montant":  self._ticket_en_cours.get("prix", 0),
            "methode":  self._ticket_en_cours.get("methode", ""),
            "date":     _dt.now().strftime("%d/%m/%Y"),
            "heure":    _dt.now().strftime("%H:%M"),
            "qr":       url_connexion_hotspot(
                self._ticket_en_cours.get("code", ""),
                self._ticket_en_cours.get("password", ""),
            ),
        }
        imprimer_ticket(data, parent=self)

    def _reinitialiser(self):
        self._combo.setCurrentIndex(0)
        self._spin_duree.definir_minutes(60)
        self._spin_appareils.setValue(5)
        self._spin_prix_forfait.setValue(self._prix_forfait_pour(5))
        self._grp_vitesse.buttons()[0].setChecked(True)
        self._btn_libre.setChecked(False)
        self._vitesse_idx = 0
        self._grp_pay.buttons()[0].setChecked(True)
        self._methode = "especes"
        self._lbl_qr.clear()
        self._stacked.setCurrentIndex(0)

    # ── Helpers UI ────────────────────────────────────────────────────────────

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
