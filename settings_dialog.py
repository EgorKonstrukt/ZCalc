from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QComboBox, QGroupBox, QSlider, QFrame, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from config import Config

_TITLE_STYLE = "QLabel{font-weight:bold;font-size:13px;color:#1a1a2e;padding:4px 0;}"
_GROUP_STYLE = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#555;"
    "border:1px solid #ddd;border-radius:6px;margin-top:8px;"
    "padding:8px 6px 6px 6px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}"
)
_BTN_PRIMARY = (
    "QPushButton{background:#3498db;color:white;border:none;border-radius:5px;"
    "font-size:12px;padding:6px 18px;}"
    "QPushButton:hover{background:#2980b9;}"
    "QPushButton:pressed{background:#2471a3;}"
)
_BTN_SECONDARY = (
    "QPushButton{background:#f0f0f0;color:#333;border:1px solid #ddd;"
    "border-radius:5px;font-size:12px;padding:6px 18px;}"
    "QPushButton:hover{background:#e0e0e0;}"
)
_BTN_DANGER = (
    "QPushButton{background:#e74c3c;color:white;border:none;border-radius:5px;"
    "font-size:12px;padding:6px 18px;}"
    "QPushButton:hover{background:#c0392b;}"
)


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = Config()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self.setModal(True)
        self.setStyleSheet(
            "QDialog{background:#fafafa;}"
            "QLabel{font-size:12px;color:#333;}"
            "QSpinBox,QComboBox,QLineEdit{"
            "border:1px solid #ccc;border-radius:4px;"
            "padding:3px 6px;font-size:12px;background:white;}"
            "QCheckBox{font-size:12px;color:#333;spacing:6px;}"
            "QCheckBox::indicator{width:16px;height:16px;border-radius:3px;"
            "border:1px solid #ccc;background:white;}"
            "QCheckBox::indicator:checked{"
            "background:#3498db;border-color:#3498db;}"
        )
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        title = QLabel("ZCalc Settings")
        title.setStyleSheet(_TITLE_STYLE)
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#e0e0e0;")
        root.addWidget(sep)

        perf_grp = QGroupBox("Performance")
        perf_grp.setStyleSheet(_GROUP_STYLE)
        pg = QGridLayout(perf_grp)
        pg.setSpacing(8)
        pg.setColumnMinimumWidth(0, 160)

        pg.addWidget(QLabel("Target FPS:"), 0, 0)
        fps_wrap = QHBoxLayout()
        fps_wrap.setSpacing(8)
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(10, 240)
        self._fps_spin.setSuffix(" fps")
        self._fps_spin.setFixedWidth(90)
        self._fps_slider = QSlider(Qt.Horizontal)
        self._fps_slider.setRange(10, 240)
        self._fps_slider.setTickInterval(30)
        self._fps_slider.setTickPosition(QSlider.TicksBelow)
        self._fps_spin.valueChanged.connect(self._fps_slider.setValue)
        self._fps_slider.valueChanged.connect(self._fps_spin.setValue)
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
        render_grp.setStyleSheet(_GROUP_STYLE)
        rg = QGridLayout(render_grp)
        rg.setSpacing(8)
        rg.setColumnMinimumWidth(0, 160)
        rg.addWidget(QLabel("Antialiasing:"), 0, 0)
        self._aa = QCheckBox()
        rg.addWidget(self._aa, 0, 1)
        rg.addWidget(QLabel("Line antialiasing:"), 1, 0)
        self._line_aa = QCheckBox()
        rg.addWidget(self._line_aa, 1, 1)
        root.addWidget(render_grp)

        ui_grp = QGroupBox("Interface")
        ui_grp.setStyleSheet(_GROUP_STYLE)
        ug = QGridLayout(ui_grp)
        ug.setSpacing(8)
        ug.setColumnMinimumWidth(0, 160)
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

        script_grp = QGroupBox("Script Editor")
        script_grp.setStyleSheet(_GROUP_STYLE)
        sg = QGridLayout(script_grp)
        sg.setSpacing(8)
        sg.setColumnMinimumWidth(0, 160)

        sg.addWidget(QLabel("Preset:"), 0, 0)
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

        sg.addWidget(QLabel("Command:"), 1, 0)
        self._editor_cmd = QLineEdit()
        self._editor_cmd.setPlaceholderText(
            "e.g.  code  |  notepad++  |  subl  (empty = system default)"
        )
        sg.addWidget(self._editor_cmd, 1, 1)

        hint = QLabel(
            "The editor opens the .py file directly.  "
            "Save the file and ZCalc auto-reloads the running script."
        )
        hint.setStyleSheet("QLabel{font-size:10px;color:#999;}")
        hint.setWordWrap(True)
        sg.addWidget(hint, 2, 0, 1, 2)
        root.addWidget(script_grp)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color:#e0e0e0;")
        root.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._reset_btn = QPushButton("Reset Defaults")
        self._reset_btn.setStyleSheet(_BTN_DANGER)
        self._reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setStyleSheet(_BTN_SECONDARY)
        self._cancel_btn.clicked.connect(self.reject)
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setStyleSheet(_BTN_PRIMARY)
        self._apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._apply_btn)
        root.addLayout(btn_row)

    def _on_preset_changed(self, name: str):
        cmd = self._presets.get(name, "")
        self._editor_cmd.blockSignals(True)
        self._editor_cmd.setText(cmd)
        self._editor_cmd.blockSignals(False)

    def _load_values(self):
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

    def _apply(self):
        self._cfg.set("target_fps",     self._fps_spin.value())
        self._cfg.set("anim_samples",   self._anim_samp.value())
        self._cfg.set("static_samples", self._static_samp.value())
        self._cfg.set("use_numpy",      self._use_numpy.isChecked())
        self._cfg.set("antialiasing",   self._aa.isChecked())
        self._cfg.set("line_aa",        self._line_aa.isChecked())
        self._cfg.set("show_fps",       self._show_fps.isChecked())
        self._cfg.set("panel_width",    self._panel_width.value())
        self._cfg.set("script_editor",  self._editor_cmd.text().strip())
        self._cfg.save()
        self.settings_applied.emit()
        self.accept()

    def _reset_defaults(self):
        self._cfg.reset_defaults()
        self._load_values()
