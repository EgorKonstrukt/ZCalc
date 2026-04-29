from __future__ import annotations
import atexit
import math
import sys
import threading
import traceback
import ctypes
import weakref
from typing import Any, Dict, List, Optional, Tuple

_SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "next": next, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip, "True": True, "False": False, "None": None,
}

_MATH_NS: Dict[str, Any] = {
    k: getattr(math, k) for k in dir(math) if not k.startswith("_")
}

_EXTRA: Dict[str, Any] = {
    "sign":     lambda x: (1 if x > 0 else -1 if x < 0 else 0),
    "clamp":    lambda x, a, b: max(a, min(b, x)),
    "lerp":     lambda a, b, t: a + (b - a) * t,
    "frac":     lambda x: x - math.floor(x),
    "sigmoid":  lambda x: 1.0 / (1.0 + math.exp(-x)),
    "gaussian": lambda x: math.exp(-x * x / 2.0),
    "sinc":     lambda x: math.sin(math.pi * x) / (math.pi * x) if x != 0.0 else 1.0,
    "step":     lambda x: 1.0 if x >= 0.0 else 0.0,
    "rect":     lambda x: 1.0 if abs(x) <= 0.5 else 0.0,
    "sawtooth": lambda x: 2.0 * (x / (2 * math.pi) - math.floor(0.5 + x / (2 * math.pi))),
    "square":   lambda x: 1.0 if math.sin(x) >= 0.0 else -1.0,
    "smoothstep": lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(max(0.0, min(1.0, (x - e0) / (e1 - e0))) if e1 != e0 else 0.0),
    "pingpong": lambda x, length: length - abs((x % (2 * length)) - length) if length != 0 else 0.0,
    "remap":    lambda x, a, b, c, d: c + (x - a) / (b - a) * (d - c) if b != a else c,
}

DEFAULT_TIMEOUT_S = 5.0
_KILL_EXTRA_S = 1.0

_active_threads: List[weakref.ref] = []
_threads_lock = threading.Lock()


def _cleanup_all_threads():
    with _threads_lock:
        refs = list(_active_threads)
    for ref in refs:
        t = ref()
        if t is not None and t.is_alive():
            _raise_in_thread(t.ident, ScriptTimeoutError)
            t.join(timeout=0.5)


atexit.register(_cleanup_all_threads)


class ScriptTimeoutError(Exception):
    pass


def _raise_in_thread(tid: int, exc_type) -> bool:
    if tid is None:
        return False
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(tid),
        ctypes.py_object(exc_type),
    )
    return res > 0


class _ScriptThread(threading.Thread):
    def __init__(self, code: str, ns: Dict[str, Any], timeout_s: float):
        super().__init__(daemon=True)
        self._code = code
        self._ns = ns
        self._timeout_s = timeout_s
        self.success = False
        self.error = ""
        self._watchdog: Optional[threading.Timer] = None

    def run(self):
        self._watchdog = threading.Timer(self._timeout_s, self._inject_timeout)
        self._watchdog.daemon = True
        self._watchdog.start()
        try:
            exec(compile(self._code, "<script>", "exec"), self._ns)
            self.success = True
        except ScriptTimeoutError:
            self.success = False
            self.error = (
                f"ScriptTimeoutError: script exceeded {self._timeout_s:.0f}s limit.\n"
                "Likely cause: infinite loop or blocking call.\n"
                "Use api.animate() for continuous updates instead of while True."
            )
        except Exception:
            self.success = False
            self.error = traceback.format_exc()
        finally:
            if self._watchdog:
                self._watchdog.cancel()

    def _inject_timeout(self):
        _raise_in_thread(self.ident, ScriptTimeoutError)

    def terminate(self):
        if self.is_alive():
            _raise_in_thread(self.ident, ScriptTimeoutError)


def build_namespace(api, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    ns: Dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
    ns.update(_MATH_NS)
    ns.update(_EXTRA)
    ns["api"] = api
    if extra:
        ns.update(extra)
    return ns


def run_script(
    code: str,
    ns: Dict[str, Any],
    timeout_s: float = DEFAULT_TIMEOUT_S,
    on_done=None,
) -> Tuple[bool, str]:
    t = _ScriptThread(code, ns, timeout_s)
    with _threads_lock:
        _active_threads.append(weakref.ref(t))
    t.start()
    t.join(timeout=timeout_s + _KILL_EXTRA_S)
    if t.is_alive():
        _raise_in_thread(t.ident, ScriptTimeoutError)
        t.join(timeout=1.0)
        if on_done:
            on_done(False, f"ScriptTimeoutError: hard kill after {timeout_s + _KILL_EXTRA_S:.0f}s")
        return False, f"ScriptTimeoutError: script did not terminate within {timeout_s + _KILL_EXTRA_S:.0f}s"
    if on_done:
        on_done(t.success, t.error)
    return t.success, t.error