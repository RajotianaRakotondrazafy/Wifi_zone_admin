import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea,
)


# TODO: remplacer par router_repository.lister_tous()
ZONES_FACTICES = [
    {
        "nom": "Zone A", "lieu": "Salle d'attente",
        "modele": "MikroTik hAP ac²", "ip": "192.168.1.1",
        "appareils": 7, "max_appareils": 20, "connecte": True,
    },
    {
        "nom": "Zone B", "lieu": "Bureau direction",
        "modele": "MikroTik RB750Gr3", "ip": "192.168.2.1",
        "appareils": 3, "max_appareils": 10, "connecte": True,
    },
    {
        "nom": "Zone C", "lieu": "Parking",
        "modele": "MikroTik hAP mini", "ip": "192.168.3.1",
        "appareils": 0, "max_appareils": 15, "connecte": False,
    },
]


class ZoneCard(QFrame):
    """Carte représentant une zone WiFi / routeur."""

    def __init__(self, donnees: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("zoneCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # ── En-tête : nom + badge statut ─────────────────────────────
        header = QHBoxLayout()

        # Icône dans cercle
        cercle = QLabel()
        cercle.setObjectName(
            "cercleIconeZoneActif" if donnees["connecte"] else "cercleIconeZoneInactif"
        )
        cercle.setFixedSize(40, 40)
        cercle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        couleur_icone = "#4ade80" if donnees["connecte"] else "#5c5f6e"
        cercle.setPixmap(qta.icon("fa5s.wifi", color=couleur_icone).pixmap(18, 18))
        header.addWidget(cercle)

        bloc_titre = QVBoxLayout()
        bloc_titre.setSpacing(2)
        nom = QLabel(donnees["nom"])
        nom.setObjectName("nomZone")
        bloc_titre.addWidget(nom)
        lieu = QLabel(donnees["lieu"])
        lieu.setObjectName("descriptionZone")
        bloc_titre.addWidget(lieu)
        header.addLayout(bloc_titre)
        header.addStretch()

        badge = QLabel(" Connecté " if donnees["connecte"] else " Hors ligne ")
        badge.setObjectName("badgeActif" if donnees["connecte"] else "badgeInactif")
        header.addWidget(badge)
        layout.addLayout(header)

        # ── Séparateur ───────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurSession")
        layout.addWidget(sep)

        # ── Infos ────────────────────────────────────────────────────
        infos = QHBoxLayout()
        infos.setSpacing(24)

        for icone_id, valeur, etiquette in [
            ("fa5s.server",  donnees["modele"],               "Modèle"),
            ("fa5s.network-wired", donnees["ip"],             "Adresse IP"),
            ("fa5s.laptop",  f"{donnees['appareils']} / {donnees['max_appareils']}", "Appareils"),
        ]:
            bloc = QVBoxLayout()
            bloc.setSpacing(3)
            lbl_et = QLabel(etiquette)
            lbl_et.setObjectName("descriptionZone")
            bloc.addWidget(lbl_et)
            lbl_val = QLabel(valeur)
            lbl_val.setObjectName("nomZone" if etiquette != "Adresse IP" else "ipZone")
            bloc.addWidget(lbl_val)
            infos.addLayout(bloc)

        infos.addStretch()
        layout.addLayout(infos)

        # ── Boutons ──────────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch()

        btn_config = QPushButton("Configurer")
        btn_config.setObjectName("boutonActionLimiter")
        btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_config.setFixedHeight(32)
        actions.addWidget(btn_config)

        if donnees["connecte"]:
            btn_action = QPushButton("Déconnecter")
            btn_action.setObjectName("boutonActionBloquer")
        else:
            btn_action = QPushButton("Reconnecter")
            btn_action.setObjectName("boutonActionIdentifier")
        btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_action.setFixedHeight(32)
        actions.addWidget(btn_action)

        layout.addLayout(actions)


class ZonesWifiPage(QWidget):
    """Page de gestion des zones WiFi / routeurs MikroTik."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        titre = QLabel("Zones WiFi")
        titre.setObjectName("titreDashboard")
        header.addWidget(titre)
        header.addStretch()

        actives = sum(1 for z in ZONES_FACTICES if z["connecte"])
        badge = QLabel(f"  {actives} zone(s) active(s)  ")
        badge.setObjectName("badgeActif")
        header.addWidget(badge)
        header.addSpacing(12)

        btn = QPushButton("  Ajouter une zone")
        btn.setObjectName("boutonActionPage")
        btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        header.addWidget(btn)
        layout.addLayout(header)

        # ── Cards zones ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        contenu = QWidget()
        contenu_layout = QVBoxLayout(contenu)
        contenu_layout.setSpacing(16)
        contenu_layout.setContentsMargins(0, 0, 0, 0)

        for zone in ZONES_FACTICES:
            contenu_layout.addWidget(ZoneCard(zone))

        contenu_layout.addStretch()
        scroll.setWidget(contenu)
        layout.addWidget(scroll, stretch=1)
