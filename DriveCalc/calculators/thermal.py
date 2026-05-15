"""Thermal and loss calculators: copper loss, cable loss, thermal rise, semiconductor losses."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, require_non_negative, collect_errors
from utils.plotting import thermal_transient_plot


def render():
    st.header("Thermal & Loss Calculators")
    tabs = st.tabs([
        "🔥 Copper Loss",
        "🌡️ Thermal Rise",
        "🔌 Cable Voltage Drop",
        "💡 Semiconductor Loss",
        "📉 Thermal Derating",
    ])
    with tabs[0]: _copper_loss()
    with tabs[1]: _thermal_rise()
    with tabs[2]: _cable_loss()
    with tabs[3]: _semiconductor_loss()
    with tabs[4]: _thermal_derating()


# ── Copper Loss ───────────────────────────────────────────────────────────────

def _copper_loss():
    st.subheader("Motor Copper (I²R) Loss Calculator")
    engineering_note(
        "Calculates stator copper losses. Two conventions are supported. "
        "Ensure you match the current type to the formula — mixing RMS/peak or phase/dq gives wrong results."
    )
    convention = st.radio(
        "Current input convention",
        ["Phase current RMS (Ia_rms)", "dq-frame peak (id, iq)"],
        key="cu_conv",
    )
    col1, col2 = st.columns(2)
    with col1:
        Rs = st.number_input("Phase resistance R_s [mΩ]", value=50.0, min_value=0.0,
                             key="cu_rs") * 1e-3
        T_ref = st.number_input("Reference temperature for R_s [°C]", value=20.0, key="cu_tref")
        T_op = st.number_input("Operating temperature [°C]", value=120.0, key="cu_top")
        mat = st.selectbox("Conductor material", ["Copper (α=0.00393)", "Aluminium (α=0.00429)"],
                           key="cu_mat")
        alpha = 0.00393 if "Copper" in mat else 0.00429
        Rs_hot = Rs * (1 + alpha * (T_op - T_ref))

    with col2:
        if convention == "Phase current RMS (Ia_rms)":
            i_rms = st.number_input("Phase current I_a RMS [A]", value=10.0, min_value=0.0,
                                    key="cu_irms")
            P_cu = 3 * i_rms**2 * Rs_hot
            formula = r"P_{cu} = 3\,I_{a,rms}^2\,R_s"
        else:
            id_ = st.number_input("i_d [A peak]", value=-5.0, key="cu_id")
            iq = st.number_input("i_q [A peak]", value=20.0, key="cu_iq")
            P_cu = 1.5 * Rs_hot * (id_**2 + iq**2)
            formula = r"P_{cu} = \frac{3}{2}\,R_s\,(i_d^2 + i_q^2)"
            i_rms = np.sqrt((id_**2 + iq**2) / 2)
            st.metric("Equivalent I_rms [A]", f"{i_rms:.4f}")

    st.metric("R_s at operating temp [mΩ]", f"{Rs_hot*1000:.4f}")
    st.metric("Copper loss P_cu [W]", f"{P_cu:.4f}")
    st.metric("Copper loss P_cu [kW]", f"{P_cu/1000:.5f}")

    with st.expander("Formula & Notes"):
        show_formula(formula)
        engineering_note(
            "<b>dq-frame formula derivation:</b> Three-phase power with balanced sinusoidal currents: "
            "P = (3/2)·R_s·(id² + iq²) where id, iq are peak amplitudes. "
            "This equals P = 3·I_rms²·R_s since I_peak = √2·I_rms, |I|² = id²+iq², I_rms = |I|/√2.<br>"
            "<b>Temperature effect:</b> R at temperature T = R_ref·(1 + α·ΔT). "
            "Copper resistance rises ~0.4%/°C — significant at high winding temperature."
        )


# ── Thermal Rise ──────────────────────────────────────────────────────────────

def _thermal_rise():
    st.subheader("Thermal Rise Calculator")
    engineering_note(
        "Calculates steady-state and transient junction/winding temperature. "
        "Input: power loss, thermal resistance, ambient/coolant temperature, thermal capacitance."
    )
    col1, col2 = st.columns(2)
    with col1:
        P_loss = st.number_input("Dissipated power P [W]", value=100.0, min_value=0.0, key="th_p")
        R_th = st.number_input("Thermal resistance R_th [K/W]", value=0.5, min_value=0.0,
                               format="%.4f", key="th_rth")
        T_amb = st.number_input("Ambient / coolant temperature T_amb [°C]", value=40.0, key="th_tamb")
        T_max = st.number_input("Maximum allowed temperature T_max [°C]", value=150.0, key="th_tmax")
    with col2:
        show_transient = st.checkbox("Show transient response", value=True, key="th_trans")
        if show_transient:
            C_th = st.number_input("Thermal capacitance C_th [J/K]", value=50.0, min_value=0.0,
                                   key="th_cth")
            t_end = st.number_input("Time horizon [s]", value=60.0, min_value=1.0, key="th_tend")

    T_ss = T_amb + P_loss * R_th
    delta_T = P_loss * R_th
    margin = T_max - T_ss

    st.metric("Steady-state temperature T_ss [°C]", f"{T_ss:.3f}")
    st.metric("Temperature rise ΔT [K]", f"{delta_T:.3f}")
    st.metric("Thermal margin [K]", f"{margin:.3f}")

    if T_ss >= T_max:
        st.error(f"🔴 Temperature ({T_ss:.1f}°C) exceeds maximum ({T_max:.1f}°C). "
                 "Reduce losses or improve cooling.")
    elif margin < 10:
        show_warning(f"Thermal margin only {margin:.1f} K — marginal for reliable operation.")
    else:
        st.success(f"✅ Thermal margin: {margin:.1f} K")

    if show_transient and C_th > 0:
        tau = R_th * C_th
        t_arr = np.linspace(0, t_end, 500)
        T_arr = T_amb + delta_T * (1 - np.exp(-t_arr / tau))
        st.metric("Thermal time constant τ = R_th·C_th [s]", f"{tau:.3f}")
        fig = thermal_transient_plot(t_arr, T_arr, T_max)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Formulas"):
        show_formula(r"T_{ss} = T_{amb} + P\,R_{th}")
        show_formula(r"T(t) = T_{amb} + \Delta T\left(1 - e^{-t/\tau}\right) \quad \tau = R_{th}\,C_{th}")
        engineering_note(
            "Foster vs Cauer network: this is a single-element model. "
            "Real power devices use 3–5 stage RC networks from datasheet Foster model. "
            "Always derate for thermal resistance junction-to-case + case-to-heatsink + heatsink-to-ambient."
        )


# ── Cable Voltage Drop ────────────────────────────────────────────────────────

def _cable_loss():
    st.subheader("Cable Voltage Drop & Loss Calculator")
    engineering_note(
        "Calculates cable resistance, voltage drop, and I²R power loss for DC or AC single-phase cables. "
        "For three-phase AC: total cable loss = 3 × single-phase result."
    )
    col1, col2 = st.columns(2)
    with col1:
        I = st.number_input("Current I [A]", value=100.0, min_value=0.0, key="cab_i")
        length = st.number_input("Cable length (one-way) L [m]", value=10.0, min_value=0.0,
                                 key="cab_len")
        area = st.number_input("Conductor cross-section A [mm²]", value=16.0, min_value=0.0,
                               key="cab_area")
        material = st.selectbox("Material", ["Copper", "Aluminium"], key="cab_mat")
        T_op = st.number_input("Operating temperature [°C]", value=70.0, key="cab_temp")
        two_way = st.checkbox("Return conductor included (×2 length)", value=True, key="cab_2way")
        ph = st.selectbox("System", ["DC / Single-phase", "Three-phase (×3 loss)"], key="cab_sys")

    errs = collect_errors(require_positive(area, "Cross-section"), require_non_negative(I, "Current"))
    if errs:
        for e in errs: show_warning(e)
        return

    # Resistivity at 20°C
    rho_20 = 1.72e-8 if material == "Copper" else 2.82e-8  # Ω·m
    alpha = 0.00393 if material == "Copper" else 0.00429
    rho = rho_20 * (1 + alpha * (T_op - 20))

    l_total = length * (2 if two_way else 1)
    A_m2 = area * 1e-6  # mm² → m²
    R = rho * l_total / A_m2
    delta_V = I * R
    P_loss = I**2 * R

    with col2:
        st.metric("Resistivity ρ at temp [nΩ·m]", f"{rho*1e9:.4f}")
        st.metric("Cable resistance R [mΩ]", f"{R*1000:.4f}")
        st.metric("Voltage drop ΔV [V]", f"{delta_V:.4f}")
        st.metric("Power loss P [W]", f"{P_loss:.4f}")
        if "Three-phase" in ph:
            st.metric("Total 3-phase loss [W]", f"{P_loss*3:.4f}")
            st.metric("Total 3-phase ΔV [V]", f"{delta_V*3:.4f}")

    with st.expander("Formulas"):
        show_formula(r"R = \frac{\rho\,l}{A} \qquad \Delta V = I\,R \qquad P_{loss} = I^2\,R")
        show_formula(r"\rho(T) = \rho_{20}\,\bigl[1 + \alpha\,(T - 20)\bigr]")
        engineering_note(
            f"Copper ρ₂₀ = 1.72×10⁻⁸ Ω·m, α = 0.00393/°C. "
            f"Aluminium ρ₂₀ = 2.82×10⁻⁸ Ω·m, α = 0.00429/°C. "
            "For three-phase: each phase cable carries phase current — calculate per-phase then ×3 for total loss."
        )


# ── Semiconductor Loss ────────────────────────────────────────────────────────

def _semiconductor_loss():
    st.subheader("Semiconductor Conduction & Switching Loss Estimator")
    engineering_note(
        "Simplified three-phase inverter loss estimation. "
        "Requires datasheet parameters: on-state voltage, switching energies."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**IGBT / MOSFET parameters:**")
        v_ce_sat = st.number_input("V_CE(sat) or R_DS(on) [V or mΩ] — use V for IGBT, mΩ for FET",
                                   value=1.8, min_value=0.0, key="sw_vce")
        device_type = st.selectbox("Device type", ["IGBT (V_CE(sat))", "MOSFET (R_ds(on))"],
                                   key="sw_type")
        E_on = st.number_input("E_on [mJ] @ test conditions", value=2.5, min_value=0.0,
                               key="sw_eon")
        E_off = st.number_input("E_off [mJ] @ test conditions", value=1.5, min_value=0.0,
                                key="sw_eoff")
        E_rr = st.number_input("Diode E_rr [mJ] (reverse recovery)", value=1.0, min_value=0.0,
                               key="sw_err")
        V_test = st.number_input("Test voltage for E [V]", value=600.0, min_value=0.0, key="sw_vt")
        I_test = st.number_input("Test current for E [A]", value=300.0, min_value=0.0, key="sw_it")
    with col2:
        I_phase = st.number_input("Phase current peak [A]", value=100.0, min_value=0.0,
                                  key="sw_iph")
        V_dc = st.number_input("DC-link V_dc [V]", value=400.0, min_value=0.0, key="sw_vdc")
        f_sw = st.number_input("Switching frequency f_sw [kHz]", value=10.0, min_value=0.0,
                               key="sw_fsw") * 1e3
        pf = st.slider("Power factor cos φ", 0.0, 1.0, 0.9, 0.01, key="sw_pf")

    I_rms = I_phase / np.sqrt(2)
    # Conduction loss per IGBT (sinusoidal approximation for half-bridge leg)
    if "IGBT" in device_type:
        P_cond_switch = (1/8 + pf / (3 * np.pi)) * v_ce_sat * I_phase  # per switch, × 6
        P_cond_diode = (1/8 - pf / (3 * np.pi)) * v_ce_sat * I_phase   # per diode, × 6
    else:  # MOSFET
        R_ds = v_ce_sat * 1e-3
        P_cond_switch = (0.125 + pf / (3 * np.pi)) * R_ds * I_phase**2
        P_cond_diode = 0.1 * R_ds * I_phase**2  # approximate body diode

    P_cond_total = (P_cond_switch + P_cond_diode) * 6

    # Switching loss (scale from test conditions)
    scale = (V_dc / V_test) * (I_phase / I_test) if V_test > 0 and I_test > 0 else 1
    P_sw_total = (E_on + E_off + E_rr) * 1e-3 * f_sw * scale * 6

    P_total = P_cond_total + P_sw_total

    st.metric("Conduction loss (6 switches) [W]", f"{P_cond_total:.2f}")
    st.metric("Switching loss (6 switches) [W]", f"{P_sw_total:.2f}")
    st.metric("Total inverter loss [W]", f"{P_total:.2f}")
    if I_rms > 0 and V_dc > 0:
        P_out_approx = 3 * I_rms**2 * (V_dc / np.sqrt(3) / I_rms) * pf / 2
        P_out = np.sqrt(3) * V_dc / np.sqrt(3) * I_rms * pf
        eta = P_out / (P_out + P_total) * 100
        st.metric("Estimated inverter efficiency [%]", f"{eta:.2f}")

    show_info(
        "This is a simplified first-order estimate. Full loss models require "
        "detailed switching waveforms, junction temperature dependence, and gate resistance effects."
    )


# ── Thermal Derating ──────────────────────────────────────────────────────────

def _thermal_derating():
    st.subheader("Current Derating vs. Temperature Calculator")
    engineering_note(
        "Estimates how much current must be reduced to stay within thermal limits "
        "as ambient temperature rises. Assumes copper loss is the dominant loss mechanism."
    )
    col1, col2 = st.columns(2)
    with col1:
        I_rated = st.number_input("Rated current I_rated [A]", value=100.0, min_value=0.0,
                                  key="der_irated")
        T_amb_rated = st.number_input("Rated ambient temperature [°C]", value=40.0, key="der_tamb_rated")
        T_max = st.number_input("Max junction/winding temperature [°C]", value=150.0, key="der_tmax")
        R_th = st.number_input("R_th junction-to-ambient [K/W]", value=0.5, min_value=0.001,
                               format="%.4f", key="der_rth")
        Rs = st.number_input("Stator / device resistance R_s [mΩ]", value=50.0, min_value=0.0,
                             key="der_rs") * 1e-3

    with col2:
        T_amb_actual = st.number_input("Actual ambient temperature [°C]", value=60.0, key="der_tamb_actual")

    delta_T_rated = T_max - T_amb_rated
    P_rated = delta_T_rated / R_th
    I_rated_check = np.sqrt(P_rated / (3 * Rs)) if Rs > 0 else 0

    delta_T_actual = T_max - T_amb_actual
    if delta_T_actual < 0:
        st.error("Ambient temperature exceeds T_max. No current allowed.")
        return

    P_allowed = delta_T_actual / R_th
    I_allowed = np.sqrt(P_allowed / (3 * Rs)) if Rs > 0 else 0
    derating_factor = I_allowed / I_rated if I_rated > 0 else 0

    st.metric("Rated thermal headroom ΔT_rated [K]", f"{delta_T_rated:.1f}")
    st.metric("Available thermal headroom ΔT_actual [K]", f"{delta_T_actual:.1f}")
    st.metric("Allowed current at {:.0f}°C [A]".format(T_amb_actual), f"{I_allowed:.2f}")
    st.metric("Derating factor", f"{derating_factor:.4f}")
    st.metric("Derating [%]", f"{(1-derating_factor)*100:.2f}")

    if derating_factor < 0.8:
        show_warning(f"Significant derating ({(1-derating_factor)*100:.1f}%) at {T_amb_actual:.0f}°C ambient. "
                     "Consider improving cooling or oversizing the device.")
    else:
        show_info(f"Derating is {(1-derating_factor)*100:.1f}% at {T_amb_actual:.0f}°C ambient.")
