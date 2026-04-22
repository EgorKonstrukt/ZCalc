import math
import re
from typing import List, Optional, Dict, Tuple
from constants import SAFE_NS, DERIV_H
try:
    import numpy as np
    _NP_OK = True
except ImportError:
    _NP_OK = False
_NP_NS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan, "atan2": np.arctan2,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "sqrt": np.sqrt, "exp": np.exp, "log": np.log,
    "log2": np.log2, "log10": np.log10,
    "abs": np.abs, "floor": np.floor, "ceil": np.ceil,
    "round": np.round, "pi": math.pi, "e": math.e, "inf": math.inf,
    "sign":     np.sign,
    "frac":     lambda x: x - np.floor(x),
    "clamp":    lambda x, a, b: np.clip(x, a, b),
    "mod":      np.fmod,
    "hypot":    np.hypot,
    "factorial": math.factorial,
    "degrees":  np.degrees,
    "radians":  np.radians,
    "sigmoid":  lambda x: 1.0 / (1.0 + np.exp(-x)),
    "step":     lambda x: np.where(x >= 0, 1.0, 0.0),
    "rect":     lambda x: np.where(np.abs(x) <= 0.5, 1.0, 0.0),
    "tri":      lambda x: np.maximum(0.0, 1.0 - np.abs(x)),
    "sawtooth": lambda x: 2.0 * (x / (2 * math.pi) - np.floor(0.5 + x / (2 * math.pi))),
    "square":   lambda x: np.where(np.sin(x) >= 0, 1.0, -1.0),
    "sinc":     lambda x: np.where(x != 0, np.sin(math.pi * x) / (math.pi * x), 1.0),
    "gaussian": lambda x: np.exp(-x * x / 2.0),
    "lerp":     lambda a, b, t: a + (b - a) * t,
    "__builtins__": {},
} if _NP_OK else {}
_use_numpy = True
def set_use_numpy(val: bool):
    global _use_numpy
    _use_numpy = val and _NP_OK
def safe_eval(expr: str, var_dict: Dict) -> float:
    ns = {**SAFE_NS, **var_dict}
    return eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns)
def _is_finite(v) -> bool:
    return isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
def linspace(a: float, b: float, n: int) -> List[float]:
    if n < 2:
        return [a]
    step = (b - a) / (n - 1)
    return [a + i * step for i in range(n)]
def _np_linspace(a: float, b: float, n: int):
    return np.linspace(a, b, n)
def sample_y(expr: str, x_vals, extra: Optional[Dict] = None) -> List[Optional[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            ns = {**_NP_NS, "x": x_arr, **ns_extra}
            result = eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns)
            arr = np.asarray(result, dtype=float)
            if arr.shape == ():
                arr = np.full(x_arr.shape, float(arr))
            finite = np.isfinite(arr)
            return [float(v) if finite[i] else None for i, v in enumerate(arr)]
        except Exception:
            pass
    results = []
    for x in x_vals:
        try:
            v = safe_eval(expr, {"x": x, **ns_extra})
            results.append(v if _is_finite(v) else None)
        except Exception:
            results.append(None)
    return results
def sample_polar(expr: str, theta_vals, extra: Optional[Dict] = None) -> Tuple[List[float], List[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            t_arr = np.asarray(theta_vals, dtype=float)
            ns = {**_NP_NS, "t": t_arr, "theta": t_arr, **ns_extra}
            r_arr = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns), dtype=float)
            if r_arr.shape == ():
                r_arr = np.full(t_arr.shape, float(r_arr))
            mask = np.isfinite(r_arr)
            t_f, r_f = t_arr[mask], r_arr[mask]
            return list(r_f * np.cos(t_f)), list(r_f * np.sin(t_f))
        except Exception:
            pass
    xs, ys = [], []
    for theta in theta_vals:
        try:
            r = safe_eval(expr, {"t": theta, "theta": theta, **ns_extra})
            if _is_finite(r):
                xs.append(r * math.cos(theta))
                ys.append(r * math.sin(theta))
        except Exception:
            pass
    return xs, ys
def sample_parametric(x_expr: str, y_expr: str, t_vals, extra: Optional[Dict] = None) -> Tuple[List[float], List[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            t_arr = np.asarray(t_vals, dtype=float)
            ns = {**_NP_NS, "t": t_arr, **ns_extra}
            xv = np.asarray(eval(compile(x_expr, "<expr>", "eval"), {"__builtins__": {}}, ns), dtype=float)
            yv = np.asarray(eval(compile(y_expr, "<expr>", "eval"), {"__builtins__": {}}, ns), dtype=float)
            if xv.shape == (): xv = np.full(t_arr.shape, float(xv))
            if yv.shape == (): yv = np.full(t_arr.shape, float(yv))
            mask = np.isfinite(xv) & np.isfinite(yv)
            return list(xv[mask]), list(yv[mask])
        except Exception:
            pass
    xs, ys = [], []
    for t in t_vals:
        try:
            xval = safe_eval(x_expr, {"t": t, **ns_extra})
            yval = safe_eval(y_expr, {"t": t, **ns_extra})
            if _is_finite(xval) and _is_finite(yval):
                xs.append(xval)
                ys.append(yval)
        except Exception:
            pass
    return xs, ys
def numerical_deriv(expr: str, x_vals, extra: Optional[Dict] = None, h: float = DERIV_H) -> List[Optional[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            ns_p = {**_NP_NS, "x": x_arr + h, **ns_extra}
            ns_m = {**_NP_NS, "x": x_arr - h, **ns_extra}
            yp = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns_p), dtype=float)
            ym = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns_m), dtype=float)
            if yp.shape == (): yp = np.full(x_arr.shape, float(yp))
            if ym.shape == (): ym = np.full(x_arr.shape, float(ym))
            d = (yp - ym) / (2 * h)
            mask = np.isfinite(d)
            return [float(d[i]) if mask[i] else None for i in range(len(d))]
        except Exception:
            pass
    results = []
    for x in x_vals:
        try:
            yp = safe_eval(expr, {"x": x + h, **ns_extra})
            ym = safe_eval(expr, {"x": x - h, **ns_extra})
            results.append((yp - ym) / (2 * h) if _is_finite(yp) and _is_finite(ym) else None)
        except Exception:
            results.append(None)
    return results
def numerical_deriv2(expr: str, x_vals, extra: Optional[Dict] = None, h: float = DERIV_H) -> List[Optional[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            ns_p = {**_NP_NS, "x": x_arr + h, **ns_extra}
            ns_c = {**_NP_NS, "x": x_arr,     **ns_extra}
            ns_m = {**_NP_NS, "x": x_arr - h, **ns_extra}
            yp = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns_p), dtype=float)
            yc = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns_c), dtype=float)
            ym = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns_m), dtype=float)
            if yp.shape == (): yp = np.full(x_arr.shape, float(yp))
            if yc.shape == (): yc = np.full(x_arr.shape, float(yc))
            if ym.shape == (): ym = np.full(x_arr.shape, float(ym))
            d2 = (yp - 2 * yc + ym) / (h * h)
            mask = np.isfinite(d2)
            return [float(d2[i]) if mask[i] else None for i in range(len(d2))]
        except Exception:
            pass
    results = []
    for x in x_vals:
        try:
            yp = safe_eval(expr, {"x": x + h, **ns_extra})
            yc = safe_eval(expr, {"x": x,     **ns_extra})
            ym = safe_eval(expr, {"x": x - h, **ns_extra})
            v = (yp - 2 * yc + ym) / (h * h)
            results.append(v if _is_finite(v) else None)
        except Exception:
            results.append(None)
    return results
def numerical_integral(expr: str, x_vals, extra: Optional[Dict] = None) -> List[Optional[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            ns = {**_NP_NS, "x": x_arr, **ns_extra}
            y_arr = np.asarray(eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns), dtype=float)
            if y_arr.shape == ():
                y_arr = np.full(x_arr.shape, float(y_arr))
            finite = np.isfinite(y_arr)
            results = []
            running = 0.0
            prev_x = prev_y = None
            for i in range(len(x_arr)):
                if finite[i]:
                    y = float(y_arr[i])
                    x = float(x_arr[i])
                    if prev_x is not None:
                        running += (y + prev_y) * 0.5 * (x - prev_x)
                    results.append(running)
                    prev_x, prev_y = x, y
                else:
                    results.append(None)
            return results
        except Exception:
            pass
    results = []
    running = 0.0
    prev_x = prev_y = None
    for x in x_vals:
        try:
            y = safe_eval(expr, {"x": x, **ns_extra})
            if _is_finite(y):
                if prev_x is not None:
                    running += (y + prev_y) * 0.5 * (x - prev_x)
                results.append(running)
                prev_x, prev_y = x, y
            else:
                results.append(None)
        except Exception:
            results.append(None)
    return results
def filter_none(xs, ys: List[Optional[float]]) -> Tuple[List[float], List[float]]:
    if _use_numpy and _NP_OK:
        x_arr = np.asarray(xs, dtype=float)
        y_arr = np.array([v if v is not None else np.nan for v in ys], dtype=float)
        mask = np.isfinite(y_arr)
        return x_arr[mask].tolist(), y_arr[mask].tolist()
    pairs = [(x, y) for x, y in zip(xs, ys) if y is not None]
    if not pairs:
        return [], []
    return list(zip(*pairs))
_FUNC_SUBS = [
    ('arcsin', r'\\arcsin'), ('arccos', r'\\arccos'), ('arctan', r'\\arctan'),
    ('asin',   r'\\arcsin'), ('acos',   r'\\arccos'),
    ('atan2',  r'\\operatorname{atan2}'), ('atan', r'\\arctan'),
    ('sinh',   r'\\sinh'),   ('cosh',   r'\\cosh'),   ('tanh',  r'\\tanh'),
    ('log10',  r'\\log_{10}'), ('log2',  r'\\log_2'), ('log',   r'\\ln'),
    ('exp',    r'\\exp'),
    ('sin',    r'\\sin'),    ('cos',    r'\\cos'),    ('tan',   r'\\tan'),
]
def expr_to_latex(expr: str) -> str:
    s = expr.strip()
    for name, latex in _FUNC_SUBS:
        s = re.sub(r'(?<![a-zA-Z])' + re.escape(name) + r'\(', latex + r'(', s)
    s = re.sub(r'(?<![a-zA-Z])sqrt\(([^()]*)\)', r'\\sqrt{\1}', s)
    s = re.sub(r'(?<![a-zA-Z])abs\(([^()]*)\)', r'|\1|', s)
    s = re.sub(r'\*\*\s*(-?[0-9]+(?:\.[0-9]+)?)', r'^{\1}', s)
    s = re.sub(r'\*\*\(([^()]*)\)', r'^{\1}', s)
    s = s.replace('**', '^')
    s = re.sub(r'(?<![\\{^])\*(?!\*)', r'\\cdot ', s)
    s = re.sub(r'(?<![{^\\])([a-zA-Z0-9])\s*/\s*([0-9]+)', r'\\frac{\1}{\2}', s)
    return s