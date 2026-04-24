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
_DISCONTINUITY_FACTOR = 10.0
def _eval_np_batch(expr: str, x_arr, ns_extra: dict):
    ns = {**_NP_NS, "x": x_arr, **ns_extra}
    raw = eval(compile(expr, "<expr>", "eval"), {"__builtins__": {}}, ns)
    y = np.asarray(raw, dtype=np.float64)
    if y.shape == ():
        y = np.full(len(x_arr), float(y))
    return y
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
        out2 = np.where(np.isfinite(y_work), y_work, None).astype(object)
        for i in np.where(np.isfinite(y_work))[0]:
            out2[i] = float(y_work[i])
        res_y: List[Optional[float]] = out2.tolist()
        return list(x_arr), res_y
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
        if len(base_x) > 0 or len(all_rx) > 0:
            combined_x = np.concatenate([base_x, all_rx])
            combined_y = np.concatenate([base_y, all_ry])
            sort_idx = np.argsort(combined_x, kind="stable")
            combined_x = combined_x[sort_idx]
            combined_y = combined_y[sort_idx]
        else:
            combined_x = x_arr
            combined_y = y_work
    else:
        combined_x = x_arr
        combined_y = y_work
    fin_f = np.isfinite(combined_y)
    res_x = combined_x.tolist()
    out_obj = np.where(fin_f, combined_y, None)
    out_obj = out_obj.astype(object)
    fin_idx = np.where(fin_f)[0]
    for i in fin_idx:
        out_obj[i] = float(combined_y[i])
    res_y_out: List[Optional[float]] = out_obj.tolist()
    return res_x, res_y_out
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