import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame


ITEMS_MENU = [
    ("fa5s.tachometer-alt", "Tableau de bord"),
    ("fa5s.cash-register",  "Ventes"),
    ("fa5s.users",          "Utilisateurs"),
    ("fa5s.wifi",           "Zones WiFi"),
    ("fa5s.chart-bar",      "Statistiques"),
    ("fa5s.file-alt",       "Rapports"),
    ("fa5s.ban",            "Blocages"),
    ("fa5s.cog",            "Paramètres"),
]


class BoutonMenu(QWidget):
    """Bouton de navigation de la sidebar avec indicateur actif."""

    clique = pyqtSignal(str)

    def __init__(self, icone_id: str, texte: str, parent=None):
        super().__init__(parent)
        self.texte = texte
        self._actif = False
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(0)

        # Barre verticale accent (masquée par défaut)
        self.barre_accent = QFrame()
        self.barre_accent.setFixedWidth(4)
        self.barre_accent.setObjectName("barreAccentSidebar")
        self.barre_accent.setVisible(False)
        layout.addWidget(self.barre_accent)

        # Contenu : icône + label
        self.conteneur = QWidget()
        self.conteneur.setObjectName("conteneurBoutonMenu")
        conteneur_layout = QHBoxLayout(self.conteneur)
        conteneur_layout.setContentsMargins(12, 0, 0, 0)
        conteneur_layout.setSpacing(12)

        self.label_icone = QLabel()
        self.label_icone.setFixedSize(18, 18)
        self.label_icone.setPixmap(qta.icon(icone_id, color="#8b8d98").pixmap(18, 18))
        conteneur_layout.addWidget(self.label_icone)

        self.label_texte = QLabel(texte)
        self.label_texte.setObjectName("labelBoutonMenu")
        conteneur_layout.addWidget(self.label_texte)
        conteneur_layout.addStretch()

        layout.addWidget(self.conteneur)

        self._icone_id = icone_id

    def mousePressEvent(self, event):
        self.clique.emit(self.texte)

    def definir_actif(self, actif: bool):
        self._actif = actif
        self.barre_accent.setVisible(actif)
        if actif:
            self.conteneur.setObjectName("conteneurBoutonMenuActif")
            self.label_texte.setObjectName("labelBoutonMenuActif")
            self.label_icone.setPixmap(qta.icon(self._icone_id, color="#5b6ee8").pixmap(18, 18))
        else:
            self.conteneur.setObjectName("conteneurBoutonMenu")
            self.label_texte.setObjectName("labelBoutonMenu")
            self.label_icone.setPixmap(qta.icon(self._icone_id, color="#8b8d98").pixmap(18, 18))
        # Forcer le rechargement du style QSS après changement d'objectName
        self.conteneur.style().unpolish(self.conteneur)
        self.conteneur.style().polish(self.conteneur)
        self.label_texte.style().unpolish(self.label_texte)
        self.label_texte.style().polish(self.label_texte)


class Sidebar(QWidget):
    """Menu latéral de navigation principal."""

    item_selectionne = pyqtSignal(str)
    deconnexion_demandee = pyqtSignal()


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("sidebar")
        self._boutons: dict[str, BoutonMenu] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- En-tête ---
        entete = QWidget()
        entete.setObjectName("entetesSidebar")
        entete.setFixedHeight(72)
        entete_layout = QHBoxLayout(entete)
        entete_layout.setContentsMargins(16, 0, 16, 0)
        entete_layout.setSpacing(10)

        icone_wifi = QLabel()
        icone_wifi.setPixmap(qta.icon("fa5s.wifi", color="#5b6ee8").pixmap(20, 20))
        entete_layout.addWidget(icone_wifi)

        titre = QLabel("WiFi-Zone Manager")
        titre.setObjectName("titreSidebar")
        entete_layout.addWidget(titre)
        entete_layout.addStretch()

        layout.addWidget(entete)

        # Séparateur fin
        separateur = QFrame()
        separateur.setFrameShape(QFrame.Shape.HLine)
        separateur.setObjectName("separateurSidebar")
        layout.addWidget(separateur)
        layout.addSpacing(8)

        # --- Items de menu ---
        for icone_id, texte in ITEMS_MENU:
            bouton = BoutonMenu(icone_id, texte)
            bouton.clique.connect(self._on_item_clique)
            layout.addWidget(bouton)
            self._boutons[texte] = bouton

        layout.addStretch()

        # --- Déconnexion en bas ---
        separateur_bas = QFrame()
        separateur_bas.setFrameShape(QFrame.Shape.HLine)
        separateur_bas.setObjectName("separateurSidebar")
        layout.addWidget(separateur_bas)

        btn_deconnexion = BoutonMenu("fa5s.sign-out-alt", "Déconnexion")
        btn_deconnexion.clique.connect(self.deconnexion_demandee.emit)
        layout.addWidget(btn_deconnexion)

        # Activer "Tableau de bord" par défaut
        self._selectionner("Tableau de bord")

    def _on_item_clique(self, texte: str):
        self._selectionner(texte)
        self.item_selectionne.emit(texte)

    def _selectionner(self, texte: str):
        for nom, bouton in self._boutons.items():
            bouton.definir_actif(nom == texte)
