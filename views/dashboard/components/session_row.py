import qtawesome as qta
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
)


# Palette de couleurs pour les avatars générés
_COULEURS_AVATAR = [
    "#5b6ee8", "#e85b6e", "#6ee85b", "#e8c45b",
    "#5be8d4", "#c45be8", "#e8825b", "#5b9ee8",
]


def _couleur_pour(cle: str) -> str:
    """Génère une couleur déterministe à partir d'une chaîne."""
    valeur = sum(ord(c) for c in cle)
    return _COULEURS_AVATAR[valeur % len(_COULEURS_AVATAR)]


def _initiales(nom: str) -> str:
    """Extrait jusqu'à 2 initiales depuis un nom."""
    if not nom or nom.lower() in ("inconnu", "unknown"):
        return "?"
    parties = nom.strip().split()
    if len(parties) >= 2:
        return (parties[0][0] + parties[1][0]).upper()
    return parties[0][:2].upper()


class AvatarCirculaire(QWidget):
    def __init__(self, nom: str, cle_couleur: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._initiales = _initiales(nom)
        self._couleur = QColor(_couleur_pour(cle_couleur))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._couleur))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 36, 36)
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initiales)


class SessionRow(QWidget):
    """Ligne représentant une session active dans la liste du tableau de bord."""

    def __init__(self, donnees: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("sessionRow")

        nom = donnees.get("nom_appareil", "Inconnu")
        mac = donnees.get("mac_address", "")
        type_appareil = donnees.get("type_appareil", "")
        debit = donnees.get("debit_actuel", 0)
        est_connecte: bool = donnees.get("est_connecte", False)
        est_identifie: bool = donnees.get("est_identifie", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # --- Pastille de statut ---
        pastille = QLabel()
        pastille.setFixedSize(10, 10)
        couleur_pastille = "#4ade80" if est_connecte else "#5c5f6e"
        pastille.setStyleSheet(
            f"background-color: {couleur_pastille}; border-radius: 5px;"
        )
        layout.addWidget(pastille)

        # --- Avatar circulaire ---
        cle = mac if mac else nom
        avatar = AvatarCirculaire(nom, cle)
        layout.addWidget(avatar)

        # --- Bloc texte ---
        bloc_texte = QVBoxLayout()
        bloc_texte.setSpacing(2)

        nom_affiche = nom if (est_identifie or nom not in ("Inconnu", "")) else "Inconnu"
        label_nom = QLabel(nom_affiche)
        label_nom.setObjectName("nomSessionRow")
        bloc_texte.addWidget(label_nom)

        detail = f"{mac}  ·  {type_appareil}" if mac else type_appareil
        label_detail = QLabel(detail)
        label_detail.setObjectName("detailSessionRow")
        bloc_texte.addWidget(label_detail)

        layout.addLayout(bloc_texte)
        layout.addStretch()

        # --- Débit actuel (uniquement si connecté) ---
        if est_connecte:
            conteneur_debit = QHBoxLayout()
            conteneur_debit.setSpacing(4)

            icone_debit = QLabel()
            icone_debit.setPixmap(
                qta.icon("fa5s.arrow-down", color="#8b8d98").pixmap(12, 12)
            )
            conteneur_debit.addWidget(icone_debit)

            label_debit = QLabel(f"{debit} Mb/s")
            label_debit.setObjectName("debitSessionRow")
            conteneur_debit.addWidget(label_debit)

            layout.addLayout(conteneur_debit)

        # --- Boutons d'action ---
        if est_connecte and est_identifie:
            layout.addWidget(self._bouton("Limiter", "boutonActionLimiter"))
            layout.addWidget(self._bouton("Bloquer", "boutonActionBloquer"))
        elif est_connecte and not est_identifie:
            layout.addWidget(self._bouton("Identifier", "boutonActionIdentifier"))
            layout.addWidget(self._bouton("Bloquer", "boutonActionBloquer"))
        else:
            label_deconnecte = QLabel("déconnecté")
            label_deconnecte.setObjectName("labelDeconnecte")
            layout.addWidget(label_deconnecte)
            layout.addWidget(self._bouton("Historique", "boutonActionHistorique"))

    @staticmethod
    def _bouton(texte: str, object_name: str) -> QPushButton:
        btn = QPushButton(texte)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)
        return btn
