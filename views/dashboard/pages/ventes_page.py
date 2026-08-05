from datetime import datetime

import qtawesome as qta
from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QProgressBar, QMessageBox,
)

from controllers.ventes.ventes_controller import VentesController
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.dialog_vente import DialogVente
from models.user import User


class SynchronisationMikrotikThread(QThread):
    """Enregistre le ticket sur le routeur MikroTik en arrière-plan."""

    terminee = pyqtSignal(dict)

    def __init__(self, controller: VentesController, ticket_id: int, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._ticket_id = ticket_id

    def run(self):
        try:
            resultat = self._controller.synchroniser_ticket_mikrotik(self._ticket_id)
        except Exception as exc:
            resultat = {"ok": False, "message": str(exc)}
        self.terminee.emit(resultat)


class DetectionConnexionsThread(QThread):
    """Détecte les premières connexions des tickets vendus sur le routeur."""

    terminee = pyqtSignal(dict)

    def __init__(self, controller: VentesController, parent=None):
        super().__init__(parent)
        self._controller = controller

    def run(self):
        try:
            resultat = self._controller.detecter_premieres_connexions()
        except Exception as exc:
            resultat = {"detectes": 0, "erreur": str(exc)}
        self.terminee.emit(resultat)


_LABELS_METHODE = {
    "especes":      ("Espèces",      "badgeActif"),
    "mobile_money": ("Mobile Money", "badgeCaissier"),
    "carte":        ("Carte",        "badgeAdmin"),
}


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setObjectName("separateurSession")
    return f


# ── Widget : ticket actif avec countdown ────────────────────────────────────

class LigneTicketActif(QWidget):
    def __init__(self, vente: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneTicketActif")

        self._expiration_dt    = vente["expiration_dt"]
        self._duree_totale_sec = vente["profil_duree_min"] * 60.0
        self._demarre          = bool(vente.get("demarre", True))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(10)

        # ── Ligne supérieure ────────────────────────────────────────────
        h_top = QHBoxLayout()
        h_top.setSpacing(12)

        # Pastille verte (grisée tant que le client ne s'est pas connecté)
        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        h_top.addWidget(self._dot)

        # Code monospace
        lbl_code = QLabel(vente["code"])
        lbl_code.setObjectName("codeTicketActif")
        h_top.addWidget(lbl_code)

        h_top.addWidget(self._pt())

        # Profil
        lbl_profil = QLabel(vente["profil"])
        lbl_profil.setObjectName("nomUtilisateur")
        h_top.addWidget(lbl_profil)

        # Badge méthode — largeur fixe
        label_m, style_m = _LABELS_METHODE.get(vente["methode"], ("—", "badgeNeutre"))
        badge = QLabel(label_m)
        badge.setObjectName(style_m)
        badge.setFixedWidth(104)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_top.addWidget(badge)

        h_top.addStretch()

        # Icône horloge
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.clock", color="#5c5f6e").pixmap(12, 12))
        h_top.addWidget(ico)

        # Countdown (mis à jour par actualiser())
        self._lbl_temps = QLabel()
        self._lbl_temps.setFixedWidth(170)
        self._lbl_temps.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h_top.addWidget(self._lbl_temps)

        lay.addLayout(h_top)

        # ── Barre de progression ────────────────────────────────────────
        h_bar = QHBoxLayout()
        h_bar.setSpacing(10)
        h_bar.addSpacing(22)  # aligne visuellement avec le code au-dessus

        self._barre = QProgressBar()
        self._barre.setRange(0, 1000)   # 1000 pour une granularité fine
        self._barre.setTextVisible(False)
        self._barre.setFixedHeight(6)
        h_bar.addWidget(self._barre, stretch=1)

        self._lbl_pct = QLabel()
        self._lbl_pct.setObjectName("labelHeure")
        self._lbl_pct.setFixedWidth(42)
        self._lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h_bar.addWidget(self._lbl_pct)

        lay.addLayout(h_bar)

        self.actualiser()

    def actualiser(self):
        """Recalcule et affiche le temps restant. Appelé chaque seconde."""
        now = datetime.now()

        # Timer non démarré : le client ne s'est pas encore connecté
        if not self._demarre:
            self._dot.setStyleSheet("background-color: #5c5f6e; border-radius: 5px;")
            self._barre.setValue(0)
            self._barre.setStyleSheet(
                "QProgressBar{background-color:#2f3340;border:none;border-radius:3px;}"
                "QProgressBar::chunk{{background-color:#5c5f6e;border-radius:3px;}}"
            )
            self._lbl_temps.setText("En attente de connexion")
            self._lbl_temps.setStyleSheet("color:#5c5f6e;font-size:13px;font-weight:bold;")
            self._lbl_pct.setText("—")
            return

        self._dot.setStyleSheet("background-color: #4ade80; border-radius: 5px;")
        restant_sec = max(0.0, (self._expiration_dt - now).total_seconds())
        ecoul_sec   = self._duree_totale_sec - restant_sec
        pct_mille   = int(min(1000, (ecoul_sec / self._duree_totale_sec) * 1000))
        pct_pct     = pct_mille // 10

        # Couleur progressive
        if pct_pct >= 80:
            couleur = "#f87171"   # rouge — urgent
        elif pct_pct >= 50:
            couleur = "#e8c45b"   # orange — attention
        else:
            couleur = "#4ade80"   # vert — OK

        self._barre.setValue(pct_mille)
        self._barre.setStyleSheet(
            "QProgressBar{background-color:#2f3340;border:none;border-radius:3px;}"
            f"QProgressBar::chunk{{background-color:{couleur};border-radius:3px;}}"
        )

        if restant_sec <= 0:
            self._lbl_temps.setText("Expiré")
            self._lbl_temps.setStyleSheet("color:#5c5f6e;font-size:13px;font-weight:bold;")
            self._lbl_pct.setText("100%")
        else:
            d = int(restant_sec // 86400)
            h = int((restant_sec % 86400) // 3600)
            m = int((restant_sec % 3600) // 60)
            s = int(restant_sec % 60)
            if d > 0:
                texte = f"{d}j {h:02d}h {m:02d}m"
            elif h > 0:
                texte = f"{h}h {m:02d}m {s:02d}s"
            elif m > 0:
                texte = f"{m}min {s:02d}s"
            else:
                texte = f"{s}s"
            self._lbl_temps.setText(f"{texte} restant")
            self._lbl_temps.setStyleSheet(
                f"color:{couleur};font-size:13px;font-weight:bold;"
            )
            self._lbl_pct.setText(f"{100 - pct_pct}%")

    @staticmethod
    def _pt() -> QLabel:
        l = QLabel("·")
        l.setObjectName("labelHeure")
        return l


# ── Widget : ligne de l'historique ──────────────────────────────────────────

class LigneVente(QWidget):
    """Ligne d'une vente dans l'historique du jour (actif ou expiré)."""

    def __init__(self, vente: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneVente")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(0)

        # Heure — colonne fixe
        lbl_h = QLabel(vente["heure"])
        lbl_h.setObjectName("heureVente")
        lbl_h.setFixedWidth(48)
        lay.addWidget(lbl_h)

        lay.addSpacing(12)

        # Code monospace — colonne fixe
        lbl_code = QLabel(vente["code"])
        lbl_code.setObjectName("codeVente")
        lbl_code.setFixedWidth(90)
        lay.addWidget(lbl_code)

        lay.addSpacing(12)

        # Profil — extensible
        lbl_profil = QLabel(vente["profil"])
        lbl_profil.setObjectName("nomUtilisateur")
        lay.addWidget(lbl_profil, stretch=1)

        lay.addSpacing(16)

        # Badge méthode — colonne fixe (Mobile Money est le plus long)
        label_m, style_m = _LABELS_METHODE.get(vente["methode"], ("—", "badgeNeutre"))
        badge_m = QLabel(label_m)
        badge_m.setObjectName(style_m)
        badge_m.setFixedWidth(104)
        badge_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_m)

        lay.addSpacing(16)

        # Montant — colonne fixe, aligné à droite
        lbl_montant = QLabel(f"{int(vente['montant'])} Ar")
        lbl_montant.setObjectName("montantVente")
        lbl_montant.setFixedWidth(80)
        lbl_montant.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(lbl_montant)

        lay.addSpacing(16)

        # Statut — colonne fixe (Expiré est le plus long)
        badge_s = QLabel("Actif" if vente.get("actif", False) else "Expiré")
        badge_s.setObjectName("badgeActif" if vente.get("actif", False) else "badgeExpire")
        badge_s.setFixedWidth(62)
        badge_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge_s)


# ── Page Ventes ──────────────────────────────────────────────────────────────

class VentesPage(QWidget):
    def __init__(self, ventes_controller: VentesController, current_user: User, parent=None):
        super().__init__(parent)
        self._controller   = ventes_controller
        self._current_user = current_user
        self._lignes_actives: list[LigneTicketActif] = []
        self._synchro_thread: SynchronisationMikrotikThread | None = None
        self._detection_thread: DetectionConnexionsThread | None = None

        self._construire_interface()

        # Timer 1 s : mise à jour des countdowns
        self._timer_secondes = QTimer(self)
        self._timer_secondes.setInterval(1000)
        self._timer_secondes.timeout.connect(self._tick_secondes)
        self._timer_secondes.start()

        # Timer 60 s : restructuration des sections (ticket expiré → historique)
        self._timer_refresh = QTimer(self)
        self._timer_refresh.setInterval(60_000)
        self._timer_refresh.timeout.connect(self.rafraichir_donnees)
        self._timer_refresh.start()

        # Timer 30 s : détection des premières connexions sur le routeur
        self._timer_detection = QTimer(self)
        self._timer_detection.setInterval(30_000)
        self._timer_detection.timeout.connect(self._lancer_detection)
        self._timer_detection.start()

        self.rafraichir_donnees()

    # ── Construction ─────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        layout.addLayout(self._header())

        # Stat cards
        layout.addLayout(self._rangee_cards())

        # Section tickets actifs + historique dans un scroll unique
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        corps = QWidget()
        corps_lay = QVBoxLayout(corps)
        corps_lay.setContentsMargins(0, 0, 0, 0)
        corps_lay.setSpacing(20)

        corps_lay.addWidget(self._card_actifs())
        corps_lay.addWidget(self._card_historique())
        corps_lay.addStretch()

        scroll.setWidget(corps)
        layout.addWidget(scroll, stretch=1)

    def _header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        titre = QLabel("Ventes")
        titre.setObjectName("titreDashboard")
        h.addWidget(titre)
        h.addStretch()

        self._badge_ca = QLabel("  Aujourd'hui : 0 Ar  ")
        self._badge_ca.setObjectName("badgeNeutre")
        h.addWidget(self._badge_ca)
        h.addSpacing(12)

        btn = QPushButton("  Vendre un ticket")
        btn.setObjectName("boutonVendre")
        btn.setIcon(qta.icon("fa5s.cash-register", color="#ffffff"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.clicked.connect(self._ouvrir_dialog)
        h.addWidget(btn)
        return h

    def _rangee_cards(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._stat_nb     = StatCard("fa5s.ticket-alt",    "Tickets vendus",    "0",       "aujourd'hui")
        self._stat_ca     = StatCard("fa5s.coins",          "Chiffre d'affaires","0 Ar",    "aujourd'hui")
        self._stat_actifs = StatCard("fa5s.wifi",           "Tickets actifs",    "0",       "en ce moment")
        for c in (self._stat_nb, self._stat_ca, self._stat_actifs):
            r.addWidget(c)
        return r

    def _card_actifs(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titre_actifs = QLabel("TICKETS EN COURS  ·  0")
        self._titre_actifs.setObjectName("titreSectionSessions")
        self._titre_actifs.setContentsMargins(20, 16, 20, 12)
        lay.addWidget(self._titre_actifs)

        self._conteneur_actifs = QWidget()
        self._lay_actifs = QVBoxLayout(self._conteneur_actifs)
        self._lay_actifs.setContentsMargins(0, 0, 0, 0)
        self._lay_actifs.setSpacing(0)

        lay.addWidget(self._conteneur_actifs)
        return card

    def _card_historique(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titre_historique = QLabel("HISTORIQUE DU JOUR  ·  0")
        self._titre_historique.setObjectName("titreSectionSessions")
        self._titre_historique.setContentsMargins(20, 16, 20, 12)
        lay.addWidget(self._titre_historique)

        self._conteneur_hist = QWidget()
        self._lay_hist = QVBoxLayout(self._conteneur_hist)
        self._lay_hist.setContentsMargins(0, 0, 0, 0)
        self._lay_hist.setSpacing(0)

        lay.addWidget(self._conteneur_hist)
        return card

    # ── Données ──────────────────────────────────────────────────────────

    def rafraichir_donnees(self):
        totaux = self._controller.total_du_jour()
        ventes = self._controller.obtenir_ventes_du_jour()

        # Stat cards
        self._stat_nb.mettre_a_jour(str(totaux["nb_ventes"]))
        self._stat_ca.mettre_a_jour(f"{int(totaux['ca_total'])} Ar")
        self._stat_actifs.mettre_a_jour(str(totaux["nb_actifs"]))
        self._badge_ca.setText(f"  Aujourd'hui : {int(totaux['ca_total'])} Ar  ")

        actifs = [v for v in ventes if v["actif"]]

        self._titre_actifs.setText(f"TICKETS EN COURS  ·  {len(actifs)}")
        self._titre_historique.setText(f"HISTORIQUE DU JOUR  ·  {len(ventes)}")

        # Reconstruire section "actifs"
        self._vider_layout(self._lay_actifs)
        self._lignes_actives.clear()

        if not actifs:
            lbl = QLabel("Aucun ticket actif en ce moment.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(20, 14, 20, 14)
            self._lay_actifs.addWidget(lbl)
        else:
            for i, v in enumerate(actifs):
                if i > 0:
                    self._lay_actifs.addWidget(_sep())
                row = LigneTicketActif(v)
                self._lay_actifs.addWidget(row)
                self._lignes_actives.append(row)

        # Reconstruire section "historique"
        self._vider_layout(self._lay_hist)

        if not ventes:
            lbl = QLabel("Aucune vente aujourd'hui.")
            lbl.setObjectName("loginUtilisateur")
            lbl.setContentsMargins(20, 14, 20, 14)
            self._lay_hist.addWidget(lbl)
        else:
            for i, v in enumerate(ventes):
                if i > 0:
                    self._lay_hist.addWidget(_sep())
                self._lay_hist.addWidget(LigneVente(v))

    def _tick_secondes(self):
        """Mise à jour des countdowns (toutes les secondes, sans recréer de widgets)."""
        for row in self._lignes_actives:
            row.actualiser()

    # ── Actions ──────────────────────────────────────────────────────────

    def _ouvrir_dialog(self):
        profils = self._controller.obtenir_profils()
        dialog  = DialogVente(profils, self._current_user.id or 1, parent=self)
        dialog.ticket_vendu.connect(self._on_ticket_vendu)
        dialog.exec()

    def _on_ticket_vendu(self, ticket: dict):
        resultat = self._controller.enregistrer_vente(ticket, self._current_user.id or 1)
        if not resultat.get("ok"):
            QMessageBox.critical(
                self, "Erreur",
                f"La vente n'a pas pu être enregistrée.\n{resultat.get('erreur', 'Erreur inconnue.')}",
            )
            return

        self.rafraichir_donnees()
        self._synchroniser_mikrotik(resultat["ticket_id"], resultat["code"])

    def _synchroniser_mikrotik(self, ticket_id: int, code: str):
        """Enregistre le ticket sur le routeur en arrière-plan puis avertit en cas d'échec."""
        if self._synchro_thread is not None and self._synchro_thread.isRunning():
            QMessageBox.warning(
                self, "Synchronisation en cours",
                "Une synchronisation est déjà en cours. Elle s'appliquera aussi au ticket précédent.",
            )
            return

        self._synchro_thread = SynchronisationMikrotikThread(self._controller, ticket_id, self)
        self._synchro_thread.terminee.connect(
            lambda r, c=code: self._on_synchro_terminee(r, c)
        )
        self._synchro_thread.start()

    def _on_synchro_terminee(self, resultat: dict, code: str):
        if not resultat.get("ok"):
            QMessageBox.warning(
                self, "Ticket non enregistré sur le routeur",
                f"Le ticket {code} a été vendu mais n'a PAS été créé sur le MikroTik.\n\n"
                f"{resultat.get('message', 'Erreur inconnue.')}\n\n"
                "Le client ne pourra pas se connecter tant que le ticket ne sera pas créé "
                "sur le routeur (Zones WiFi → Configurer, ou IP → Hotspot → Users).",
            )

    def _lancer_detection(self):
        """Détecte les premières connexions en arrière-plan (routeur)."""
        if self._detection_thread is not None and self._detection_thread.isRunning():
            return
        self._detection_thread = DetectionConnexionsThread(self._controller, self)
        self._detection_thread.terminee.connect(self._on_detection_terminee)
        self._detection_thread.start()

    def _on_detection_terminee(self, resultat: dict):
        if resultat.get("detectes", 0) > 0:
            self.rafraichir_donnees()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _vider_layout(lay: QVBoxLayout):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
