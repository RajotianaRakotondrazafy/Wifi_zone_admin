import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

_NB_ETOILES_MIN = 6


class MontantMasquable(QWidget):
    def __init__(self, texte: str = "", object_name: str = "", parent=None):
        super().__init__(parent)
        self._texte_reel = texte
        self._revele = False
        self.setObjectName("montantMasquable")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.label = QLabel()
        self.label.setObjectName(object_name or "montantMasquableTexte")
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self.label, stretch=1)

        self.btn_oeil = QPushButton()
        self.btn_oeil.setObjectName("boutonToggleMontant")
        self.btn_oeil.setFixedSize(18, 18)
        self.btn_oeil.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_oeil.setToolTip("Afficher / masquer le montant")
        self.btn_oeil.setFlat(True)
        self.btn_oeil.clicked.connect(self._basculer)
        lay.addWidget(self.btn_oeil, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._mettre_a_jour_icone()
        self._mettre_a_jour_affichage()

    def definir_texte(self, texte: str):
        """Fixe la valeur réelle (masquée tant que non révélée)."""
        self._texte_reel = texte
        self._mettre_a_jour_affichage()

    def reveler(self):
        self._revele = True
        self._mettre_a_jour_affichage()

    def masquer(self):
        self._revele = False
        self._mettre_a_jour_affichage()

    def est_revele(self) -> bool:
        return self._revele

    def _basculer(self):
        if self._revele:
            self.masquer()
        else:
            self.reveler()

    def _masque_dynamique(self) -> str:
        """Étoiles adaptées à la largeur du label (min 6 par défaut)."""
        largeur = self.label.width()
        if largeur <= 0:
            return "*" * _NB_ETOILES_MIN
        largeur_char = self.label.fontMetrics().horizontalAdvance("*")
        if largeur_char <= 0:
            return "*" * _NB_ETOILES_MIN
        nb = int(largeur // largeur_char)
        return "*" * max(_NB_ETOILES_MIN, nb)

    def _mettre_a_jour_affichage(self):
        if not self._texte_reel:
            self.label.setText("")
        elif self._revele:
            self.label.setText(self._texte_reel)
        else:
            self.label.setText(self._masque_dynamique())

    def resizeEvent(self, event):
        """Recalcule le nombre d'étoiles quand la largeur change."""
        if not self._revele:
            self._mettre_a_jour_affichage()
        super().resizeEvent(event)

    def _mettre_a_jour_icone(self):
        icone = "fa5s.eye-slash" if self._revele else "fa5s.eye"
        self.btn_oeil.setIcon(qta.icon(icone, color="#5c5f6e"))