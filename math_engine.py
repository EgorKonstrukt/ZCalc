import math
from typing import List, Optional, Dict, Tuple
from constants import SAFE_NS, DERIV_H
try:
    import numpy as np
    import numexpr as ne
    _NP_OK = True
    _NE_OK = True
except ImportError:
    try:
        import numpy as np
        _NP_OK = True
        _NE_OK = False
    except ImportError:
        _NP_OK = False
        _NE_OK = False

_DISCONTINUITY_FACTOR = 10.0
_COMPILE_CACHE: Dict[str, object] = {}

def _compile(expr: str) -> object:
    if expr not in _COMPILE_CACHE:
        _COMPILE_CACHE[expr] = compile(expr, "<expr>", "eval")
    return _COMPILE_CACHE[expr]

_NP_NS: Dict = {}
if _NP_OK:
    _NP_NS = {
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan, "atan2": np.arctan2,
        "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
        "sqrt": np.sqrt, "exp": np.exp, "log": np.log,
        "log2": np.log2, "log10": np.log10,
        "abs": np.abs, "floor": np.floor, "ceil": np.ceil,
        "round": np.round, "pi": math.pi, "e": math.e, "inf": math.inf,
        "sign": np.sign,
        "frac": lambda x: x - np.floor(x),
        "clamp": lambda x, a, b: np.clip(x, a, b),
        "mod": np.fmod,
        "hypot": np.hypot,
        "factorial": math.factorial,
        "degrees": np.degrees,
        "radians": np.radians,
        "sigmoid": lambda x: 1.0 / (1.0 + np.exp(-x)),
        "step": lambda x: np.where(x >= 0, 1.0, 0.0),
        "rect": lambda x: np.where(np.abs(x) <= 0.5, 1.0, 0.0),
        "tri": lambda x: np.maximum(0.0, 1.0 - np.abs(x)),
        "sawtooth": lambda x: 2.0 * (x / (2 * math.pi) - np.floor(0.5 + x / (2 * math.pi))),
        "square": lambda x: np.where(np.sin(x) >= 0, 1.0, -1.0),
        "sinc": lambda x: np.where(x != 0, np.sin(math.pi * x) / (math.pi * x), 1.0),
        "gaussian": lambda x: np.exp(-x * x / 2.0),
        "lerp": lambda a, b, t: a + (b - a) * t,
        "__builtins__": {},
    }

_use_numpy = True

def set_use_numpy(val: bool):
    global _use_numpy
    _use_numpy = val and _NP_OK

def safe_eval(expr: str, var_dict: Dict) -> float:
    ns = {**SAFE_NS, **var_dict}
    return eval(_compile(expr), {"__builtins__": {}}, ns)

def _is_finite(v) -> bool:
    return isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)

def linspace(a: float, b: float, n: int) -> List[float]:
    if n < 2:
        return [a]
    if _NP_OK:
        return np.linspace(a, b, n)
    step = (b - a) / (n - 1)
    return [a + i * step for i in range(n)]

def _np_linspace(a: float, b: float, n: int):
    return np.linspace(a, b, n)

def _eval_np_batch(expr: str, x_arr: "np.ndarray", ns_extra: dict) -> "np.ndarray":
    ns = {**_NP_NS, "x": x_arr, **ns_extra}
    raw = eval(_compile(expr), {"__builtins__": {}}, ns)
    y = np.asarray(raw, dtype=np.float64)
    if y.shape == ():
        y = np.full(len(x_arr), float(y))
    return y

def _finalize_y(arr: "np.ndarray") -> List[Optional[float]]:
    finite = np.isfinite(arr)
    out = [None] * len(arr)
    idxs = np.where(finite)[0]
    for i in idxs:
        out[i] = float(arr[i])
    return out

def sample_y(expr: str, x_vals, extra: Optional[Dict] = None) -> List[Optional[float]]:
    ns_extra = extra or {}
    if _use_numpy and _NP_OK:
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            arr = _eval_np_batch(expr, x_arr, ns_extra)
            return _finalize_y(arr)
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
            r_arr = np.asarray(eval(_compile(expr), {"__builtins__": {}}, ns), dtype=float)
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
            xv = np.asarray(eval(_compile(x_expr), {"__builtins__": {}}, ns), dtype=float)
            yv = np.asarray(eval(_compile(y_expr), {"__builtins__": {}}, ns), dtype=float)
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
            c = _compile(expr)
            yp = np.asarray(eval(c, {"__builtins__": {}}, ns_p), dtype=float)
            ym = np.asarray(eval(c, {"__builtins__": {}}, ns_m), dtype=float)
            if yp.shape == (): yp = np.full(x_arr.shape, float(yp))
            if ym.shape == (): ym = np.full(x_arr.shape, float(ym))
            d = (yp - ym) / (2 * h)
            return _finalize_y(d)
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
            c = _compile(expr)
            ns_p = {**_NP_NS, "x": x_arr + h, **ns_extra}
            ns_c = {**_NP_NS, "x": x_arr,     **ns_extra}
            ns_m = {**_NP_NS, "x": x_arr - h, **ns_extra}
            yp = np.asarray(eval(c, {"__builtins__": {}}, ns_p), dtype=float)
            yc = np.asarray(eval(c, {"__builtins__": {}}, ns_c), dtype=float)
            ym = np.asarray(eval(c, {"__builtins__": {}}, ns_m), dtype=float)
            for arr, ref in ((yp, x_arr), (yc, x_arr), (ym, x_arr)):
                if arr.shape == ():
                    arr = np.full(ref.shape, float(arr))
            d2 = (yp - 2 * yc + ym) / (h * h)
            return _finalize_y(d2)
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
            y_arr = _eval_np_batch(expr, x_arr, ns_extra)
            finite = np.isfinite(y_arr)
            y_arr = np.where(finite, y_arr, 0.0)
            dx = np.diff(x_arr)
            trap = (y_arr[:-1] + y_arr[1:]) * 0.5 * dx
            trap = np.where(finite[:-1] & finite[1:], trap, 0.0)
            cumsum = np.concatenate([[0.0], np.cumsum(trap)])
            mask = np.ones(len(x_arr), dtype=bool)
            mask[~finite] = False
            results = [None] * len(x_arr)
            for i in np.where(mask)[0]:
                results[i] = float(cumsum[i])
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

def sample_y_adaptive(expr: str, x_vals, extra: Optional[Dict] = None) -> Tuple[List[float], List[Optional[float]]]:
    ns_extra = extra or {}
    if not (_use_numpy and _NP_OK):
        ys = sample_y(expr, x_vals, ns_extra)
        return list(x_vals), ys
    x_arr = np.asarray(x_vals, dtype=np.float64)
    n = len(x_arr)
    if n < 2:
        return list(x_arr), sample_y(expr, x_vals, ns_extra)
    try:
        y_arr = _eval_np_batch(expr, x_arr, ns_extra)
    except Exception:
        return list(x_arr), [None] * n
    fin = np.isfinite(y_arr)
    y_work = np.where(fin, y_arr, np.nan)
    fin_vals = y_arr[fin]
    y_range = float(np.ptp(fin_vals)) if len(fin_vals) >= 2 else 1.0
    if y_range == 0.0:
        y_range = 1.0
    threshold = y_range * _DISCONTINUITY_FACTOR
    dy_abs = np.abs(np.diff(y_work))
    both_fin = fin[:-1] & fin[1:]
    jumps = np.where((dy_abs > threshold) | ~both_fin)[0]
    for ji in jumps:
        y_work[ji] = np.nan
        if ji + 1 < n:
            y_work[ji + 1] = np.nan
    if len(jumps) == 0:
        return list(x_arr), _finalize_y(y_work)
    dx_step = float(x_arr[1] - x_arr[0]) if n >= 2 else 1.0
    ranges: List[Tuple[float, float]] = []
    for ji in jumps:
        xl = float(x_arr[max(0, ji - 1)])
        xr = float(x_arr[min(n - 1, ji + 2)])
        ranges.append((xl, xr))
    merged: List[List[float]] = []
    for rng in sorted(ranges):
        if merged and rng[0] <= merged[-1][1] + dx_step * 2:
            merged[-1][1] = max(merged[-1][1], rng[1])
        else:
            merged.append([rng[0], rng[1]])
    all_rx = np.concatenate([
        np.linspace(xl, xr, min(128, max(16, int((xr - xl) / max(dx_step, 1e-30) * 8))), dtype=np.float64)
        for xl, xr in merged
    ]) if merged else np.empty(0, dtype=np.float64)
    if len(all_rx) > 0:
        try:
            all_ry = _eval_np_batch(expr, all_rx, ns_extra)
            ry_fin = np.isfinite(all_ry)
            ry_range = float(np.ptp(all_ry[ry_fin])) if ry_fin.any() else y_range
            ry_thresh = max(threshold, (ry_range or y_range) * _DISCONTINUITY_FACTOR)
            dy_r = np.abs(np.diff(all_ry))
            both_r = ry_fin[:-1] & ry_fin[1:]
            disc_r = np.where((dy_r > ry_thresh) | ~both_r)[0]
            for di in disc_r:
                all_ry[di] = np.nan
                if di + 1 < len(all_ry):
                    all_ry[di + 1] = np.nan
        except Exception:
            all_rx = np.empty(0, dtype=np.float64)
            all_ry = np.empty(0, dtype=np.float64)
    else:
        all_ry = np.empty(0, dtype=np.float64)
    if len(merged) > 0 and len(all_rx) > 0:
        covered = np.zeros(n, dtype=bool)
        for xl, xr in merged:
            covered |= (x_arr >= xl) & (x_arr <= xr)
        keep = ~covered
        base_x = x_arr[keep]
        base_y = y_work[keep]
        combined_x = np.concatenate([base_x, all_rx]) if (len(base_x) > 0 or len(all_rx) > 0) else x_arr
        combined_y = np.concatenate([base_y, all_ry]) if (len(base_y) > 0 or len(all_ry) > 0) else y_work
        sort_idx = np.argsort(combined_x, kind="stable")
        combined_x = combined_x[sort_idx]
        combined_y = combined_y[sort_idx]
    else:
        combined_x = x_arr
        combined_y = y_work
    return combined_x.tolist(), _finalize_y(combined_y)

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

def expr_to_latex(expr: str) -> str:
    """Convert a Python expression string to LaTeX via sympy_engine."""
    from sympy_engine import sympy_to_latex
    return sympy_to_latex(expr)