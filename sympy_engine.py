from __future__ import annotations
from typing import Optional
import sympy
from sympy import latex, symbols, Symbol
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

_EXTRA_NS: dict = {
    "sigmoid": sympy.Function("sigmoid"),
    "step": sympy.Function("step"),
    "rect": sympy.Function("rect"),
    "tri": sympy.Function("tri"),
    "sawtooth": sympy.Function("sawtooth"),
    "square": sympy.Function("square"),
    "sinc": sympy.Function("sinc"),
    "gaussian": sympy.Function("gaussian"),
    "clamp": sympy.Function("clamp"),
    "frac": sympy.Function("frac"),
    "lerp": sympy.Function("lerp"),
    "sech": sympy.Function("sech"),
    "sign": sympy.sign,
}


def sympy_to_latex(sympy_expr: str, var: str = "x") -> str:
    """Convert a sympy-compatible expression string to LaTeX."""
    try:
        sym = symbols(var)
        local_ns = {var: sym, **_EXTRA_NS}
        expr = parse_expr(sympy_expr, local_dict=local_ns, transformations=_TRANSFORMS)
        return latex(expr)
    except Exception:
        return sympy_expr


def sympy_to_python(sympy_expr: str) -> str:
    """Return a Python-eval-compatible string from sympy output."""
    return sympy_expr


def normalize_editor_expr(expr: str, var: str = "x") -> str:
    """
    Clean up sympy strings emitted by MathEditor.

    The editor sometimes emits variable names as zero-arg calls, e.g. ``x()``
    instead of ``x``.  This function strips those spurious parentheses so the
    expression evaluates correctly in math_engine.
    """
    import re
    _KNOWN_FUNCS = {
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh", "sqrt", "exp", "log", "log2", "log10",
        "abs", "floor", "ceil", "round", "sign", "frac", "clamp", "mod",
        "hypot", "factorial", "degrees", "radians", "sigmoid", "step",
        "rect", "tri", "sawtooth", "square", "sinc", "gaussian", "lerp",
        "max", "min", "gcd", "lcm", "sech",
    }
    def _strip_var_call(m: re.Match) -> str:
        name = m.group(1)
        if name in _KNOWN_FUNCS:
            return m.group(0)
        return name
    result = re.sub(r'\b([A-Za-z_][A-Za-z0-9_]*)\(\)', _strip_var_call, expr)
    return result


def validate_expr(expr: str, var: str = "x") -> Optional[str]:
    """Return error string if expr is invalid, else None."""
    try:
        sym = symbols(var)
        local_ns = {var: sym, **_EXTRA_NS}
        parse_expr(expr, local_dict=local_ns, transformations=_TRANSFORMS)
        return None
    except Exception as exc:
        return str(exc)