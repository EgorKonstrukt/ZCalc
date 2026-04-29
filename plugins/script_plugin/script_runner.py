from __future__ import annotations
import math
import traceback
from typing import Any, Dict, Optional, Tuple

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
    "sign":       lambda x: (1 if x > 0 else -1 if x < 0 else 0),
    "clamp":      lambda x, a, b: max(a, min(b, x)),
    "lerp":       lambda a, b, t: a + (b - a) * t,
    "frac":       lambda x: x - math.floor(x),
    "sigmoid":    lambda x: 1.0 / (1.0 + math.exp(-x)),
    "gaussian":   lambda x: math.exp(-x * x / 2.0),
    "sinc":       lambda x: math.sin(math.pi * x) / (math.pi * x) if x != 0.0 else 1.0,
    "step":       lambda x: 1.0 if x >= 0.0 else 0.0,
    "rect":       lambda x: 1.0 if abs(x) <= 0.5 else 0.0,
    "sawtooth":   lambda x: 2.0 * (x / (2 * math.pi) - math.floor(0.5 + x / (2 * math.pi))),
    "square":     lambda x: 1.0 if math.sin(x) >= 0.0 else -1.0,
    "smoothstep": lambda e0, e1, x: (
        lambda t: t * t * (3 - 2 * t)
    )(max(0.0, min(1.0, (x - e0) / (e1 - e0))) if e1 != e0 else 0.0),
    "pingpong":   lambda x, length: (
        length - abs((x % (2 * length)) - length) if length != 0 else 0.0
    ),
    "remap":      lambda x, a, b, c, d: (
        c + (x - a) / (b - a) * (d - c) if b != a else c
    ),
}

DEFAULT_TIMEOUT_S = 5.0


def build_namespace(api, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    """
    Execute script synchronously in the calling (main) thread.
    Scripts using api.animate() register QTimers and return immediately —
    they do NOT block the Qt event loop.
    Infinite loops without api.animate() will still freeze the UI;
    that is user error, not a framework issue.
    """
    try:
        exec(compile(code, "<script>", "exec"), ns)
        if on_done:
            on_done(True, "")
        return True, ""
    except Exception:
        err = traceback.format_exc()
        if on_done:
            on_done(False, err)
        return False, err