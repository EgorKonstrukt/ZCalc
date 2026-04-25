from __future__ import annotations
import math
import traceback
from typing import Any, Dict, Tuple

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

_EXTRA_MATH: Dict[str, Any] = {
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
}


def build_namespace(api, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build the full execution namespace for a script."""
    ns: Dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
    ns.update(_MATH_NS)
    ns.update(_EXTRA_MATH)
    ns["api"] = api
    if extra:
        ns.update(extra)
    return ns


def run_script(code: str, ns: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute code string inside ns.
    Returns (success, error_traceback_or_empty).
    """
    try:
        exec(compile(code, "<script>", "exec"), ns)
        return True, ""
    except Exception:
        return False, traceback.format_exc()
