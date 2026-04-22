import json
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from constants import APP_NAME, APP_VERSION

if TYPE_CHECKING:
    from panels import FunctionPanel


class IoManager:
    FILE_FILTER = "ZCalc Session (*.zcalc);;JSON (*.json);;All Files (*)"

    def __init__(self, panel: "FunctionPanel", parent=None):
        self._panel  = panel
        self._parent = parent
        self._current_path: str = ""

    def save(self):
        if self._current_path:
            self._write(self._current_path)
        else:
            self.save_as()

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Save Session", "", self.FILE_FILTER)
        if path:
            if not (path.endswith(".zcalc") or path.endswith(".json")):
                path += ".zcalc"
            self._current_path = path
            self._write(path)

    def load(self):
        path, _ = QFileDialog.getOpenFileName(
            self._parent, "Open Session", "", self.FILE_FILTER)
        if path:
            self._read(path)

    def _write(self, path: str):
        doc = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "state": self._panel.to_state(),
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self._parent, "Save Error", str(e))

    def _read(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            state = doc.get("state", doc)
            self._panel.apply_state(state)
            self._current_path = path
        except Exception as e:
            QMessageBox.critical(self._parent, "Load Error", str(e))