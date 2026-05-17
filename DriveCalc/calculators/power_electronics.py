"""Power electronics calculators: inverter voltage, SVPWM, Buck, Boost, DC-link."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, require_range, collect_errors
from utils.plotting import svpwm_hexagon_plot
import plotly.graph_objects as go


def render():
    st.header("Power Electronics Calculators")
    tabs = st.tabs([
        "🔌 Inverter Voltage",
        "🔷 SVPWM Duty & Sector",
        "⬇️ Buck Converter",
        "⬆️ Boost Converter",
        "⚡ DC-link Capacitor Ripple",
    ])
    with tabs[0]: _inverter_voltage()
    with tabs[1]: _svpwm()
    with tabs[2]: _buck()
    with tabs[3]: _boost()
    with tabs[4]: _dclink_ripple()


# ── Inverter Voltage ──────────────────────────────────────────────────────────

def _inverter_voltage():
    st.subheader("Three-Phase Inverter Voltage Calculator")
    engineering_note(
        "Calculates output voltages from DC-link voltage, modulation index, and PWM method. "
        "Assumptions: ideal switch, balanced three-phase load."
    )
    col1, col2 = st.columns(2)
    with col1:
        vdc = st.number_input("DC-link voltage V_dc [V]", value=400.0, min_value=0.0, key="inv_vdc")
        mi = st.slider("Modulation index m (0–1)", 0.0, 1.0, 1.0, 0.01, key="inv_mi")
        method = st.selectbox("PWM method", ["SPWM", "SVPWM"], key="inv_method")

    if method == "SPWM":
        v_ph_peak = mi * vdc / 2
        util_note = "SPWM: V_phase_peak = m · V_dc / 2. Max at m=1: 50% of V_dc."
    else:
        v_ph_peak = mi * vdc / np.sqrt(3)
        util_note = "SVPWM: V_phase_peak = m · V_dc / √3. Max at m=1: 57.7% of V_dc."

    v_ph_rms = v_ph_peak / np.sqrt(2)
    v_ll_rms = v_ph_rms * np.sqrt(3)
    v_ll_peak = v_ll_rms * np.sqrt(2)
    utilization = v_ph_peak / (vdc / 2) * 100

    with col2:
        st.metric("V_phase peak [V]", f"{v_ph_peak:.3f}")
        st.metric("V_phase RMS [V]", f"{v_ph_rms:.3f}")
        st.metric("V_LL RMS [V]", f"{v_ll_rms:.3f}")
        st.metric("V_LL peak [V]", f"{v_ll_peak:.3f}")
        st.metric("DC utilization [%]", f"{utilization:.1f}")

    show_info(util_note)

    with st.expander("Formulas"):
        show_formula(
            r"V_{ph,peak} = m\cdot\frac{V_{dc}}{2} \;(\text{SPWM}) \qquad "
            r"V_{ph,peak} = m\cdot\frac{V_{dc}}{\sqrt{3}} \;(\text{SVPWM})"
        )
        engineering_note(
            "SVPWM gain over SPWM: 2/√3 = 1.155 (+15.5%). "
            "Over-modulation (m > 1) increases output voltage but introduces low-order harmonics. "
            "<b>Common mistake:</b> using line-line voltage where phase voltage is required."
        )


# ── SVPWM ─────────────────────────────────────────────────────────────────────

def _svpwm():
    st.subheader("SVPWM Sector and Duty-Cycle Calculator")
    engineering_note(
        "Space Vector PWM: decomposes the reference voltage vector into adjacent "
        "active vectors and zero vectors within each switching period."
    )
    col1, col2 = st.columns(2)
    with col1:
        vdc = st.number_input("V_dc [V]", value=400.0, min_value=1.0, key="sv_vdc")
        v_mag = st.number_input("Reference vector |V*| [V]", value=150.0, min_value=0.0, key="sv_vmag")
        v_angle = st.number_input("Reference vector angle θ [deg]", value=30.0, key="sv_ang",
                                  min_value=0.0, max_value=360.0)
        T_sw = st.number_input("Switching period T_sw [µs]", value=100.0, min_value=1.0,
                               key="sv_tsw") * 1e-6

    v_max = vdc / np.sqrt(3)
    if v_mag > v_max:
        show_warning(f"Reference magnitude ({v_mag:.1f} V) exceeds linear SVPWM limit "
                     f"({v_max:.1f} V). Over-modulation: results are approximate.")

    theta = np.radians(v_angle % 360)
    sector = int(np.floor(v_angle % 360 / 60)) + 1

    # Normalise angle within sector
    theta_s = theta - np.radians((sector - 1) * 60)
    # Active vector times
    T1 = np.sqrt(3) * T_sw * v_mag / vdc * np.sin(np.pi / 3 - theta_s)
    T2 = np.sqrt(3) * T_sw * v_mag / vdc * np.sin(theta_s)
    T0 = T_sw - T1 - T2
    T0 = max(T0, 0)

    # Duties: sector-dependent switching sequence (simplified symmetric)
    # Map sector to ABC duties using standard SVPWM table
    _sv_duties = {
        1: lambda t1, t2, t0: ((T_sw - t0/2) / T_sw,
                                (T_sw - t0/2 - t1) / T_sw,
                                t0 / 2 / T_sw),
        2: lambda t1, t2, t0: ((T_sw - t0/2 - t2) / T_sw,
                                (T_sw - t0/2) / T_sw,
                                t0 / 2 / T_sw),
        3: lambda t1, t2, t0: (t0 / 2 / T_sw,
                                (T_sw - t0/2) / T_sw,
                                (T_sw - t0/2 - t1) / T_sw),
        4: lambda t1, t2, t0: (t0 / 2 / T_sw,
                                (T_sw - t0/2 - t2) / T_sw,
                                (T_sw - t0/2) / T_sw),
        5: lambda t1, t2, t0: ((T_sw - t0/2 - t1) / T_sw,
                                t0 / 2 / T_sw,
                                (T_sw - t0/2) / T_sw),
        6: lambda t1, t2, t0: ((T_sw - t0/2) / T_sw,
                                t0 / 2 / T_sw,
                                (T_sw - t0/2 - t2) / T_sw),
    }
    da, db, dc = _sv_duties.get(sector, _sv_duties[1])(T1, T2, T0)
    da = np.clip(da, 0, 1)
    db = np.clip(db, 0, 1)
    dc = np.clip(dc, 0, 1)

    with col2:
        st.metric("Sector", f"{sector}")
        st.metric("T1 [µs]", f"{T1*1e6:.2f}")
        st.metric("T2 [µs]", f"{T2*1e6:.2f}")
        st.metric("T0 (zero vectors) [µs]", f"{T0*1e6:.2f}")
        st.metric("Duty A", f"{da:.4f}")
        st.metric("Duty B", f"{db:.4f}")
        st.metric("Duty C", f"{dc:.4f}")

    st.plotly_chart(svpwm_hexagon_plot(v_mag, v_angle, vdc), use_container_width=True)

    with st.expander("Formulas & Notes"):
        show_formula(
            r"T_1 = \sqrt{3}\,\frac{T_{sw}\,|V^*|}{V_{dc}}\sin\!\left(\frac{\pi}{3} - \theta_s\right)"
        )
        show_formula(
            r"T_2 = \sqrt{3}\,\frac{T_{sw}\,|V^*|}{V_{dc}}\sin\theta_s \qquad T_0 = T_{sw} - T_1 - T_2"
        )
        engineering_note(
            "θ_s is the angle of the reference vector within the current sector (0–60°). "
            "T_0 is split equally between V000 and V111 zero vectors in symmetric (center-aligned) SVPWM."
        )


# ── Buck Converter ─────────────────────────────────────────────────────────────

def _buck():
    st.subheader("Buck Converter Calculator (CCM)")
    engineering_note("Ideal synchronous or diode-based buck converter in CCM. Input: steady-state operating point.")
    col1, col2 = st.columns(2)
    with col1:
        vin = st.number_input("Input voltage V_in [V]", value=48.0, min_value=0.0, key="buck_vin")
        d = st.slider("Duty cycle D", 0.01, 0.99, 0.5, 0.01, key="buck_d")
        f_sw = st.number_input("Switching frequency f_sw [kHz]", value=100.0, min_value=0.0,
                               key="buck_fsw") * 1e3
        L = st.number_input("Inductance L [µH]", value=100.0, min_value=0.0,
                            key="buck_l") * 1e-6
        C = st.number_input("Output capacitance C [µF]", value=100.0, min_value=0.0,
                            key="buck_c") * 1e-6
        R_load = st.number_input("Load resistance R [Ω]", value=5.0, min_value=0.0, key="buck_r")

    errs = collect_errors(require_positive(vin, "V_in"), require_positive(f_sw, "f_sw"),
                          require_positive(L, "L"), require_positive(C, "C"),
                          require_positive(R_load, "R_load"))
    if errs:
        for e in errs: show_warning(e)
        return

    vout = d * vin
    i_out = vout / R_load
    delta_il = (vin - vout) * d / (L * f_sw)
    delta_vc = delta_il / (8 * C * f_sw)
    i_l_avg = i_out
    # CCM boundary: delta_il < 2 * i_out
    ccm = delta_il < 2 * i_out
    p_out = vout * i_out
    ripple_pct = delta_vc / vout * 100 if vout > 0 else 0

    with col2:
        st.metric("V_out [V]", f"{vout:.4f}")
        st.metric("I_out [A]", f"{i_out:.4f}")
        st.metric("ΔI_L (inductor ripple) [A]", f"{delta_il:.4f}")
        st.metric("ΔV_C (capacitor ripple) [mV]", f"{delta_vc*1000:.4f}")
        st.metric("Output ripple [%]", f"{ripple_pct:.3f}")
        st.metric("P_out [W]", f"{p_out:.3f}")
        if ccm:
            st.success("✅ CCM: continuous conduction mode")
        else:
            show_warning("DCM: discontinuous conduction mode. CCM formulas are not valid. Reduce L or increase load.")

    with st.expander("Formulas"):
        show_formula(r"V_{out} = D\,V_{in} \qquad \Delta I_L = \frac{(V_{in}-V_{out})\,D}{L\,f_{sw}}")
        show_formula(r"\Delta V_C = \frac{\Delta I_L}{8\,C\,f_{sw}}")
        engineering_note(
            "CCM condition: ΔI_L < 2·I_out. "
            "This model assumes ideal switches, ESR = 0, and continuous conduction. "
            "Real converters have switch losses, diode drops, and capacitor ESR."
        )


# ── Boost Converter ────────────────────────────────────────────────────────────

def _boost():
    st.subheader("Boost Converter Calculator (CCM)")
    engineering_note("Ideal boost converter in CCM. High duty-cycle operation (D > 0.8) is unreliable in practice.")
    col1, col2 = st.columns(2)
    with col1:
        vin = st.number_input("Input voltage V_in [V]", value=24.0, min_value=0.0, key="bst_vin")
        d = st.slider("Duty cycle D", 0.01, 0.95, 0.5, 0.01, key="bst_d")
        f_sw = st.number_input("Switching frequency f_sw [kHz]", value=100.0, min_value=0.1,
                               key="bst_fsw") * 1e3
        L = st.number_input("Inductance L [µH]", value=100.0, min_value=0.0,
                            key="bst_l") * 1e-6
        C = st.number_input("Output capacitance C [µF]", value=470.0, min_value=0.0,
                            key="bst_c") * 1e-6
        R_load = st.number_input("Load resistance R [Ω]", value=20.0, min_value=0.0, key="bst_r")

    if d >= 0.9:
        show_warning("D > 0.9: ideal boost gain is very high and impractical. Real converters degrade due to parasitics.")

    vout = vin / (1 - d)
    i_out = vout / R_load
    i_in = i_out / (1 - d)  # = i_L_avg
    delta_il = vin * d / (L * f_sw)
    delta_vc = i_out * d / (C * f_sw)
    p_out = vout * i_out
    ccm = delta_il < 2 * i_in

    with col2:
        st.metric("V_out [V]", f"{vout:.4f}")
        st.metric("I_out [A]", f"{i_out:.4f}")
        st.metric("I_L avg (= I_in) [A]", f"{i_in:.4f}")
        st.metric("ΔI_L [A]", f"{delta_il:.4f}")
        st.metric("ΔV_out [mV]", f"{delta_vc*1000:.4f}")
        st.metric("P_out [W]", f"{p_out:.3f}")
        if ccm:
            st.success("✅ CCM")
        else:
            show_warning("⚠️ DCM: CCM formulas not valid.")

    with st.expander("Formulas"):
        show_formula(r"V_{out} = \frac{V_{in}}{1-D} \qquad \Delta I_L = \frac{V_{in}\,D}{L\,f_{sw}}")
        show_formula(r"\Delta V_{out} = \frac{I_{out}\,D}{C\,f_{sw}}")
        engineering_note(
            "Boost converter switch carries full input current. "
            "Switch stress = V_out. "
            "At D → 1: gain → ∞ theoretically, but parasitic resistance limits real gain."
        )


# ── DC-link Capacitor Ripple ───────────────────────────────────────────────────

def _dclink_ripple():
    st.subheader("DC-link Capacitor Ripple Current Estimator")
    engineering_note(
        "Estimates the RMS ripple current in the DC-link capacitor of a three-phase inverter. "
        "High ripple reduces capacitor lifetime. Electrolytic caps are typically ripple-current limited."
    )
    col1, col2 = st.columns(2)
    with col1:
        vdc = st.number_input("V_dc [V]", value=400.0, min_value=0.0, key="dcr_vdc")
        i_phase_peak = st.number_input("Phase current peak I_peak [A]", value=30.0, min_value=0.0,
                                       key="dcr_ipk")
        mi = st.slider("Modulation index m", 0.1, 1.0, 0.9, 0.01, key="dcr_mi")
        pf = st.slider("Power factor cos φ", 0.0, 1.0, 0.9, 0.01, key="dcr_pf")

    # Approximate RMS ripple current for three-phase inverter
    # I_ripple ≈ I_phase_peak * sqrt(√3/2 * m * (√3/4 * m - pf²))  [simplified Mohan formula]
    # Using a common approximation: I_C_rms ≈ I_peak * sqrt(A)
    # A = sqrt(3)/2 * m * (sqrt(3)/2*m - pf^2)  -- only valid for 0 < A < 1
    A = np.sqrt(3) / 2 * mi * (np.sqrt(3) / 2 * mi - pf**2)
    if A <= 0:
        i_ripple = 0.0
        show_info("Ripple is negligible at this operating point.")
    else:
        i_ripple = i_phase_peak * np.sqrt(A)

    i_dc = 0.75 * mi * i_phase_peak * pf  # approximate DC battery current
    p_approx = np.sqrt(3) / 2 * vdc * mi * i_phase_peak * pf / 1000

    with col2:
        st.metric("Estimated I_C_ripple RMS [A]", f"{i_ripple:.3f}")
        st.metric("Approx DC current I_dc [A]", f"{i_dc:.3f}")
        st.metric("Approx output power [kW]", f"{p_approx:.3f}")

    engineering_note(
        "This is a simplified first-harmonic approximation. "
        "Full harmonic analysis requires simulation. "
        "Select capacitors with I_ripple_rated ≥ 1.5 × estimated I_C_ripple for reliability. "
        "Film capacitors are preferred in modern inverters for higher ripple tolerance."
    )
