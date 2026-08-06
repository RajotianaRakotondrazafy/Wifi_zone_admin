import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QMessageBox, QScrollArea,
)

from controllers.blocages.blocages_controller import BlocagesController


def _formater_date(iso: str) -> str:
    try:
        return iso[:10].replace("-", "/")
    except (TypeError, ValueError):
        return iso or ""


class LigneBlocage(QWidget):
    """Ligne représentant un appareil bloqué."""

    deblocage_demande = pyqtSignal(int)

    def __init__(self, donnees: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ligneBlocage")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(16)

        # Icône bloc
        icone = QLabel()
        icone.setPixmap(qta.icon("fa5s.ban", color="#f87171").pixmap(16, 16))
        layout.addWidget(icone)

        # Bloc texte
        bloc = QVBoxLayout()
        bloc.setSpacing(3)

        ligne1 = QHBoxLayout()
        ligne1.setSpacing(10)
        nom = QLabel(donnees["nom"])
        nom.setObjectName("nomUtilisateur")
        ligne1.addWidget(nom)
        mac = QLabel(donnees["mac_address"])
        mac.setObjectName("macBlocage")
        ligne1.addWidget(mac)
        ligne1.addStretch()
        bloc.addLayout(ligne1)

        ligne2 = QHBoxLayout()
        ligne2.setSpacing(10)
        raison = QLabel(f"Raison : {donnees['raison']}")
        raison.setObjectName("raisonBlocage")
        ligne2.addWidget(raison)
        date = QLabel(f"· Bloqué le {_formater_date(donnees.get('date_blocage'))}")
        date.setObjectName("dateBlocage")
        ligne2.addWidget(date)
        ligne2.addStretch()
        bloc.addLayout(ligne2)

        layout.addLayout(bloc)
        layout.addStretch()

        # IP
        lbl_ip = QLabel(donnees.get("ip_assignee", "") or "—")
        lbl_ip.setObjectName("ipZone")
        layout.addWidget(lbl_ip)

        layout.addSpacing(8)

        # Bouton débloquer
        btn = QPushButton("Débloquer")
        btn.setObjectName("boutonActionIdentifier")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.clicked.connect(lambda: self.deblocage_demande.emit(donnees.get("id")))
        layout.addWidget(btn)


class BlocagesPage(QWidget):
    """Page de gestion des appareils bloqués (données réelles)."""

    def __init__(self, controller: BlocagesController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._blocages: list[dict] = []

        self._construire_interface()

        # Rafraîchissement périodique : les blocages du tableau de bord
        # doivent apparaître ici sans relancer l'application
        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self._rafraichir)
        self._timer.start()

        self._rafraichir()

    # ── Construction ──────────────────────────────────────────────────────

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        titre = QLabel("Appareils bloqués")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        self._badge = QLabel("  0 bloqué(s)  ")
        self._badge.setObjectName("badgeBlocage")
        header.addWidget(self._badge)
        layout.addLayout(header)

        # ── Recherche ────────────────────────────────────────────────────
        self._recherche = QLineEdit()
        self._recherche.setObjectName("barreRecherche")
        self._recherche.setPlaceholderText("   Rechercher par MAC, nom ou IP…")
        self._recherche.setFixedHeight(40)
        self._recherche.textChanged.connect(self._rafraichir)
        layout.addWidget(self._recherche)

        # ── Liste ────────────────────────────────────────────────────────
        self._card = QFrame()
        self._card.setObjectName("cardSessions")
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(0)

        self._titre_section = QLabel("LISTE DES BLOCAGES  ·  0")
        self._titre_section.setObjectName("titreSectionSessions")
        self._titre_section.setContentsMargins(20, 16, 20, 12)
        self._card_layout.addWidget(self._titre_section)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        self._card_layout.addWidget(sep)

        self._conteneur_lignes = QWidget()
        self._conteneur_lignes.setStyleSheet("background: transparent;")
        self._layout_lignes = QVBoxLayout(self._conteneur_lignes)
        self._layout_lignes.setContentsMargins(0, 0, 0, 0)
        self._layout_lignes.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(self._conteneur_lignes)
        self._card_layout.addWidget(scroll, stretch=1)

        layout.addWidget(self._card, stretch=1)

    # ── Données ──────────────────────────────────────────────────────────

    def _rafraichir(self):
        self._blocages = self._controller.lister()
        total = len(self._blocages)

        self._badge.setText(f"  {total} bloqué(s)  ")
        self._titre_section.setText(f"LISTE DES BLOCAGES  ·  {total}")

        filtres = self._recherche.text().strip().lower()
        lignes = [
            b for b in self._blocages
            if not filtres
            or filtres in b["mac_address"].lower()
            or filtres in (b["nom"] or "").lower()
            or filtres in (b["ip_assignee"] or "").lower()
        ]

        self._vider_layout(self._layout_lignes)

        if not lignes:
            message = "Aucun appareil bloqué." if total == 0 else "Aucun résultat pour cette recherche."
            vide = QLabel(message)
            vide.setObjectName("loginUtilisateur")
            vide.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vide.setContentsMargins(0, 24, 0, 24)
            self._layout_lignes.addWidget(vide)
            return

        for i, b in enumerate(lignes):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setObjectName("separateurSession")
                self._layout_lignes.addWidget(sep)
            ligne = LigneBlocage(b)
            ligne.deblocage_demande.connect(self._demander_deblocage)
            self._layout_lignes.addWidget(ligne)

        self._layout_lignes.addStretch()

    # ── Actions ──────────────────────────────────────────────────────────

    def _demander_deblocage(self, blocage_id):
        blocage = next((b for b in self._blocages if b.get("id") == blocage_id), None)
        nom = blocage["nom"] if blocage else "cet appareil"
        rep = QMessageBox.question(
            self, "Débloquer l'appareil",
            f"Autoriser à nouveau <b>{nom}</b> à se connecter au hotspot ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if rep != QMessageBox.StandardButton.Yes:
            return

        resultat = self._controller.debloquer_appareil(blocage_id)
        if resultat.get("ok"):
            self._rafraichir()
            QMessageBox.information(self, "Appareil débloqué", resultat.get("message", ""))
        else:
            QMessageBox.warning(self, "Erreur", resultat.get("message", "Échec du déblocage."))

    @staticmethod
    def _vider_layout(lay: QVBoxLayout):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
