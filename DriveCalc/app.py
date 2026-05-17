"""
DriveCalc: Electrical, Motor Control & Power Electronics Calculator
Professional engineering toolbox for motor control, power electronics,
embedded firmware, thermal analysis, and EV propulsion.
"""
import sys
import os

# Ensure the DriveCalc directory is on the path so imports work whether
# the app is launched from the repo root (Streamlit Cloud) or locally.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# Page configuration: must be first Streamlit call
st.set_page_config(
    page_title="DriveCalc",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "DriveCalc: Professional engineering calculator for motor control, "
                 "power electronics, and EV propulsion.\n"
                 "Developed by Masoud Bakhshi.\n"
                 "Built with Python & Streamlit.",
    },
)

# Custom CSS
st.markdown(
    """
    <style>
    /* Sidebar */
    [data-testid="stSidebar"] { background: #1a1f36; }
    [data-testid="stSidebar"] * { color: #e8eaf6 !important; }
    [data-testid="stSidebar"] .stRadio > label { font-size: 0.82rem; }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1565c0;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem;
        color: #555;
    }

    /* Section headers */
    h1 { color: #1a237e; }
    h2 { color: #283593; border-bottom: 2px solid #e8eaf6; padding-bottom: 6px; }
    h3 { color: #3949ab; }

    /* Streamlit tabs */
    .stTabs [data-baseweb="tab"] { font-size: 0.85rem; }

    /* Footer */
    .footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: #f5f5f5; border-top: 1px solid #ddd;
        padding: 4px 16px; font-size: 0.75rem; color: #888;
        text-align: center; z-index: 100;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Lazy imports: only load the selected module to keep startup fast
SECTIONS = {
    "🏠 Home": None,
    "🔄 Unit Converters": "unit_converters",
    "⚙️ Motor Control": "motor_control",
    "🔌 Power Electronics": "power_electronics",
    "🖥️ Embedded / PWM": "embedded_pwm",
    "🌡️ Thermal & Loss": "thermal",
    "🚗 EV / Vehicle": "vehicle",
    "⚡ General Electrical": "electrical",
    "📚 Formula Reference": None,
}


def render_home():
    st.title("⚡ DriveCalc")
    st.markdown(
        "### Professional Engineering Calculator: Motor Control, Power Electronics & EV Propulsion"
    )
    st.markdown(
        "<p style='color:#555;font-size:0.9rem;margin-top:-8px'>"
        "Developed by <strong>Masoud Bakhshi</strong></p>",
        unsafe_allow_html=True,
    )
    st.divider()

    cols = st.columns(3)
    with cols[0]:
        st.markdown("""
**🔄 Unit Converters**
- Electrical, motor-control, mechanical, thermal quantities
- rpm ↔ rad/s, RMS ↔ Peak, V_LL ↔ V_phase

**⚙️ Motor Control**
- PMSM/IPMSM & EESM torque models
- dq voltage, field weakening voltage margin
- PI current controller gain design
- Torque-speed envelope plot
""")
    with cols[1]:
        st.markdown("""
**🔌 Power Electronics**
- Three-phase inverter voltage (SPWM / SVPWM)
- SVPWM sector & duty-cycle calculation + hexagon plot
- Buck & Boost converter (CCM)
- DC-link capacitor ripple estimator

**🖥️ Embedded / PWM**
- PWM timer register (TBPRD / ARR) calculator
- Minimum pulse width & safe duty range
- Dead-time voltage error estimator
- Discrete PI (Tustin / Euler) coefficients
""")
    with cols[2]:
        st.markdown("""
**🌡️ Thermal & Loss**
- Motor copper (I²R) loss: RMS and dq convention
- Thermal rise: steady-state & transient with plot
- Cable voltage drop & I²R loss
- Semiconductor loss (conduction + switching)

**🚗 EV / Vehicle**
- Battery power & current (motoring & regen)
- Tractive force & vehicle acceleration
- Road load decomposition (rolling + aero + grade)
- Regen braking energy recovery
- 0–100 km/h performance simulation
""")

    st.divider()
    st.markdown("""
**⚡ General Electrical**: Ohm's law, RC/RL/RLC circuits, power factor, impedance, filter design

**📚 Formula Reference**: All formulas used in the tool with derivations and engineering notes

---
> **Usage:** Select a section from the left sidebar.
> All inputs use SI units by default. Unit conversions are built into each calculator.
> Formulas and engineering notes are available by expanding the ▾ section beneath each calculator.
""")

    st.info(
        "💡 **Tip:** Each calculator shows its formula, assumptions, and common engineering mistakes "
        "in the expandable notes section. Read these before trusting the output for critical design work."
    )


def render_formula_reference():
    st.header("📚 Engineering Formula Reference")
    st.markdown("Quick reference for all formulas used in DriveCalc.")

    sections = {
        "Motor Speed & Angle Relationships": r"""
$$\omega_m = \frac{2\pi n}{60} \qquad \omega_e = p\,\omega_m \qquad f_e = \frac{\omega_e}{2\pi} \qquad \theta_e = p\,\theta_m$$

- $n$: mechanical speed [rpm], $\omega_m$: mechanical speed [rad/s]
- $p$: pole pairs, $\omega_e$: electrical speed [rad/s]
- $f_e$: electrical frequency [Hz], $T_e = 1/f_e$: electrical period
""",
        "Torque & Power": r"""
$$P = T\,\omega_m \qquad P_{kW} = \frac{T_{Nm}\cdot n_{rpm}}{9549}$$

- $P$: mechanical power [W], $T$: torque [Nm], $\omega_m$: rad/s
""",
        "PMSM/IPMSM Electromagnetic Torque": r"""
$$T_e = \frac{3}{2}\,p\,\left[\psi_f\,i_q + (L_d - L_q)\,i_d\,i_q\right]$$

- $\psi_f$: permanent magnet flux linkage [Wb]
- $i_d, i_q$: d/q axis currents: **peak values** (not RMS)
- First term: magnet torque. Second term: reluctance torque (IPMSM: $L_q > L_d$)
""",
        "EESM Electromagnetic Torque": r"""
$$\psi_f = M_f\,I_f \qquad T_e = \frac{3}{2}\,p\,\left[M_f\,I_f\,i_q + (L_d - L_q)\,i_d\,i_q\right]$$

- $M_f$: stator-rotor mutual inductance [H], $I_f$: DC field current [A]
""",
        "dq Voltage Equations (steady-state + transient)": r"""
$$v_d = R_s\,i_d + L_d\,\frac{di_d}{dt} - \omega_e\,L_q\,i_q$$

$$v_q = R_s\,i_q + L_q\,\frac{di_q}{dt} + \omega_e\,L_d\,i_d + \omega_e\,\psi_f$$

$$|V_{dq}| = \sqrt{v_d^2 + v_q^2} \leq V_{max}$$
""",
        "Inverter Voltage Limits": r"""
$$V_{phase,peak,max} = \begin{cases} V_{dc}/2 & \text{SPWM} \\ V_{dc}/\sqrt{3} & \text{SVPWM} \end{cases}$$

SVPWM advantage: $2/\sqrt{3} \approx 1.155$ (+15.5% voltage utilization)
""",
        "PI Current Controller Gains (bandwidth method)": r"""
$$K_{p,d} = L_d\,\omega_c \qquad K_{i,d} = R_s\,\omega_c \qquad \omega_c = 2\pi f_c$$

$$K_{p,q} = L_q\,\omega_c \qquad K_{i,q} = R_s\,\omega_c$$

Rules: $f_c < f_{sw}/10$. Total delay $\approx 1.5\,T_s$ reduces phase margin.
""",
        "Discrete PI (Tustin / Bilinear)": r"""
$$b_0 = K_p + K_i\,\frac{T_s}{2} \qquad b_1 = -K_p + K_i\,\frac{T_s}{2}$$

$$u[k] = u[k-1] + b_0\,e[k] + b_1\,e[k-1]$$
""",
        "SVPWM Duty Times": r"""
$$T_1 = \sqrt{3}\,\frac{T_{sw}\,|V^*|}{V_{dc}}\sin\!\left(\frac{\pi}{3}-\theta_s\right)$$

$$T_2 = \sqrt{3}\,\frac{T_{sw}\,|V^*|}{V_{dc}}\sin\theta_s \qquad T_0 = T_{sw} - T_1 - T_2$$
""",
        "PWM Timer Registers": r"""
$$\text{TBPRD} = \frac{f_{clk}}{f_{pwm}} - 1 \quad\text{(up-count)} \qquad \text{TBPRD} = \frac{f_{clk}}{2\,f_{pwm}} \quad\text{(up-down)}$$
""",
        "Dead-Time Voltage Error": r"""
$$\Delta V \approx V_{dc}\,\frac{t_{dead}}{T_{sw}}$$

Creates low-order voltage harmonics: compensate by adjusting duty based on current direction.
""",
        "Buck Converter (CCM)": r"""
$$V_{out} = D\,V_{in} \qquad \Delta I_L = \frac{(V_{in}-V_{out})\,D}{L\,f_{sw}} \qquad \Delta V_C = \frac{\Delta I_L}{8\,C\,f_{sw}}$$
""",
        "Boost Converter (CCM)": r"""
$$V_{out} = \frac{V_{in}}{1-D} \qquad \Delta I_L = \frac{V_{in}\,D}{L\,f_{sw}} \qquad \Delta V_{out} = \frac{I_{out}\,D}{C\,f_{sw}}$$
""",
        "Copper Loss": r"""
$$P_{cu} = 3\,I_{a,rms}^2\,R_s = \frac{3}{2}\,R_s\,(i_d^2 + i_q^2)$$

$i_d, i_q$ are peak values. Temperature correction: $R_s(T) = R_{s,20}[1+\alpha(T-20)]$
""",
        "Thermal Rise": r"""
$$T_{ss} = T_{amb} + P\,R_{th} \qquad T(t) = T_{amb} + \Delta T\left(1-e^{-t/\tau}\right) \qquad \tau = R_{th}\,C_{th}$$
""",
        "Cable Resistance & Loss": r"""
$$R = \frac{\rho\,l}{A} \qquad \Delta V = I\,R \qquad P_{loss} = I^2\,R$$

$$\rho(T) = \rho_{20}\bigl[1+\alpha(T-20)\bigr]$$

Cu: $\rho_{20}=1.72\times10^{-8}\ \Omega\text{m}$, Al: $\rho_{20}=2.82\times10^{-8}\ \Omega\text{m}$
""",
        "Road Load & Vehicle": r"""
$$F_{roll} = m\,g\,C_{rr}\cos\alpha \quad F_{aero} = \tfrac{1}{2}\rho\,C_d\,A\,v^2 \quad F_{grade} = m\,g\sin\alpha$$

$$T_{wheel} = T_{motor}\,i_{gear}\,\eta_{dl} \qquad F_t = T_{wheel}/r_{wheel} \qquad a = (F_t - F_{road})/m$$
""",
        "ADC Scaling": r"""
$$\text{LSB} = \frac{V_{ref}}{2^N} \qquad \text{Physical} = \frac{V_{meas} - V_{offset}}{G_{sensor}}$$
""",
        "Q-Format Fixed-Point": r"""
$$\text{Resolution} = 2^{-Q} \qquad \text{Scale factor} = 2^Q$$

Signed Q15: range $[-1, 1-2^{-15}]$, resolution $3.05\times10^{-5}$
""",
    }

    for title, content in sections.items():
        with st.expander(title):
            st.markdown(content)


def main():
    # Sidebar navigation
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align:center;color:#e8eaf6;margin:0 0 4px 0'>⚡ DriveCalc</h2>"
            "<p style='text-align:center;font-size:0.72rem;color:#9fa8da;margin:0 0 16px 0'>"
            "Motor Control & Power Electronics</p>",
            unsafe_allow_html=True,
        )
        selected = st.radio("Navigate to:", list(SECTIONS.keys()), key="nav",
                            label_visibility="collapsed")
        st.divider()
        st.markdown(
            "<p style='font-size:0.72rem;color:#7986cb;text-align:center'>"
            "All formulas use SI units.<br>"
            "Expand ▾ for derivations.</p>"
            "<p style='font-size:0.78rem;color:#c5cae9;text-align:center;"
            "margin-top:8px;border-top:1px solid #2e3560;padding-top:8px'>"
            "Developed by<br>"
            "<strong style='color:#e8eaf6;font-size:0.85rem'>Masoud Bakhshi</strong></p>"
            "<p style='font-size:0.68rem;color:#5c6bc0;text-align:center;margin-top:2px'>"
            "v1.0 · Python + Streamlit</p>",
            unsafe_allow_html=True,
        )

    # Route to section
    module_name = SECTIONS[selected]

    if selected == "🏠 Home":
        render_home()
    elif selected == "📚 Formula Reference":
        render_formula_reference()
    elif module_name == "unit_converters":
        from calculators import unit_converters
        unit_converters.render()
    elif module_name == "motor_control":
        from calculators import motor_control
        motor_control.render()
    elif module_name == "power_electronics":
        from calculators import power_electronics
        power_electronics.render()
    elif module_name == "embedded_pwm":
        from calculators import embedded_pwm
        embedded_pwm.render()
    elif module_name == "thermal":
        from calculators import thermal
        thermal.render()
    elif module_name == "vehicle":
        from calculators import vehicle
        vehicle.render()
    elif module_name == "electrical":
        from calculators import electrical
        electrical.render()

    # Footer
    st.markdown(
        "<div class='footer'>DriveCalc: Developed by <strong>Masoud Bakhshi</strong> &nbsp;·&nbsp; "
        "All results are for educational and design support only. "
        "Verify critical values with measurements and certified analysis.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
