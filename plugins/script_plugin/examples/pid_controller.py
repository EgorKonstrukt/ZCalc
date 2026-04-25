"""
PID Controller Simulation
==========================
Simulates a first-order plant under PID control in real time.

Plant:      G(s) = K_p / (tau*s + 1)
Controller: u = Kp*e + Ki*integral(e) + Kd*(de/dt)

Use the Kp / Ki / Kd parameter sliders to tune the controller live.
A step disturbance is injected at t = DISTURBANCE_T seconds.
The simulation resets automatically at PERIOD seconds.
"""

K_PLANT       = 1.0
TAU_PLANT     = 1.0
SETPOINT      = 1.0
DT            = 0.02
PERIOD_S      = 18.0
DISTURBANCE_T = 9.0
DISTURBANCE_D = 0.4
MAX_HISTORY   = 900
FPS           = 30

api.add_param("Kp", lo=0.0, hi=10.0, val=2.0)
api.add_param("Ki", lo=0.0, hi=5.0,  val=0.5)
api.add_param("Kd", lo=0.0, hi=2.0,  val=0.1)

win = api.new_window("PID Controller Simulation")
win.chart.setLabel("bottom", "time (s)")
win.chart.setLabel("left",   "value")

l_out = win.plot([], [], label="plant output",    color="#3498db", width=2)
l_sp  = win.plot([], [], label="setpoint",        color="#2ecc71", width=1)
l_err = win.plot([], [], label="error e(t)",      color="#e74c3c", width=1)
l_u   = win.plot([], [], label="control u(t)",    color="#9b59b6", width=1)
l_dis = win.plot([], [], label="disturbance",     color="#f39c12", width=1)

state = dict(y=0.0, integral=0.0, prev_e=0.0, sim_t=0.0)
buf   = dict(ts=[], ys=[], es=[], us=[], sps=[], ds=[])


def reset():
    state.update(y=0.0, integral=0.0, prev_e=0.0, sim_t=0.0)
    for lst in buf.values():
        lst.clear()


def tick(elapsed):
    kp = api.get_param("Kp", 2.0)
    ki = api.get_param("Ki", 0.5)
    kd = api.get_param("Kd", 0.1)

    y, intg, pe, st = state["y"], state["integral"], state["prev_e"], state["sim_t"]

    e      = SETPOINT - y
    intg  += e * DT
    u      = kp * e + ki * intg + kd * (e - pe) / DT
    u      = max(-20.0, min(20.0, u))

    dist   = DISTURBANCE_D if st >= DISTURBANCE_T else 0.0
    dy     = (K_PLANT * (u + dist) - y) / TAU_PLANT
    y     += dy * DT
    st    += DT

    state.update(y=y, integral=intg, prev_e=e, sim_t=st)

    buf["ts"].append(st)
    buf["ys"].append(y)
    buf["es"].append(e)
    buf["us"].append(u)
    buf["sps"].append(SETPOINT)
    buf["ds"].append(dist)

    for lst in buf.values():
        if len(lst) > MAX_HISTORY:
            del lst[0]

    l_out.setData(xs=buf["ts"], ys=buf["ys"])
    l_sp.setData( xs=buf["ts"], ys=buf["sps"])
    l_err.setData(xs=buf["ts"], ys=buf["es"])
    l_u.setData(  xs=buf["ts"], ys=buf["us"])
    l_dis.setData(xs=buf["ts"], ys=buf["ds"])

    if st >= PERIOD_S:
        reset()


reset()
anim = api.animate(tick, fps=FPS)
api.status("PID sim running — adjust Kp/Ki/Kd sliders to tune the controller")