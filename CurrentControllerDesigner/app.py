"""
app.py: CurrentControllerDesigner  (Streamlit main entry point)
Author : Masoud Bakhshi
Version: 1.0

Automotive-grade PI current / torque / speed controller design tool
for EESM, IPMSM, and Induction Machine propulsion drives.
"""

import json
import io

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import control

from machine_models    import EESMModel, IPMSMModel, IMModel, total_delay_s
from controller_design import (design_current_pi, design_speed_pi,
                                build_loop_tf, build_closed_loop_tf,
                                build_sensitivity_tf, PIController)
from discrete_design   import (discretize_pi, discretize_plant,
                                closed_loop_discrete_poles,
                                check_discrete_stability, generate_c_snippet)
from stability_analysis import (analyse_loop, full_analysis_figures,
                                 resistance_sensitivity_sweep,
                                 inductance_sensitivity_sweep,
                                 delay_sensitivity_sweep,
                                 sensitivity_sweep_figure)
from report_generator  import generate_report

# ===========================================================================
# Page config
# ===========================================================================

st.set_page_config(
    page_title="CurrentControllerDesigner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main-title {
      font-size: 2.1rem; font-weight: 800;
      background: linear-gradient(90deg, #1a73e8 0%, #0d47a1 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
  }
  .sub-title {
      font-size: 1.05rem; color: #37474f;
      font-style: italic; margin-top: -4px;
  }
  .author-line {
      font-size: 0.88rem; color: #546e7a;
      margin-top: 4px; margin-bottom: 0;
  }
  .section-hdr {
      font-size: 1.15rem; font-weight: 600;
      border-bottom: 2px solid #1a73e8; padding-bottom: 4px;
  }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚡ CurrentControllerDesigner</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    'Frequency-Domain PI Controller Synthesis and Stability Analysis for '
    'AC Electric Machine Drives: Current Loop, Torque Loop, and Speed Loop'
    '</div>',
    unsafe_allow_html=True)
st.markdown(
    '<div class="author-line">Developed by <strong>Masoud Bakhshi</strong></div>',
    unsafe_allow_html=True)
st.markdown("---")

# ===========================================================================
# Helper: must be defined before any tab renders
# ===========================================================================

def _show_pi_card(title: str, pi: PIController, method: str):
    st.markdown(f"**{title}**")
    df = pd.DataFrame({
        "Quantity": ["Kp", "Ki", "Ti = Kp/Ki", "Method"],
        "Value":    [f"{pi.Kp:.6g}", f"{pi.Ki:.6g}",
                     f"{pi.Ti:.6g} s", method],
    })
    st.dataframe(df, hide_index=True, use_container_width=True)


# ===========================================================================
# Sidebar
# ===========================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    machine_type_label = st.selectbox(
        "Machine Type",
        ["EESM: Electrically Excited Synchronous Machine",
         "IPMSM: Interior Permanent Magnet Synchronous Machine",
         "IM: Induction Machine"],
        index=0,
    )
    MT = machine_type_label.split("-")[0].strip()

    st.markdown("---")

    design_method = st.selectbox(
        "Design Method",
        ["bandwidth", "symmetrical_optimum",
         "magnitude_optimum", "bandwidth_pm"],
        format_func=lambda x: {
            "bandwidth":           "Bandwidth / Pole Cancellation",
            "symmetrical_optimum": "Symmetrical Optimum",
            "magnitude_optimum":   "Magnitude Optimum",
            "bandwidth_pm":        "Bandwidth + Phase Margin",
        }[x],
    )

    disc_method = st.selectbox(
        "Discretization Method",
        ["tustin", "zoh", "forward_euler", "backward_euler", "mpz"],
        format_func=lambda x: {
            "tustin":         "Tustin / Bilinear",
            "zoh":            "Zero-Order Hold (ZOH)",
            "forward_euler":  "Forward Euler",
            "backward_euler": "Backward Euler",
            "mpz":            "Matched Pole-Zero (MPZ)",
        }[x],
    )

    st.markdown("---")
    delay_order = st.select_slider(
        "Padé Delay Order", options=[1, 2, 3], value=2)
    include_speed_loop = st.checkbox("Include Speed Loop", value=False)
    pm_target = st.slider("Phase Margin Target (°)", 30, 75, 45, step=5)

# ===========================================================================
# Tabs
# ===========================================================================

tab_params, tab_design, tab_stab, tab_export = st.tabs(
    ["📥 Parameters", "🔧 Controller Design",
     "📊 Stability Analysis", "📤 Export"]
)

# ===========================================================================
# TAB 1: Parameters
# ===========================================================================

with tab_params:
    st.markdown('<div class="section-hdr">Machine & Inverter Parameters</div>',
                unsafe_allow_html=True)
    st.info(
        "Default values are example only, replace with measured / validated data."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Stator Electrical**")
        Rs  = st.number_input("Stator resistance Rs (Ω)",
                              value=0.012, format="%.5f", min_value=1e-5)
        Ld  = st.number_input("d-axis inductance Ld (H)",
                              value=0.00045, format="%.6f", min_value=1e-7)
        Lq  = st.number_input("q-axis inductance Lq (H)",
                              value=0.00065, format="%.6f", min_value=1e-7)
        pole_pairs = int(st.number_input("Pole pairs p",
                                         value=4, min_value=1, step=1))

    with col2:
        st.markdown("**Inverter / Limits**")
        Vdc   = st.number_input("DC-link voltage Vdc (V)",
                                value=700.0, format="%.1f", min_value=1.0)
        f_pwm = int(st.number_input("PWM frequency (Hz)",
                                    value=10000, min_value=100, step=100))
        T_pwm_val = 1.0 / f_pwm
        st.caption(f"T_pwm = {T_pwm_val*1e6:.1f} µs")
        id_max = st.number_input("Max |id| (A)", value=300.0,
                                 format="%.1f", min_value=0.0)
        iq_max = st.number_input("Max |iq| (A)", value=550.0,
                                 format="%.1f", min_value=0.0)
        V_lim  = Vdc / np.sqrt(3)
        st.caption(f"V_limit (SVM) = {V_lim:.1f} V")

    with col3:
        st.markdown("**Delays & Sampling**")
        T_samp_cur_us = st.number_input("Current-loop Ts (µs)",
                                        value=100.0, format="%.1f", min_value=1.0)
        T_samp_spd_us = st.number_input("Speed-loop Ts (µs)",
                                        value=1000.0, format="%.1f", min_value=10.0)
        T_comp_us     = st.number_input("Computation delay (µs)",
                                        value=50.0, format="%.1f", min_value=0.0)
        T_adc_us      = st.number_input("ADC/sample delay (µs)",
                                        value=10.0, format="%.1f", min_value=0.0)
        T_filter_us   = st.number_input("Measurement filter delay (µs)",
                                        value=20.0, format="%.1f", min_value=0.0)

    T_samp_cur  = T_samp_cur_us  * 1e-6
    T_samp_spd  = T_samp_spd_us  * 1e-6
    T_comp      = T_comp_us      * 1e-6
    T_adc       = T_adc_us       * 1e-6
    T_filter    = T_filter_us    * 1e-6

    base_params = dict(
        Rs=Rs, Ld=Ld, Lq=Lq, pole_pairs=pole_pairs,
        Vdc=Vdc, f_pwm=float(f_pwm),
        T_pwm=T_pwm_val, T_comp=T_comp,
        T_adc=T_adc, T_filter=T_filter,
    )

    st.markdown("---")
    col4, col5 = st.columns(2)

    # ---- Machine-specific inputs ----
    if MT == "EESM":
        with col4:
            st.markdown("**EESM: Rotor Field Winding**")
            Rf   = st.number_input("Field resistance Rf (Ω)",
                                   value=0.85, format="%.4f", min_value=1e-5)
            Lf   = st.number_input("Field inductance Lf (H)",
                                   value=0.42, format="%.4f", min_value=1e-5)
            Lm   = st.number_input("Mutual inductance Lm (H)",
                                   value=0.038, format="%.5f", min_value=1e-6)
            if_nom = st.number_input("Nominal field current If_nom (A)",
                                     value=12.0, format="%.2f", min_value=0.0)
            if_max = st.number_input("Max field current If_max (A)",
                                     value=20.0, format="%.2f", min_value=0.0)
            T_comp_field_us = st.number_input(
                "Field controller comp delay (µs)", value=100.0, format="%.1f")
            T_comp_field = T_comp_field_us * 1e-6

        with col5:
            st.markdown("**EESM: Bandwidths**")
            J   = st.number_input("Inertia J (kg·m²)",
                                  value=2.5, format="%.3f", min_value=1e-5)
            B   = st.number_input("Damping B (N·m·s/rad)",
                                  value=0.05, format="%.4f", min_value=0.0)
            omega_bw_cur   = st.number_input("Stator current-loop BW (rad/s)",
                                             value=2000.0, format="%.1f", min_value=10.0)
            omega_bw_field = st.number_input("Field current-loop BW (rad/s)",
                                             value=200.0, format="%.1f", min_value=1.0)
            omega_bw_spd   = st.number_input("Speed-loop BW (rad/s)",
                                             value=50.0, format="%.1f", min_value=0.1)
            psi_f_lin = Lm * if_nom
            st.caption(f"ψ_f (linear nominal) = {psi_f_lin:.4f} Wb")

        machine_params = {**base_params,
                          "Rf": Rf, "Lf": Lf, "Lm": Lm,
                          "if_nom": if_nom, "if_max": if_max,
                          "T_comp_field": T_comp_field,
                          "J": J, "B": B}

    elif MT == "IPMSM":
        with col4:
            st.markdown("**IPMSM: PM Flux**")
            psi_pm = st.number_input("PM flux linkage ψ_pm (Wb)",
                                     value=0.085, format="%.5f", min_value=1e-6)
            omega_bw_cur = st.number_input("Current-loop BW (rad/s)",
                                           value=2000.0, format="%.1f", min_value=10.0)
            omega_bw_spd = st.number_input("Speed-loop BW (rad/s)",
                                           value=50.0, format="%.1f", min_value=0.1)
        with col5:
            st.markdown("**IPMSM: Mechanical**")
            J = st.number_input("Inertia J (kg·m²)",
                                value=2.5, format="%.3f", min_value=1e-5)
            B = st.number_input("Damping B (N·m·s/rad)",
                                value=0.05, format="%.4f", min_value=0.0)

        machine_params = {**base_params, "psi_pm": psi_pm, "J": J, "B": B}
        omega_bw_field = None
        if_max = 0.0

    else:  # IM
        with col4:
            st.markdown("**IM: Rotor**")
            Rr    = st.number_input("Rotor resistance Rr (Ω)",
                                    value=0.008, format="%.5f", min_value=1e-6)
            Ls_im = st.number_input("Stator inductance Ls (H)",
                                    value=0.00095, format="%.6f", min_value=1e-7)
            Lr_im = st.number_input("Rotor inductance Lr (H)",
                                    value=0.00092, format="%.6f", min_value=1e-7)
            Lm_im = st.number_input("Magnetizing inductance Lm (H)",
                                    value=0.00088, format="%.6f", min_value=1e-7)
            omega_bw_cur = st.number_input("Current-loop BW (rad/s)",
                                           value=2000.0, format="%.1f", min_value=10.0)
        with col5:
            st.markdown("**IM: Mechanical**")
            J = st.number_input("Inertia J (kg·m²)",
                                value=2.5, format="%.3f", min_value=1e-5)
            B = st.number_input("Damping B (N·m·s/rad)",
                                value=0.05, format="%.4f", min_value=0.0)
            omega_bw_spd = st.number_input("Speed-loop BW (rad/s)",
                                           value=50.0, format="%.1f", min_value=0.1)

        machine_params = {**base_params,
                          "Rr": Rr, "Ls": Ls_im, "Lr": Lr_im, "Lm": Lm_im,
                          "J": J, "B": B}
        omega_bw_field = None
        if_max = 0.0

    # Store params always so other tabs can reference them
    st.session_state["machine_params"]   = machine_params
    st.session_state["MT"]               = MT
    st.session_state["T_samp_cur"]       = T_samp_cur
    st.session_state["T_samp_spd"]       = T_samp_spd
    st.session_state["omega_bw_cur"]     = omega_bw_cur
    st.session_state["omega_bw_spd"]     = omega_bw_spd
    st.session_state["omega_bw_field"]   = omega_bw_field
    st.session_state["id_max"]           = id_max
    st.session_state["iq_max"]           = iq_max
    st.session_state["if_max_param"]     = if_max
    st.session_state["disc_method"]      = disc_method
    st.session_state["design_method"]    = design_method
    st.session_state["include_spd"]      = include_speed_loop

# ===========================================================================
# TAB 2: Controller Design
# ===========================================================================

with tab_design:
    st.markdown('<div class="section-hdr">Controller Design Results</div>',
                unsafe_allow_html=True)

    if st.button("▶  Run Design", type="primary", key="btn_design"):

        mp    = st.session_state["machine_params"]
        mt    = st.session_state["MT"]
        dm    = st.session_state["design_method"]
        bw    = st.session_state["omega_bw_cur"]
        bwf   = st.session_state["omega_bw_field"]
        bws   = st.session_state["omega_bw_spd"]
        Ts    = st.session_state["T_samp_cur"]
        Ts_s  = st.session_state["T_samp_spd"]
        disc  = st.session_state["disc_method"]
        do_spd = st.session_state["include_spd"]

        T_del = total_delay_s(mp)

        if mt == "EESM":
            mdl = EESMModel(mp)
            G_d = mdl.plant_d(delay_order=delay_order)
            G_q = mdl.plant_q(delay_order=delay_order)
            pi_d = design_current_pi(mp["Rs"], mp["Ld"], T_del, dm, bw, pm_target)
            pi_q = design_current_pi(mp["Rs"], mp["Lq"], T_del, dm, bw, pm_target)
            T_del_f = mp.get("T_comp_field", T_del)
            G_f  = mdl.plant_field(delay_order=delay_order)
            pi_f = design_current_pi(mp["Rf"], mp["Lf"], T_del_f,
                                     dm, bwf, pm_target)

        elif mt == "IPMSM":
            mdl = IPMSMModel(mp)
            G_d = mdl.plant_d(delay_order=delay_order)
            G_q = mdl.plant_q(delay_order=delay_order)
            pi_d = design_current_pi(mp["Rs"], mp["Ld"], T_del, dm, bw, pm_target)
            pi_q = design_current_pi(mp["Rs"], mp["Lq"], T_del, dm, bw, pm_target)
            G_f, pi_f = None, None

        else:  # IM
            mdl = IMModel(mp)
            G_d = mdl.plant_sd(delay_order=delay_order)
            G_q = mdl.plant_sq(delay_order=delay_order)
            pi_d = design_current_pi(mdl.R_eff, mdl.L_eff, T_del, dm, bw, pm_target)
            pi_q = design_current_pi(mdl.R_eff, mdl.L_eff, T_del, dm, bw, pm_target)
            G_f, pi_f = None, None

        pi_spd = None
        if do_spd:
            T_del_spd = 3.0 / bw
            pi_spd = design_speed_pi(mp["J"], mp["B"], T_del_spd,
                                     bws, pm_target)

        # Discrete
        dr_d   = discretize_pi(pi_d.Kp, pi_d.Ki, Ts, disc)
        dr_q   = discretize_pi(pi_q.Kp, pi_q.Ki, Ts, disc)
        dr_f   = discretize_pi(pi_f.Kp, pi_f.Ki, Ts, disc) if pi_f else None
        dr_spd = (discretize_pi(pi_spd.Kp, pi_spd.Ki, Ts_s, disc)
                  if pi_spd else None)

        st.session_state.update({
            "model": mdl,
            "G_d": G_d, "G_q": G_q, "G_f": G_f,
            "pi_d": pi_d, "pi_q": pi_q, "pi_f": pi_f, "pi_spd": pi_spd,
            "dr_d": dr_d, "dr_q": dr_q, "dr_f": dr_f, "dr_spd": dr_spd,
            "T_del_total": T_del,
            "design_done": True,
        })

    if st.session_state.get("design_done"):
        pi_d   = st.session_state["pi_d"]
        pi_q   = st.session_state["pi_q"]
        pi_f   = st.session_state.get("pi_f")
        pi_spd = st.session_state.get("pi_spd")
        dr_d   = st.session_state["dr_d"]
        dr_q   = st.session_state["dr_q"]
        dr_f   = st.session_state.get("dr_f")
        dr_spd = st.session_state.get("dr_spd")
        dm     = st.session_state["design_method"]

        colA, colB = st.columns(2)
        with colA:
            _show_pi_card("d-axis Current PI", pi_d, dm)
        with colB:
            _show_pi_card("q-axis Current PI", pi_q, dm)

        if pi_f:
            colC, _ = st.columns(2)
            with colC:
                _show_pi_card("Field Excitation Current PI", pi_f, dm)

        if pi_spd:
            colE, _ = st.columns(2)
            with colE:
                _show_pi_card("Speed PI", pi_spd, dm)

        # --- Discrete coefficients table ---
        st.markdown("---")
        st.markdown("#### Discrete-Time Coefficients")

        ch_names = ["d-axis", "q-axis"]
        pis_list = [pi_d, pi_q]
        drs_list = [dr_d, dr_q]
        if pi_f:
            ch_names.append("Field")
            pis_list.append(pi_f)
            drs_list.append(dr_f)
        if pi_spd:
            ch_names.append("Speed")
            pis_list.append(pi_spd)
            drs_list.append(dr_spd)

        rows = []
        for ch, pi, dr in zip(ch_names, pis_list, drs_list):
            rows.append({
                "Channel": ch,
                "Kp":      f"{pi.Kp:.5g}",
                "Ki (CT)": f"{pi.Ki:.5g}",
                "b0":      f"{dr.b0:.5g}" if dr else "-",
                "b1":      f"{dr.b1:.5g}" if dr else "-",
                "Ki_d":    f"{dr.Ki_d:.5g}" if dr else "-",
                "Method":  dr.method if dr else "-",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True,
                     use_container_width=True)

        st.markdown("**Difference equation** (position form):")
        st.code("u[k] = u[k-1]  +  b0 · e[k]  +  b1 · e[k-1]")

        # --- C snippets ---
        st.markdown("---")
        st.markdown("#### Embedded C Code")
        iq_lim = st.session_state.get("iq_max", 550.0)
        id_lim = st.session_state.get("id_max", 300.0)
        if_lim = st.session_state.get("if_max_param", 20.0)

        with st.expander("d-axis C snippet"):
            st.code(generate_c_snippet("id_ctrl", dr_d, id_lim), language="c")
        with st.expander("q-axis C snippet"):
            st.code(generate_c_snippet("iq_ctrl", dr_q, iq_lim), language="c")
        if dr_f:
            with st.expander("Field current C snippet"):
                st.code(generate_c_snippet("if_ctrl", dr_f, if_lim), language="c")
        if dr_spd:
            with st.expander("Speed C snippet"):
                st.code(generate_c_snippet("spd_ctrl", dr_spd, iq_lim), language="c")
    else:
        st.info("Set parameters in the **Parameters** tab, then click **▶ Run Design**.")

# ===========================================================================
# TAB 3: Stability Analysis
# ===========================================================================

with tab_stab:
    st.markdown('<div class="section-hdr">Stability & Robustness Analysis</div>',
                unsafe_allow_html=True)

    if st.button("▶  Run Stability Analysis", type="primary", key="btn_stab"):
        if not st.session_state.get("design_done"):
            st.warning("Run controller design first.")
        else:
            pi_d  = st.session_state["pi_d"]
            pi_q  = st.session_state["pi_q"]
            pi_f  = st.session_state.get("pi_f")
            G_d   = st.session_state["G_d"]
            G_q   = st.session_state["G_q"]
            G_f   = st.session_state.get("G_f")
            mp    = st.session_state["machine_params"]
            mt    = st.session_state["MT"]
            T_del = st.session_state["T_del_total"]
            disc  = st.session_state["disc_method"]
            Ts    = st.session_state["T_samp_cur"]

            stab_results = {}
            stab_figs    = {}

            channels = [("d-axis", pi_d, G_d), ("q-axis", pi_q, G_q)]
            if pi_f and G_f:
                channels.append(("Field", pi_f, G_f))

            for ch_name, pi, G_plant in channels:
                L_tf = build_loop_tf(pi, G_plant)
                T_tf = build_closed_loop_tf(pi, G_plant)
                S_tf = build_sensitivity_tf(pi, G_plant)

                sr = analyse_loop(L_tf, T_tf, S_tf, label=ch_name)

                try:
                    G_dt = discretize_plant(G_plant, Ts, method=disc)
                    d_poles = closed_loop_discrete_poles(pi.Kp, pi.Ki, G_dt)
                    sr.discrete_stable, sr.worst_pole_z_mag = \
                        check_discrete_stability(d_poles)
                    sr.discrete_poles = d_poles
                except Exception as ex:
                    sr.warnings.append(f"Discrete check failed: {ex}")

                stab_results[ch_name] = sr

                ch_figs = full_analysis_figures(L_tf, T_tf, S_tf, ch_name)
                for k, f in ch_figs.items():
                    stab_figs[f"{ch_name}: {k}"] = f

            # Parameter sweeps for d-axis
            R_nom = mp["Rs"]
            L_nom = mp["Ld"]
            Ra, pm_r, gm_r = resistance_sensitivity_sweep(
                R_nom, L_nom, pi_d.Kp, pi_d.Ki, T_del)
            La, pm_l, gm_l = inductance_sensitivity_sweep(
                R_nom, L_nom, pi_d.Kp, pi_d.Ki, T_del)
            Ta, pm_t, gm_t = delay_sensitivity_sweep(
                R_nom, L_nom, pi_d.Kp, pi_d.Ki, T_del)

            stab_figs["Resistance Sensitivity (d)"] = sensitivity_sweep_figure(
                Ra, pm_r, gm_r, "R (Ω)", R_nom, "R Sensitivity: d-axis")
            stab_figs["Inductance Sensitivity (d)"] = sensitivity_sweep_figure(
                La, pm_l, gm_l, "L (H)", L_nom, "L Sensitivity: d-axis")
            stab_figs["Delay Sensitivity (d)"] = sensitivity_sweep_figure(
                Ta * 1e6, pm_t, gm_t, "T_delay (µs)",
                T_del * 1e6, "Delay Sensitivity: d-axis")

            st.session_state["stab_results"] = stab_results
            st.session_state["stab_figs"]    = stab_figs
            st.session_state["stab_done"]    = True

    if st.session_state.get("stab_done"):
        stab_results = st.session_state["stab_results"]
        stab_figs    = st.session_state["stab_figs"]

        for ch_name, sr in stab_results.items():
            st.markdown(f"#### {ch_name} Channel")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Phase Margin",
                      f"{sr.phase_margin_deg:.1f}°",
                      delta="OK" if sr.phase_margin_deg >= 45 else "LOW",
                      delta_color="normal" if sr.phase_margin_deg >= 45 else "inverse")
            c2.metric("Gain Margin",
                      f"{sr.gain_margin_db:.1f} dB",
                      delta="OK" if sr.gain_margin_db >= 6 else "LOW",
                      delta_color="normal" if sr.gain_margin_db >= 6 else "inverse")
            c3.metric("CL BW (−3 dB)", f"{sr.bandwidth_cl:.0f} rad/s")
            c4.metric("Overshoot",     f"{sr.overshoot_pct:.1f}%")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Rise Time",     f"{sr.rise_time_ms:.2f} ms")
            c6.metric("Settling Time", f"{sr.settling_time_ms:.2f} ms")
            c7.metric("Ms (peak)",     f"{sr.Ms:.3f}",
                      delta="OK" if sr.Ms < 2.0 else "HIGH",
                      delta_color="normal" if sr.Ms < 2.0 else "inverse")
            c8.metric("DT Stable",
                      "Yes" if sr.discrete_stable else "No",
                      delta="OK" if sr.discrete_stable else "FAIL",
                      delta_color="normal" if sr.discrete_stable else "inverse")

            for w in sr.warnings:
                st.warning(w)

            if len(sr.discrete_poles):
                with st.expander(f"{ch_name}: Discrete closed-loop poles"):
                    pole_df = pd.DataFrame({
                        "Re": sr.discrete_poles.real,
                        "Im": sr.discrete_poles.imag,
                        "|z|": np.abs(sr.discrete_poles),
                    })
                    st.dataframe(pole_df, use_container_width=True)

            st.markdown("---")

        st.markdown("#### Plots")
        fig_names = list(stab_figs.keys())
        sel = st.selectbox("Select plot", fig_names, key="sel_fig")
        fig_obj = stab_figs.get(sel)
        if fig_obj:
            st.pyplot(fig_obj, use_container_width=True)
    else:
        st.info("Run design first, then click **▶ Run Stability Analysis**.")

# ===========================================================================
# TAB 4: Export
# ===========================================================================

with tab_export:
    st.markdown('<div class="section-hdr">Export Results</div>',
                unsafe_allow_html=True)

    if not st.session_state.get("design_done"):
        st.info("Run the controller design first to enable export.")
    else:
        pi_d   = st.session_state["pi_d"]
        pi_q   = st.session_state["pi_q"]
        pi_f   = st.session_state.get("pi_f")
        pi_spd = st.session_state.get("pi_spd")
        dr_d   = st.session_state["dr_d"]
        dr_q   = st.session_state["dr_q"]
        dr_f   = st.session_state.get("dr_f")
        dr_spd = st.session_state.get("dr_spd")
        mt     = st.session_state["MT"]
        mp     = st.session_state["machine_params"]
        dm     = st.session_state["design_method"]
        disc   = st.session_state["disc_method"]
        bw     = st.session_state["omega_bw_cur"]
        bwf    = st.session_state.get("omega_bw_field")
        bws    = st.session_state["omega_bw_spd"]
        iq_lim = st.session_state.get("iq_max", 550.0)
        id_lim = st.session_state.get("id_max", 300.0)
        if_lim = st.session_state.get("if_max_param", 20.0)

        col_e1, col_e2 = st.columns(2)

        # ---- JSON gains ----
        with col_e1:
            st.markdown("**Controller Gains (JSON)**")
            gains = {
                "machine_type": mt,
                "author":       "Masoud Bakhshi",
                "design_method": dm,
                "discretization": disc,
                "d_axis": {"Kp": pi_d.Kp, "Ki": pi_d.Ki, "Ti": pi_d.Ti,
                           "b0": dr_d.b0, "b1": dr_d.b1},
                "q_axis": {"Kp": pi_q.Kp, "Ki": pi_q.Ki, "Ti": pi_q.Ti,
                           "b0": dr_q.b0, "b1": dr_q.b1},
            }
            if pi_f and dr_f:
                gains["field"] = {"Kp": pi_f.Kp, "Ki": pi_f.Ki, "Ti": pi_f.Ti,
                                   "b0": dr_f.b0, "b1": dr_f.b1}
            if pi_spd and dr_spd:
                gains["speed"] = {"Kp": pi_spd.Kp, "Ki": pi_spd.Ki,
                                   "Ti": pi_spd.Ti, "b0": dr_spd.b0,
                                   "b1": dr_spd.b1}

            st.download_button(
                "⬇ Download gains.json",
                data=json.dumps(gains, indent=2).encode(),
                file_name="controller_gains.json",
                mime="application/json",
            )

        # ---- C code ----
        with col_e2:
            st.markdown("**Embedded C Code**")
            c_snippets = {}
            c_snippets["id_ctrl"] = generate_c_snippet("id_ctrl", dr_d, id_lim)
            c_snippets["iq_ctrl"] = generate_c_snippet("iq_ctrl", dr_q, iq_lim)
            if dr_f:
                c_snippets["if_ctrl"] = generate_c_snippet("if_ctrl", dr_f, if_lim)
            if dr_spd:
                c_snippets["spd_ctrl"] = generate_c_snippet("spd_ctrl", dr_spd, iq_lim)

            st.download_button(
                "⬇ Download pi_controllers.c",
                data="\n\n".join(c_snippets.values()).encode(),
                file_name="pi_controllers.c",
                mime="text/plain",
            )

        # ---- Word report ----
        st.markdown("---")
        st.markdown("**Full Word Document Report**")

        if st.button("📄  Generate Word Report", type="primary", key="btn_report"):
            with st.spinner("Building report…"):
                stab_results = st.session_state.get("stab_results", {})
                stab_figs    = st.session_state.get("stab_figs", {})

                design_res = {
                    "d-axis": {"method": dm, "Kp": pi_d.Kp,
                               "Ki": pi_d.Ki, "Ti": pi_d.Ti,
                               "omega_bw": bw},
                    "q-axis": {"method": dm, "Kp": pi_q.Kp,
                               "Ki": pi_q.Ki, "Ti": pi_q.Ti,
                               "omega_bw": bw},
                }
                if pi_f:
                    design_res["Field"] = {"method": dm, "Kp": pi_f.Kp,
                                           "Ki": pi_f.Ki, "Ti": pi_f.Ti,
                                           "omega_bw": bwf}
                if pi_spd:
                    design_res["Speed"] = {"method": dm, "Kp": pi_spd.Kp,
                                           "Ki": pi_spd.Ki, "Ti": pi_spd.Ti,
                                           "omega_bw": bws}

                disc_res = {}
                for ch, dr in [("d-axis", dr_d), ("q-axis", dr_q),
                                ("Field", dr_f), ("Speed", dr_spd)]:
                    if dr:
                        disc_res[ch] = dr

                docx_bytes = generate_report(
                    machine_type=mt,
                    params=mp,
                    design_results=design_res,
                    stability_reports=stab_results,
                    figures=stab_figs,
                    discrete_results=disc_res,
                    c_snippets=c_snippets,
                )

            st.download_button(
                "⬇ Download Report.docx",
                data=docx_bytes,
                file_name=f"ControllerDesign_{mt}_Report.docx",
                mime="application/vnd.openxmlformats-officedocument"
                     ".wordprocessingml.document",
            )
            st.success("Report ready.")

# ===========================================================================
# Footer
# ===========================================================================

st.markdown("---")
st.markdown(
    "<small style='color:#90a4ae;'>"
    "CurrentControllerDesigner v1.0 &nbsp;|&nbsp; "
    "Developed by <strong>Masoud Bakhshi</strong> &nbsp;|&nbsp; "
    "For pre-design and stability verification only. "
    "Validate all results before deployment in safety-critical systems."
    "</small>",
    unsafe_allow_html=True,
)
