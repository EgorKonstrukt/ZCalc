from __future__ import annotations
import copy


class AddScriptCmd:
    """Record the addition of a ScriptRow to the ScriptPanel."""
    def __init__(self, panel, state: dict):
        self._panel = panel
        self._state = copy.deepcopy(state)
        self._row = None

    def redo(self):
        self._row = self._panel.add_script_from_state(copy.deepcopy(self._state))

    def undo(self):
        if self._row is not None and self._row in self._panel._script_rows:
            self._panel._remove_script(self._row, record=False)


class RemoveScriptCmd:
    """Record the removal of a ScriptRow from the ScriptPanel."""
    def __init__(self, panel, row):
        self._panel = panel
        self._state = copy.deepcopy(row.to_state())
        self._row = row

    def redo(self):
        if self._row in self._panel._script_rows:
            self._panel._remove_script(self._row, record=False)

    def undo(self):
        self._row = self._panel.add_script_from_state(copy.deepcopy(self._state))
