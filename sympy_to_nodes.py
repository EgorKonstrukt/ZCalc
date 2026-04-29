from __future__ import annotations
import tokenize, io
from typing import Optional, List
from pyqt5_math_widget._renderer import (
    FormulaNode, SeqNode, TextNode, FracNode, SqrtNode,
    PowerNode, ParenNode, AbsNode,
    FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
)

_GREEK_UNICODE: dict[str, str] = {
    "alpha": "\u03B1", "beta": "\u03B2", "gamma": "\u03B3", "delta": "\u03B4",
    "epsilon": "\u03B5", "zeta": "\u03B6", "eta": "\u03B7", "theta": "\u03B8",
    "iota": "\u03B9", "kappa": "\u03BA", "lamda": "\u03BB", "lam": "\u03BB",
    "mu": "\u03BC", "nu": "\u03BD", "xi": "\u03BE", "pi": "\u03C0",
    "rho": "\u03C1", "sigma": "\u03C3", "tau": "\u03C4", "upsilon": "\u03C5",
    "phi": "\u03C6", "chi": "\u03C7", "psi": "\u03C8", "omega": "\u03C9",
}

_FUNC_NAMES: dict[str, str] = {
    "sin": "sin", "cos": "cos", "tan": "tan",
    "asin": "arcsin", "acos": "arccos", "atan": "arctan", "atan2": "atan2",
    "sinh": "sinh", "cosh": "cosh", "tanh": "tanh",
    "log": "ln", "log2": "log\u2082", "log10": "log",
    "exp": "exp", "sqrt": "sqrt",
    "abs": "abs", "floor": "floor", "ceil": "ceil",
    "sign": "sign", "factorial": "factorial",
    "sigmoid": "sigmoid", "step": "step", "rect": "rect",
    "tri": "tri", "sawtooth": "sawtooth", "square": "square",
    "sinc": "sinc", "gaussian": "gaussian",
    "clamp": "clamp", "frac": "frac", "lerp": "lerp",
    "max": "max", "min": "min", "hypot": "hypot",
    "degrees": "deg", "radians": "rad",
    "mod": "mod", "gcd": "gcd", "lcm": "lcm", "sech": "sech",
    "round": "round",
}

_ITALIC_SYMS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

_TOK_NUM  = "NUM"
_TOK_NAME = "NAME"
_TOK_OP   = "OP"
_TOK_EOF  = "EOF"


class _Token:
    __slots__ = ("kind", "value")
    def __init__(self, kind: str, value: str):
        self.kind = kind
        self.value = value


def _tokenize(expr: str) -> List[_Token]:
    tokens: List[_Token] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(expr).readline):
            if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT,
                            tokenize.ENDMARKER, 0, 4, 62):
                continue
            if tok.type == tokenize.NUMBER:
                tokens.append(_Token(_TOK_NUM, tok.string))
            elif tok.type == tokenize.NAME:
                tokens.append(_Token(_TOK_NAME, tok.string))
            elif tok.type == tokenize.OP:
                tokens.append(_Token(_TOK_OP, tok.string))
    except tokenize.TokenError:
        pass
    tokens.append(_Token(_TOK_EOF, ""))
    return tokens


def _t(s: str, italic: bool = False, size: int = FONT_SIZE_NORMAL) -> TextNode:
    return TextNode(s, size, italic, False)


def _seq(*nodes: FormulaNode) -> SeqNode:
    return SeqNode(list(nodes))


def _wrap_seq(n: FormulaNode) -> SeqNode:
    return n if isinstance(n, SeqNode) else SeqNode([n])


def _paren(inner: FormulaNode) -> ParenNode:
    return ParenNode(_wrap_seq(inner))


class _Parser:
    def __init__(self, tokens: List[_Token]):
        self._t = tokens
        self._i = 0

    def _peek(self) -> _Token:
        return self._t[self._i]

    def _eat(self) -> _Token:
        t = self._t[self._i]
        self._i += 1
        return t

    def _expect(self, v: str):
        tok = self._eat()
        if tok.value != v:
            raise SyntaxError(f"expected {v!r} got {tok.value!r}")

    def parse(self) -> FormulaNode:
        n = self._expr()
        if self._peek().kind != _TOK_EOF:
            raise SyntaxError(f"trailing token {self._peek().value!r}")
        return n

    # expr = term (('+' | '-') term)*
    def _expr(self) -> FormulaNode:
        parts: List[FormulaNode] = [self._term()]
        ops: List[str] = ["+"]
        while self._peek().kind == _TOK_OP and self._peek().value in ("+", "-"):
            ops.append(self._eat().value)
            parts.append(self._term())
        if len(parts) == 1:
            return parts[0]
        children: List[FormulaNode] = []
        for i, (op, node) in enumerate(zip(ops, parts)):
            if i == 0:
                if op == "-":
                    children.append(_t("\u2212"))
                children.append(node)
            else:
                children.append(_t("\u00A0\u2212\u00A0" if op == "-" else "\u00A0+\u00A0"))
                children.append(node)
        return _seq(*children)

    # term = signed_power ('*' signed_power | '/' signed_power)*
    # division becomes a FracNode spanning numer/denom
    def _term(self) -> FormulaNode:
        factors: List[FormulaNode] = [self._signed_power()]
        while self._peek().kind == _TOK_OP and self._peek().value in ("*", "/"):
            op = self._eat().value
            rhs = self._signed_power()
            if op == "/":
                numer = _seq(*factors) if len(factors) > 1 else factors[0]
                return FracNode(_wrap_seq(numer), _wrap_seq(rhs))
            factors.append(rhs)
        return _seq(*factors) if len(factors) > 1 else factors[0]

    # signed_power = '-' primary ('**' unary)? | primary ('**' unary)?
    # Unary minus has LOWER precedence than **: -x**2 = -(x**2)
    def _signed_power(self) -> FormulaNode:
        neg = False
        if self._peek().kind == _TOK_OP and self._peek().value == "-":
            self._eat()
            neg = True
        base = self._primary()
        if self._peek().kind == _TOK_OP and self._peek().value == "**":
            self._eat()
            exp = self._signed_power()
            base = PowerNode(base, _wrap_seq(exp))
        if neg:
            return _seq(_t("\u2212"), base)
        return base

    # primary = number | name | func'('args')' | '('expr')'
    def _primary(self) -> FormulaNode:
        tok = self._peek()

        if tok.kind == _TOK_NUM:
            self._eat()
            return _t(tok.value)

        if tok.kind == _TOK_NAME:
            name = tok.value
            self._eat()
            if self._peek().kind == _TOK_OP and self._peek().value == "(":
                return self._func_call(name)
            if name == "pi":
                return _t("\u03C0")
            if name in ("inf", "oo"):
                return _t("\u221E")
            if name in _GREEK_UNICODE:
                return _t(_GREEK_UNICODE[name])
            italic = len(name) == 1 and name in _ITALIC_SYMS
            return _t(name, italic=italic)

        if tok.kind == _TOK_OP and tok.value == "(":
            self._eat()
            inner = self._expr()
            self._expect(")")
            return _paren(inner)

        raise SyntaxError(f"unexpected token {tok.value!r}")

    def _func_call(self, name: str) -> FormulaNode:
        self._expect("(")
        args: List[FormulaNode] = []
        if self._peek().value != ")":
            args.append(self._expr())
            while self._peek().value == ",":
                self._eat()
                args.append(self._expr())
        self._expect(")")

        if name == "sqrt" and len(args) == 1:
            return SqrtNode(_wrap_seq(args[0]))

        if name == "abs" and len(args) == 1:
            return AbsNode(_wrap_seq(args[0]))

        display = _FUNC_NAMES.get(name, name)

        if len(args) == 1:
            return _seq(_t(display, italic=False), _paren(args[0]))

        parts: List[FormulaNode] = [_t(display, italic=False), _t("(")]
        for i, a in enumerate(args):
            if i > 0:
                parts.append(_t(",\u00A0"))
            parts.append(a)
        parts.append(_t(")"))
        return _seq(*parts)


def expr_str_to_node(expr: str) -> Optional[FormulaNode]:
    """Parse a Python/sympy expression string into a FormulaNode tree."""
    expr = expr.strip()
    if not expr:
        return None
    try:
        return _Parser(_tokenize(expr)).parse()
    except Exception:
        return None


# Keep old name as alias for any existing imports
sympy_str_to_node = expr_str_to_node