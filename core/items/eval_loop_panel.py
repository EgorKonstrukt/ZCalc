from __future__ import annotations

from typing import List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QDoubleSpinBox, QSpinBox, QLineEdit, QPushButton,
    QFrame, QSizePolicy,
)
from PyQt5.QtCore import pyqtSignal, Qt

_VIS_MODES = ["orbit", "cobweb", "bifurcation", "fixed"]
_VIS_TIPS = {
    "orbit":       "Plot x_n vs n (time series of iterated map)",
    "cobweb":      "Staircase diagram over y=f(x) and y=x",
    "bifurcation": "Attractor diagram sweeping a named parameter",
    "fixed":       "Scan and highlight fixed points f(x)=x",
}
_DEFAULT_STEPS = 60
_DEFAULT_BURN_IN = 200
_DEFAULT_SAMPLES = 400
_DEFAULT_X0 = "0.5"
_DEFAULT_P_MIN = 2.5
_DEFAULT_P_MAX = 4.0
_PANEL_STYLE = (
    "QFrame#elp_frame{background:#f0f4ff;border:1px solid #b0c4de;"
    "border-radius:4px;margin:2px;}"
)
_LABEL_STYLE = "QLabel{font-size:10px;color:#555;}"
_PERIOD_STYLE = "QLabel{font-size:10px;color:#2980b9;font-weight:bold;}"
_FIXED_STYLE = "QLabel{font-size:10px;color:#c0392b;}"


def _parse_x0_list(text: str) -> List[float]:
    """
    Parse a comma-separated string of floats into a list.

    Returns a list containing 0.5 as fallback if parsing fails entirely.
    Individual tokens that cannot be converted are silently skipped.
    """
    results = []
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            results.append(float(tok))
        except ValueError:
            pass
    return results or [0.5]


class EvalLoopPanel(QFrame):
    """
    Collapsible per-row control panel for eval-loop visualisation.

    Exposes the interface expected by Plotter._replot_eval_loop:
      is_enabled(), vis_mode(), x0_list(), steps(),
      bifurc_param(), bifurc_range(), burn_in(), attractor_samples(),
      set_detected_period(), set_fixed_points().

    Emits `changed` whenever any control is modified so the parent row
    can trigger a replot.
    """

    changed = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("elp_frame")
        self.setStyleSheet(_PANEL_STYLE)
        self._enabled = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(3)
        header = QHBoxLayout()
        self._enable_chk = QCheckBox("Eval-loop")
        self._enable_chk.setStyleSheet("QCheckBox{font-size:11px;font-weight:bold;color:#2c3e50;}")
        self._enable_chk.toggled.connect(self._on_enabled_toggled)
        self._mode_combo = QComboBox()
        for m in _VIS_MODES:
            self._mode_combo.addItem(m)
        self._mode_combo.setFixedWidth(100)
        self._mode_combo.setStyleSheet("QComboBox{font-size:10px;border:1px solid #ccc;border-radius:3px;}")
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._tip_lbl = QLabel(_VIS_TIPS["orbit"])
        self._tip_lbl.setStyleSheet("QLabel{font-size:9px;color:#aaa;}")
        self._tip_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header.addWidget(self._enable_chk)
        header.addWidget(self._mode_combo)
        header.addWidget(self._tip_lbl, 1)
        root.addLayout(header)
        self._body = QWidget()
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(3)
        seeds_row = QHBoxLayout()
        x0_lbl = QLabel("x0:")
        x0_lbl.setStyleSheet(_LABEL_STYLE)
        x0_lbl.setFixedWidth(18)
        self._x0_edit = QLineEdit(_DEFAULT_X0)
        self._x0_edit.setPlaceholderText("e.g. 0.3, 0.5, 0.7")
        self._x0_edit.setFixedWidth(140)
        self._x0_edit.setStyleSheet("QLineEdit{font-size:10px;border:1px solid #ccc;border-radius:3px;padding:1px 3px;}")
        self._x0_edit.textChanged.connect(self.changed.emit)
        steps_lbl = QLabel("steps:")
        steps_lbl.setStyleSheet(_LABEL_STYLE)
        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 10000)
        self._steps_spin.setValue(_DEFAULT_STEPS)
        self._steps_spin.setFixedWidth(64)
        self._steps_spin.setStyleSheet("QSpinBox{font-size:10px;border:1px solid #ccc;border-radius:3px;}")
        self._steps_spin.valueChanged.connect(self.changed.emit)
        seeds_row.addWidget(x0_lbl)
        seeds_row.addWidget(self._x0_edit)
        seeds_row.addSpacing(8)
        seeds_row.addWidget(steps_lbl)
        seeds_row.addWidget(self._steps_spin)
        seeds_row.addStretch()
        body_lay.addLayout(seeds_row)
        self._bifurc_widget = QWidget()
        b_lay = QHBoxLayout(self._bifurc_widget)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(4)
        p_lbl = QLabel("param:")
        p_lbl.setStyleSheet(_LABEL_STYLE)
        self._param_edit = QLineEdit("r")
        self._param_edit.setFixedWidth(30)
        self._param_edit.setStyleSheet("QLineEdit{font-size:10px;border:1px solid #ccc;border-radius:3px;padding:1px 3px;font-weight:bold;}")
        self._param_edit.textChanged.connect(self.changed.emit)
        range_lbl = QLabel("range:")
        range_lbl.setStyleSheet(_LABEL_STYLE)
        self._p_min_spin = self._mk_dspin(-1e4, 1e4, _DEFAULT_P_MIN)
        to_lbl = QLabel("to")
        to_lbl.setStyleSheet(_LABEL_STYLE)
        self._p_max_spin = self._mk_dspin(-1e4, 1e4, _DEFAULT_P_MAX)
        burn_lbl = QLabel("burn:")
        burn_lbl.setStyleSheet(_LABEL_STYLE)
        self._burn_spin = QSpinBox()
        self._burn_spin.setRange(0, 100000)
        self._burn_spin.setValue(_DEFAULT_BURN_IN)
        self._burn_spin.setFixedWidth(60)
        self._burn_spin.setStyleSheet("QSpinBox{font-size:10px;border:1px solid #ccc;border-radius:3px;}")
        self._burn_spin.valueChanged.connect(self.changed.emit)
        att_lbl = QLabel("samples:")
        att_lbl.setStyleSheet(_LABEL_STYLE)
        self._att_spin = QSpinBox()
        self._att_spin.setRange(1, 10000)
        self._att_spin.setValue(_DEFAULT_SAMPLES)
        self._att_spin.setFixedWidth(60)
        self._att_spin.setStyleSheet("QSpinBox{font-size:10px;border:1px solid #ccc;border-radius:3px;}")
        self._att_spin.valueChanged.connect(self.changed.emit)
        for w in (p_lbl, self._param_edit, range_lbl, self._p_min_spin, to_lbl, self._p_max_spin,
                  burn_lbl, self._burn_spin, att_lbl, self._att_spin):
            b_lay.addWidget(w)
        b_lay.addStretch()
        body_lay.addWidget(self._bifurc_widget)
        info_row = QHBoxLayout()
        self._period_lbl = QLabel("")
        self._period_lbl.setStyleSheet(_PERIOD_STYLE)
        self._fixed_lbl = QLabel("")
        self._fixed_lbl.setStyleSheet(_FIXED_STYLE)
        info_row.addWidget(self._period_lbl)
        info_row.addSpacing(12)
        info_row.addWidget(self._fixed_lbl)
        info_row.addStretch()
        body_lay.addLayout(info_row)
        root.addWidget(self._body)
        self._body.setVisible(False)
        self._bifurc_widget.setVisible(False)

    def _mk_dspin(self, lo: float, hi: float, val: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setDecimals(2)
        s.setFixedWidth(64)
        s.setStyleSheet("QDoubleSpinBox{font-size:10px;border:1px solid #ccc;border-radius:3px;}")
        s.valueChanged.connect(self.changed.emit)
        return s

    def _on_enabled_toggled(self, enabled: bool):
        self._enabled = enabled
        self._body.setVisible(enabled)
        self._period_lbl.setText("")
        self._fixed_lbl.setText("")
        self.changed.emit()

    def _on_mode_changed(self, mode: str):
        self._tip_lbl.setText(_VIS_TIPS.get(mode, ""))
        self._bifurc_widget.setVisible(mode == "bifurcation")
        self._period_lbl.setText("")
        self._fixed_lbl.setText("")
        self.changed.emit()

    def is_enabled(self) -> bool:
        """Return True if the eval-loop overlay is active."""
        return self._enabled

    def vis_mode(self) -> str:
        """Return the currently selected visualisation mode string."""
        return self._mode_combo.currentText()

    def x0_list(self) -> List[float]:
        """Return the parsed list of seed values from the x0 text field."""
        return _parse_x0_list(self._x0_edit.text())

    def steps(self) -> int:
        """Return the number of iteration steps."""
        return self._steps_spin.value()

    def bifurc_param(self) -> str:
        """Return the parameter name used for bifurcation sweep."""
        return self._param_edit.text().strip() or "r"

    def bifurc_range(self):
        """Return (p_min, p_max) for the bifurcation sweep."""
        return self._p_min_spin.value(), self._p_max_spin.value()

    def burn_in(self) -> int:
        """Return the number of burn-in iterations for bifurcation."""
        return self._burn_spin.value()

    def attractor_samples(self) -> int:
        """Return the number of attractor samples per parameter value."""
        return self._att_spin.value()

    def set_detected_period(self, period: Optional[int]):
        """Display the detected orbit period in the info bar."""
        if period is None:
            self._period_lbl.setText("")
        else:
            self._period_lbl.setText(f"period: {period}")

    def set_fixed_points(self, fps: List[float]):
        """Display fixed point candidates in the info bar."""
        if not fps:
            self._fixed_lbl.setText("")
        else:
            pts = ", ".join(f"{x:.4g}" for x in fps[:8])
            suffix = "..." if len(fps) > 8 else ""
            self._fixed_lbl.setText(f"fixed: {pts}{suffix}")

    def to_state(self) -> dict:
        """Serialise panel state to a plain dict for session save/restore."""
        return {
            "enabled":    self._enabled,
            "mode":       self.vis_mode(),
            "x0":         self._x0_edit.text(),
            "steps":      self.steps(),
            "bifurc_param": self.bifurc_param(),
            "p_min":      self._p_min_spin.value(),
            "p_max":      self._p_max_spin.value(),
            "burn_in":    self.burn_in(),
            "att_samples": self.attractor_samples(),
        }

    def apply_state(self, state: dict):
        """Restore panel state from a plain dict."""
        self._mode_combo.blockSignals(True)
        self._enable_chk.blockSignals(True)
        mode = state.get("mode", "orbit")
        if mode in _VIS_MODES:
            self._mode_combo.setCurrentText(mode)
        self._param_edit.setText(state.get("bifurc_param", "r"))
        self._x0_edit.setText(state.get("x0", _DEFAULT_X0))
        self._steps_spin.setValue(state.get("steps", _DEFAULT_STEPS))
        self._p_min_spin.setValue(state.get("p_min", _DEFAULT_P_MIN))
        self._p_max_spin.setValue(state.get("p_max", _DEFAULT_P_MAX))
        self._burn_spin.setValue(state.get("burn_in", _DEFAULT_BURN_IN))
        self._att_spin.setValue(state.get("att_samples", _DEFAULT_SAMPLES))
        enabled = state.get("enabled", False)
        self._enable_chk.setChecked(enabled)
        self._enabled = enabled
        self._body.setVisible(enabled)
        self._bifurc_widget.setVisible(mode == "bifurcation")
        self._tip_lbl.setText(_VIS_TIPS.get(mode, ""))
        self._mode_combo.blockSignals(False)
        self._enable_chk.blockSignals(False)