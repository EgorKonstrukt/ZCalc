import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar,
    QAction, QLabel, QApplication
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QKeySequence
from pyqt5_chart_widget import ChartWidget
from constants import APP_NAME, APP_VERSION
from panels import FunctionPanel
from plotter import Plotter
from history import History
from io_manager import IoManager
from config import Config
from settings_dialog import SettingsDialog
import math_engine
_INITIAL_FUNCTION = {
    "expr": "sin(x)", "mode": "y=f(x)", "expr2": "",
    "color": "#3498db", "width": 2, "enabled": True, "type": "function"
}
_EMPTY_FUNCTION = {
    "expr": "", "mode": "y=f(x)", "expr2": "",
    "color": "#3498db", "width": 2, "enabled": True, "type": "function"
}
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._cfg = Config()
        math_engine.set_use_numpy(self._cfg.use_numpy)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1280, 820)
        self._history = History()
        self._fps_times = []
        self._build_ui()
        self._plotter = Plotter(self._chart, self._panel)
        self._io = IoManager(self._panel, self)
        self._upd_timer = QTimer(self)
        self._upd_timer.setSingleShot(True)
        self._upd_timer.timeout.connect(self._replot)
        self._panel.update_requested.connect(self._schedule)
        self._panel.anim_update_requested.connect(self._replot)
        self._build_menu()
        self._panel.settings.infinite_changed.connect(self._on_infinite_changed)
        self._apply_config()
        self._panel.add_function_from_state(_INITIAL_FUNCTION)
    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self._panel = FunctionPanel(None, self._history)
        self._chart = ChartWidget(
            show_toolbar=True, show_legend=True,
            show_sidebar=False, threaded_fit=False, anim_duration=60
        )
        self._panel.bind_chart(self._chart)
        self._panel.settings.changed.connect(self._schedule)
        self._panel.deriv_panel.changed.connect(self._schedule)
        self._chart.setLabel("left", "y")
        self._chart.setLabel("bottom", "x")
        self._info_bar = QLabel()
        self._info_bar.setAlignment(Qt.AlignCenter)
        self._fps_label = QLabel("-- fps")
        self._fps_label.setAlignment(Qt.AlignRight)
        self._fps_label.setFixedWidth(70)
        self._fps_label.setStyleSheet("QLabel{color:#888;font-size:11px;}")
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self._chart)
        self._left_wrap = QWidget()
        self._left_wrap.setFixedWidth(self._cfg.panel_width)
        ll = QHBoxLayout(self._left_wrap)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self._panel)
        splitter.addWidget(self._left_wrap)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        central = QWidget()
        cl = QHBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(splitter)
        self.setCentralWidget(central)
        sb = QStatusBar()
        sb.addPermanentWidget(self._fps_label)
        sb.addPermanentWidget(self._info_bar)
        sb.showMessage("+ f(x) to add function  |  + param to add slider  |  Ctrl+Z/Y = undo/redo")
        self.setStatusBar(sb)
    def _build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        def act(label, shortcut, fn):
            a = QAction(label, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
                a.setShortcutContext(Qt.ApplicationShortcut)
            a.triggered.connect(fn)
            self.addAction(a)
            return a
        fm.addAction(act("&New",        "Ctrl+N",       self._new_session))
        fm.addAction(act("&Open...",    "Ctrl+O",       self._io.load))
        fm.addAction(act("&Save",       "Ctrl+S",       self._io.save))
        fm.addAction(act("Save &As...", "Ctrl+Shift+S", self._io.save_as))
        fm.addSeparator()
        fm.addAction(act("&Quit",       "Ctrl+Q",       QApplication.quit))
        em = mb.addMenu("&Edit")
        self._undo_act = act("&Undo", "Ctrl+Z", self._undo)
        self._redo_act = act("&Redo", "Ctrl+Y", self._redo)
        em.addAction(self._undo_act)
        em.addAction(self._redo_act)
        vm = mb.addMenu("&View")
        vm.addAction(act("&Autofit",   "Ctrl+F", self._chart.autofit))
        vm.addAction(act("&Clear All", None,      self._panel._clear_all))
        sm = mb.addMenu("&Settings")
        sm.addAction(act("&Preferences...", "Ctrl+,", self._open_settings))
    def _apply_config(self):
        math_engine.set_use_numpy(self._cfg.use_numpy)
        self._panel.set_anim_interval(self._cfg.anim_interval_ms)
        self._left_wrap.setFixedWidth(self._cfg.panel_width)
        self._fps_label.setVisible(self._cfg.show_fps)
        if self._cfg.antialiasing:
            try:
                import pyqtgraph as pg
                pg.setConfigOptions(antialias=True)
            except Exception:
                pass
    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.settings_applied.connect(self._apply_config)
        dlg.exec_()
    def _undo(self):
        self._history.undo()
        self._schedule()
    def _redo(self):
        self._history.redo()
        self._schedule()
    def _on_infinite_changed(self, enabled: bool):
        self._chart.setAutofitEnabled(not enabled)
        if not enabled:
            self._chart.autofit()
        self._schedule()
    def _schedule(self):
        self._upd_timer.start(self._cfg.replot_delay_ms)
    def _replot(self):
        t0 = time.perf_counter()
        result = self._plotter.replot()
        if result:
            total, x_min, x_max, n_fn = result
            self._info_bar.setText(
                f"~{total:,} pts  x in [{x_min:.2f}, {x_max:.2f}]  {n_fn} fn")
        if self._cfg.show_fps:
            now = time.perf_counter()
            self._fps_times.append(now)
            cutoff = now - 1.0
            self._fps_times = [t for t in self._fps_times if t > cutoff]
            self._fps_label.setText(f"{len(self._fps_times)} fps")
    def _new_session(self):
        self._panel._clear_all()
        self._panel.add_function_from_state(_EMPTY_FUNCTION)