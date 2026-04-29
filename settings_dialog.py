from __future__ import annotations
from typing import List, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QComboBox, QGroupBox, QSlider, QFrame, QLineEdit,
    QTabWidget, QWidget, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal
from config import Config
from core.plugins.settings_page import SettingsPage
if TYPE_CHECKING:
    from core import AppContext


class _BuiltinPage(SettingsPage):
    """Built-in Performance/Rendering/Interface/Scripts settings tab."""
    tab_label = "General"
    def __init__(self) -> None:
        self._cfg = Config()
        self._widget: QWidget = None
    def create_widget(self, context: "AppContext") -> QWidget:
        self._widget = QWidget()
        root = QVBoxLayout(self._widget)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(10)
        perf_grp = QGroupBox("Performance")
        pg = QGridLayout(perf_grp)
        pg.setSpacing(8)
        pg.setColumnMinimumWidth(0, 170)
        pg.addWidget(QLabel("Target FPS:"), 0, 0)
        fps_wrap = QHBoxLayout()
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(10, 240)
        self._fps_spin.setSuffix(" fps")
        self._fps_spin.setFixedWidth(90)
        self._fps_slider = QSlider(Qt.Horizontal)
        self._fps_slider.setRange(10, 240)
        self._fps_slider.setTickInterval(30)
        self._fps_slider.setTickPosition(QSlider.TicksBelow)
        self._fps_spin.valueChanged.connect(self._on_fps_spin_changed)
        self._fps_slider.valueChanged.connect(self._on_fps_slider_changed)
        fps_wrap.addWidget(self._fps_spin)
        fps_wrap.addWidget(self._fps_slider, 1)
        pg.addLayout(fps_wrap, 0, 1)
        pg.addWidget(QLabel("Samples (animation):"), 1, 0)
        self._anim_samp = QSpinBox()
        self._anim_samp.setRange(50, 4000)
        self._anim_samp.setSingleStep(50)
        self._anim_samp.setFixedWidth(90)
        pg.addWidget(self._anim_samp, 1, 1, Qt.AlignLeft)
        pg.addWidget(QLabel("Samples (static):"), 2, 0)
        self._static_samp = QSpinBox()
        self._static_samp.setRange(100, 8000)
        self._static_samp.setSingleStep(100)
        self._static_samp.setFixedWidth(90)
        pg.addWidget(self._static_samp, 2, 1, Qt.AlignLeft)
        pg.addWidget(QLabel("Use NumPy acceleration:"), 3, 0)
        self._use_numpy = QCheckBox()
        pg.addWidget(self._use_numpy, 3, 1)
        root.addWidget(perf_grp)
        render_grp = QGroupBox("Rendering")
        rg = QGridLayout(render_grp)
        rg.setSpacing(8)
        rg.setColumnMinimumWidth(0, 170)
        rg.addWidget(QLabel("Antialiasing:"), 0, 0)
        self._aa = QCheckBox()
        rg.addWidget(self._aa, 0, 1)
        rg.addWidget(QLabel("Line antialiasing:"), 1, 0)
        self._line_aa = QCheckBox()
        rg.addWidget(self._line_aa, 1, 1)
        root.addWidget(render_grp)
        ui_grp = QGroupBox("Interface")
        ug = QGridLayout(ui_grp)
        ug.setSpacing(8)
        ug.setColumnMinimumWidth(0, 170)
        ug.addWidget(QLabel("Show FPS counter:"), 0, 0)
        self._show_fps = QCheckBox()
        ug.addWidget(self._show_fps, 0, 1)
        ug.addWidget(QLabel("Panel width:"), 1, 0)
        self._panel_width = QSpinBox()
        self._panel_width.setRange(300, 700)
        self._panel_width.setSingleStep(10)
        self._panel_width.setSuffix(" px")
        self._panel_width.setFixedWidth(90)
        ug.addWidget(self._panel_width, 1, 1, Qt.AlignLeft)
        root.addWidget(ui_grp)
        script_grp = QGroupBox("Scripts")
        sg = QGridLayout(script_grp)
        sg.setSpacing(8)
        sg.setColumnMinimumWidth(0, 170)
        sg.addWidget(QLabel("External editor preset:"), 0, 0)
        self._editor_preset = QComboBox()
        try:
            from plugins.script_plugin.editor_launcher import get_editor_presets
            self._presets = get_editor_presets()
        except ImportError:
            self._presets = {"System Default": ""}
        for name in self._presets:
            self._editor_preset.addItem(name)
        self._editor_preset.currentTextChanged.connect(self._on_preset_changed)
        sg.addWidget(self._editor_preset, 0, 1)
        sg.addWidget(QLabel("Editor command:"), 1, 0)
        self._editor_cmd = QLineEdit()
        self._editor_cmd.setPlaceholderText(
            "e.g.  code  |  notepad++  |  subl  (empty = system default)"
        )
        sg.addWidget(self._editor_cmd, 1, 1)
        sg.addWidget(QLabel("Script timeout (seconds):"), 2, 0)
        timeout_row = QHBoxLayout()
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 300)
        self._timeout_spin.setSuffix(" s")
        self._timeout_spin.setFixedWidth(80)
        timeout_hint = QLabel("Kills infinite loops. Use api.animate() for continuous updates.")
        timeout_hint.setStyleSheet("QLabel{font-size:10px;color:#888;}")
        timeout_hint.setWordWrap(True)
        timeout_row.addWidget(self._timeout_spin)
        timeout_row.addWidget(timeout_hint, 1)
        sg.addLayout(timeout_row, 2, 1)
        root.addWidget(script_grp)
        root.addStretch()
        return self._widget
    def _on_fps_spin_changed(self, val: int) -> None:
        self._fps_slider.blockSignals(True)
        self._fps_slider.setValue(val)
        self._fps_slider.blockSignals(False)
    def _on_fps_slider_changed(self, val: int) -> None:
        self._fps_spin.blockSignals(True)
        self._fps_spin.setValue(val)
        self._fps_spin.blockSignals(False)
    def load(self) -> None:
        self._fps_spin.setValue(self._cfg.target_fps)
        self._anim_samp.setValue(self._cfg.anim_samples)
        self._static_samp.setValue(self._cfg.static_samples)
        self._use_numpy.setChecked(self._cfg.use_numpy)
        self._aa.setChecked(self._cfg.antialiasing)
        self._line_aa.setChecked(self._cfg.line_aa)
        self._show_fps.setChecked(self._cfg.show_fps)
        self._panel_width.setValue(self._cfg.panel_width)
        saved_cmd = self._cfg.get("script_editor") or ""
        self._editor_cmd.setText(saved_cmd)
        for name, cmd in self._presets.items():
            if cmd == saved_cmd:
                self._editor_preset.blockSignals(True)
                self._editor_preset.setCurrentText(name)
                self._editor_preset.blockSignals(False)
                break
        self._timeout_spin.setValue(int(self._cfg.get("script_timeout_s") or 5))
    def apply(self) -> None:
        self._cfg.set("target_fps",       self._fps_spin.value())
        self._cfg.set("anim_samples",     self._anim_samp.value())
        self._cfg.set("static_samples",   self._static_samp.value())
        self._cfg.set("use_numpy",        self._use_numpy.isChecked())
        self._cfg.set("antialiasing",     self._aa.isChecked())
        self._cfg.set("line_aa",          self._line_aa.isChecked())
        self._cfg.set("show_fps",         self._show_fps.isChecked())
        self._cfg.set("panel_width",      self._panel_width.value())
        self._cfg.set("script_editor",    self._editor_cmd.text().strip())
        self._cfg.set("script_timeout_s", self._timeout_spin.value())
        self._cfg.save()
    def reset(self) -> None:
        self._cfg.reset_defaults()
        self.load()
    def _on_preset_changed(self, name: str) -> None:
        cmd = self._presets.get(name, "")
        self._editor_cmd.blockSignals(True)
        self._editor_cmd.setText(cmd)
        self._editor_cmd.blockSignals(False)


class SettingsDialog(QDialog):
    """
    Application settings dialog.

    Built-in settings occupy the first tab.  Plugins contribute additional tabs
    by registering SettingsPage instances in the SettingsRegistry service before
    this dialog is opened.
    """
    settings_applied = pyqtSignal()
    def __init__(self, context: "AppContext", parent: QWidget = None) -> None:
        super().__init__(parent)
        self._ctx = context
        self._pages: List[SettingsPage] = []
        self.setWindowTitle("Settings")
        self.setMinimumWidth(540)
        self.setMinimumHeight(480)
        self.setModal(True)

        self._build_ui()
    def _collect_pages(self) -> List[SettingsPage]:
        pages: List[SettingsPage] = [_BuiltinPage()]
        registry = self._ctx.get_service("settings_registry")
        if registry is not None:
            pages.extend(registry.pages)
        return pages
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)
        title = QLabel("ZCalc Settings")
        root.addWidget(title)
        root.addWidget(self._sep())
        self._tabs = QTabWidget()
        self._pages = self._collect_pages()
        for page in self._pages:
            w = page.create_widget(self._ctx)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(w)
            self._tabs.addTab(scroll, page.tab_label)
            page.load()
        root.addWidget(self._tabs, 1)
        root.addWidget(self._sep())
        btn_row = QHBoxLayout()
        self._reset_btn = QPushButton("Reset Defaults")
        self._reset_btn.clicked.connect(self._reset_current)
        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._apply_btn)
        root.addLayout(btn_row)
    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFrameShape(QFrame.HLine)
        s.setStyleSheet("color:#e0e0e0;")
        return s
    def _apply(self) -> None:
        for page in self._pages:
            page.apply()
        self.settings_applied.emit()
        self.accept()
    def _reset_current(self) -> None:
        idx = self._tabs.currentIndex()
        if 0 <= idx < len(self._pages):
            self._pages[idx].reset()