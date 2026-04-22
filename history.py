from typing import Any, List, Optional
import copy


class Command:
    def redo(self): ...
    def undo(self): ...


class AddFunctionCmd(Command):
    def __init__(self, panel, state: dict):
        self._panel = panel
        self._state = state
        self._row = None
    def redo(self):
        self._row = self._panel.add_function_from_state(self._state)
    def undo(self):
        if self._row and self._row in self._panel.func_rows:
            self._panel.remove_function(self._row, record=False)


class RemoveFunctionCmd(Command):
    def __init__(self, panel, row):
        self._panel = panel
        self._state = row.to_state()
        self._row = row
    def redo(self):
        if self._row in self._panel.func_rows:
            self._panel.remove_function(self._row, record=False)
    def undo(self):
        self._row = self._panel.add_function_from_state(self._state)


class EditFunctionCmd(Command):
    def __init__(self, row, old_state: dict, new_state: dict):
        self._row = row
        self._old = old_state
        self._new = new_state
    def redo(self):
        self._row.apply_state(self._new)
    def undo(self):
        self._row.apply_state(self._old)


class AddParamCmd(Command):
    def __init__(self, panel, name: str):
        self._panel = panel
        self._name = name
    def redo(self):
        self._panel.add_param(self._name, record=False)
    def undo(self):
        self._panel.remove_param(self._name, record=False)


class RemoveParamCmd(Command):
    def __init__(self, panel, name: str, state: dict):
        self._panel = panel
        self._name = name
        self._state = state
    def redo(self):
        self._panel.remove_param(self._name, record=False)
    def undo(self):
        self._panel.add_param(self._name, record=False, state=self._state)


class History:
    MAX = 100

    def __init__(self):
        self._stack: List[Command] = []
        self._pos: int = -1

    def push(self, cmd: Command):
        self._stack = self._stack[:self._pos + 1]
        self._stack.append(cmd)
        if len(self._stack) > self.MAX:
            self._stack.pop(0)
        self._pos = len(self._stack) - 1
        cmd.redo()

    def undo(self):
        if self._pos < 0:
            return
        self._stack[self._pos].undo()
        self._pos -= 1

    def redo(self):
        if self._pos >= len(self._stack) - 1:
            return
        self._pos += 1
        self._stack[self._pos].redo()

    def can_undo(self) -> bool:
        return self._pos >= 0

    def can_redo(self) -> bool:
        return self._pos < len(self._stack) - 1