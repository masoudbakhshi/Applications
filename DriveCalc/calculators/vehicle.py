"""EV / Vehicle propulsion calculators: battery, tractive force, road load, regen."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, require_non_negative, collect_errors
import plotly.graph_objects as go


def render():
    st.header("EV / Vehicle Propulsion Calculators")
    tabs = st.tabs([
        "🔋 Battery Power & Current",
        "⚙️ Tractive Force",
        "🛣️ Road Load",
        "🔄 Regen Braking",
        "🏎️ Performance Estimator",
    ])
    with tabs[0]: _battery()
    with tabs[1]: _tractive_force()
    with tabs[2]: _road_load()
    with tabs[3]: _regen()
    with tabs[4]: _performance()


# ── Battery ───────────────────────────────────────────────────────────────────

def _battery():
    st.subheader("Battery Power & Current Calculator")
    engineering_note(
        "Calculates battery current demand for motoring and regenerative braking. "
        "Includes drivetrain efficiency. Battery internal resistance losses are not modelled here."
    )
    col1, col2 = st.columns(2)
    with col1:
        V_bat = st.number_input("Battery voltage V_bat [V]", value=400.0, min_value=0.0,
                                key="bat_v")
        P_mech = st.number_input("Required mechanical power P_mech [kW]", value=50.0,
                                 key="bat_p")
        eta = st.slider("Drivetrain efficiency η", 0.5, 1.0, 0.92, 0.01, key="bat_eta")
        mode = st.radio("Operating mode", ["Motoring (drive)", "Regen (braking)"], key="bat_mode")
        I_limit = st.number_input("Battery current limit I_max [A]", value=300.0, min_value=0.0,
                                  key="bat_ilim")

    P_mech_w = P_mech * 1e3
    if mode == "Motoring (drive)":
        P_bat = P_mech_w / eta
        I_bat = P_bat / V_bat if V_bat > 0 else 0
        label = "Battery (discharge) current [A]"
    else:
        P_bat = P_mech_w * eta
        I_bat = P_bat / V_bat if V_bat > 0 else 0
        label = "Battery (charge) current [A]"

    with col2:
        st.metric("Battery power P_bat [kW]", f"{P_bat/1000:.3f}")
        st.metric(label, f"{I_bat:.3f}")
        st.metric("Power loss in drivetrain [kW]", f"{abs(P_mech_w - P_bat)/1000:.3f}")

    if I_bat > I_limit:
        st.error(f"🔴 Battery current ({I_bat:.1f} A) exceeds limit ({I_limit:.1f} A). "
                 f"Reduce power demand to ≤ {I_limit * V_bat * eta / 1000:.1f} kW mechanical.")
    else:
        st.success(f"✅ Current OK ({I_bat:.1f} / {I_limit:.1f} A)")

    with st.expander("Formulas"):
        show_formula(
            r"P_{bat} = \frac{P_{mech}}{\eta} \;(\text{motoring}) \qquad "
            r"P_{bat} = P_{regen}\,\eta \;(\text{regen})"
        )
        show_formula(r"I_{bat} = \frac{P_{bat}}{V_{bat}}")
        engineering_note(
            "Battery internal resistance causes a voltage sag: V_terminal = V_OCV - I·R_int. "
            "At high current, actual terminal voltage is lower than nominal. "
            "Use a more detailed battery model (Thevenin equivalent) for accurate SoC-based simulation."
        )


# ── Tractive Force ────────────────────────────────────────────────────────────

def _tractive_force():
    st.subheader("Tractive Force & Vehicle Acceleration Calculator")
    engineering_note(
        "Calculates wheel torque, tractive force at tire contact patch, and vehicle acceleration "
        "from motor torque, gear ratio, and vehicle mass."
    )
    col1, col2 = st.columns(2)
    with col1:
        T_motor = st.number_input("Motor torque T_motor [Nm]", value=200.0, min_value=0.0,
                                  key="tf_tm")
        gear_ratio = st.number_input("Total gear ratio (motor→wheel)", value=9.0, min_value=0.0,
                                     key="tf_gr")
        eta_dl = st.slider("Driveline efficiency η_dl", 0.7, 1.0, 0.95, 0.01, key="tf_eta")
        r_wheel = st.number_input("Wheel radius r [m]", value=0.32, min_value=0.0,
                                  format="%.4f", key="tf_rw")
        m_veh = st.number_input("Vehicle mass m [kg]", value=2000.0, min_value=0.0, key="tf_m")
        F_road = st.number_input("Road resistance force F_road [N] (optional)", value=500.0,
                                 min_value=0.0, key="tf_fr",
                                 help="Rolling + grade + aero at current speed")

    errs = collect_errors(require_positive(r_wheel, "Wheel radius"), require_positive(m_veh, "Mass"))
    if errs:
        for e in errs: show_warning(e)
        return

    T_wheel = T_motor * gear_ratio * eta_dl
    F_tractive = T_wheel / r_wheel
    F_net = F_tractive - F_road
    a = F_net / m_veh

    with col2:
        st.metric("T_wheel [Nm]", f"{T_wheel:.2f}")
        st.metric("Tractive force F_t [N]", f"{F_tractive:.2f}")
        st.metric("Net force F_net [N]", f"{F_net:.2f}")
        st.metric("Acceleration a [m/s²]", f"{a:.4f}")
        st.metric("Acceleration [g]", f"{a/9.81:.4f}")

    with st.expander("Formulas"):
        show_formula(
            r"T_{wheel} = T_{motor}\,i_{gear}\,\eta_{dl} \qquad "
            r"F_t = \frac{T_{wheel}}{r_{wheel}} \qquad "
            r"a = \frac{F_t - F_{road}}{m}"
        )
        engineering_note(
            "Wheel radius changes ≈ 0.5–1% with load (tire deflection). "
            "For accurate acceleration: also include rotational inertia of drivetrain "
            "(J_eff = J_motor·i²  + J_wheel). "
            "Traction limit: F_t ≤ μ·m·g where μ ≈ 0.8–1.2 on dry asphalt."
        )


# ── Road Load ─────────────────────────────────────────────────────────────────

def _road_load():
    st.subheader("Road Load Calculator")
    engineering_note(
        "Decomposes total road resistance into rolling, aerodynamic, and grade components. "
        "Useful for duty-cycle analysis and power sizing."
    )
    col1, col2 = st.columns(2)
    with col1:
        m = st.number_input("Vehicle mass m [kg]", value=2000.0, min_value=0.0, key="rl_m")
        v_kmh = st.number_input("Speed v [km/h]", value=100.0, min_value=0.0, key="rl_v")
        grade_pct = st.number_input("Road grade [%]", value=0.0, key="rl_grade")
        Crr = st.number_input("Rolling resistance coeff. C_rr", value=0.012, min_value=0.0,
                              format="%.5f", key="rl_crr",
                              help="0.008–0.012 for car tires, 0.004–0.008 for truck")
        Cd = st.number_input("Drag coefficient C_d", value=0.28, min_value=0.0,
                             format="%.4f", key="rl_cd")
        A_front = st.number_input("Frontal area A [m²]", value=2.2, min_value=0.0, key="rl_A")
        rho_air = st.number_input("Air density ρ [kg/m³]", value=1.225, min_value=0.0,
                                  key="rl_rho")

    v = v_kmh / 3.6
    alpha = np.arctan(grade_pct / 100)
    g = 9.81

    F_roll = m * g * Crr * np.cos(alpha)
    F_aero = 0.5 * rho_air * Cd * A_front * v**2
    F_grade = m * g * np.sin(alpha)
    F_total = F_roll + F_aero + F_grade
    P_wheel = F_total * v / 1000  # kW

    with col2:
        st.metric("F_rolling [N]", f"{F_roll:.2f}")
        st.metric("F_aero [N]", f"{F_aero:.2f}")
        st.metric("F_grade [N]", f"{F_grade:.2f}")
        st.metric("F_total [N]", f"{F_total:.2f}")
        st.metric("Required wheel power P [kW]", f"{P_wheel:.3f}")

    # Pie chart of force components
    labels = ["Rolling", "Aerodynamic", "Grade"]
    values = [max(F_roll, 0), max(F_aero, 0), max(F_grade, 0)]
    if sum(values) > 0:
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4))
        fig.update_layout(title="Road Load Breakdown", paper_bgcolor="white",
                          font=dict(family="Arial"))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Formulas"):
        show_formula(
            r"F_{roll} = m\,g\,C_{rr}\cos\alpha \qquad "
            r"F_{aero} = \tfrac{1}{2}\rho\,C_d\,A\,v^2 \qquad "
            r"F_{grade} = m\,g\sin\alpha"
        )
        show_formula(r"P_{wheel} = F_{total}\cdot v")
        engineering_note(
            "Aerodynamic drag scales as v²: doubles the speed → 4× aero power. "
            "At highway speed, aero typically dominates. "
            "At low speed on steep grade, grade force dominates."
        )


# ── Regen Braking ─────────────────────────────────────────────────────────────

def _regen():
    st.subheader("Regenerative Braking Calculator")
    engineering_note(
        "Estimates energy recovered during deceleration. "
        "Actual regen is limited by battery charge rate, wheel slip, and brake blending strategy."
    )
    col1, col2 = st.columns(2)
    with col1:
        m = st.number_input("Vehicle mass m [kg]", value=2000.0, min_value=0.0, key="rg_m")
        v_start = st.number_input("Initial speed v1 [km/h]", value=100.0, min_value=0.0, key="rg_v1")
        v_end = st.number_input("Final speed v2 [km/h]", value=0.0, min_value=0.0, key="rg_v2")
        eta_regen = st.slider("Regen efficiency η_regen", 0.5, 1.0, 0.80, 0.01, key="rg_eta",
                              help="Combined motor + inverter + battery efficiency")
        regen_fraction = st.slider("Regen brake fraction (1=all brake force)", 0.0, 1.0, 0.7, 0.05,
                                   key="rg_frac",
                                   help="Fraction of braking handled by motor vs. friction brakes")

    v1 = v_start / 3.6
    v2 = v_end / 3.6
    KE_total = 0.5 * m * (v1**2 - v2**2)
    KE_regen_input = KE_total * regen_fraction
    E_recovered = KE_regen_input * eta_regen
    E_lost_friction = KE_total * (1 - regen_fraction)
    E_lost_heat = KE_regen_input * (1 - eta_regen)

    with col2:
        st.metric("Total kinetic energy [kJ]", f"{KE_total/1000:.4f}")
        st.metric("Energy into regen system [kJ]", f"{KE_regen_input/1000:.4f}")
        st.metric("Energy recovered to battery [kJ]", f"{E_recovered/1000:.4f}")
        st.metric("Energy recovered [Wh]", f"{E_recovered/3600:.4f}")
        st.metric("Lost to friction brakes [kJ]", f"{E_lost_friction/1000:.4f}")
        st.metric("Lost as heat in regen system [kJ]", f"{E_lost_heat/1000:.4f}")
        if KE_total > 0:
            overall_eff = E_recovered / KE_total * 100
            st.metric("Overall recovery efficiency [%]", f"{overall_eff:.2f}")

    with st.expander("Formulas"):
        show_formula(r"E_k = \frac{1}{2}m(v_1^2 - v_2^2)")
        show_formula(r"E_{recovered} = f_{regen}\,\eta_{regen}\,E_k")
        engineering_note(
            "Typical regen efficiency chain: motor (~96%) × inverter (~98%) × battery charging (~98%) ≈ 92%. "
            "High regen fraction improves range but may exceed battery charge rate limits (C-rate). "
            "Optimal regen strategy uses all-wheel drive with front/rear torque vectoring."
        )


# ── Performance Estimator ─────────────────────────────────────────────────────

def _performance():
    st.subheader("EV 0–100 km/h Performance Estimator")
    engineering_note(
        "Rough 0–100 km/h time estimate based on peak motor torque, gear ratio, and vehicle mass. "
        "Assumes constant peak torque until base speed, then constant power. "
        "Does not model tire traction limits or shifting."
    )
    col1, col2 = st.columns(2)
    with col1:
        T_peak = st.number_input("Peak motor torque [Nm]", value=350.0, min_value=0.0, key="perf_t")
        gear_ratio = st.number_input("Gear ratio", value=9.0, min_value=0.0, key="perf_gr")
        r_wheel = st.number_input("Wheel radius [m]", value=0.32, min_value=0.01, key="perf_rw")
        eta_dl = st.slider("Driveline efficiency", 0.7, 1.0, 0.94, 0.01, key="perf_eta")
        m = st.number_input("Vehicle mass [kg]", value=2000.0, min_value=0.0, key="perf_m")
        Crr = st.number_input("C_rr", value=0.012, format="%.4f", key="perf_crr")
        Cd = st.number_input("C_d", value=0.28, format="%.4f", key="perf_cd")
        A = st.number_input("Frontal area [m²]", value=2.2, key="perf_A")

    F_peak = T_peak * gear_ratio * eta_dl / r_wheel
    rho = 1.225
    g = 9.81
    dt = 0.01  # s integration step
    v = 0.0
    t = 0.0
    v_target = 100 / 3.6
    times, speeds = [0], [0]

    P_peak = T_peak * (6000 * 2 * np.pi / 60)  # assume base speed at 6000 rpm nominal

    while v < v_target and t < 60:
        F_road = m * g * Crr + 0.5 * rho * Cd * A * v**2
        F_t = min(F_peak, P_peak / max(v, 0.1))  # current/power limit
        F_net = F_t - F_road
        a = F_net / m
        v += a * dt
        t += dt
        times.append(t)
        speeds.append(v * 3.6)

    with col2:
        if v >= v_target:
            st.metric("0–100 km/h time [s]", f"{t:.2f}")
        else:
            show_warning("Could not reach 100 km/h within 60 s with given parameters.")
        st.metric("Peak tractive force [kN]", f"{F_peak/1000:.3f}")
        st.metric("Peak acceleration [g]", f"{F_peak/m/g:.3f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=speeds, mode="lines", name="Speed [km/h]",
                             line=dict(color="#1f77b4", width=2)))
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100 km/h")
    fig.update_layout(title="Acceleration Run (estimate)",
                      xaxis_title="Time [s]", yaxis_title="Speed [km/h]",
                      paper_bgcolor="white", plot_bgcolor="#f8f9fa",
                      font=dict(family="Arial"))
    st.plotly_chart(fig, use_container_width=True)
    engineering_note(
        "This simulation uses Euler integration with constant driveline model. "
        "Real performance depends on tire traction (μ·m·g ≈ 16–20 kN for a 2-tonne car), "
        "state-of-charge, temperature, and control strategy."
    )
