from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QMessageBox,
)

from controllers.blocages.blocages_controller import BlocagesController
from controllers.dashboard.dashboard_controller import DashboardController
from services.mikrotik_worker import WorkerDashboard
from utils.formatage import formater_montant
from views.dashboard.components.stat_card import StatCard
from views.dashboard.components.session_row import SessionRow
from views.dashboard.components.dialog_limiter import DialogLimiter


def _formater_debit(octets_par_sec: float) -> tuple[str, str]:
    """Retourne (valeur_formatée, unité) selon la magnitude du débit en octets/s."""
    if octets_par_sec >= 1_000_000:
        return f"{octets_par_sec / 1_000_000:.1f}", "Mo/s"
    if octets_par_sec >= 1_000:
        return f"{octets_par_sec / 1_000:.0f}", "Ko/s"
    return f"{octets_par_sec:.0f}", "o/s"


class TableauDeBordPage(QWidget):
    """Page principale : statistiques réseau + sessions actives."""

    def __init__(
        self,
        dashboard_controller: DashboardController,
        blocages_controller: BlocagesController,
        parent=None,
    ):
        super().__init__(parent)
        self._controller = dashboard_controller
        self._blocages_controller = blocages_controller
        self._worker: WorkerDashboard | None = None

        self._construire_interface()

        # Rafraîchissement toutes les 5 secondes en arrière-plan
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._lancer_rafraichissement)
        self._timer.start()

        self._lancer_rafraichissement()

    # ── Construction ────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)
        layout.addLayout(self._construire_header())
        layout.addLayout(self._construire_rangee_stats())
        layout.addLayout(self._construire_rangee_ventes())
        layout.addWidget(self._construire_card_sessions(), stretch=1)

    def _construire_header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        titre = QLabel("Tableau de bord réseau")
        titre.setObjectName("titreDashboard")
        h.addWidget(titre)
        h.addStretch()

        self._badge_connexion = QWidget()
        self._badge_connexion.setObjectName("badgeConnexion")
        bl = QHBoxLayout(self._badge_connexion)
        bl.setContentsMargins(12, 6, 14, 6)
        bl.setSpacing(6)

        self._pastille = QLabel()
        self._pastille.setFixedSize(8, 8)
        self._pastille.setObjectName("pastilleConnexion")
        bl.addWidget(self._pastille)

        self._lbl_badge = QLabel("Connexion…")
        self._lbl_badge.setObjectName("texteBadgeConnexion")
        bl.addWidget(self._lbl_badge)

        h.addWidget(self._badge_connexion)
        return h

    def _construire_rangee_stats(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._card_appareils  = StatCard("fa5s.laptop",     "Appareils connectés", "—", "en ligne")
        self._card_debit_down = StatCard("fa5s.arrow-down", "Débit descendant",    "—", "")
        self._card_debit_up   = StatCard("fa5s.arrow-up",   "Débit montant",       "—", "")
        self._card_latence    = StatCard("fa5s.signal",      "Latence",             "—", "ms")
        for c in (self._card_appareils, self._card_debit_down, self._card_debit_up, self._card_latence):
            r.addWidget(c)
        return r

    def _construire_rangee_ventes(self) -> QHBoxLayout:
        r = QHBoxLayout()
        r.setSpacing(16)
        self._card_nb_ventes = StatCard("fa5s.receipt", "Ventes du jour",  "—", "tickets")
        self._card_ca        = StatCard("fa5s.coins",   "CA du jour",      "—", "Ar", masquable=True)
        self._card_ca_produits = StatCard("fa5s.shopping-basket", "CA produits du jour", "—", "Ar", masquable=True)
        self._card_nb_produits = StatCard("fa5s.box-open",   "Articles produits", "—", "articles")
        for c in (self._card_nb_ventes, self._card_ca, self._card_ca_produits, self._card_nb_produits):
            r.addWidget(c)
        r.addStretch()
        return r

    def _construire_card_sessions(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardSessions")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._titre_sessions = QLabel("SESSIONS ACTIVES  ·  —")
        self._titre_sessions.setObjectName("titreSectionSessions")
        self._titre_sessions.setContentsMargins(20, 16, 20, 12)
        layout.addWidget(self._titre_sessions)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._conteneur_sessions = QWidget()
        self._layout_sessions = QVBoxLayout(self._conteneur_sessions)
        self._layout_sessions.setContentsMargins(0, 0, 0, 0)
        self._layout_sessions.setSpacing(0)
        self._layout_sessions.addStretch()

        scroll.setWidget(self._conteneur_sessions)
        layout.addWidget(scroll)
        return card

    # ── Rafraîchissement ────────────────────────────────────────────────

    def _lancer_rafraichissement(self):
        """Démarre un worker de fond si aucun n'est en cours."""
        if self._worker and self._worker.isRunning():
            return
        self._worker = WorkerDashboard(self._controller, parent=self)
        self._worker.donnees_prete.connect(self.rafraichir_donnees)
        self._worker.start()

    def rafraichir_donnees(self, donnees: dict):
        connecte = donnees.get("connecte", False)
        stats    = donnees.get("statistiques", {})
        sessions = donnees.get("sessions_actives", [])

        # ── Badge de connexion ──────────────────────────────────────
        if connecte:
            self._pastille.setStyleSheet(
                "background-color: #4ade80; border-radius: 4px;"
            )
            self._lbl_badge.setText("Routeur connecté")
        else:
            self._pastille.setStyleSheet(
                "background-color: #f87171; border-radius: 4px;"
            )
            self._lbl_badge.setText("Routeur déconnecté")

        # ── Stat cards ──────────────────────────────────────────────
        nb = stats.get("appareils_connectes", 0)
        self._card_appareils.mettre_a_jour(str(nb) if connecte else "—", "en ligne")

        down = stats.get("debit_descendant", 0.0)
        if connecte:
            val_d, unit_d = _formater_debit(down)
            self._card_debit_down.mettre_a_jour(val_d, unit_d)
        else:
            self._card_debit_down.mettre_a_jour("—", "")

        up = stats.get("debit_montant", 0.0)
        if connecte:
            val_u, unit_u = _formater_debit(up)
            self._card_debit_up.mettre_a_jour(val_u, unit_u)
        else:
            self._card_debit_up.mettre_a_jour("—", "")

        lat = stats.get("latence", -1)
        if connecte and lat >= 0:
            self._card_latence.mettre_a_jour(str(lat), "ms")
        else:
            self._card_latence.mettre_a_jour("—", "ms")

        # ── KPIs commerciaux ────────────────────────────────────────
        ventes = donnees.get("ventes", {})
        self._card_nb_ventes.mettre_a_jour(str(ventes.get("nb_ventes", 0)), "tickets")
        ca = ventes.get("ca_total", 0)
        ca_str = formater_montant(ca)
        self._card_ca.mettre_a_jour(ca_str, "Ar")

        produits = donnees.get("produits", {})
        ca_p = produits.get("ca_total", 0)
        self._card_ca_produits.mettre_a_jour(formater_montant(ca_p), "Ar")
        self._card_nb_produits.mettre_a_jour(
            str(produits.get("nb_articles", 0)), "articles"
        )

        # ── Titre section sessions ──────────────────────────────────
        self._titre_sessions.setText(
            f"SESSIONS ACTIVES  ·  {nb}" if connecte else "SESSIONS ACTIVES  ·  —"
        )

        # ── Liste des sessions ──────────────────────────────────────
        while self._layout_sessions.count() > 1:
            item = self._layout_sessions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sessions:
            lbl = QLabel(
                "Aucune session active" if connecte else "Routeur non connecté"
            )
            lbl.setObjectName("detailSessionRow")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setContentsMargins(0, 24, 0, 24)
            self._layout_sessions.insertWidget(0, lbl)
            return

        for i, session in enumerate(sessions):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                self._layout_sessions.insertWidget(
                    self._layout_sessions.count() - 1, sep
                )
            row = SessionRow(session)
            row.limiter_demande.connect(self._on_limiter)
            row.bloquer_demande.connect(self._on_bloquer)
            self._layout_sessions.insertWidget(
                self._layout_sessions.count() - 1, row
            )

    # ── Actions session ──────────────────────────────────────────────

    def _on_limiter(self, donnees: dict):
        nom = donnees.get("nom_appareil", "Inconnu")
        ip  = donnees.get("adresse_ip", "")
        dlg = DialogLimiter(nom, parent=self)
        if dlg.exec() != DialogLimiter.DialogCode.Accepted:
            return
        ok = self._controller.limiter_session(ip, dlg.debit_ko())
        if ok:
            QMessageBox.information(
                self, "Limite appliquée",
                f"Limite de {dlg.debit_ko()} Ko/s appliquée à {nom}."
            )
        else:
            QMessageBox.warning(
                self, "Erreur",
                f"Impossible d'appliquer la limite pour {nom}.\n"
                "Vérifiez la connexion au routeur."
            )

    def _on_bloquer(self, donnees: dict):
        nom = donnees.get("nom_appareil", "Inconnu")
        rep = QMessageBox.question(
            self, "Bloquer l'appareil",
            f"Bloquer définitivement <b>{nom}</b> ?<br>"
            "Il sera déconnecté et ne pourra plus se reconnecter au hotspot.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if rep != QMessageBox.StandardButton.Yes:
            return
        resultat = self._blocages_controller.bloquer_appareil(donnees)
        if resultat.get("ok"):
            QMessageBox.information(
                self, "Appareil bloqué",
                resultat.get("message", "Appareil bloqué."),
            )
        else:
            QMessageBox.warning(
                self, "Erreur",
                resultat.get("message", "Impossible de bloquer l'appareil."),
            )
