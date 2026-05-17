"""General electrical engineering calculators: impedance, RC/RL, power factor, filter, Ohm's law."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, collect_errors
import plotly.graph_objects as go


def render():
    st.header("General Electrical Engineering Calculators")
    tabs = st.tabs([
        "🔋 Ohm's Law & Power",
        "🔁 RC / RL / RLC Circuits",
        "📐 Power Factor & Reactive Power",
        "📡 Impedance Calculator",
        "🌊 Filter Design Helper",
    ])
    with tabs[0]: _ohms_law()
    with tabs[1]: _rc_rl_rlc()
    with tabs[2]: _power_factor()
    with tabs[3]: _impedance()
    with tabs[4]: _filter_design()


# ── Ohm's Law & Power ─────────────────────────────────────────────────────────

def _ohms_law():
    st.subheader("Ohm's Law & DC Power Calculator")
    engineering_note("Enter any two of {V, I, R, P} to calculate the others.")
    col1, col2 = st.columns(2)
    with col1:
        V = st.number_input("Voltage V [V]  (0 = unknown)", value=12.0, min_value=0.0, key="ohm_v")
        I = st.number_input("Current I [A]  (0 = unknown)", value=2.0, min_value=0.0, key="ohm_i")
        R = st.number_input("Resistance R [Ω]  (0 = unknown)", value=0.0, min_value=0.0, key="ohm_r")
        P = st.number_input("Power P [W]  (0 = unknown)", value=0.0, min_value=0.0, key="ohm_p")

    known = {k: v for k, v in {"V": V, "I": I, "R": R, "P": P}.items() if v != 0}
    results = dict(known)

    try:
        if "V" in known and "I" in known:
            results["R"] = known["V"] / known["I"]
            results["P"] = known["V"] * known["I"]
        elif "V" in known and "R" in known:
            results["I"] = known["V"] / known["R"]
            results["P"] = known["V"]**2 / known["R"]
        elif "I" in known and "R" in known:
            results["V"] = known["I"] * known["R"]
            results["P"] = known["I"]**2 * known["R"]
        elif "P" in known and "V" in known:
            results["I"] = known["P"] / known["V"]
            results["R"] = known["V"]**2 / known["P"]
        elif "P" in known and "I" in known:
            results["V"] = known["P"] / known["I"]
            results["R"] = known["P"] / known["I"]**2
        elif "P" in known and "R" in known:
            results["V"] = np.sqrt(known["P"] * known["R"])
            results["I"] = np.sqrt(known["P"] / known["R"])
        else:
            show_info("Enter at least two known values.")
            return
    except ZeroDivisionError:
        show_warning("Division by zero: check your inputs.")
        return

    with col2:
        st.metric("V [V]", f"{results.get('V', 0):.5g}")
        st.metric("I [A]", f"{results.get('I', 0):.5g}")
        st.metric("R [Ω]", f"{results.get('R', 0):.5g}")
        st.metric("P [W]", f"{results.get('P', 0):.5g}")

    with st.expander("Formulas"):
        show_formula(r"V = I\,R \qquad P = V\,I = \frac{V^2}{R} = I^2\,R")


# ── RC / RL / RLC ─────────────────────────────────────────────────────────────

def _rc_rl_rlc():
    st.subheader("RC / RL / RLC Circuit Calculator")
    circuit = st.selectbox("Circuit type", ["RC (low-pass)", "RL (low-pass)", "RLC series"],
                           key="rc_type")
    col1, col2 = st.columns(2)
    with col1:
        R = st.number_input("R [Ω]", value=100.0, min_value=0.0, key="rc_r")
        if circuit != "RL (low-pass)":
            C = st.number_input("C [µF]", value=1.0, min_value=0.0, key="rc_c") * 1e-6
        if circuit != "RC (low-pass)":
            L = st.number_input("L [mH]", value=10.0, min_value=0.0, key="rc_l") * 1e-3

    with col2:
        if circuit == "RC (low-pass)":
            f_c = 1 / (2 * np.pi * R * C) if R * C > 0 else 0
            tau = R * C
            st.metric("Cutoff f_c [Hz]", f"{f_c:.4f}")
            st.metric("Time constant τ [ms]", f"{tau*1000:.4f}")
            show_formula(r"f_c = \frac{1}{2\pi RC} \qquad \tau = RC")
        elif circuit == "RL (low-pass)":
            f_c = R / (2 * np.pi * L) if L > 0 else 0
            tau = L / R if R > 0 else 0
            st.metric("Cutoff f_c [Hz]", f"{f_c:.4f}")
            st.metric("Time constant τ [ms]", f"{tau*1000:.4f}")
            show_formula(r"f_c = \frac{R}{2\pi L} \qquad \tau = \frac{L}{R}")
        else:
            f_res = 1 / (2 * np.pi * np.sqrt(L * C)) if L * C > 0 else 0
            zeta = R / 2 * np.sqrt(C / L) if L > 0 else 0
            Q = 1 / (R) * np.sqrt(L / C) if C > 0 and R > 0 else 0
            Z_res = R  # at resonance
            st.metric("Resonant f_0 [Hz]", f"{f_res:.4f}")
            st.metric("Damping ratio ζ", f"{zeta:.4f}")
            st.metric("Quality factor Q", f"{Q:.4f}")
            st.metric("Z at resonance [Ω]", f"{Z_res:.4f}")
            show_formula(
                r"f_0 = \frac{1}{2\pi\sqrt{LC}} \qquad "
                r"\zeta = \frac{R}{2}\sqrt{\frac{C}{L}} \qquad "
                r"Q = \frac{1}{R}\sqrt{\frac{L}{C}}"
            )
            if zeta < 0.5:
                show_warning("ζ < 0.5: underdamped system, oscillatory transient response.")

    # Bode magnitude plot
    freqs = np.logspace(0, 6, 1000)
    omega = 2 * np.pi * freqs
    if circuit == "RC (low-pass)":
        Hjw = 1 / (1 + 1j * omega * R * C)
    elif circuit == "RL (low-pass)":
        Hjw = R / (R + 1j * omega * L)
    else:
        Z_L = 1j * omega * L
        Z_C = 1 / (1j * omega * C)
        Hjw = R / (R + Z_L + Z_C)

    gain_db = 20 * np.log10(np.abs(Hjw))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=gain_db, mode="lines",
                             line=dict(color="#1f77b4", width=2)))
    fig.update_layout(title="Bode Magnitude Plot", xaxis_title="Frequency [Hz]",
                      xaxis_type="log", yaxis_title="Gain [dB]",
                      paper_bgcolor="white", plot_bgcolor="#f8f9fa",
                      font=dict(family="Arial"))
    st.plotly_chart(fig, use_container_width=True)


# ── Power Factor & Reactive Power ─────────────────────────────────────────────

def _power_factor():
    st.subheader("Power Factor & Reactive Power Calculator")
    engineering_note("Computes apparent, active, and reactive power for AC circuits.")
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("Input mode", ["V, I, PF", "P, Q", "P, S"], key="pf_mode")
        if mode == "V, I, PF":
            Vrms = st.number_input("V_rms [V]", value=230.0, min_value=0.0, key="pf_v")
            Irms = st.number_input("I_rms [A]", value=10.0, min_value=0.0, key="pf_i")
            pf = st.slider("Power factor cos φ", 0.0, 1.0, 0.85, 0.01, key="pf_pf")
            S = Vrms * Irms
            P = S * pf
            Q = np.sqrt(max(S**2 - P**2, 0))
        elif mode == "P, Q":
            P = st.number_input("Active power P [W]", value=2000.0, key="pf_p")
            Q = st.number_input("Reactive power Q [VAr]", value=1000.0, key="pf_q")
            S = np.sqrt(P**2 + Q**2)
            pf = P / S if S > 0 else 0
            Vrms = Irms = None
        else:
            P = st.number_input("Active power P [W]", value=2000.0, key="pf_p2")
            S = st.number_input("Apparent power S [VA]", value=2500.0, min_value=0.0, key="pf_s")
            Q = np.sqrt(max(S**2 - P**2, 0))
            pf = P / S if S > 0 else 0
            Vrms = Irms = None

    with col2:
        st.metric("Apparent power S [VA]", f"{S:.4f}")
        st.metric("Active power P [W]", f"{P:.4f}")
        st.metric("Reactive power Q [VAr]", f"{Q:.4f}")
        st.metric("Power factor cos φ", f"{pf:.4f}")
        phi = np.degrees(np.arccos(np.clip(pf, 0, 1)))
        st.metric("Phase angle φ [deg]", f"{phi:.3f}")

    with st.expander("Formulas"):
        show_formula(r"S = V_{rms}\,I_{rms} \qquad P = S\cos\varphi \qquad Q = S\sin\varphi")
        show_formula(r"S^2 = P^2 + Q^2")


# ── Impedance Calculator ──────────────────────────────────────────────────────

def _impedance():
    st.subheader("Impedance Calculator (Series & Parallel)")
    st.markdown("Computes impedance magnitude and phase for R, L, C combinations.")
    col1, col2 = st.columns(2)
    with col1:
        f = st.number_input("Frequency f [Hz]", value=50.0, min_value=0.0, key="imp_f")
        R = st.number_input("R [Ω]", value=10.0, min_value=0.0, key="imp_r")
        L = st.number_input("L [mH]", value=10.0, min_value=0.0, key="imp_l") * 1e-3
        C = st.number_input("C [µF]", value=100.0, min_value=0.0, key="imp_c") * 1e-6
        config = st.selectbox("Configuration", ["Series RLC", "Parallel RLC"], key="imp_cfg")

    omega = 2 * np.pi * f
    Z_R = R
    Z_L = 1j * omega * L
    Z_C = 1 / (1j * omega * C) if C > 0 else 0

    if config == "Series RLC":
        Z = Z_R + Z_L + Z_C
    else:
        inv_Z = 0
        if R > 0: inv_Z += 1 / Z_R
        if L > 0: inv_Z += 1 / Z_L
        if C > 0: inv_Z += 1 / Z_C
        Z = 1 / inv_Z if inv_Z != 0 else float("inf")

    Z_mag = abs(Z)
    Z_phase = np.degrees(np.angle(Z))

    with col2:
        st.metric("Z magnitude [Ω]", f"{Z_mag:.5f}")
        st.metric("Z phase [deg]", f"{Z_phase:.4f}")
        st.metric("X_L = ωL [Ω]", f"{omega*L:.5f}")
        st.metric("X_C = 1/(ωC) [Ω]", f"{1/(omega*C) if C>0 else 'inf'}")
        st.metric("Z_real [Ω]", f"{Z.real:.5f}")
        st.metric("Z_imag [Ω]", f"{Z.imag:.5f}")


# ── Filter Design Helper ──────────────────────────────────────────────────────

def _filter_design():
    st.subheader("Low-Pass Filter Design Helper")
    engineering_note(
        "Designs first-order (RC/RL) or second-order (RLC/LC) passive low-pass filters "
        "given a cutoff frequency and source/load impedance."
    )
    col1, col2 = st.columns(2)
    with col1:
        f_c = st.number_input("Desired cutoff frequency f_c [Hz]", value=1000.0, min_value=0.0,
                              key="flt_fc")
        order = st.selectbox("Filter order", ["1st order (RC)", "1st order (RL)",
                                              "2nd order (RLC)", "2nd order (LC: ideal)"],
                             key="flt_ord")
        if "RC" in order:
            R = st.number_input("R [Ω]", value=100.0, min_value=0.0, key="flt_r")
            C = 1 / (2 * np.pi * f_c * R) if R > 0 and f_c > 0 else 0
            st.metric("Required C [µF]", f"{C*1e6:.4f}")
            show_formula(r"C = \frac{1}{2\pi f_c R}")
        elif "RL" in order and "RLC" not in order:
            R = st.number_input("R [Ω]", value=100.0, min_value=0.0, key="flt_r2")
            L = R / (2 * np.pi * f_c) if f_c > 0 else 0
            st.metric("Required L [mH]", f"{L*1000:.4f}")
            show_formula(r"L = \frac{R}{2\pi f_c}")
        elif "RLC" in order:
            R = st.number_input("R [Ω] (determines damping)", value=10.0, min_value=0.0, key="flt_r3")
            Q_target = st.number_input("Target Q factor", value=0.707, min_value=0.01, key="flt_q")
            L = Q_target * R / (2 * np.pi * f_c) if f_c > 0 else 0
            C = 1 / ((2 * np.pi * f_c)**2 * L) if L > 0 else 0
            st.metric("Required L [mH]", f"{L*1000:.4f}")
            st.metric("Required C [µF]", f"{C*1e6:.4f}")
            show_formula(r"f_0 = \frac{1}{2\pi\sqrt{LC}} \qquad Q = \frac{1}{R}\sqrt{\frac{L}{C}}")
        else:  # LC
            L = st.number_input("L [mH]", value=1.0, min_value=0.0, key="flt_l_lc") * 1e-3
            C = 1 / ((2 * np.pi * f_c)**2 * L) if L > 0 and f_c > 0 else 0
            st.metric("Required C [µF]", f"{C*1e6:.4f}")
            show_formula(r"C = \frac{1}{(2\pi f_c)^2 L}")

    with col2:
        engineering_note(
            "<b>Design tip:</b> For motor drive output filters (dV/dt reduction), "
            "use f_c ≈ 5–10× f_fundamental and ≤ 0.1× f_switching. "
            "For current sensing anti-alias filter: f_c ≈ f_sw/4 to f_sw/2."
        )
