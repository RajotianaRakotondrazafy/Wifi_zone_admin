from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSpinBox, QComboBox


_UNITES = [
    ("min",  1),
    ("h",    60),
    ("jour", 1440),
]
_PLAGES = [(1, 10080), (1, 168), (1, 30)]


class SpinDuree(QWidget):
    """SpinBox + sélecteur d'unité (min / h / jour).

    API publique :
        changed              — signal(int) émis avec la valeur en minutes
        valeur_minutes       — property lecture, retourne toujours des minutes
        definir_minutes(n)   — initialise depuis des minutes
    """

    changed = pyqtSignal(int)  # valeur en minutes

    def __init__(self, valeur_minutes: int = 60, parent=None):
        super().__init__(parent)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._spin = QSpinBox()
        self._spin.setObjectName("comboParametres")
        self._spin.setFixedHeight(40)
        lay.addWidget(self._spin, stretch=1)

        self._combo = QComboBox()
        self._combo.setObjectName("comboParametres")
        self._combo.setFixedHeight(40)
        self._combo.setFixedWidth(72)
        for label, _ in _UNITES:
            self._combo.addItem(label)
        lay.addWidget(self._combo)

        self._idx = 0

        self._definir_sans_signal(valeur_minutes)

        self._spin.valueChanged.connect(self._emettre)
        self._combo.currentIndexChanged.connect(self._on_unite_change)

    # ── API publique ──────────────────────────────────────────────────────────

    @property
    def valeur_minutes(self) -> int:
        return self._spin.value() * _UNITES[self._idx][1]

    def definir_minutes(self, minutes: int):
        self._combo.blockSignals(True)
        self._spin.blockSignals(True)
        self._definir_sans_signal(minutes)
        self._combo.blockSignals(False)
        self._spin.blockSignals(False)

    # ── Logique interne ───────────────────────────────────────────────────────

    def _definir_sans_signal(self, minutes: int):
        if minutes % 1440 == 0 and minutes >= 1440:
            idx, valeur = 2, minutes // 1440
        elif minutes % 60 == 0 and minutes >= 60:
            idx, valeur = 1, minutes // 60
        else:
            idx, valeur = 0, minutes

        self._idx = idx
        self._combo.setCurrentIndex(idx)
        lo, hi = _PLAGES[idx]
        self._spin.setRange(lo, hi)
        self._spin.setValue(valeur)

    def _on_unite_change(self, new_idx: int):
        minutes = self._spin.value() * _UNITES[self._idx][1]
        self._idx = new_idx
        lo, hi = _PLAGES[new_idx]
        self._spin.setRange(lo, hi)
        self._spin.setValue(max(lo, minutes // _UNITES[new_idx][1]))
        self.changed.emit(self.valeur_minutes)

    def _emettre(self, _):
        self.changed.emit(self.valeur_minutes)
