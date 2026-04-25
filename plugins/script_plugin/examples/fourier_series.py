"""
Fourier Series Approximation
==============================
Builds a square-wave approximation from N odd harmonics:
    f(x) = sum_{k=0}^{N-1} 4 / ((2k+1)*pi) * sin((2k+1)*x)

The 'terms' parameter slider controls how many harmonics are shown.
Each harmonic is also drawn individually in the new window.
The main chart shows the running sum overlaid on the target square wave.
"""

X_MIN   = -pi
X_MAX   =  pi
N_PTS   = 600
MAX_N   = 40
FPS     = 20

api.add_param("terms", lo=1.0, hi=float(MAX_N), val=5.0)

xs = api.linspace(X_MIN, X_MAX, N_PTS)

target_ys = [1.0 if x > 0.0 else (-1.0 if x < 0.0 else 0.0) for x in xs]

sum_line = api.plot(xs, target_ys, label="Fourier sum",  color="#3498db", width=2)
tgt_line = api.plot(xs, target_ys, label="square wave",  color="#e74c3c", width=1)

win = api.new_window("Fourier Harmonics")
win.chart.setLabel("bottom", "x")
win.chart.setLabel("left",   "amplitude")
harmonic_lines = {}


def build_sum(n_terms):
    result = [0.0] * N_PTS
    for k in range(int(n_terms)):
        m = 2 * k + 1
        c = 4.0 / (pi * m)
        for i, x in enumerate(xs):
            result[i] += c * sin(m * x)
    return result


def tick(elapsed):
    n = max(1, int(api.get_param("terms", 5.0)))

    approx = build_sum(n)
    sum_line.setData(xs=xs, ys=approx)

    active = set()
    for k in range(n):
        m = 2 * k + 1
        c = 4.0 / (pi * m)
        ys_k = [c * sin(m * x) for x in xs]
        key = f"n={m}"
        active.add(key)
        fade = max(0.15, 1.0 - k / (n + 1))
        r = int(52  + (1.0 - fade) * 180)
        g = int(152 * fade)
        b = int(219 * fade)
        color = f"#{r:02x}{g:02x}{b:02x}"
        if key not in harmonic_lines:
            harmonic_lines[key] = win.plot(xs, ys_k, label=key, color=color, width=1)
        else:
            harmonic_lines[key].setData(xs=xs, ys=ys_k)

    for key, line in list(harmonic_lines.items()):
        if key not in active:
            line.setData(xs=[], ys=[])

    if "sum" not in harmonic_lines:
        harmonic_lines["sum"] = win.plot(xs, approx, label="sum", color="#f39c12", width=2)
    else:
        harmonic_lines["sum"].setData(xs=xs, ys=approx)


anim = api.animate(tick, fps=FPS)
api.status("Fourier series — adjust 'terms' slider to add or remove harmonics")