"""
stability_analysis.py — Comprehensive stability and robustness analysis
Author: Masoud Bakhshi
"""

import numpy as np
import control
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from utils import bode_plot, step_response_plot, pole_zero_plot, nyquist_plot


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class StabilityReport:
    # Continuous-time loop
    gain_margin_db: float = np.inf
    phase_margin_deg: float = np.inf
    gain_crossover_freq: float = 0.0
    phase_crossover_freq: float = 0.0
    bandwidth_cl: float = 0.0          # -3 dB closed-loop bandwidth

    # Discrete-time
    discrete_stable: bool = True
    worst_pole_z_mag: float = 0.0
    discrete_poles: np.ndarray = field(default_factory=lambda: np.array([]))

    # Sensitivity peak
    Ms: float = 1.0                    # max |S(jω)|

    # Step response
    rise_time_ms: float = 0.0
    settling_time_ms: float = 0.0
    overshoot_pct: float = 0.0

    # Parameter sensitivity
    resistance_sensitivity: Dict[str, float] = field(default_factory=dict)
    inductance_sensitivity: Dict[str, float] = field(default_factory=dict)

    # Flags
    continuous_stable: bool = True
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse_loop(L_tf: control.TransferFunction,
                 T_tf: control.TransferFunction,
                 S_tf: control.TransferFunction,
                 label: str = "") -> StabilityReport:
    """Full stability analysis for a given open-loop TF."""
    rpt = StabilityReport()

    # ---- Gain/Phase margin ----
    try:
        gm, pm, wpc, wgc = control.margin(L_tf)
        rpt.gain_margin_db    = float(20 * np.log10(gm)) if (gm is not None and np.isfinite(gm) and gm > 0) else np.inf
        rpt.phase_margin_deg  = float(pm)  if pm  is not None else np.inf
        rpt.phase_crossover_freq = float(wpc) if wpc is not None else 0.0
        rpt.gain_crossover_freq  = float(wgc) if wgc is not None else 0.0
    except Exception as ex:
        rpt.warnings.append(f"Margin computation failed: {ex}")

    # ---- Continuous-time closed-loop stability ----
    try:
        cl_poles = T_tf.poles()
        rpt.continuous_stable = bool(np.all(cl_poles.real < 0))
        if not rpt.continuous_stable:
            rpt.warnings.append("Closed-loop system is UNSTABLE (continuous-time).")
    except Exception as ex:
        rpt.warnings.append(f"Pole computation failed: {ex}")

    # ---- Bandwidth (−3 dB of closed-loop) ----
    try:
        omega = np.logspace(-1, 6, 5000)
        mag_cl, _, _ = control.bode(T_tf, omega, plot=False)
        mag_cl_db = 20 * np.log10(mag_cl + 1e-300)
        dc_gain = mag_cl_db[0]
        idx = np.where(mag_cl_db < dc_gain - 3.0)[0]
        if len(idx):
            rpt.bandwidth_cl = float(omega[idx[0]])
    except Exception:
        pass

    # ---- Sensitivity peak ----
    try:
        omega = np.logspace(-1, 6, 5000)
        mag_s, _, _ = control.bode(S_tf, omega, plot=False)
        rpt.Ms = float(np.max(mag_s))
        if rpt.Ms > 2.0:
            rpt.warnings.append(f"Sensitivity peak Ms={rpt.Ms:.2f} > 2 — poor robustness.")
    except Exception:
        pass

    # ---- Step response metrics ----
    try:
        t_end = max(0.05, 10.0 / rpt.bandwidth_cl) if rpt.bandwidth_cl > 0 else 0.02
        t, y = control.step_response(T_tf, T=t_end)
        y_ss = float(y[-1]) if len(y) else 1.0
        if abs(y_ss) < 1e-9:
            y_ss = 1.0
        y_norm = y / y_ss

        # Rise time (10%→90%)
        idx10 = np.where(y_norm >= 0.1)[0]
        idx90 = np.where(y_norm >= 0.9)[0]
        if len(idx10) and len(idx90):
            rpt.rise_time_ms = float((t[idx90[0]] - t[idx10[0]]) * 1e3)

        # Settling time (±2%)
        settled = np.where(np.abs(y_norm - 1.0) > 0.02)[0]
        if len(settled):
            rpt.settling_time_ms = float(t[settled[-1]] * 1e3)

        # Overshoot
        rpt.overshoot_pct = float(max(0.0, (np.max(y_norm) - 1.0) * 100.0))
    except Exception:
        pass

    if rpt.phase_margin_deg < 30.0:
        rpt.warnings.append(f"Phase margin {rpt.phase_margin_deg:.1f}° < 30° — marginal stability.")
    if rpt.gain_margin_db < 6.0:
        rpt.warnings.append(f"Gain margin {rpt.gain_margin_db:.1f} dB < 6 dB — marginal.")

    return rpt


# ---------------------------------------------------------------------------
# Parameter variation / sensitivity sweep
# ---------------------------------------------------------------------------

def resistance_sensitivity_sweep(R_nom: float, L: float,
                                  pi_kp: float, pi_ki: float,
                                  T_delay: float,
                                  r_range: Tuple[float, float] = (0.5, 2.0),
                                  n_pts: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sweep R from r_range[0]*R_nom to r_range[1]*R_nom.
    Return (R_array, PM_array, GM_array).
    """
    from machine_models import pade_tf
    R_arr = np.linspace(r_range[0] * R_nom, r_range[1] * R_nom, n_pts)
    pm_arr = np.zeros(n_pts)
    gm_arr = np.zeros(n_pts)

    for i, R in enumerate(R_arr):
        G = control.tf([1], [L, R])
        G_del = pade_tf(T_delay, 2)
        C = control.tf([pi_kp, pi_ki], [1, 0])
        L_s = control.series(C, G, G_del)
        try:
            gm, pm, _, _ = control.margin(L_s)
            gm_arr[i] = 20 * np.log10(gm) if (gm and np.isfinite(gm)) else 40.0
            pm_arr[i] = pm if pm is not None else 90.0
        except Exception:
            gm_arr[i] = 0.0
            pm_arr[i] = 0.0

    return R_arr, pm_arr, gm_arr


def inductance_sensitivity_sweep(R: float, L_nom: float,
                                  pi_kp: float, pi_ki: float,
                                  T_delay: float,
                                  l_range: Tuple[float, float] = (0.5, 2.0),
                                  n_pts: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    from machine_models import pade_tf
    L_arr = np.linspace(l_range[0] * L_nom, l_range[1] * L_nom, n_pts)
    pm_arr = np.zeros(n_pts)
    gm_arr = np.zeros(n_pts)

    for i, L in enumerate(L_arr):
        G = control.tf([1], [L, R])
        G_del = pade_tf(T_delay, 2)
        C = control.tf([pi_kp, pi_ki], [1, 0])
        L_s = control.series(C, G, G_del)
        try:
            gm, pm, _, _ = control.margin(L_s)
            gm_arr[i] = 20 * np.log10(gm) if (gm and np.isfinite(gm)) else 40.0
            pm_arr[i] = pm if pm is not None else 90.0
        except Exception:
            gm_arr[i] = 0.0
            pm_arr[i] = 0.0

    return L_arr, pm_arr, gm_arr


def delay_sensitivity_sweep(R: float, L: float,
                             pi_kp: float, pi_ki: float,
                             T_delay_nom: float,
                             d_range: Tuple[float, float] = (0.5, 3.0),
                             n_pts: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    from machine_models import pade_tf
    T_arr = np.linspace(d_range[0] * T_delay_nom,
                        d_range[1] * T_delay_nom, n_pts)
    pm_arr = np.zeros(n_pts)
    gm_arr = np.zeros(n_pts)

    for i, T in enumerate(T_arr):
        G = control.tf([1], [L, R])
        G_del = pade_tf(T, 2)
        C = control.tf([pi_kp, pi_ki], [1, 0])
        L_s = control.series(C, G, G_del)
        try:
            gm, pm, _, _ = control.margin(L_s)
            gm_arr[i] = 20 * np.log10(gm) if (gm and np.isfinite(gm)) else 40.0
            pm_arr[i] = pm if pm is not None else 90.0
        except Exception:
            gm_arr[i] = 0.0
            pm_arr[i] = 0.0

    return T_arr, pm_arr, gm_arr


# ---------------------------------------------------------------------------
# Figure generators
# ---------------------------------------------------------------------------

def sensitivity_sweep_figure(x_arr: np.ndarray, pm_arr: np.ndarray,
                              gm_arr: np.ndarray,
                              x_label: str, x_nom: float,
                              title: str = "Parameter Sensitivity") -> plt.Figure:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle(title)

    ax1.plot(x_arr, pm_arr, "b-o", ms=4)
    ax1.axhline(45, color="r", ls="--", lw=1, label="45° limit")
    ax1.axvline(x_nom, color="k", ls=":", lw=1, label="Nominal")
    ax1.set_xlabel(x_label)
    ax1.set_ylabel("Phase Margin (deg)")
    ax1.legend(fontsize=8)
    ax1.grid(True, ls=":", alpha=0.6)

    ax2.plot(x_arr, gm_arr, "g-o", ms=4)
    ax2.axhline(6, color="r", ls="--", lw=1, label="6 dB limit")
    ax2.axvline(x_nom, color="k", ls=":", lw=1, label="Nominal")
    ax2.set_xlabel(x_label)
    ax2.set_ylabel("Gain Margin (dB)")
    ax2.legend(fontsize=8)
    ax2.grid(True, ls=":", alpha=0.6)

    fig.tight_layout()
    return fig


def full_analysis_figures(L_tf, T_tf, S_tf,
                           label: str = "") -> Dict[str, plt.Figure]:
    """Return a dict of figures for the stability section."""
    figs = {}
    figs["bode"]      = bode_plot(L_tf, title=f"Bode — {label}")
    figs["step"]      = step_response_plot(T_tf, title=f"Step Response — {label}")
    figs["pz"]        = pole_zero_plot(T_tf, title=f"Closed-Loop Poles/Zeros — {label}")
    figs["nyquist"]   = nyquist_plot(L_tf, title=f"Nyquist — {label}")
    return figs
