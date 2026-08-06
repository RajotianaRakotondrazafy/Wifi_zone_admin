from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QComboBox, QPushButton, QFrame,
)


_UNITES = [("Ko/s", 1), ("Mo/s", 1000)]


class DialogLimiter(QDialog):
    """Saisie d'une limite de bande passante pour un appareil."""

    def __init__(self, nom_appareil: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Limiter la bande passante")
        self.setModal(True)
        self.setFixedWidth(380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 24)

        # ── En-tête ──────────────────────────────────────────────────
        titre = QLabel("Limiter la bande passante")
        titre.setObjectName("titreDialog")
        layout.addWidget(titre)

        sous_titre = QLabel(f"Appareil : <b>{nom_appareil}</b>")
        sous_titre.setObjectName("sousTexteDialog")
        layout.addWidget(sous_titre)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separateurDialog")
        layout.addWidget(sep)

        # ── Saisie débit ─────────────────────────────────────────────
        lbl = QLabel("Vitesse maximale")
        lbl.setObjectName("labelChamp")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._spin = QSpinBox()
        self._spin.setRange(1, 99999)
        self._spin.setValue(512)
        self._spin.setFixedHeight(38)
        row.addWidget(self._spin, stretch=1)

        self._combo = QComboBox()
        for label, _ in _UNITES:
            self._combo.addItem(label)
        self._combo.setFixedHeight(38)
        self._combo.setFixedWidth(90)
        row.addWidget(self._combo)

        layout.addLayout(row)

        note = QLabel("La limite s'applique en téléchargement et en envoi.")
        note.setObjectName("noteDialog")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addSpacing(4)

        # ── Boutons ───────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(10)

        btn_annuler = QPushButton("Annuler")
        btn_annuler.setObjectName("boutonSecondaire")
        btn_annuler.setFixedHeight(38)
        btn_annuler.clicked.connect(self.reject)

        btn_ok = QPushButton("Appliquer la limite")
        btn_ok.setObjectName("boutonPrimaire")
        btn_ok.setFixedHeight(38)
        btn_ok.clicked.connect(self.accept)

        btns.addWidget(btn_annuler)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)

    def debit_ko(self) -> int:
        """Retourne la limite choisie en Ko/s."""
        val = self._spin.value()
        multiplicateur = _UNITES[self._combo.currentIndex()][1]
        return val * multiplicateur
