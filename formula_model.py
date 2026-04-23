from typing import Optional, List, Dict, Any, Tuple
from formula_renderer import (
    FormulaNode, HSeqNode, TextNode, PlaceholderNode, FracNode,
    SqrtNode, PowerNode, SubNode, ParenNode, IntegralNode, SumProdNode,
    RENDER_FONT_SIZE, RENDER_SMALL_FONT_SIZE, RENDER_TINY_FONT_SIZE
)

_GREEK_MAP = {
    "alpha": "\u03B1", "beta": "\u03B2", "gamma": "\u03B3", "delta": "\u03B4",
    "epsilon": "\u03B5", "zeta": "\u03B6", "eta": "\u03B7", "theta": "\u03B8",
    "iota": "\u03B9", "kappa": "\u03BA", "lambda": "\u03BB", "mu": "\u03BC",
    "nu": "\u03BD", "xi": "\u03BE", "pi": "\u03C0", "rho": "\u03C1",
    "sigma": "\u03C3", "tau": "\u03C4", "upsilon": "\u03C5", "phi": "\u03C6",
    "chi": "\u03C7", "psi": "\u03C8", "omega": "\u03C9",
    "Alpha": "\u0391", "Beta": "\u0392", "Gamma": "\u0393", "Delta": "\u0394",
    "Theta": "\u0398", "Lambda": "\u039B", "Pi": "\u03A0", "Sigma": "\u03A3",
    "Phi": "\u03A6", "Psi": "\u03A8", "Omega": "\u03A9",
    "inf": "\u221E", "infty": "\u221E",
}

_OP_MAP = {
    "+": "+", "-": "\u2212", "*": "\u00B7", "/": "/", "=": "=",
    "!=": "\u2260", "<=": "\u2264", ">=": "\u2265",
    "->": "\u2192", "<-": "\u2190", "<->": "\u2194",
    "pm": "\u00B1", "times": "\u00D7", "div": "\u00F7",
    "cdot": "\u00B7", "approx": "\u2248", "sim": "\u223C",
    "in": "\u2208", "notin": "\u2209", "subset": "\u2282",
    "cup": "\u222A", "cap": "\u2229", "partial": "\u2202",
    "nabla": "\u2207",
}

_FUNC_NAMES = {
    "sin", "cos", "tan", "cot", "sec", "csc",
    "arcsin", "arccos", "arctan",
    "sinh", "cosh", "tanh",
    "log", "ln", "exp", "lim",
    "max", "min", "gcd", "lcm",
    "det", "tr", "rank",
}


def _make_text(s: str, size: int = RENDER_FONT_SIZE, italic: bool = True) -> TextNode:
    return TextNode(s, size, italic)


def _make_op(s: str) -> TextNode:
    return TextNode(s, RENDER_FONT_SIZE, False)


def _ph(size: int = RENDER_FONT_SIZE) -> PlaceholderNode:
    return PlaceholderNode(size)


def _small_text(s: str) -> TextNode:
    return TextNode(s, RENDER_SMALL_FONT_SIZE, True)


def _tiny_text(s: str) -> TextNode:
    return TextNode(s, RENDER_TINY_FONT_SIZE, True)


class FormulaModel:
    def __init__(self):
        self._root: FormulaNode = HSeqNode([_ph()])
        self._cursor_id: Optional[int] = None
        self._selected_ids: set = set()
        self._history: List[FormulaNode] = []
        self._redo_stack: List[FormulaNode] = []
        self._cursor_id = self._root.collect_ids()[0]
    def get_root(self) -> FormulaNode:
        return self._root
    def get_cursor_id(self) -> Optional[int]:
        return self._cursor_id
    def get_selected_ids(self) -> set:
        return self._selected_ids
    def _push_history(self):
        import copy
        self._history.append(copy.deepcopy(self._root))
        self._redo_stack.clear()
        if len(self._history) > 100:
            self._history.pop(0)
    def undo(self):
        if not self._history:
            return
        import copy
        self._redo_stack.append(copy.deepcopy(self._root))
        self._root = self._history.pop()
        ids = self._root.collect_ids()
        self._cursor_id = ids[0] if ids else None
        self._selected_ids.clear()
    def redo(self):
        if not self._redo_stack:
            return
        import copy
        self._history.append(copy.deepcopy(self._root))
        self._root = self._redo_stack.pop()
        ids = self._root.collect_ids()
        self._cursor_id = ids[0] if ids else None
        self._selected_ids.clear()
    def _find_parent_seq(self, root: FormulaNode, target_id: int
                         ) -> Optional[Tuple["HSeqNode", int]]:
        if isinstance(root, HSeqNode):
            for i, c in enumerate(root.children):
                if c.node_id == target_id:
                    return root, i
                r = self._find_parent_seq(c, target_id)
                if r:
                    return r
        for attr in ["num", "den", "body", "base", "exp", "sub", "var",
                     "lower", "upper", "index"]:
            child = getattr(root, attr, None)
            if child is not None:
                if child.node_id == target_id:
                    wrapped = HSeqNode([child])
                    return wrapped, 0
                r = self._find_parent_seq(child, target_id)
                if r:
                    return r
        return None
    def _ids_list(self) -> List[int]:
        return self._root.collect_ids()
    def move_cursor_left(self):
        ids = self._ids_list()
        if self._cursor_id is None or self._cursor_id not in ids:
            return
        idx = ids.index(self._cursor_id)
        if idx > 0:
            self._cursor_id = ids[idx - 1]
    def move_cursor_right(self):
        ids = self._ids_list()
        if self._cursor_id is None or self._cursor_id not in ids:
            return
        idx = ids.index(self._cursor_id)
        if idx < len(ids) - 1:
            self._cursor_id = ids[idx + 1]
    def _find_seq_with_cursor(self) -> Optional[Tuple["HSeqNode", int]]:
        if self._cursor_id is None:
            return None
        return self._find_parent_seq(self._root, self._cursor_id)
    def insert_text(self, text: str):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        node = seq.children[idx]
        if isinstance(node, PlaceholderNode):
            seq.children[idx] = _make_text(text)
            self._cursor_id = seq.children[idx].node_id
        else:
            new_node = _make_text(text)
            seq.children.insert(idx + 1, new_node)
            self._cursor_id = new_node.node_id
    def insert_operator(self, op: str):
        self._push_history()
        symbol = _OP_MAP.get(op, op)
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        node = _make_op(symbol)
        seq.children.insert(idx + 1, node)
        self._cursor_id = node.node_id
    def insert_greek(self, name: str):
        sym = _GREEK_MAP.get(name, name)
        self.insert_text(sym)
    def insert_frac(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        num_ph = _ph()
        den_ph = _ph()
        frac = FracNode(HSeqNode([num_ph]), HSeqNode([den_ph]))
        seq.children.insert(idx + 1, frac)
        self._cursor_id = num_ph.node_id
    def insert_sqrt(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        body_ph = _ph()
        sqrt_node = SqrtNode(HSeqNode([body_ph]))
        seq.children.insert(idx + 1, sqrt_node)
        self._cursor_id = body_ph.node_id
    def insert_power(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        base = seq.children[idx]
        exp_ph = _ph(RENDER_SMALL_FONT_SIZE)
        pwr = PowerNode(base, HSeqNode([exp_ph]))
        seq.children[idx] = pwr
        self._cursor_id = exp_ph.node_id
    def insert_subscript(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        base = seq.children[idx]
        sub_ph = _ph(RENDER_SMALL_FONT_SIZE)
        sub = SubNode(base, HSeqNode([sub_ph]))
        seq.children[idx] = sub
        self._cursor_id = sub_ph.node_id
    def insert_parens(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        body_ph = _ph()
        paren = ParenNode(HSeqNode([body_ph]))
        seq.children.insert(idx + 1, paren)
        self._cursor_id = body_ph.node_id
    def insert_integral(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        body_ph = _ph()
        var_ph = _ph(RENDER_SMALL_FONT_SIZE)
        lo_ph = _ph(RENDER_TINY_FONT_SIZE)
        hi_ph = _ph(RENDER_TINY_FONT_SIZE)
        node = IntegralNode(HSeqNode([body_ph]), HSeqNode([var_ph]),
                            HSeqNode([lo_ph]), HSeqNode([hi_ph]))
        seq.children.insert(idx + 1, node)
        self._cursor_id = body_ph.node_id
    def insert_sum(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        body_ph = _ph()
        var_ph = _small_text("k")
        lo_ph = _ph(RENDER_TINY_FONT_SIZE)
        hi_ph = _ph(RENDER_TINY_FONT_SIZE)
        node = SumProdNode("sum", HSeqNode([body_ph]), HSeqNode([var_ph]),
                           HSeqNode([lo_ph]), HSeqNode([hi_ph]))
        seq.children.insert(idx + 1, node)
        self._cursor_id = body_ph.node_id
    def insert_product(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        body_ph = _ph()
        var_ph = _small_text("k")
        lo_ph = _ph(RENDER_TINY_FONT_SIZE)
        hi_ph = _ph(RENDER_TINY_FONT_SIZE)
        node = SumProdNode("prod", HSeqNode([body_ph]), HSeqNode([var_ph]),
                           HSeqNode([lo_ph]), HSeqNode([hi_ph]))
        seq.children.insert(idx + 1, node)
        self._cursor_id = body_ph.node_id
    def insert_func(self, name: str):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        fn_node = TextNode(name, RENDER_FONT_SIZE, False)
        body_ph = _ph()
        paren = ParenNode(HSeqNode([body_ph]))
        seq.children.insert(idx + 1, fn_node)
        seq.children.insert(idx + 2, paren)
        self._cursor_id = body_ph.node_id
    def delete_at_cursor(self):
        self._push_history()
        res = self._find_seq_with_cursor()
        if res is None:
            return
        seq, idx = res
        if isinstance(seq.children[idx], PlaceholderNode):
            if len(seq.children) > 1:
                seq.children.pop(idx)
                new_idx = max(0, idx - 1)
                self._cursor_id = seq.children[new_idx].node_id
            return
        if idx > 0:
            seq.children.pop(idx)
            self._cursor_id = seq.children[idx - 1].node_id
        elif len(seq.children) > 1:
            seq.children.pop(idx)
            self._cursor_id = seq.children[0].node_id
        else:
            seq.children[0] = _ph()
            self._cursor_id = seq.children[0].node_id
    def clear(self):
        self._push_history()
        ph = _ph()
        self._root = HSeqNode([ph])
        self._cursor_id = ph.node_id
        self._selected_ids.clear()
    def to_sympy_str(self) -> str:
        return self._root.to_sympy()
    def to_text(self) -> str:
        return self._root.to_text()
    def set_cursor_by_id(self, node_id: int):
        ids = self._ids_list()
        if node_id in ids:
            self._cursor_id = node_id