"""Embedded firmware & PWM calculators: timer, pulse width, dead time, discrete PI, ADC, Q-format, dB."""
import numpy as np
import streamlit as st
from utils.formatting import show_formula, show_warning, engineering_note, show_info
from utils.validation import require_positive, collect_errors


def render():
    st.header("Embedded Firmware / PWM Calculators")
    tabs = st.tabs([
        "⏱️ PWM Timer",
        "📏 Min Pulse Width",
        "💀 Dead-Time Error",
        "🔢 Discrete PI",
        "📡 ADC Scaling",
        "🔢 Q-Format",
        "📊 dB & Gain",
        "🖥️ CPU Load / ISR",
    ])
    with tabs[0]: _pwm_timer()
    with tabs[1]: _min_pulse_width()
    with tabs[2]: _dead_time_error()
    with tabs[3]: _discrete_pi()
    with tabs[4]: _adc_scaling()
    with tabs[5]: _q_format()
    with tabs[6]: _db_gain()
    with tabs[7]: _cpu_load()


# ── PWM Timer ─────────────────────────────────────────────────────────────────

def _pwm_timer():
    st.subheader("PWM Timer Register Calculator")
    engineering_note(
        "Computes timer period register (TBPRD / ARR) for a given clock and PWM frequency. "
        "Generic — applicable to TI C2000, STM32, Infineon TriCore, NXP S32 family."
    )
    col1, col2 = st.columns(2)
    with col1:
        f_clk = st.number_input("Timer clock f_clk [MHz]", value=200.0, min_value=0.0,
                                key="pwm_fclk") * 1e6
        f_pwm = st.number_input("Desired PWM frequency f_pwm [kHz]", value=10.0, min_value=0.0,
                                key="pwm_fpwm") * 1e3
        mode = st.selectbox("Count mode", ["Up-count (edge-aligned)", "Up-down (center-aligned)"],
                            key="pwm_mode")
        resolution_bits = st.number_input("Timer resolution (bits)", value=16, min_value=8,
                                          max_value=32, step=1, key="pwm_res")

    errs = collect_errors(require_positive(f_clk, "f_clk"), require_positive(f_pwm, "f_pwm"))
    if errs:
        for e in errs: show_warning(e)
        return

    if "edge" in mode.lower():
        tbprd = f_clk / f_pwm - 1
        f_actual = f_clk / (tbprd + 1)
        formula = r"\mathrm{TBPRD} = \frac{f_{clk}}{f_{pwm}} - 1"
    else:
        tbprd = f_clk / (2 * f_pwm)
        f_actual = f_clk / (2 * tbprd)
        formula = r"\mathrm{TBPRD} = \frac{f_{clk}}{2\,f_{pwm}}"

    tbprd_int = int(round(tbprd))
    f_error_ppm = abs(f_actual - f_pwm) / f_pwm * 1e6 if "edge" not in mode.lower() else \
        abs(f_clk / (tbprd_int + 1) - f_pwm) / f_pwm * 1e6
    max_count = 2**resolution_bits - 1
    duty_resolution_bits = np.log2(tbprd_int + 1) if tbprd_int > 0 else 0

    with col2:
        st.metric("TBPRD / ARR (integer)", f"{tbprd_int}")
        st.metric("Actual f_pwm [kHz]", f"{f_actual/1000:.4f}")
        st.metric("Frequency error [ppm]", f"{f_error_ppm:.1f}")
        st.metric("Duty resolution [bits]", f"{duty_resolution_bits:.2f}")
        st.metric("Duty steps", f"{tbprd_int + 1}")

    if tbprd_int > max_count:
        show_warning(f"TBPRD ({tbprd_int}) exceeds {resolution_bits}-bit register max ({max_count}). "
                     "Increase prescaler or clock divider.")

    with st.expander("Formulas & Notes"):
        show_formula(formula)
        engineering_note(
            "<b>Edge-aligned (up-count):</b> Period = (TBPRD+1) / f_clk. Duty ripple occurs at f_pwm.<br>"
            "<b>Center-aligned (up-down):</b> Period = 2·TBPRD / f_clk. Symmetrical carrier — "
            "preferred for motor control (natural harmonic cancellation).<br>"
            "<b>Common mistake:</b> forgetting that center-aligned halves the effective period count."
        )


# ── Minimum Pulse Width ────────────────────────────────────────────────────────

def _min_pulse_width():
    st.subheader("Minimum Pulse Width Checker")
    engineering_note(
        "Checks whether high/low pulse widths remain above the minimum gate-driver and "
        "power-device requirement. Violation causes shoot-through risk or gate-drive malfunction."
    )
    col1, col2 = st.columns(2)
    with col1:
        f_pwm = st.number_input("PWM frequency [kHz]", value=10.0, min_value=0.0,
                                key="mpw_fpwm") * 1e3
        d = st.slider("Duty cycle D", 0.0, 1.0, 0.5, 0.001, key="mpw_d")
        t_dead = st.number_input("Dead time t_dead [ns]", value=500.0, min_value=0.0,
                                 key="mpw_td") * 1e-9
        t_min = st.number_input("Min allowed pulse width t_min [ns]", value=1000.0, min_value=0.0,
                                key="mpw_tmin") * 1e-9
        update_mode = st.selectbox("Update mode", ["Single (once per period)", "Double (twice per period)"],
                                   key="mpw_mode")

    errs = collect_errors(require_positive(f_pwm, "f_pwm"))
    if errs:
        for e in errs: show_warning(e)
        return

    T_pwm = 1 / f_pwm
    if "double" in update_mode.lower():
        T_pwm_eff = T_pwm / 2
    else:
        T_pwm_eff = T_pwm

    T_on = d * T_pwm_eff
    T_off = (1 - d) * T_pwm_eff
    T_on_eff = T_on - t_dead
    T_off_eff = T_off - t_dead

    with col2:
        st.metric("T_pwm [µs]", f"{T_pwm*1e6:.3f}")
        st.metric("T_on [µs]", f"{T_on*1e6:.3f}")
        st.metric("T_off [µs]", f"{T_off*1e6:.3f}")
        st.metric("T_on after dead time [µs]", f"{T_on_eff*1e6:.3f}")
        st.metric("T_off after dead time [µs]", f"{T_off_eff*1e6:.3f}")

    on_ok = T_on_eff >= t_min
    off_ok = T_off_eff >= t_min
    if on_ok and off_ok:
        st.success("✅ Both high and low pulses are above minimum width.")
    else:
        if not on_ok:
            st.error(f"🔴 T_on too short ({T_on_eff*1e6:.3f} µs < {t_min*1e6:.3f} µs min).")
        if not off_ok:
            st.error(f"🔴 T_off too short ({T_off_eff*1e6:.3f} µs < {t_min*1e6:.3f} µs min).")

    # Safe duty range
    d_min_safe = (t_min + t_dead) / T_pwm_eff
    d_max_safe = 1 - (t_min + t_dead) / T_pwm_eff
    st.metric("Safe duty range", f"{d_min_safe*100:.2f}% – {d_max_safe*100:.2f}%")

    with st.expander("Formulas"):
        show_formula(
            r"T_{on} = D\,T_{pwm} \qquad T_{off} = (1-D)\,T_{pwm}"
        )
        show_formula(
            r"T_{on,eff} = T_{on} - t_{dead} \geq t_{min}"
        )
        engineering_note(
            "Double update mode halves the effective period for pulse width calculations. "
            "<b>Common mistake:</b> ignoring dead time when checking minimum pulse — "
            "gate driver requires t_min measured from actual gate signal, not modulator output."
        )


# ── Dead-Time Voltage Error ────────────────────────────────────────────────────

def _dead_time_error():
    st.subheader("Dead-Time Voltage Error Estimator")
    engineering_note(
        "Estimates the average voltage error caused by dead time insertion. "
        "Dead time always opposes current direction — creates a fundamental distortion, "
        "particularly visible at low speed and low current (small back-EMF)."
    )
    col1, col2 = st.columns(2)
    with col1:
        vdc = st.number_input("V_dc [V]", value=400.0, min_value=0.0, key="dt_vdc")
        t_dead = st.number_input("Dead time t_dead [ns]", value=500.0, min_value=0.0,
                                 key="dt_td") * 1e-9
        f_sw = st.number_input("Switching frequency f_sw [kHz]", value=10.0, min_value=0.0,
                               key="dt_fsw") * 1e3

    errs = collect_errors(require_positive(f_sw, "f_sw"))
    if errs:
        for e in errs: show_warning(e)
        return

    T_sw = 1 / f_sw
    delta_v = vdc * t_dead / T_sw
    delta_v_pct = delta_v / (vdc / 2) * 100

    with col2:
        st.metric("T_sw [µs]", f"{T_sw*1e6:.3f}")
        st.metric("ΔV_avg per leg [V]", f"{delta_v:.4f}")
        st.metric("ΔV as % of V_phase_peak", f"{delta_v_pct:.3f}%")
        st.metric("Estimated line-line distortion [V]", f"{delta_v*2:.4f}")

    show_info("This simplified estimate assumes ideal switches and rectangular current waveform. "
              "Actual distortion depends on current waveform and device characteristics.")

    with st.expander("Formula & Notes"):
        show_formula(r"\Delta V \approx V_{dc}\,\frac{t_{dead}}{T_{sw}}")
        engineering_note(
            "<b>Effect:</b> Low-order voltage harmonics (6th, 12th in line-line) → torque ripple.<br>"
            "<b>Compensation:</b> Measure current direction and add/subtract t_dead correction to duty cycle.<br>"
            "<b>Worst case:</b> Low speed, low current — distortion is highest relative to fundamental.<br>"
            "<b>Common mistake:</b> ignoring dead-time effect in closed-loop current controller — "
            "the controller partially compensates, but residual distortion remains."
        )


# ── Discrete PI ───────────────────────────────────────────────────────────────

def _discrete_pi():
    st.subheader("Discrete-Time PI Controller Coefficient Calculator")
    engineering_note(
        "Converts continuous-time PI gains to discrete difference equation coefficients. "
        "Choose discretization method based on stability and implementation requirements."
    )
    col1, col2 = st.columns(2)
    with col1:
        kp = st.number_input("Proportional gain K_p", value=1.0, key="dpi_kp")
        ki = st.number_input("Integral gain K_i [1/s]", value=100.0, key="dpi_ki")
        ts = st.number_input("Sampling period T_s [µs]", value=100.0, min_value=0.01,
                             key="dpi_ts") * 1e-6
        method = st.selectbox("Discretization method",
                              ["Tustin (bilinear)", "Forward Euler", "Backward Euler"],
                              key="dpi_method")

    if "tustin" in method.lower():
        b0 = kp + ki * ts / 2
        b1 = -kp + ki * ts / 2
        eq = "u[k] = u[k-1] + b0·e[k] + b1·e[k-1]"
        method_note = "Tustin maps s=0 to z=1 (DC accurate) and s=jω to |z|=1 (stable). Recommended for control loops."
    elif "forward" in method.lower():
        b0 = kp
        b1 = ki * ts - kp
        eq = "u[k] = u[k-1] + b0·e[k] + b1·e[k-1]  (forward Euler integration)"
        method_note = "Forward Euler: integrator maps s=0→z=1. Can be unstable at large T_s·K_i. Simple but less accurate."
    else:
        b0 = kp + ki * ts
        b1 = -kp
        eq = "u[k] = u[k-1] + b0·e[k] + b1·e[k-1]  (backward Euler integration)"
        method_note = "Backward Euler: always stable integrator, but introduces phase lag at high frequencies."

    with col2:
        st.metric("b0", f"{b0:.8f}")
        st.metric("b1", f"{b1:.8f}")
        st.markdown(f"**Difference equation:**")
        st.code(eq)
        show_info(method_note)

    with st.expander("Formulas & Implementation Notes"):
        show_formula(
            r"\text{Tustin: } b_0 = K_p + K_i\frac{T_s}{2}, \quad b_1 = -K_p + K_i\frac{T_s}{2}"
        )
        st.markdown("""
**Implementation (C pseudocode):**
```c
float pi_update(float e) {
    float u = u_prev + b0 * e + b1 * e_prev;
    u = clamp(u, u_min, u_max);  // anti-windup clamping
    e_prev = e;
    u_prev = u;
    return u;
}
```
""")
        engineering_note(
            "<b>Anti-windup is mandatory</b> — without it, integrator winds up during saturation "
            "and causes large transients on recovery. "
            "Options: clamping (clamp u before storing u_prev) or back-calculation."
        )


# ── ADC Scaling ───────────────────────────────────────────────────────────────

def _adc_scaling():
    st.subheader("ADC & Sensor Scaling Calculator")
    engineering_note(
        "Converts raw ADC counts to physical values, accounting for sensor gain, offset, "
        "and ADC reference voltage. Used for current, voltage, and temperature sensing."
    )
    col1, col2 = st.columns(2)
    with col1:
        n_bits = st.number_input("ADC resolution [bits]", value=12, min_value=8, max_value=24,
                                 step=1, key="adc_bits")
        v_ref = st.number_input("ADC reference voltage V_ref [V]", value=3.3, min_value=0.0,
                                key="adc_vref")
        sensor_gain = st.number_input("Sensor gain [V / physical_unit]", value=0.066,
                                      format="%.6f", key="adc_gain",
                                      help="e.g. 0.066 V/A for a 50A/3.3V hall sensor")
        sensor_offset_v = st.number_input("Sensor offset [V] (0 = no offset)", value=1.65,
                                          key="adc_offset",
                                          help="Midpoint voltage for bipolar sensors")
    with col2:
        adc_count = st.number_input("Measured ADC count", value=2048, min_value=0,
                                    max_value=2**24 - 1, step=1, key="adc_count")

    full_scale = 2**n_bits
    lsb_v = v_ref / full_scale
    v_measured = adc_count * lsb_v
    physical_value = (v_measured - sensor_offset_v) / sensor_gain if sensor_gain != 0 else 0
    quant_error_phys = lsb_v / sensor_gain if sensor_gain != 0 else 0
    range_phys = v_ref / sensor_gain if sensor_gain != 0 else 0

    st.metric("ADC LSB [mV]", f"{lsb_v*1000:.4f}")
    st.metric("Measured voltage [V]", f"{v_measured:.5f}")
    st.metric("Physical value", f"{physical_value:.5f}")
    st.metric("Resolution (1 LSB in phys. units)", f"{quant_error_phys:.6f}")
    st.metric("Full-scale range [phys. units]", f"{range_phys:.4f}")

    with st.expander("Formulas & Notes"):
        show_formula(r"\mathrm{LSB} = \frac{V_{ref}}{2^N}")
        show_formula(r"V_{meas} = \mathrm{count}\cdot\mathrm{LSB}")
        show_formula(r"\mathrm{Physical} = \frac{V_{meas} - V_{offset}}{G_{sensor}}")
        engineering_note(
            "<b>Bipolar sensors</b> (e.g. current via Hall effect) have V_offset = V_ref/2 "
            "to represent ±range symmetrically. "
            "Always verify calibration: measure zero and full-scale with a reference instrument."
        )


# ── Q-Format ──────────────────────────────────────────────────────────────────

def _q_format():
    st.subheader("Fixed-Point Q-Format Calculator")
    engineering_note(
        "Determines Q-format and representable range for fixed-point arithmetic. "
        "Used in DSP and embedded motor-control firmware."
    )
    col1, col2 = st.columns(2)
    with col1:
        word_bits = st.number_input("Word length [bits]", value=16, min_value=4, max_value=64,
                                    step=1, key="qf_wl")
        frac_bits = st.number_input("Fractional bits (Q number)", value=15, min_value=0,
                                    max_value=63, step=1, key="qf_frac")
        signed = st.checkbox("Signed (two's complement)", value=True, key="qf_signed")
        signal_max = st.number_input("Expected max signal value", value=1.0, key="qf_sig_max")

    frac_bits = min(frac_bits, word_bits - (1 if signed else 0))
    int_bits = word_bits - frac_bits - (1 if signed else 0)

    resolution = 2**(-frac_bits)
    if signed:
        val_max = (2**(word_bits - 1) - 1) * resolution
        val_min = -(2**(word_bits - 1)) * resolution
    else:
        val_max = (2**word_bits - 1) * resolution
        val_min = 0.0

    scale_factor = 2**frac_bits
    overflow = signal_max > val_max
    headroom = val_max / signal_max if signal_max != 0 else float("inf")

    with col2:
        q_name = f"Q{int_bits}.{frac_bits}" if not signed else f"IQ{frac_bits}"
        st.metric("Q-format name", q_name)
        st.metric("Resolution (1 LSB)", f"{resolution:.10f}")
        st.metric("Representable max", f"{val_max:.6f}")
        st.metric("Representable min", f"{val_min:.6f}")
        st.metric("Scale factor (LSB multiplier)", f"{scale_factor:.0f}")
        st.metric("Headroom (val_max / signal_max)", f"{headroom:.3f}")

    if overflow:
        st.error(f"🔴 Overflow: signal_max ({signal_max}) > representable max ({val_max:.4f}). "
                 "Reduce fractional bits or increase word length.")
    else:
        st.success(f"✅ No overflow. {headroom:.2f}× headroom available.")

    st.markdown(f"""
**C macro suggestion:**
```c
#define Q{frac_bits}_SCALE  {int(scale_factor)}
#define FLOAT_TO_Q{frac_bits}(x)  (({('int16_t' if word_bits <= 16 else 'int32_t') if signed else ('uint16_t' if word_bits <= 16 else 'uint32_t')})((x) * Q{frac_bits}_SCALE))
#define Q{frac_bits}_TO_FLOAT(x)  ((float)(x) / Q{frac_bits}_SCALE)
```
""")

    with st.expander("Notes"):
        engineering_note(
            "<b>TI IQmath library</b> uses GLOBAL_Q format (default Q24 for C28x). "
            "<b>ARM CMSIS DSP</b> uses q15_t and q31_t. "
            "Always reserve at least 2 integer bits for intermediate multiplication results to avoid overflow. "
            "<b>Common mistake:</b> multiplying two Q15 numbers and storing in Q15 without arithmetic right-shift by 15."
        )


# ── dB & Gain ─────────────────────────────────────────────────────────────────

def _db_gain():
    st.subheader("dB and Linear Gain Converter")
    engineering_note("Converts between linear amplitude/power ratios and decibels. Specify mode carefully.")
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("Quantity type", ["Voltage / Current (amplitude)", "Power"], key="db_mode")
        linear = st.number_input("Linear ratio (output/input)", value=10.0, min_value=0.0,
                                 format="%g", key="db_lin")
        db_val = st.number_input("dB value (leave 0 to compute)", value=0.0, key="db_db")

    if db_val == 0 and linear > 0:
        if "amplitude" in mode.lower():
            db_out = 20 * np.log10(linear)
        else:
            db_out = 10 * np.log10(linear)
        lin_out = linear
    elif db_val != 0:
        db_out = db_val
        if "amplitude" in mode.lower():
            lin_out = 10 ** (db_val / 20)
        else:
            lin_out = 10 ** (db_val / 10)
    else:
        show_warning("Enter either a nonzero linear ratio or dB value.")
        return

    with col2:
        st.metric("Linear ratio", f"{lin_out:.6g}")
        st.metric("dB value", f"{db_out:.4f} dB")

    with st.expander("Formulas"):
        show_formula(
            r"G_{dB} = 20\log_{10}(G) \;\text{(amplitude)} \qquad "
            r"G_{dB} = 10\log_{10}(P_{ratio}) \;\text{(power)}"
        )
        engineering_note(
            "Remember: 6 dB ≈ ×2 amplitude, 20 dB = ×10 amplitude, 3 dB ≈ ×2 power. "
            "<b>Common mistake:</b> using 20 log₁₀ for power ratios — must use 10 log₁₀."
        )


# ── CPU Load / ISR Timing ─────────────────────────────────────────────────────

def _cpu_load():
    st.subheader("CPU Load & ISR Timing Calculator")
    engineering_note(
        "Estimates CPU load from interrupt service routines (ISRs). "
        "Critical for real-time motor control — current-loop ISR must complete within one PWM period."
    )
    col1, col2 = st.columns(2)
    with col1:
        f_cpu = st.number_input("CPU clock f_cpu [MHz]", value=200.0, min_value=0.0,
                                key="cpu_fclk") * 1e6
        f_isr = st.number_input("ISR frequency f_isr [kHz]", value=10.0, min_value=0.0,
                                key="cpu_fisr") * 1e3
        isr_cycles = st.number_input("ISR execution time [CPU cycles]", value=2000, min_value=0,
                                     step=100, key="cpu_cyc")

    T_isr_period = 1 / f_isr if f_isr > 0 else float("inf")
    isr_exec_s = isr_cycles / f_cpu if f_cpu > 0 else 0
    cpu_load = isr_exec_s / T_isr_period * 100
    cycles_available = int(T_isr_period * f_cpu)
    margin_cycles = cycles_available - isr_cycles

    with col2:
        st.metric("ISR period [µs]", f"{T_isr_period*1e6:.3f}")
        st.metric("ISR execution time [µs]", f"{isr_exec_s*1e6:.3f}")
        st.metric("CPU load [%]", f"{cpu_load:.2f}")
        st.metric("Available cycles per ISR", f"{cycles_available}")
        st.metric("Margin [cycles]", f"{margin_cycles}")

    if cpu_load > 80:
        show_warning("CPU load > 80%. Risk of ISR overrun — optimize code or reduce ISR frequency.")
    elif cpu_load > 50:
        show_info("CPU load between 50–80%. Monitor carefully and leave headroom for other tasks.")
    else:
        st.success(f"✅ CPU load {cpu_load:.1f}% — adequate margin.")

    engineering_note(
        "<b>Rule of thumb:</b> Current-loop ISR should use < 50% of CPU budget. "
        "Reserve cycles for: ADC read latency, PWM update, communication tasks, diagnostics.<br>"
        "Measure actual cycle count with a logic analyzer or profiling GPIO toggle."
    )
