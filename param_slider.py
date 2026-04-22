import math
import random
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox,
    QPushButton, QLineEdit, QComboBox, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from expr_item import ExprItem, ITEM_HEIGHT
_SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
_DEFAULT_SPEED = 1.0
_TICK_MS = 16
_SLIDER_STEPS = 1000
_PARAM_ITEM_HEIGHT = 72
_ANIM_MODES = ["loop", "bounce", "sine", "ease-in-out", "ease-in", "ease-out", "pulse", "random"]
_MODE_TIPS = {
    "loop":        "Linear loop: min to max, then jump back",
    "bounce":      "Ping-pong: min to max and back",
    "sine":        "Smooth sinusoidal oscillation",
    "ease-in-out": "Slow start and end, fast middle",
    "ease-in":     "Starts slow, ends fast",
    "ease-out":    "Starts fast, ends slow",
    "pulse":       "Snaps between min and max",
    "random":      "Random walk with smooth drift",
}
def _ease_in_out(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)
def _ease_in(t: float) -> float:
    return t * t * t
def _ease_out(t: float) -> float:
    t = 1.0 - t
    return 1.0 - t * t * t
class ParamSliderWidget(ExprItem):
    param_changed = pyqtSignal(str, float)
    name_changed  = pyqtSignal(str, str)
    removed       = pyqtSignal(object)
    def __init__(self, name: str, lo: float = -5.0, hi: float = 5.0,
                 val: float = 1.0, parent=None):
        super().__init__(parent)
        self.name = name
        self._lo = lo
        self._hi = hi
        self._val = val
        self._animating = False
        self._speed = _DEFAULT_SPEED
        self._anim_mode = "loop"
        self._phase = 0.0
        self._bounce_dir = 1.0
        self._random_target = val
        self._random_vel = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self.setFixedHeight(_PARAM_ITEM_HEIGHT)
        self._build_ui()
    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        bar = QFrame()
        bar.setFixedWidth(6)
        bar.setStyleSheet("background:#95a5a6;border-radius:3px;")
        outer.addWidget(bar)
        inner = QVBoxLayout()
        inner.setContentsMargins(8, 3, 4, 3)
        inner.setSpacing(2)
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        self._play_btn = QPushButton("Play")
        self._play_btn.setCheckable(True)
        self._play_btn.setFixedWidth(44)
        self._play_btn.setFixedHeight(20)
        self._play_btn.setStyleSheet(
            "QPushButton{background:#3498db;color:white;border:none;border-radius:3px;font-size:10px;}"
            "QPushButton:checked{background:#e74c3c;}"
        )
        self._play_btn.toggled.connect(self._on_play_toggled)
        self._name_edit = QLineEdit(self.name)
        self._name_edit.setFixedWidth(32)
        self._name_edit.setFixedHeight(20)
        self._name_edit.setAlignment(Qt.AlignCenter)
        self._name_edit.setStyleSheet(
            "QLineEdit{border:1px solid #ccc;border-radius:3px;font-weight:bold;"
            "font-size:12px;padding:0px;background:#f9f9f9;}"
            "QLineEdit:focus{border:1px solid #3498db;background:white;}"
        )
        self._name_edit.editingFinished.connect(self._on_name_changed)
        eq_lbl = QLabel("=")
        eq_lbl.setFixedWidth(8)
        self._val_spin = QDoubleSpinBox()
        self._val_spin.setRange(self._lo, self._hi)
        self._val_spin.setValue(self._val)
        self._val_spin.setDecimals(3)
        self._val_spin.setFixedWidth(80)
        self._val_spin.setStyleSheet("QDoubleSpinBox{border:none;font-size:12px;}")
        self._val_spin.valueChanged.connect(self._on_spin)
        self._speed_combo = QComboBox()
        for s in _SPEEDS:
            self._speed_combo.addItem(f"x{s}")
        self._speed_combo.setCurrentIndex(_SPEEDS.index(_DEFAULT_SPEED))
        self._speed_combo.setFixedWidth(52)
        self._speed_combo.setFixedHeight(20)
        self._speed_combo.setStyleSheet("QComboBox{font-size:10px;border:none;background:#f0f0f0;}")
        self._speed_combo.currentIndexChanged.connect(lambda i: setattr(self, '_speed', _SPEEDS[i]))
        rm = self._mk_remove_btn()
        for w in (self._play_btn, self._name_edit, eq_lbl, self._val_spin, self._speed_combo, rm):
            row1.addWidget(w)
        row1.addStretch()
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        self._lo_spin = self._mk_range_spin(self._lo)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, _SLIDER_STEPS)
        self._slider.setValue(self._to_slider(self._val))
        self._slider.valueChanged.connect(self._on_slider)
        self._hi_spin = self._mk_range_spin(self._hi)
        row2.addWidget(self._lo_spin)
        row2.addWidget(self._slider, 1)
        row2.addWidget(self._hi_spin)
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet("QLabel{font-size:10px;color:#888;}")
        mode_lbl.setFixedWidth(34)
        self._mode_combo = QComboBox()
        for m in _ANIM_MODES:
            self._mode_combo.addItem(m)
        self._mode_combo.setFixedHeight(18)
        self._mode_combo.setStyleSheet(
            "QComboBox{font-size:10px;border:1px solid #ddd;border-radius:3px;"
            "background:#f8f8f8;padding:0px 3px;}"
            "QComboBox:hover{border-color:#3498db;}"
        )
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._mode_tip = QLabel(_MODE_TIPS["loop"])
        self._mode_tip.setStyleSheet("QLabel{font-size:9px;color:#aaa;}")
        self._mode_tip.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row3.addWidget(mode_lbl)
        row3.addWidget(self._mode_combo)
        row3.addWidget(self._mode_tip, 1)
        inner.addLayout(row1)
        inner.addLayout(row2)
        inner.addLayout(row3)
        outer.addLayout(inner)
    def _on_mode_changed(self, mode: str):
        self._anim_mode = mode
        self._mode_tip.setText(_MODE_TIPS.get(mode, ""))
        self._reset_phase()
    def _reset_phase(self):
        span = self._hi - self._lo
        if span <= 0:
            self._phase = 0.0
            return
        self._phase = (self._val - self._lo) / span
        self._bounce_dir = 1.0
        self._random_target = self._val
        self._random_vel = 0.0
    def _on_name_changed(self):
        new_name = self._name_edit.text().strip()
        if not new_name or new_name == self.name:
            self._name_edit.setText(self.name)
            return
        old_name = self.name
        self.name = new_name
        self.name_changed.emit(old_name, new_name)
    def _mk_range_spin(self, val: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-9999, 9999)
        s.setValue(val)
        s.setDecimals(1)
        s.setFixedWidth(52)
        s.setStyleSheet("QDoubleSpinBox{font-size:10px;border:none;}")
        s.valueChanged.connect(self._on_range)
        return s
    def _to_slider(self, v: float) -> int:
        if self._hi == self._lo:
            return 0
        return int(max(0, min(_SLIDER_STEPS, (v - self._lo) / (self._hi - self._lo) * _SLIDER_STEPS)))
    def _from_slider(self, s: int) -> float:
        return self._lo + s / _SLIDER_STEPS * (self._hi - self._lo)
    def _on_play_toggled(self, playing: bool):
        self._animating = playing
        self._play_btn.setText("Pause" if playing else "Play")
        if playing:
            self._reset_phase()
            self._timer.start()
        else:
            self._timer.stop()
    def _tick(self):
        span = self._hi - self._lo
        if span <= 0:
            return
        dt = _TICK_MS / 1000.0
        phase_step = self._speed * dt / 6.0
        mode = self._anim_mode
        if mode == "loop":
            self._phase += phase_step
            if self._phase >= 1.0:
                self._phase -= 1.0
            new_val = self._lo + self._phase * span
        elif mode == "bounce":
            self._phase += phase_step * self._bounce_dir
            if self._phase >= 1.0:
                self._phase = 1.0
                self._bounce_dir = -1.0
            elif self._phase <= 0.0:
                self._phase = 0.0
                self._bounce_dir = 1.0
            new_val = self._lo + self._phase * span
        elif mode == "sine":
            self._phase += phase_step
            new_val = self._lo + (math.sin(self._phase * 2.0 * math.pi) * 0.5 + 0.5) * span
        elif mode == "ease-in-out":
            self._phase += phase_step
            if self._phase >= 1.0:
                self._phase -= 1.0
            mirror = self._phase if self._phase < 0.5 else 1.0 - self._phase
            t = mirror * 2.0
            eased = _ease_in_out(t) * 0.5
            new_val = self._lo + (eased if self._phase < 0.5 else 1.0 - eased) * span
        elif mode == "ease-in":
            self._phase += phase_step
            if self._phase >= 1.0:
                self._phase -= 1.0
            new_val = self._lo + _ease_in(self._phase) * span
        elif mode == "ease-out":
            self._phase += phase_step
            if self._phase >= 1.0:
                self._phase -= 1.0
            new_val = self._lo + _ease_out(self._phase) * span
        elif mode == "pulse":
            self._phase += phase_step * 2.0
            if self._phase >= 1.0:
                self._phase -= 1.0
            new_val = self._hi if self._phase < 0.5 else self._lo
        elif mode == "random":
            stiffness = 2.5 * self._speed
            damping = 4.0
            noise = (random.random() - 0.5) * span * self._speed * 0.8
            self._random_target += noise * dt
            self._random_target = max(self._lo, min(self._hi, self._random_target))
            force = stiffness * (self._random_target - self._val)
            self._random_vel += force * dt
            self._random_vel *= max(0.0, 1.0 - damping * dt)
            self._val += self._random_vel * dt
            new_val = max(self._lo, min(self._hi, self._val))
        else:
            new_val = self._val
        self._val = new_val
        self._slider.blockSignals(True)
        self._slider.setValue(self._to_slider(self._val))
        self._slider.blockSignals(False)
        self._val_spin.blockSignals(True)
        self._val_spin.setValue(self._val)
        self._val_spin.blockSignals(False)
        self.param_changed.emit(self.name, self._val)
    def _on_slider(self, s: int):
        self._val = self._from_slider(s)
        self._val_spin.blockSignals(True)
        self._val_spin.setValue(self._val)
        self._val_spin.blockSignals(False)
        self.param_changed.emit(self.name, self._val)
    def _on_spin(self, v: float):
        self._val = v
        self._slider.blockSignals(True)
        self._slider.setValue(self._to_slider(v))
        self._slider.blockSignals(False)
        self.param_changed.emit(self.name, v)
    def _on_range(self):
        lo, hi = self._lo_spin.value(), self._hi_spin.value()
        if lo >= hi:
            return
        self._lo, self._hi = lo, hi
        self._val_spin.setRange(lo, hi)
        clamped = max(lo, min(hi, self._val))
        self._slider.blockSignals(True)
        self._slider.setValue(self._to_slider(clamped))
        self._slider.blockSignals(False)
    def get_value(self) -> float:
        return self._val
    def to_state(self) -> dict:
        return {
            "name": self.name, "lo": self._lo, "hi": self._hi,
            "val": self._val, "speed": self._speed,
            "anim_mode": self._anim_mode, "type": "param",
        }
    def apply_state(self, state: dict):
        self._lo_spin.setValue(state.get("lo", self._lo))
        self._hi_spin.setValue(state.get("hi", self._hi))
        v = state.get("val", self._val)
        self._val = v
        self._val_spin.blockSignals(True)
        self._val_spin.setValue(v)
        self._val_spin.blockSignals(False)
        self._slider.blockSignals(True)
        self._slider.setValue(self._to_slider(v))
        self._slider.blockSignals(False)
        spd = state.get("speed", _DEFAULT_SPEED)
        if spd in _SPEEDS:
            self._speed_combo.setCurrentIndex(_SPEEDS.index(spd))
        self._speed = spd
        mode = state.get("anim_mode", "loop")
        if mode in _ANIM_MODES:
            self._mode_combo.setCurrentText(mode)
        self._anim_mode = mode
        self._reset_phase()