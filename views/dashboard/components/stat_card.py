import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class StatCard(QFrame):
    """Carte de statistique réutilisable pour le tableau de bord."""

    def __init__(
        self,
        icone_qtawesome: str,
        titre: str,
        valeur: str,
        sous_texte: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        # --- Icône dans un cercle de fond coloré ---
        conteneur_icone = QHBoxLayout()
        conteneur_icone.setContentsMargins(0, 0, 0, 0)

        self._cercle_icone = QLabel()
        self._cercle_icone.setObjectName("cercleIconeStatCard")
        self._cercle_icone.setFixedSize(38, 38)
        self._cercle_icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cercle_icone.setPixmap(qta.icon(icone_qtawesome, color="#5b6ee8").pixmap(18, 18))
        conteneur_icone.addWidget(self._cercle_icone)
        conteneur_icone.addStretch()

        layout.addLayout(conteneur_icone)

        # --- Titre ---
        self._label_titre = QLabel(titre)
        self._label_titre.setObjectName("titreStatCard")
        layout.addWidget(self._label_titre)

        # --- Valeur ---
        self._label_valeur = QLabel(valeur)
        self._label_valeur.setObjectName("valeurStatCard")
        layout.addWidget(self._label_valeur)

        # --- Sous-texte ---
        self._label_sous_texte = QLabel(sous_texte)
        self._label_sous_texte.setObjectName("sousTexteStatCard")
        self._label_sous_texte.setVisible(bool(sous_texte))
        layout.addWidget(self._label_sous_texte)

    def mettre_a_jour(self, valeur: str, sous_texte: str = None):
        """Rafraîchit la valeur et le sous-texte sans recréer le widget."""
        self._label_valeur.setText(valeur)
        if sous_texte is not None:
            self._label_sous_texte.setText(sous_texte)
            self._label_sous_texte.setVisible(bool(sous_texte))
