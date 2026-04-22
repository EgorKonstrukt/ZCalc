import math

APP_NAME = "ZCalc"
APP_VERSION = "1.0.0"

COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#c0392b", "#e91e63", "#00bcd4",
]

PRESETS = {
    "sin(x)":        ("sin(x)",                          None,        None),
    "cos(x)":        ("cos(x)",                          None,        None),
    "tan(x)":        ("tan(x)",                          None,        None),
    "x^2":           ("x**2",                            None,        None),
    "x^3":           ("x**3",                            None,        None),
    "sqrt(x)":       ("sqrt(x)",                         None,        None),
    "exp(x)":        ("exp(x)",                          None,        None),
    "ln(x)":         ("log(x)",                          None,        None),
    "abs(x)":        ("abs(x)",                          None,        None),
    "1/x":           ("1/x",                             None,        None),
    "sin(x)/x":      ("sin(x)/x if x!=0 else 1",         None,        None),
    "Gauss":         ("exp(-x**2/2)",                    None,        None),
    "Sawtooth":      ("sawtooth(x)",                     None,        None),
    "Square":        ("square(x)",                       None,        None),
    "Lissajous":     ("sin(3*t)",                        "parametric","cos(2*t)"),
    "Circle":        ("cos(t)",                          "parametric","sin(t)"),
    "Spiral":        ("t*cos(t)",                        "parametric","t*sin(t)"),
    "Heart":         ("16*sin(t)**3",                    "parametric","13*cos(t)-5*cos(2*t)-2*cos(3*t)-cos(4*t)"),
    "Butterfly":     ("sin(t)*(exp(cos(t))-2*cos(4*t))", "parametric","cos(t)*(exp(cos(t))-2*cos(4*t))"),
    "Rose cos(3t)":  ("cos(3*t)*cos(t)",                 "parametric","cos(3*t)*sin(t)"),
    "Hypotrochoid":  ("3*cos(t)+cos(3*t)*0.5",           "parametric","3*sin(t)-sin(3*t)*0.5"),
    "Astroid":       ("cos(t)**3",                        "parametric","sin(t)**3"),
}

SAFE_NS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
    "log2": math.log2, "log10": math.log10,
    "abs": abs, "floor": math.floor, "ceil": math.ceil,
    "round": round, "pi": math.pi, "e": math.e, "inf": math.inf,
    "sign":     lambda x: (1 if x > 0 else -1 if x < 0 else 0),
    "frac":     lambda x: x - math.floor(x),
    "clamp":    lambda x, a, b: max(a, min(b, x)),
    "mod":      math.fmod,
    "hypot":    math.hypot,
    "factorial":math.factorial,
    "degrees":  math.degrees,
    "radians":  math.radians,
    "sigmoid":  lambda x: 1 / (1 + math.exp(-x)),
    "step":     lambda x: 1.0 if x >= 0 else 0.0,
    "rect":     lambda x: 1.0 if abs(x) <= 0.5 else 0.0,
    "tri":      lambda x: max(0.0, 1.0 - abs(x)),
    "sawtooth": lambda x: 2*(x/(2*math.pi) - math.floor(0.5 + x/(2*math.pi))),
    "square":   lambda x: 1.0 if math.sin(x) >= 0 else -1.0,
    "sinc":     lambda x: math.sin(math.pi*x)/(math.pi*x) if x != 0 else 1.0,
    "gaussian": lambda x: math.exp(-x*x/2),
    "lerp":     lambda a, b, t: a + (b - a)*t,
    "__builtins__": {},
}

DEFAULT_XMIN   = -10.0
DEFAULT_XMAX   =  10.0
DEFAULT_YMIN   =  -8.0
DEFAULT_YMAX   =   8.0
DEFAULT_TMIN   = -2 * math.pi
DEFAULT_TMAX   =  2 * math.pi
DEFAULT_SAMPLES = 800
ANIM_INTERVAL_MS = 30
ANIM_STEP = 0.06
DERIV_H = 1e-5
INFINITE_MARGIN = 5.0