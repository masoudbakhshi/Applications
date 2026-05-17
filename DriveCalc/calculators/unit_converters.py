"""Unit converter calculators: all four domains."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, engineering_note, show_info


# ── helpers ──────────────────────────────────────────────────────────────────

def _convert(value: float, from_factor: float, to_factor: float) -> float:
    """Convert via SI: value × from_factor / to_factor."""
    return value * from_factor / to_factor


def _select_unit(label: str, units: dict[str, float], key: str) -> tuple[float, str]:
    """Dropdown that returns (SI_factor, symbol)."""
    choice = st.selectbox(label, list(units.keys()), key=key)
    return units[choice], choice


# ── section render ────────────────────────────────────────────────────────────

def render():
    st.header("Unit Converters")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["⚡ Electrical", "🔄 Motor-Control", "🚗 Mechanical & Vehicle", "🌡️ Thermal"]
    )

    with tab1:
        _electrical_converters()
    with tab2:
        _motor_control_converters()
    with tab3:
        _mechanical_converters()
    with tab4:
        _thermal_converters()


# ── A. Electrical converters ──────────────────────────────────────────────────

def _electrical_converters():
    st.subheader("Electrical Quantity Converter")
    engineering_note(
        "Enter any value with its unit. The converter calculates all equivalent values in SI and common multiples."
    )

    quantities: dict[str, dict[str, float]] = {
        "Voltage [V]": {"V": 1, "mV": 1e-3, "kV": 1e3},
        "Current [A]": {"A": 1, "mA": 1e-3, "kA": 1e3},
        "Resistance [Ω]": {"Ω": 1, "mΩ": 1e-3, "kΩ": 1e3, "MΩ": 1e6},
        "Capacitance [F]": {"F": 1, "mF": 1e-3, "µF": 1e-6, "nF": 1e-9, "pF": 1e-12},
        "Inductance [H]": {"H": 1, "mH": 1e-3, "µH": 1e-6, "nH": 1e-9},
        "Power [W]": {"W": 1, "kW": 1e3, "MW": 1e6, "hp": 745.7},
        "Energy [J]": {"J": 1, "Wh": 3600, "kWh": 3.6e6, "MJ": 1e6},
        "Frequency [Hz]": {"Hz": 1, "kHz": 1e3, "MHz": 1e6},
        "Charge [C]": {"C": 1, "Ah": 3600, "mAh": 3.6},
        "Magnetic Flux [Wb]": {"Wb": 1, "mWb": 1e-3},
        "Flux Density [T]": {"T": 1, "mT": 1e-3, "Gauss": 1e-4},
        "Current Density [A/m²]": {"A/m²": 1, "A/mm²": 1e6},
    }

    qty_name = st.selectbox("Quantity", list(quantities.keys()), key="elec_qty")
    units = quantities[qty_name]
    col1, col2 = st.columns(2)
    with col1:
        value = st.number_input("Value", value=1.0, format="%g", key="elec_val")
    with col2:
        from_unit = st.selectbox("From unit", list(units.keys()), key="elec_from")

    si_value = value * units[from_unit]

    st.markdown("**Equivalent values:**")
    cols = st.columns(min(len(units), 4))
    for i, (sym, factor) in enumerate(units.items()):
        with cols[i % len(cols)]:
            st.metric(sym, f"{si_value / factor:.6g}")


# ── B. Motor-control converters ───────────────────────────────────────────────

def _motor_control_converters():
    st.subheader("Motor-Control Quantity Converter")

    choice = st.radio(
        "Conversion type",
        [
            "Speed: rpm ↔ rad/s",
            "Mech ↔ Elec speed / angle",
            "Phase current: RMS ↔ Peak",
            "Voltage: Line-Line RMS ↔ Phase Peak",
            "DC-link → Available phase voltage",
        ],
        key="mc_conv_choice",
    )

    if choice == "Speed: rpm ↔ rad/s":
        col1, col2 = st.columns(2)
        with col1:
            rpm = st.number_input("Speed [rpm]", value=3000.0, key="spd_rpm")
        with col2:
            rad_s = st.number_input("Speed [rad/s]", value=0.0, key="spd_rads",
                                    help="Leave 0 to compute from rpm; set nonzero to compute rpm")
        if rad_s == 0:
            result_rads = rpm * 2 * np.pi / 60
            result_rpm = rpm
        else:
            result_rads = rad_s
            result_rpm = rad_s * 60 / (2 * np.pi)
        c1, c2 = st.columns(2)
        c1.metric("ω [rad/s]", f"{result_rads:.4f}")
        c2.metric("n [rpm]", f"{result_rpm:.4f}")
        show_formula(r"\omega_m = \frac{2\pi\, n}{60}", "n in rpm, ω in rad/s")

    elif choice == "Mech ↔ Elec speed / angle":
        col1, col2 = st.columns(2)
        with col1:
            n_rpm = st.number_input("Mechanical speed [rpm]", value=3000.0, key="me_rpm")
            pole_pairs = st.number_input("Pole pairs p", value=4, min_value=1, step=1, key="me_pp")
            theta_m = st.number_input("Mechanical angle θ_m [deg]", value=45.0, key="me_th")
        with col2:
            omega_m = n_rpm * 2 * np.pi / 60
            omega_e = pole_pairs * omega_m
            f_e = omega_e / (2 * np.pi)
            theta_e = pole_pairs * theta_m

        st.markdown("**Results:**")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("ω_m [rad/s]", f"{omega_m:.4f}")
        r2.metric("ω_e [rad/s]", f"{omega_e:.4f}")
        r3.metric("f_e [Hz]", f"{f_e:.4f}")
        r4.metric("θ_e [deg]", f"{theta_e:.2f}")
        with st.expander("Formulas"):
            show_formula(r"\omega_e = p\,\omega_m \qquad f_e = \frac{\omega_e}{2\pi} \qquad \theta_e = p\,\theta_m")

    elif choice == "Phase current: RMS ↔ Peak":
        col1, col2 = st.columns(2)
        with col1:
            i_rms = st.number_input("Phase current RMS [A]", value=10.0, key="i_rms")
        with col2:
            i_pk = st.number_input("Phase current Peak [A]", value=0.0, key="i_pk",
                                   help="Leave 0 to compute from RMS")
        if i_pk == 0:
            pk = i_rms * np.sqrt(2)
            rms = i_rms
        else:
            pk = i_pk
            rms = i_pk / np.sqrt(2)
        c1, c2 = st.columns(2)
        c1.metric("I_RMS [A]", f"{rms:.4f}")
        c2.metric("I_peak [A]", f"{pk:.4f}")
        engineering_note(
            "dq-frame currents id, iq are <b>peak</b> values. "
            "Use I_peak = √2 · I_RMS for sinusoidal steady-state."
        )

    elif choice == "Voltage: Line-Line RMS ↔ Phase Peak":
        vll_rms = st.number_input("Line-Line RMS voltage V_LL [V]", value=400.0, key="v_ll")
        v_ph_peak = vll_rms * np.sqrt(2) / np.sqrt(3)
        v_ph_rms = vll_rms / np.sqrt(3)
        c1, c2, c3 = st.columns(3)
        c1.metric("V_LL_RMS [V]", f"{vll_rms:.3f}")
        c2.metric("V_phase_RMS [V]", f"{v_ph_rms:.3f}")
        c3.metric("V_phase_peak [V]", f"{v_ph_peak:.3f}")
        with st.expander("Formulas"):
            show_formula(
                r"V_{ph,peak} = \frac{\sqrt{2}}{\sqrt{3}}\,V_{LL,RMS} \qquad "
                r"V_{ph,RMS} = \frac{V_{LL,RMS}}{\sqrt{3}}"
            )

    elif choice == "DC-link → Available phase voltage":
        col1, col2 = st.columns(2)
        with col1:
            vdc = st.number_input("DC-link voltage V_dc [V]", value=400.0, key="vdc_conv")
        with col2:
            method = st.selectbox("Modulation", ["SPWM", "SVPWM"], key="vdc_mod")
        if method == "SPWM":
            v_ph_peak = vdc / 2
            note = "SPWM: V_phase_peak_max = V_dc / 2 (modulation index = 1)"
        else:
            v_ph_peak = vdc / np.sqrt(3)
            note = "SVPWM: V_phase_peak_max = V_dc / √3 ≈ 15.5% higher than SPWM"
        v_ph_rms = v_ph_peak / np.sqrt(2)
        v_ll_rms = v_ph_rms * np.sqrt(3)
        c1, c2, c3 = st.columns(3)
        c1.metric("V_phase_peak [V]", f"{v_ph_peak:.3f}")
        c2.metric("V_phase_RMS [V]", f"{v_ph_rms:.3f}")
        c3.metric("V_LL_RMS [V]", f"{v_ll_rms:.3f}")
        show_info(note)


# ── C. Mechanical & Vehicle converters ────────────────────────────────────────

def _mechanical_converters():
    st.subheader("Mechanical & Vehicle Converter")

    quantities: dict[str, dict[str, float]] = {
        "Torque [Nm]": {"Nm": 1, "lb·ft": 1.35582, "kgf·m": 9.80665},
        "Force [N]": {"N": 1, "kN": 1e3, "lbf": 4.44822, "kgf": 9.80665},
        "Speed [m/s]": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704},
        "Acceleration [m/s²]": {"m/s²": 1, "g (9.81 m/s²)": 9.80665},
        "Mass [kg]": {"kg": 1, "tonne": 1000, "lb": 0.453592},
        "Moment of inertia [kg·m²]": {"kg·m²": 1, "kg·cm²": 1e-4, "lb·ft²": 0.042140},
        "Pressure [Pa]": {"Pa": 1, "bar": 1e5, "psi": 6894.76, "kPa": 1e3},
        "Road grade": {"% grade": 1},  # handled separately
    }

    qty_name = st.selectbox("Quantity", list(quantities.keys()), key="mech_qty")

    if qty_name == "Road grade":
        grade_pct = st.number_input("Grade [%]", value=10.0, key="grade_pct")
        grade_deg = np.degrees(np.arctan(grade_pct / 100))
        grade_rad = np.radians(grade_deg)
        c1, c2, c3 = st.columns(3)
        c1.metric("Grade [%]", f"{grade_pct:.3f}")
        c2.metric("Grade [deg]", f"{grade_deg:.4f}")
        c3.metric("sin(α)", f"{np.sin(grade_rad):.5f}")
        engineering_note("sin(α) is used in road load calculations for grade force.")
        return

    units = quantities[qty_name]
    col1, col2 = st.columns(2)
    with col1:
        value = st.number_input("Value", value=1.0, format="%g", key="mech_val")
    with col2:
        from_unit = st.selectbox("From unit", list(units.keys()), key="mech_from")

    si_value = value * units[from_unit]
    st.markdown("**Equivalent values:**")
    cols = st.columns(min(len(units), 4))
    for i, (sym, factor) in enumerate(units.items()):
        with cols[i % len(cols)]:
            st.metric(sym, f"{si_value / factor:.6g}")


# ── D. Thermal converters ─────────────────────────────────────────────────────

def _thermal_converters():
    st.subheader("Thermal Converter")

    choice = st.radio("Conversion", ["Temperature", "Thermal resistance", "Coolant flow"], key="th_choice")

    if choice == "Temperature":
        col1, col2 = st.columns(2)
        with col1:
            val = st.number_input("Value", value=25.0, key="temp_val")
        with col2:
            unit = st.selectbox("From", ["°C", "K", "°F"], key="temp_unit")
        if unit == "°C":
            c = val;  k = val + 273.15;  f = val * 9 / 5 + 32
        elif unit == "K":
            k = val;  c = val - 273.15;  f = c * 9 / 5 + 32
        else:
            f = val;  c = (val - 32) * 5 / 9;  k = c + 273.15
        r1, r2, r3 = st.columns(3)
        r1.metric("°C", f"{c:.3f}")
        r2.metric("K", f"{k:.3f}")
        r3.metric("°F", f"{f:.3f}")

    elif choice == "Thermal resistance":
        val = st.number_input("Thermal resistance value", value=1.0, key="rth_val")
        units = {"K/W": 1, "°C/W": 1}
        st.info("K/W and °C/W are numerically identical (temperature difference, not absolute).")
        st.metric("K/W = °C/W", f"{val:.6g}")

    elif choice == "Coolant flow":
        st.markdown("Convert volumetric flow to mass flow rate.")
        col1, col2 = st.columns(2)
        with col1:
            flow_lpm = st.number_input("Flow rate [L/min]", value=10.0, key="flow_lpm")
        with col2:
            density = st.number_input("Coolant density [kg/L]", value=1.06,
                                      help="Water ≈ 1.0, 50/50 glycol ≈ 1.06", key="flow_rho")
        mass_flow = flow_lpm * density / 60  # kg/s
        vol_m3s = flow_lpm / 60 / 1000       # m³/s
        c1, c2 = st.columns(2)
        c1.metric("Mass flow [kg/s]", f"{mass_flow:.4f}")
        c2.metric("Vol. flow [m³/s]", f"{vol_m3s:.6g}")
        show_formula(r"\dot{m} = \dot{V}\,\rho", "Flow × density → mass flow rate")
