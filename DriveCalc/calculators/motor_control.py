"""Motor-control calculators: speed, torque, dq voltage, field weakening, PI gains."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, require_non_negative, collect_errors
import plotly.graph_objects as go


def render():
    st.header("Motor Control Calculators")
    tabs = st.tabs([
        "⚡ Speed & Frequency",
        "🔩 Torque-Power-Speed",
        "🧲 PMSM/IPMSM Torque",
        "🔁 EESM Torque",
        "📐 dq Voltage",
        "🔋 Field Weakening",
        "🎛️ PI Gain Design",
        "📊 Torque-Speed Envelope",
    ])
    with tabs[0]: _speed_frequency()
    with tabs[1]: _torque_power_speed()
    with tabs[2]: _pmsm_torque()
    with tabs[3]: _eesm_torque()
    with tabs[4]: _dq_voltage()
    with tabs[5]: _field_weakening()
    with tabs[6]: _pi_gain_design()
    with tabs[7]: _torque_speed_envelope()


# ── 1. Speed & Frequency ──────────────────────────────────────────────────────

def _speed_frequency():
    st.subheader("Motor Speed & Electrical Frequency Calculator")
    engineering_note(
        "Converts mechanical speed to electrical quantities. "
        "Fundamental: electrical speed = p × mechanical speed."
    )
    col1, col2 = st.columns(2)
    with col1:
        n_rpm = st.number_input("Mechanical speed n [rpm]", value=3000.0,
                                min_value=0.0, key="sf_rpm")
        p = st.number_input("Pole pairs p", value=4, min_value=1, step=1, key="sf_pp")
    errs = collect_errors(require_positive(n_rpm + 1e-9, "Speed"), require_positive(p, "Pole pairs"))
    if errs:
        for e in errs: show_warning(e)
        return

    omega_m = 2 * np.pi * n_rpm / 60
    omega_e = p * omega_m
    f_e = omega_e / (2 * np.pi)
    T_e = 1 / f_e if f_e > 0 else float("inf")

    with col2:
        st.markdown("**Results:**")
        st.metric("ω_m: mechanical [rad/s]", f"{omega_m:.5f}")
        st.metric("ω_e: electrical [rad/s]", f"{omega_e:.5f}")
        st.metric("f_e: electrical frequency [Hz]", f"{f_e:.5f}")
        st.metric("T_e: electrical period [ms]", f"{T_e*1000:.4f}")

    with st.expander("Formulas & Notes"):
        show_formula(
            r"\omega_m = \frac{2\pi n}{60} \qquad "
            r"\omega_e = p\,\omega_m \qquad "
            r"f_e = \frac{\omega_e}{2\pi} \qquad "
            r"\theta_e = p\,\theta_m"
        )
        engineering_note(
            "<b>Common mistake:</b> confusing ω_m and ω_e. "
            "For a 4-pole-pair motor at 3000 rpm: ω_m = 314.16 rad/s, ω_e = 1256.6 rad/s, f_e = 200 Hz."
        )


# ── 2. Torque-Power-Speed ─────────────────────────────────────────────────────

def _torque_power_speed():
    st.subheader("Torque-Power-Speed Calculator")
    engineering_note("P = T·ω. Use to convert between motor shaft power, torque, and speed.")
    col1, col2 = st.columns(2)
    with col1:
        torque = st.number_input("Torque T [Nm]", value=100.0, min_value=0.0, key="tps_t")
        speed = st.number_input("Speed n [rpm]", value=3000.0, min_value=0.0, key="tps_n")
    errs = collect_errors(require_non_negative(torque, "Torque"), require_positive(speed + 1e-9, "Speed"))
    if errs:
        for e in errs: show_warning(e)
        return

    omega_m = 2 * np.pi * speed / 60
    power_w = torque * omega_m
    power_kw = power_w / 1000
    power_hp = power_w / 745.7
    power_kw_approx = torque * speed / 9549  # practical formula

    with col2:
        st.metric("ω_m [rad/s]", f"{omega_m:.4f}")
        st.metric("P [W]", f"{power_w:.2f}")
        st.metric("P [kW]", f"{power_kw:.4f}")
        st.metric("P [hp]", f"{power_hp:.4f}")

    with st.expander("Formulas & Notes"):
        show_formula(
            r"P = T\,\omega_m \qquad "
            r"P_{kW} \approx \frac{T_{Nm}\cdot n_{rpm}}{9549}"
        )
        show_info(f"Verification: {torque:.1f} Nm × {speed:.0f} rpm / 9549 = {power_kw_approx:.3f} kW "
                  f"(exact: {power_kw:.3f} kW)")
        engineering_note(
            "The 9549 constant is 60000 / (2π × 1000). Useful quick mental check on test bench."
        )


# ── 3. PMSM / IPMSM Torque ────────────────────────────────────────────────────

def _pmsm_torque():
    st.subheader("PMSM / IPMSM Electromagnetic Torque Calculator")
    engineering_note(
        "Calculates electromagnetic torque using the dq-frame model. "
        "id, iq are <b>peak</b> (not RMS) dq-frame current values."
    )
    col1, col2 = st.columns(2)
    with col1:
        p = st.number_input("Pole pairs p", value=4, min_value=1, step=1, key="pmsm_p")
        psi_f = st.number_input("Flux linkage ψ_f [Wb]", value=0.08, min_value=0.0,
                                format="%.5f", key="pmsm_psi")
        ld = st.number_input("d-axis inductance L_d [mH]", value=1.5, min_value=0.0, key="pmsm_ld")
        lq = st.number_input("q-axis inductance L_q [mH]", value=3.0, min_value=0.0, key="pmsm_lq")
    with col2:
        id_ = st.number_input("d-axis current i_d [A peak]", value=-5.0, key="pmsm_id",
                              help="Negative id for flux weakening, 0 for MTPA start")
        iq = st.number_input("q-axis current i_q [A peak]", value=20.0, key="pmsm_iq")

    Ld = ld * 1e-3
    Lq = lq * 1e-3

    Te_reluctance = 1.5 * p * (Lq - Ld) * id_ * iq
    Te_magnet = 1.5 * p * psi_f * iq
    Te = Te_magnet + Te_reluctance

    st.markdown("**Results:**")
    r1, r2, r3 = st.columns(3)
    r1.metric("T_e [Nm]", f"{Te:.4f}")
    r2.metric("T_magnet contribution [Nm]", f"{Te_magnet:.4f}")
    r3.metric("T_reluctance contribution [Nm]", f"{Te_reluctance:.4f}")

    if abs(Te_reluctance) > 0 and abs(Te_magnet) > 0:
        ratio = abs(Te_reluctance / Te_magnet) * 100
        st.metric("Reluctance torque share [%]", f"{ratio:.1f}")

    with st.expander("Formula & Notes"):
        show_formula(
            r"T_e = \frac{3}{2}\,p\,\left[\psi_f\,i_q + (L_d - L_q)\,i_d\,i_q\right]"
        )
        engineering_note(
            "<b>Current convention:</b> i_d and i_q are peak dq-frame values. "
            "For SPMSM: L_d ≈ L_q → reluctance torque ≈ 0. "
            "For IPMSM: L_q > L_d → positive reluctance torque when i_d < 0. "
            "<b>Common mistake:</b> using RMS current in this formula: multiply by √2 first."
        )
        if Lq > Ld:
            show_info("IPMSM detected (L_q > L_d). Reluctance torque is utilizable.")
        elif abs(Lq - Ld) < 0.05 * Ld:
            show_info("L_d ≈ L_q → SPMSM or round-rotor machine.")


# ── 4. EESM Torque ────────────────────────────────────────────────────────────

def _eesm_torque():
    st.subheader("EESM Electromagnetic Torque Calculator")
    engineering_note(
        "Electrically Excited Synchronous Machine (wound-field). "
        "Flux linkage is generated by rotor field current I_f via mutual inductance M_f. "
        "This is a simplified linear model: saturation and cross-saturation are not included."
    )
    col1, col2 = st.columns(2)
    with col1:
        p = st.number_input("Pole pairs p", value=4, min_value=1, step=1, key="eesm_p")
        Ld = st.number_input("L_d [mH]", value=2.0, min_value=0.0, key="eesm_ld") * 1e-3
        Lq = st.number_input("L_q [mH]", value=4.0, min_value=0.0, key="eesm_lq") * 1e-3
        Mf = st.number_input("M_f: stator-rotor mutual inductance [mH]", value=50.0,
                             min_value=0.0, key="eesm_mf",
                             help="Mutual inductance between stator and rotor field winding") * 1e-3
    with col2:
        I_f = st.number_input("Field current I_f [A]", value=5.0, min_value=0.0, key="eesm_if")
        id_ = st.number_input("i_d [A peak]", value=-10.0, key="eesm_id")
        iq = st.number_input("i_q [A peak]", value=30.0, key="eesm_iq")

    psi_f = Mf * I_f
    Te_excitation = 1.5 * p * psi_f * iq
    Te_reluctance = 1.5 * p * (Ld - Lq) * id_ * iq
    Te = Te_excitation + Te_reluctance

    st.metric("Excitation flux linkage ψ_f = M_f·I_f [Wb]", f"{psi_f:.5f}")
    r1, r2, r3 = st.columns(3)
    r1.metric("T_e [Nm]", f"{Te:.4f}")
    r2.metric("T_excitation [Nm]", f"{Te_excitation:.4f}")
    r3.metric("T_reluctance [Nm]", f"{Te_reluctance:.4f}")

    with st.expander("Formula & Notes"):
        show_formula(
            r"\psi_f = M_f\,I_f \qquad "
            r"T_e = \frac{3}{2}\,p\,\left[M_f\,I_f\,i_q + (L_d - L_q)\,i_d\,i_q\right]"
        )
        engineering_note(
            "EESM field current I_f is a DC rotor current: it can be varied in real-time "
            "to control flux independently of stator currents. This enables efficient operation "
            "across a wide speed range. <b>Note:</b> a full EESM model requires flux maps "
            "(lookup tables) to handle magnetic saturation accurately."
        )


# ── 5. dq Voltage ─────────────────────────────────────────────────────────────

def _dq_voltage():
    st.subheader("dq Voltage Calculator")
    engineering_note(
        "Calculates the required stator dq voltages for given operating conditions. "
        "Includes back-EMF, resistive drop, and transient inductance terms."
    )
    col1, col2 = st.columns(2)
    with col1:
        Rs = st.number_input("Stator resistance R_s [mΩ]", value=50.0, min_value=0.0, key="dqv_rs") * 1e-3
        Ld = st.number_input("L_d [mH]", value=1.5, min_value=0.0, key="dqv_ld") * 1e-3
        Lq = st.number_input("L_q [mH]", value=3.0, min_value=0.0, key="dqv_lq") * 1e-3
        psi_f = st.number_input("ψ_f [Wb]", value=0.08, min_value=0.0, format="%.5f", key="dqv_psi")
        omega_e = st.number_input("Electrical speed ω_e [rad/s]", value=500.0, min_value=0.0, key="dqv_we")
    with col2:
        id_ = st.number_input("i_d [A peak]", value=-5.0, key="dqv_id")
        iq = st.number_input("i_q [A peak]", value=20.0, min_value=0.0, key="dqv_iq")
        did_dt = st.number_input("di_d/dt [A/s]", value=0.0, key="dqv_didt",
                                 help="Set to 0 for steady-state")
        diq_dt = st.number_input("di_q/dt [A/s]", value=0.0, key="dqv_diqdt")
        vdc = st.number_input("DC-link V_dc [V] (optional, 0=skip)", value=400.0, min_value=0.0,
                              key="dqv_vdc")
        mod_method = st.selectbox("Modulation", ["SVPWM", "SPWM"], key="dqv_mod")

    vd = Rs * id_ + Ld * did_dt - omega_e * Lq * iq
    vq = Rs * iq + Lq * diq_dt + omega_e * Ld * id_ + omega_e * psi_f
    v_mag = np.sqrt(vd**2 + vq**2)
    v_angle = np.degrees(np.arctan2(vq, vd))

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("v_d [V]", f"{vd:.4f}")
    r2.metric("v_q [V]", f"{vq:.4f}")
    r3.metric("|V_dq| [V]", f"{v_mag:.4f}")
    r4.metric("∠V_dq [deg]", f"{v_angle:.2f}")

    if vdc > 0:
        v_max = vdc / np.sqrt(3) if mod_method == "SVPWM" else vdc / 2
        margin = v_max - v_mag
        utilization = v_mag / v_max * 100
        m1, m2 = st.columns(2)
        m1.metric(f"V_max ({mod_method}) [V]", f"{v_max:.4f}")
        m2.metric("Voltage margin [V]", f"{margin:.4f}",
                  delta=f"{'OK' if margin >= 0 else 'VIOLATION'}")
        if margin < 0:
            show_warning(f"Required voltage ({v_mag:.2f} V) exceeds available ({v_max:.2f} V). "
                         f"Field weakening required or reduce load.")
        else:
            show_info(f"Voltage utilization: {utilization:.1f}%")

    with st.expander("Formulas & Notes"):
        show_formula(
            r"v_d = R_s\,i_d + L_d\,\frac{di_d}{dt} - \omega_e\,L_q\,i_q"
        )
        show_formula(
            r"v_q = R_s\,i_q + L_q\,\frac{di_q}{dt} + \omega_e\,L_d\,i_d + \omega_e\,\psi_f"
        )
        engineering_note(
            "<b>Back-EMF term:</b> ω_e·ψ_f dominates v_q at high speed. "
            "<b>Cross-coupling:</b> ω_e·L_q·i_q in v_d and ω_e·L_d·i_d in v_q must be compensated "
            "by the current controller (decoupling feed-forward)."
        )


# ── 6. Field Weakening Voltage Margin ────────────────────────────────────────

def _field_weakening():
    st.subheader("Field Weakening Voltage Margin Calculator")
    engineering_note(
        "Determines whether field weakening (negative i_d) is needed at the operating point. "
        "Compares required dq voltage magnitude with the inverter voltage limit circle."
    )
    col1, col2 = st.columns(2)
    with col1:
        vdc = st.number_input("V_dc [V]", value=400.0, min_value=0.0, key="fw_vdc")
        method = st.selectbox("Modulation", ["SVPWM", "SPWM"], key="fw_mod")
        Rs = st.number_input("R_s [mΩ]", value=50.0, min_value=0.0, key="fw_rs") * 1e-3
        Ld = st.number_input("L_d [mH]", value=1.5, min_value=0.0, key="fw_ld") * 1e-3
        Lq = st.number_input("L_q [mH]", value=3.0, min_value=0.0, key="fw_lq") * 1e-3
        psi_f = st.number_input("ψ_f [Wb]", value=0.08, format="%.5f", key="fw_psi")
    with col2:
        omega_e = st.number_input("ω_e [rad/s]", value=1000.0, min_value=0.0, key="fw_we")
        id_ = st.number_input("i_d [A peak]", value=0.0, key="fw_id")
        iq = st.number_input("i_q [A peak]", value=20.0, min_value=0.0, key="fw_iq")

    v_max = vdc / np.sqrt(3) if method == "SVPWM" else vdc / 2
    vd = Rs * id_ - omega_e * Lq * iq
    vq = Rs * iq + omega_e * Ld * id_ + omega_e * psi_f
    v_req = np.sqrt(vd**2 + vq**2)
    margin = v_max - v_req
    fw_needed = margin < 0

    r1, r2, r3 = st.columns(3)
    r1.metric(f"V_max ({method}) [V]", f"{v_max:.3f}")
    r2.metric("V_required [V]", f"{v_req:.3f}")
    r3.metric("Voltage margin [V]", f"{margin:.3f}")

    if fw_needed:
        st.error("🔴 Field weakening required. Apply negative i_d to stay within voltage limit.")
        # Estimate needed id for FW (simplified: ignore Rs, steady-state)
        # |V|² = (ω_e·L_q·i_q)² + (ω_e·(L_d·i_d + ψ_f))²  = V_max²
        # solve for i_d
        vq_term_sq = (v_max**2) - (omega_e * Lq * iq)**2
        if vq_term_sq > 0:
            vq_req = np.sqrt(vq_term_sq)
            id_fw = (vq_req - omega_e * psi_f) / (omega_e * Ld) if omega_e * Ld > 0 else 0
            st.metric("Suggested i_d for FW [A peak]", f"{id_fw:.3f}")
    else:
        st.success(f"✅ No field weakening needed. Voltage utilization: {v_req/v_max*100:.1f}%")

    with st.expander("Formulas & Notes"):
        show_formula(
            r"V_{max} = \begin{cases} V_{dc}/2 & \text{SPWM} \\ V_{dc}/\sqrt{3} & \text{SVPWM} \end{cases}"
        )
        show_formula(
            r"|V_{dq}| = \sqrt{v_d^2 + v_q^2} \leq V_{max}"
        )
        engineering_note(
            "SVPWM provides 15.5% higher voltage utilization than SPWM (ratio: 2/√3 = 1.155). "
            "Field weakening begins when |V_dq| reaches V_max: negative i_d reduces ψ_f·ω_e "
            "back-EMF contribution."
        )


# ── 7. PI Gain Design ─────────────────────────────────────────────────────────

def _pi_gain_design():
    st.subheader("Current Controller PI Gain Calculator")
    engineering_note(
        "First-order bandwidth-based PI design for d- and q-axis current controllers. "
        "Assumes symmetrical optimum / pole-zero cancellation of the motor R/L pole."
    )
    col1, col2 = st.columns(2)
    with col1:
        Rs = st.number_input("R_s [mΩ]", value=50.0, min_value=0.001, key="pi_rs") * 1e-3
        Ld = st.number_input("L_d [mH]", value=1.5, min_value=0.001, key="pi_ld") * 1e-3
        Lq = st.number_input("L_q [mH]", value=3.0, min_value=0.001, key="pi_lq") * 1e-3
    with col2:
        bw_hz = st.number_input("Desired current-loop bandwidth f_c [Hz]", value=500.0,
                                min_value=1.0, key="pi_bw")
        Ts = st.number_input("Sampling period T_s [µs]", value=100.0, min_value=0.1,
                             key="pi_ts") * 1e-6
        f_sw = st.number_input("Switching frequency f_sw [kHz]", value=10.0, min_value=0.1,
                               key="pi_fsw") * 1e3

    omega_c = 2 * np.pi * bw_hz

    Kp_d = Ld * omega_c
    Ki_d = Rs * omega_c
    Kp_q = Lq * omega_c
    Ki_q = Rs * omega_c

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**d-axis controller:**")
        st.metric("Kp_d", f"{Kp_d:.6f}")
        st.metric("Ki_d [1/s]", f"{Ki_d:.6f}")
        st.metric("L_d/R_s = τ_d [ms]", f"{Ld/Rs*1000:.3f}")
    with r2:
        st.markdown("**q-axis controller:**")
        st.metric("Kp_q", f"{Kp_q:.6f}")
        st.metric("Ki_q [1/s]", f"{Ki_q:.6f}")
        st.metric("L_q/R_s = τ_q [ms]", f"{Lq/Rs*1000:.3f}")

    # Warnings
    bw_ratio = bw_hz / f_sw
    if bw_ratio > 0.1:
        show_warning(
            f"Bandwidth ({bw_hz:.0f} Hz) is {bw_ratio*100:.1f}% of switching frequency "
            f"({f_sw/1000:.1f} kHz). Recommend f_c < 10% of f_sw for adequate phase margin."
        )
    delay_samples = 1.5  # typical: 1 computation + 0.5 PWM
    delay_s = delay_samples * Ts
    phase_loss = np.degrees(omega_c * delay_s)
    if phase_loss > 30:
        show_warning(f"Control delay ≈ {delay_s*1e6:.1f} µs causes ~{phase_loss:.1f}° phase loss at bandwidth. "
                     "Consider reducing bandwidth or adding Smith predictor.")

    with st.expander("Design Method & Notes"):
        show_formula(
            r"K_{p,d} = L_d\,\omega_c \qquad K_{i,d} = R_s\,\omega_c \qquad \omega_c = 2\pi\,f_c"
        )
        show_formula(
            r"K_{p,q} = L_q\,\omega_c \qquad K_{i,q} = R_s\,\omega_c"
        )
        engineering_note(
            "<b>Design basis:</b> Cancel motor R/L pole with integrator zero (pole-zero cancellation). "
            "Closed-loop bandwidth ≈ ω_c. "
            "<b>Practical rules:</b><br>"
            "• f_c < f_sw / 10 (typically)<br>"
            "• Implement anti-windup (clamping or back-calculation)<br>"
            "• Add cross-coupling decoupling (ω_e·L_d·iq, ω_e·L_q·id) as feed-forward<br>"
            "• Total control delay ≈ 1.5 × T_s (one computation + half PWM period)"
        )


# ── 8. Torque-Speed Envelope ──────────────────────────────────────────────────

def _torque_speed_envelope():
    st.subheader("PMSM Torque-Speed Envelope (Simplified)")
    engineering_note(
        "Plots approximate torque-speed and power-speed curves based on current and voltage limits. "
        "Peak torque region: current-limited. Field weakening region: voltage-limited."
    )
    col1, col2 = st.columns(2)
    with col1:
        p = st.number_input("Pole pairs p", value=4, min_value=1, step=1, key="env_p")
        psi_f = st.number_input("ψ_f [Wb]", value=0.08, format="%.5f", key="env_psi")
        Ld = st.number_input("L_d [mH]", value=1.5, key="env_ld") * 1e-3
        Lq = st.number_input("L_q [mH]", value=3.0, key="env_lq") * 1e-3
        Rs = st.number_input("R_s [mΩ]", value=50.0, key="env_rs") * 1e-3
    with col2:
        I_max = st.number_input("Max current I_max [A peak]", value=30.0, min_value=0.1, key="env_imax")
        vdc = st.number_input("V_dc [V]", value=400.0, min_value=0.0, key="env_vdc")
        n_max = st.number_input("Max speed [rpm]", value=10000.0, min_value=100.0, key="env_nmax")

    v_max = vdc / np.sqrt(3)  # SVPWM

    # Base speed: where voltage limit is first hit with id=0
    # |V| = omega_e * sqrt((L_q*I_max)^2 + psi_f^2) ≈ V_max (simplified, ignoring Rs)
    omega_e_base = v_max / np.sqrt((Lq * I_max)**2 + psi_f**2)
    n_base = omega_e_base / p * 60 / (2 * np.pi)

    speeds = np.linspace(10, n_max, 500)
    torques = []
    for n in speeds:
        omega_e = p * 2 * np.pi * n / 60
        if n <= n_base:
            # Constant torque: MTPA approximately id=0 for SPM, or simple for IPM
            iq = I_max
            id_ = 0.0
        else:
            # Field weakening: voltage-limited
            # Simplified: id from voltage limit circle (ignore Rs)
            denom = (omega_e * Ld)
            if denom < 1e-9:
                id_ = 0.0
                iq = I_max
            else:
                id_ = max(-(psi_f / Ld), -(v_max / denom - psi_f / Ld))
                iq_sq = (I_max**2) - id_**2
                iq = np.sqrt(max(iq_sq, 0))
        Te = 1.5 * p * (psi_f * iq + (Ld - Lq) * id_ * iq)
        torques.append(max(Te, 0))

    torques = np.array(torques)
    powers = torques * speeds * 2 * np.pi / 60 / 1000  # kW

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=speeds, y=torques, name="Torque [Nm]",
                             line=dict(color="#1f77b4", width=2)))
    fig.add_trace(go.Scatter(x=speeds, y=powers * 10, name="Power × 10 [kW × 10]",
                             line=dict(color="#ff7f0e", width=2, dash="dash"),
                             yaxis="y"))
    fig.add_vline(x=n_base, line_dash="dot", line_color="green",
                  annotation_text=f"n_base ≈ {n_base:.0f} rpm")
    fig.update_layout(
        title="Torque-Speed Envelope",
        xaxis_title="Speed [rpm]",
        yaxis_title="Torque [Nm] | Power×10 [W×10]",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        font=dict(family="Arial", size=12),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Approximate base speed", f"{n_base:.0f} rpm")
    st.metric("Peak torque (MTPA, id=0)", f"{torques[0]:.2f} Nm")
    st.metric("Peak power estimate", f"{powers.max():.2f} kW")

    engineering_note(
        "This is a simplified linear model. A full production design requires "
        "MTPA trajectory optimization, cross-saturation effects, and thermal derating maps."
    )
