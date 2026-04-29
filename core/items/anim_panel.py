import math
from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QPushButton, QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

_SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
_DEFAULT_SPEED = 1.0
_TICK_MS = 30
_SLIDER_STEPS = 1000


class AnimPanel(QGroupBox):
    t_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__("Animation  (use 't' in y=f(x) expressions)", parent)
        self._t = 0.0
        self._t_min = -2 * math.pi
        self._t_max = 2 * math.pi
        self._speed = _DEFAULT_SPEED
        self._playing = False
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._build_ui()

    def _build_ui(self):
        vlay = QVBoxLayout(self)
        vlay.setSpacing(4)
        vlay.setContentsMargins(6, 6, 6, 6)

        row1 = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._play_btn.setCheckable(True)
        self._play_btn.toggled.connect(self._on_play_toggled)

        self._t_label = QLabel("t = 0.000")

        speed_lbl = QLabel("Speed:")
        self._speed_combo = QComboBox()
        for s in _SPEEDS:
            self._speed_combo.addItem(f"x{s}")
        self._speed_combo.setCurrentIndex(_SPEEDS.index(_DEFAULT_SPEED))
        self._speed_combo.currentIndexChanged.connect(self._on_speed_change)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(50)
        reset_btn.clicked.connect(self._reset)

        row1.addWidget(self._play_btn)
        row1.addWidget(self._t_label)
        row1.addWidget(speed_lbl)
        row1.addWidget(self._speed_combo)
        row1.addWidget(reset_btn)
        row1.addStretch()

        row2 = QHBoxLayout()
        self._t_min_spin = self._mk_spin(-1e3, 0, self._t_min, 3)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, _SLIDER_STEPS)
        self._slider.setValue(self._val_to_slider(self._t))
        self._slider.valueChanged.connect(self._on_slider)
        self._t_max_spin = self._mk_spin(0, 1e3, self._t_max, 3)
        row2.addWidget(self._t_min_spin)
        row2.addWidget(self._slider, 1)
        row2.addWidget(self._t_max_spin)

        vlay.addLayout(row1)
        vlay.addLayout(row2)

    def _mk_spin(self, lo, hi, val, dec):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setDecimals(dec)
        s.setFixedWidth(64)
        s.valueChanged.connect(self._on_range_change)
        return s

    def _val_to_slider(self, v: float) -> int:
        if self._t_max == self._t_min:
            return 0
        frac = (v - self._t_min) / (self._t_max - self._t_min)
        return int(max(0, min(_SLIDER_STEPS, frac * _SLIDER_STEPS)))

    def _slider_to_val(self, s: int) -> float:
        return self._t_min + s / _SLIDER_STEPS * (self._t_max - self._t_min)

    def _on_play_toggled(self, playing: bool):
        self._playing = playing
        self._play_btn.setText("Pause" if playing else "Play")
        if playing:
            self._timer.start()
        else:
            self._timer.stop()

    def _on_speed_change(self, idx: int):
        self._speed = _SPEEDS[idx]

    def _on_slider(self, val: int):
        self._t = self._slider_to_val(val)
        self._t_label.setText(f"t = {self._t:.3f}")
        self.t_changed.emit(self._t)

    def _on_range_change(self):
        lo = self._t_min_spin.value()
        hi = self._t_max_spin.value()
        if lo >= hi:
            return
        self._t_min = lo
        self._t_max = hi
        self._slider.blockSignals(True)
        self._slider.setValue(self._val_to_slider(self._t))
        self._slider.blockSignals(False)

    def _tick(self):
        span = self._t_max - self._t_min
        if span <= 0:
            return
        step = self._speed * (_TICK_MS / 1000.0) * span / 6.0
        self._t += step
        if self._t > self._t_max:
            self._t = self._t_min
        self._slider.blockSignals(True)
        self._slider.setValue(self._val_to_slider(self._t))
        self._slider.blockSignals(False)
        self._t_label.setText(f"t = {self._t:.3f}")
        self.t_changed.emit(self._t)

    def _reset(self):
        self._on_play_toggled(False)
        self._play_btn.setChecked(False)
        self._t = self._t_min
        self._slider.blockSignals(True)
        self._slider.setValue(0)
        self._slider.blockSignals(False)
        self._t_label.setText(f"t = {self._t:.3f}")
        self.t_changed.emit(self._t)

    def get_t(self) -> float:
        return self._t

    def to_state(self) -> dict:
        return {
            "t":     self._t,
            "t_min": self._t_min,
            "t_max": self._t_max,
            "speed": self._speed,
        }

    def apply_state(self, state: dict):
        self._t_min_spin.setValue(state.get("t_min", self._t_min))
        self._t_max_spin.setValue(state.get("t_max", self._t_max))
        speed = state.get("speed", _DEFAULT_SPEED)
        idx = _SPEEDS.index(speed) if speed in _SPEEDS else _SPEEDS.index(_DEFAULT_SPEED)
        self._speed_combo.setCurrentIndex(idx)
        self._speed = speed
        t = state.get("t", self._t_min)
        self._t = t
        self._slider.blockSignals(True)
        self._slider.setValue(self._val_to_slider(t))
        self._slider.blockSignals(False)
        self._t_label.setText(f"t = {t:.3f}")
