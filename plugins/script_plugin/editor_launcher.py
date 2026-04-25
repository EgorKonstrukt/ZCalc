from __future__ import annotations
import os
import subprocess
import sys
from shutil import which
from typing import Dict, Optional

EDITOR_PRESETS: Dict[str, str] = {
    "System Default":  "",
    "Notepad":         "notepad.exe",
    "Notepad++":       "notepad++",
    "Sublime Text":    "subl",
    "VS Code":         "code",
    "PyCharm":         "pycharm",
    "IDLE":            "idle",
    "gedit":           "gedit",
    "kate":            "kate",
    "nano":            "nano",
    "vim":             "vim",
}


def get_editor_presets() -> Dict[str, str]:
    """Return the built-in preset name -> command mapping."""
    return dict(EDITOR_PRESETS)


def resolve_editor(cmd: str) -> Optional[str]:
    """
    Resolve cmd to an absolute executable path.
    Returns None if cmd is empty or not found on PATH.
    """
    if not cmd:
        return None
    if os.path.isabs(cmd) and os.path.isfile(cmd):
        return cmd
    return which(cmd)


def open_in_editor(path: str, editor_cmd: str) -> bool:
    """
    Open path in editor_cmd.  Falls back to OS default when cmd is empty.
    Returns True if the subprocess launched without an error.
    """
    if not editor_cmd:
        return _open_default(path)
    resolved = resolve_editor(editor_cmd) or editor_cmd
    try:
        subprocess.Popen([resolved, path])
        return True
    except FileNotFoundError:
        return False
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
