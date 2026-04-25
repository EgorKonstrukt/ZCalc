from typing import Any, List, Optional
import copy


class Command:
    def redo(self): ...
    def undo(self): ...


class AddFunctionCmd(Command):
    def __init__(self, panel, state: dict):
        self._panel = panel
        self._state = copy.deepcopy(state)
        self._row = None
    def redo(self):
        self._row = self._panel.add_function_from_state(copy.deepcopy(self._state))
    def undo(self):
        if self._row and self._row in self._panel.func_rows:
            self._panel.remove_function(self._row, record=False)


class RemoveFunctionCmd(Command):
    def __init__(self, panel, row):
        self._panel = panel
        self._state = copy.deepcopy(row.to_state())
        self._row = row
    def redo(self):
        if self._row in self._panel.func_rows:
            self._panel.remove_function(self._row, record=False)
    def undo(self):
        self._row = self._panel.add_function_from_state(copy.deepcopy(self._state))


class EditFunctionCmd(Command):
    """
    Record an atomic edit to a single FunctionRow (expression, mode, color,
    width, or eval-loop configuration).

    Caller is responsible for capturing old_state before the edit and
    new_state after, then pushing this command.
    """
    def __init__(self, row, old_state: dict, new_state: dict):
        self._row = row
        self._old = copy.deepcopy(old_state)
        self._new = copy.deepcopy(new_state)
    def redo(self):
        self._row.apply_state(copy.deepcopy(self._new))
    def undo(self):
        self._row.apply_state(copy.deepcopy(self._old))


class EditEvalLoopCmd(Command):
    """
    Record a change to a row's EvalLoopPanel configuration.

    Separates eval-loop edits from full-row edits so that typing in the
    expression field does not collapse the undo stack with eval-loop changes.
    """
    def __init__(self, row, old_state: dict, new_state: dict):
        self._row = row
        self._old = copy.deepcopy(old_state)
        self._new = copy.deepcopy(new_state)
    def redo(self):
        self._row.eval_loop_panel.apply_state(copy.deepcopy(self._new))
    def undo(self):
        self._row.eval_loop_panel.apply_state(copy.deepcopy(self._old))


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
        self._state = copy.deepcopy(state)
    def redo(self):
        self._panel.remove_param(self._name, record=False)
    def undo(self):
        self._panel.add_param(self._name, record=False, state=copy.deepcopy(self._state))


class EditParamCmd(Command):
    """
    Record a change to a ParamSliderWidget's range, value, speed, or
    animation mode.

    Granularity: one command per editing session (focus-in / focus-out),
    not per keystroke — the caller decides when to push.
    """
    def __init__(self, panel, name: str, old_state: dict, new_state: dict):
        self._panel = panel
        self._name = name
        self._old = copy.deepcopy(old_state)
        self._new = copy.deepcopy(new_state)
    def redo(self):
        w = self._panel._param_widgets.get(self._name)
        if w:
            w.apply_state(copy.deepcopy(self._new))
    def undo(self):
        w = self._panel._param_widgets.get(self._name)
        if w:
            w.apply_state(copy.deepcopy(self._old))


class EditAnimPanelCmd(Command):
    """
    Record a change to the AnimPanel (t_min, t_max, speed, playing state).

    The t value itself is intentionally excluded from undo because it changes
    every tick and makes the undo stack unusable.  Only structural settings
    (range, speed) are recorded.
    """
    def __init__(self, anim_panel, old_state: dict, new_state: dict):
        self._panel = anim_panel
        self._old = copy.deepcopy(old_state)
        self._new = copy.deepcopy(new_state)
    def redo(self):
        self._panel.apply_state(copy.deepcopy(self._new))
    def undo(self):
        self._panel.apply_state(copy.deepcopy(self._old))


class EditGraphSettingsCmd(Command):
    """
    Record a change to GraphSettings (x/y/t range, samples, infinite mode).
    """
    def __init__(self, settings_widget, old_state: dict, new_state: dict):
        self._widget = settings_widget
        self._old = copy.deepcopy(old_state)
        self._new = copy.deepcopy(new_state)
    def redo(self):
        self._widget.apply_state(copy.deepcopy(self._new))
    def undo(self):
        self._widget.apply_state(copy.deepcopy(self._old))


class History:
    """
    Linear undo/redo stack with a fixed capacity.

    All Command subclasses must implement redo() and undo() as pure inverse
    operations — push() immediately calls redo() on the new command.
    """

    MAX = 200

    def __init__(self):
        self._stack: List[Command] = []
        self._pos: int = -1

    def push(self, cmd: Command):
        """Truncate future, append cmd, call cmd.redo()."""
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

    def clear(self):
        """Discard all history entries."""
        self._stack.clear()
        self._pos = -1