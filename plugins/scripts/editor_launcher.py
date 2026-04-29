from __future__ import annotations
import os
import subprocess
import sys
from shutil import which
from typing import Dict

EDITOR_PRESETS: Dict[str, str] = {
    "System Default": "",
    "Notepad":        "notepad.exe",
    "Notepad++":      "notepad++",
    "Sublime Text":   "subl",
    "VS Code":        "code",
    "PyCharm":        "pycharm",
    "IDLE":           "idle",
    "gedit":          "gedit",
    "kate":           "kate",
    "nano":           "nano",
    "vim":            "vim",
}


def get_editor_presets() -> Dict[str, str]:
    return dict(EDITOR_PRESETS)


def open_in_editor(path: str, editor_cmd: str) -> bool:
    """Open path in editor_cmd. Falls back to OS default when cmd is empty."""
    if not editor_cmd:
        return _open_default(path)
    resolved = which(editor_cmd) or editor_cmd
    try:
        subprocess.Popen([resolved, path])
        return True
    except Exception:
        return False


def _open_default(path: str) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False
