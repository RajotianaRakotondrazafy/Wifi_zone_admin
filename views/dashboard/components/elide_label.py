from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QLabel


class LabelElide(QLabel):
    """QLabel qui tronque son texte avec « … » si l'espace manque.

    Sa largeur minimale reste petite (même pour un long texte), ce qui
    garantit que les colonnes voisines restent alignées dans un layout.
    """

    def __init__(self, texte: str = "", largeur_min: int = 40, parent=None):
        super().__init__(texte, parent)
        self._texte_complet = texte
        self._largeur_min = largeur_min

    def setLargeurMin(self, largeur: int):
        self._largeur_min = largeur
        self.updateGeometry()
        self._appliquer()

    def setTexte(self, texte: str):
        self._texte_complet = texte
        self._appliquer()

    def texteComplet(self) -> str:
        return self._texte_complet

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(self._largeur_min, hint.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._appliquer()

    def _appliquer(self):
        fm = QFontMetrics(self.font())
        largeur = max(self.width(), self._largeur_min)
        elide = fm.elidedText(
            self._texte_complet, Qt.TextElideMode.ElideRight, largeur
        )
        if elide != self.text():
            self.setText(elide)
