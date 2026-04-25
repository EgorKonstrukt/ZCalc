"""
Lorenz Attractor
=================
Integrates the Lorenz chaotic system in real time using RK4:
    dx/dt = sigma * (y - x)
    dy/dt = x * (rho - z) - y
    dz/dt = x*y - beta*z

Parameter sliders let you explore the parameter space live.
Two phase-portrait windows show XY and XZ projections.
The main chart shows x(t) over the rolling time window.
"""

SIGMA0  = 10.0
RHO0    = 28.0
BETA0   = 8.0 / 3.0
DT      = 0.005
TRAIL   = 2500
SPF     = 6
FPS     = 30
X0, Y0, Z0 = 1.0, 1.0, 1.5

api.add_param("sigma", lo=1.0,  hi=20.0, val=SIGMA0)
api.add_param("rho",   lo=1.0,  hi=50.0, val=RHO0)
api.add_param("beta",  lo=0.1,  hi=6.0,  val=BETA0)

win_xy = api.new_window("Lorenz — XY phase portrait")
win_xy.chart.setLabel("bottom", "x")
win_xy.chart.setLabel("left",   "y")
line_xy = win_xy.plot([], [], label="x vs y", color="#3498db", width=1)

win_xz = api.new_window("Lorenz — XZ phase portrait")
win_xz.chart.setLabel("bottom", "x")
win_xz.chart.setLabel("left",   "z")
line_xz = win_xz.plot([], [], label="x vs z", color="#e74c3c", width=1)

xt_line = api.plot([], [], label="x(t) Lorenz", color="#9b59b6", width=1)

pos = [X0, Y0, Z0]
xs, ys, zs, ts_buf = [], [], [], []
sim_t = [0.0]


def lorenz(x, y, z, sigma, rho, beta):
    return (
        sigma * (y - x),
        x * (rho - z) - y,
        x * y - beta * z,
    )


def rk4(x, y, z, dt, sigma, rho, beta):
    k1 = lorenz(x, y, z, sigma, rho, beta)
    k2 = lorenz(x + dt/2*k1[0], y + dt/2*k1[1], z + dt/2*k1[2], sigma, rho, beta)
    k3 = lorenz(x + dt/2*k2[0], y + dt/2*k2[1], z + dt/2*k2[2], sigma, rho, beta)
    k4 = lorenz(x + dt*k3[0],   y + dt*k3[1],   z + dt*k3[2],   sigma, rho, beta)
    nx = x + dt/6*(k1[0] + 2*k2[0] + 2*k3[0] + k4[0])
    ny = y + dt/6*(k1[1] + 2*k2[1] + 2*k3[1] + k4[1])
    nz = z + dt/6*(k1[2] + 2*k2[2] + 2*k3[2] + k4[2])
    return nx, ny, nz


def tick(elapsed):
    sigma = api.get_param("sigma", SIGMA0)
    rho   = api.get_param("rho",   RHO0)
    beta  = api.get_param("beta",  BETA0)

    for _ in range(SPF):
        pos[0], pos[1], pos[2] = rk4(pos[0], pos[1], pos[2], DT, sigma, rho, beta)
        xs.append(pos[0])
        ys.append(pos[1])
        zs.append(pos[2])
        ts_buf.append(sim_t[0])
        sim_t[0] += DT

    if len(xs) > TRAIL:
        excess = len(xs) - TRAIL
        del xs[:excess]
        del ys[:excess]
        del zs[:excess]
        del ts_buf[:excess]

    line_xy.setData(xs=xs, ys=ys)
    line_xz.setData(xs=xs, ys=zs)
    xt_line.setData(xs=ts_buf, ys=xs)


anim = api.animate(tick, fps=FPS)
api.status(
    f"Lorenz attractor  sigma={SIGMA0}  rho={RHO0}  beta={BETA0:.3f}  "
    "— drag sliders to explore chaos"
)