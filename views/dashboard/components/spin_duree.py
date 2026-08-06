from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSpinBox, QComboBox, QLabel


_UNITES = [
    ("min",  1),
    ("h",    60),
    ("jour", 1440),
]
_PLAGES = [(1, 10080), (1, 168), (1, 30)]


class SpinDuree(QWidget):
    """SpinBox + sélecteur d'unité (min / h / jour).

    En mode « h », un second spin (0-59 min) apparaît pour saisir
    des durées comme 2h 45min.

    API publique :
        changed              — signal(int) émis en minutes
        valeur_minutes       — property, retourne toujours des minutes
        definir_minutes(n)   — initialise depuis des minutes
    """

    changed = pyqtSignal(int)

    def __init__(self, valeur_minutes: int = 60, parent=None):
        super().__init__(parent)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Spin principal (heures / minutes / jours)
        self._spin = QSpinBox()
        self._spin.setObjectName("comboParametres")
        self._spin.setFixedHeight(40)
        self._spin.setFixedWidth(68)
        lay.addWidget(self._spin)

        # Sélecteur d'unité
        self._combo = QComboBox()
        self._combo.setObjectName("comboParametres")
        self._combo.setFixedHeight(40)
        self._combo.setFixedWidth(72)
        for label, _ in _UNITES:
            self._combo.addItem(label)
        lay.addWidget(self._combo)

        # Spin supplémentaire pour les minutes résiduelles (mode "h" seulement)
        self._spin_min = QSpinBox()
        self._spin_min.setObjectName("comboParametres")
        self._spin_min.setRange(0, 59)
        self._spin_min.setFixedHeight(40)
        self._spin_min.setFixedWidth(64)
        lay.addWidget(self._spin_min)

        self._lbl_min = QLabel("min")
        self._lbl_min.setObjectName("labelParametre")
        lay.addWidget(self._lbl_min)

        lay.addStretch()

        self._idx = 0
        self._spin_min.hide()
        self._lbl_min.hide()

        self._definir_sans_signal(valeur_minutes)

        self._spin.valueChanged.connect(self._emettre)
        self._spin_min.valueChanged.connect(self._emettre)
        self._combo.currentIndexChanged.connect(self._on_unite_change)

    # ── API publique ──────────────────────────────────────────────────────────

    @property
    def valeur_minutes(self) -> int:
        total = self._spin.value() * _UNITES[self._idx][1]
        if self._idx == 1:          # mode "h" : ajouter les minutes résiduelles
            total += self._spin_min.value()
        return total

    def definir_minutes(self, minutes: int):
        self._combo.blockSignals(True)
        self._spin.blockSignals(True)
        self._spin_min.blockSignals(True)
        self._definir_sans_signal(minutes)
        self._combo.blockSignals(False)
        self._spin.blockSignals(False)
        self._spin_min.blockSignals(False)

    # ── Logique interne ───────────────────────────────────────────────────────

    def _definir_sans_signal(self, minutes: int):
        if minutes % 1440 == 0 and minutes >= 1440:
            idx, valeur, extra = 2, minutes // 1440, 0
        elif minutes >= 60:
            idx   = 1
            valeur = minutes // 60
            extra  = minutes % 60
        else:
            idx, valeur, extra = 0, minutes, 0

        self._idx = idx
        self._combo.setCurrentIndex(idx)
        lo, hi = _PLAGES[idx]
        self._spin.setRange(lo, hi)
        self._spin.setValue(valeur)
        self._spin_min.setValue(extra)
        self._spin_min.setVisible(idx == 1)
        self._lbl_min.setVisible(idx == 1)

    def _on_unite_change(self, new_idx: int):
        minutes  = self.valeur_minutes      # total avant changement d'unité
        self._idx = new_idx
        lo, hi = _PLAGES[new_idx]
        self._spin.setRange(lo, hi)
        self._spin.setValue(max(lo, minutes // _UNITES[new_idx][1]))
        en_mode_h = (new_idx == 1)
        self._spin_min.setVisible(en_mode_h)
        self._lbl_min.setVisible(en_mode_h)
        self._spin_min.setValue(minutes % 60 if en_mode_h else 0)
        self.changed.emit(self.valeur_minutes)

    def _emettre(self, _):
        self.changed.emit(self.valeur_minutes)
