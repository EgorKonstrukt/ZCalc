from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, QTimer, QFileSystemWatcher

if TYPE_CHECKING:
    from core.app_context import AppContext

from .script_api import ScriptAPI
from .script_runner import build_namespace, run_script
from .editor_launcher import open_in_editor

_FRAME_STYLE = (
    "QFrame#script_frame{background:#f6fff6;border:1px solid #88cc88;"
    "border-radius:4px;margin:2px;}"
)
_BTN_RUN  = ("QPushButton{background:#27ae60;color:white;border:none;border-radius:3px;"
             "font-size:10px;padding:3px 8px;}"
             "QPushButton:hover{background:#219a52;}")
_BTN_STOP = ("QPushButton{background:#e74c3c;color:white;border:none;border-radius:3px;"
             "font-size:10px;padding:3px 8px;}"
             "QPushButton:hover{background:#c0392b;}")
_BTN_EDIT = ("QPushButton{background:#3498db;color:white;border:none;border-radius:3px;"
             "font-size:10px;padding:3px 8px;}"
             "QPushButton:hover{background:#2980b9;}")
_BTN_LOAD = ("QPushButton{background:#7f8c8d;color:white;border:none;border-radius:3px;"
             "font-size:10px;padding:3px 8px;}"
             "QPushButton:hover{background:#636e72;}")
_BTN_RM   = ("QPushButton{background:#bdc3c7;color:#444;border:none;border-radius:3px;"
             "font-size:11px;font-weight:bold;padding:2px 6px;}"
             "QPushButton:hover{background:#e74c3c;color:white;}")
_ST_OK    = "QLabel{font-size:9px;color:#27ae60;}"
_ST_ERR   = "QLabel{font-size:9px;color:#e74c3c;}"
_ST_IDLE  = "QLabel{font-size:9px;color:#95a5a6;}"
_WATCH_DEBOUNCE_MS = 600


class ScriptRow(QFrame):
    """
    Panel item that manages one Python script file.

    Handles run/stop lifecycle, file-system watching for auto-reload,
    and serialisation for session save/restore.
    """
    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, context: "AppContext", script_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("script_frame")
        self.setStyleSheet(_FRAME_STYLE)
        self._ctx = context
        self._script_path: Optional[str] = script_path
        self._running = False
        self._api: Optional[ScriptAPI] = None
        self._script_lines: Dict[str, Any] = {}
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_WATCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._auto_reload)
        self._build_ui()
        if script_path and os.path.isfile(script_path):
            self._watcher.addPath(script_path)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(2)
        header = QHBoxLayout()
        self._name_lbl = QLabel(self._display_name())
        self._name_lbl.setStyleSheet(
            "QLabel{font-size:11px;font-weight:bold;color:#1a6b1a;}"
        )
        self._name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._status_lbl = QLabel("idle")
        self._status_lbl.setStyleSheet(_ST_IDLE)
        self._run_btn  = self._mk_btn("Run",  _BTN_RUN,  self._on_run)
        self._stop_btn = self._mk_btn("Stop", _BTN_STOP, self._on_stop)
        self._stop_btn.setEnabled(False)
        self._edit_btn = self._mk_btn("Edit", _BTN_EDIT, self._on_edit)
        self._load_btn = self._mk_btn("Load", _BTN_LOAD, self._on_load)
        rm_btn = QPushButton("x")
        rm_btn.setStyleSheet(_BTN_RM)
        rm_btn.setFixedSize(22, 22)
        rm_btn.clicked.connect(lambda: self.removed.emit(self))
        for w in (self._name_lbl, self._status_lbl, self._run_btn,
                  self._stop_btn, self._edit_btn, self._load_btn, rm_btn):
            header.addWidget(w)
        outer.addLayout(header)
        self._path_lbl = QLabel("No file loaded")
        self._path_lbl.setStyleSheet("QLabel{font-size:9px;color:#b0b0b0;}")
        self._path_lbl.setWordWrap(True)
        outer.addWidget(self._path_lbl)

    def _mk_btn(self, text: str, style: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(style)
        btn.setFixedHeight(22)
        btn.clicked.connect(slot)
        return btn

    def _display_name(self) -> str:
        return Path(self._script_path).stem if self._script_path else "Script"

    def _on_file_changed(self, _path: str):
        if self._running:
            self._debounce.start()

    def _auto_reload(self):
        if self._running and self._script_path and os.path.isfile(self._script_path):
            self._on_stop()
            self._on_run()

    def _on_run(self):
        if not self._script_path or not os.path.isfile(self._script_path):
            self._set_status("No script file loaded", error=True)
            return
        try:
            code = Path(self._script_path).read_text(encoding="utf-8")
        except Exception as exc:
            self._set_status(f"Read error: {exc}", error=True)
            return
        if self._api:
            self._api.cleanup()
        self._api = ScriptAPI(self._ctx, self)
        ns = build_namespace(self._api)
        ok, err = run_script(code, ns)
        if ok:
            self._running = True
            self._run_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._set_status("running", ok=True)
        else:
            first_err = err.strip().splitlines()[-1] if err.strip() else "Error"
            self._set_status(first_err, error=True)
            self._ctx.show_status(f"Script error: {first_err}", 6000)
        self.changed.emit()

    def _on_stop(self):
        if self._api:
            self._api.cleanup()
            self._api = None
        self._running = False
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._set_status("stopped")
        self.changed.emit()

    def _on_edit(self):
        from config import Config
        editor_cmd = Config().get("script_editor") or ""
        if not self._script_path:
            self._create_new_and_edit(editor_cmd)
            return
        if not os.path.isfile(self._script_path):
            try:
                Path(self._script_path).parent.mkdir(parents=True, exist_ok=True)
                Path(self._script_path).write_text("", encoding="utf-8")
            except Exception as exc:
                self._set_status(f"Cannot create: {exc}", error=True)
                return
        if not open_in_editor(self._script_path, editor_cmd):
            QMessageBox.warning(
                self, "Editor Not Found",
                f"Cannot launch '{editor_cmd}'.\n"
                "Change the editor in Settings > Script Editor.",
            )

    def _create_new_and_edit(self, editor_cmd: str):
        scripts_dir = self._default_scripts_dir()
        scripts_dir.mkdir(parents=True, exist_ok=True)
        base = scripts_dir / "new_script.py"
        n = 1
        while base.exists():
            base = scripts_dir / f"new_script_{n}.py"
            n += 1
        base.write_text(
            '"""\nZCalc Script\nUse `api` to interact with the application.\n"""\n\n',
            encoding="utf-8",
        )
        self._set_path(str(base))
        if not open_in_editor(str(base), editor_cmd):
            QMessageBox.warning(
                self, "Editor Not Found",
                f"Cannot launch '{editor_cmd}'.\n"
                "Change the editor in Settings > Script Editor.",
            )

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Script", str(self._default_scripts_dir()),
            "Python (*.py);;All Files (*)",
        )
        if path:
            self._set_path(path)
            self.changed.emit()

    def _set_path(self, path: str):
        for f in self._watcher.files():
            self._watcher.removePath(f)
        self._script_path = path
        self._name_lbl.setText(self._display_name())
        self._path_lbl.setText(path)
        if os.path.isfile(path):
            self._watcher.addPath(path)

    def _default_scripts_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "scripts"

    def _set_status(self, msg: str, error: bool = False, ok: bool = False):
        self._status_lbl.setText(msg)
        if error:
            self._status_lbl.setStyleSheet(_ST_ERR)
        elif ok:
            self._status_lbl.setStyleSheet(_ST_OK)
        else:
            self._status_lbl.setStyleSheet(_ST_IDLE)

    def to_state(self) -> dict:
        return {
            "type": "script",
            "plugin_id": "zcalc.script",
            "script_path": self._script_path or "",
            "running": self._running,
        }

    def apply_state(self, state: dict):
        path = state.get("script_path", "")
        if path and os.path.isfile(path):
            self._set_path(path)
        if state.get("running", False) and path and os.path.isfile(path):
            self._on_run()

    def deleteLater(self):
        if self._api:
            self._api.cleanup()
        super().deleteLater()
