from __future__ import annotations
import sys
import io
import traceback
import code
from typing import Dict, Any, Tuple, Optional

class ReplExecutor:
    """
    Stateful Python interpreter for the console REPL.
    Supports multi-line blocks, preserves state between calls.
    """
    def __init__(self, initial_ns: Optional[Dict[str, Any]] = None) -> None:
        self._ns: Dict[str, Any] = {"__name__": "__console__", "__doc__": None}
        if initial_ns:
            self._ns.update(initial_ns)
        self._partial: list = []
        self._console = code.InteractiveConsole(self._ns)

    @property
    def namespace(self) -> Dict[str, Any]:
        return self._ns

    def update_namespace(self, updates: Dict[str, Any]) -> None:
        self._ns.update(updates)

    def execute(self, source: str) -> Tuple[str, str, bool]:
        """
        Execute source in the interpreter namespace.
        Returns (stdout, stderr, is_incomplete) where is_incomplete means
        the input is a partial block (e.g. 'if x:').
        """
        old_out = sys.stdout
        old_err = sys.stderr
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        sys.stdout = buf_out
        sys.stderr = buf_err
        incomplete = False
        try:
            self._partial.append(source)
            combined = "\n".join(self._partial)
            try:
                obj = compile(combined, "<console>", "single")
                exec(obj, self._ns)
                self._partial.clear()
            except SyntaxError as exc:
                if "unexpected EOF" in str(exc) or "was never closed" in str(exc):
                    incomplete = True
                else:
                    self._partial.clear()
                    buf_err.write(traceback.format_exc())
            except Exception:
                self._partial.clear()
                buf_err.write(traceback.format_exc())
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        return buf_out.getvalue(), buf_err.getvalue(), incomplete

    def reset_partial(self) -> None:
        self._partial.clear()

    def is_partial(self) -> bool:
        return bool(self._partial)