"""
controller_design.py: Continuous-time PI controller synthesis
Author: Masoud Bakhshi

Methods implemented:
  1. Bandwidth / pole-placement (desired closed-loop bandwidth)
  2. Symmetrical Optimum (SO)
  3. Magnitude Optimum (MO)
  4. User-defined bandwidth + target phase margin (iterative)
"""

import numpy as np
import control
from machine_models import pade_tf, inverter_tf, total_delay_s


# ---------------------------------------------------------------------------
# Core PI design
# ---------------------------------------------------------------------------

class PIController:
    """
    PI controller:  C(s) = Kp * (1 + 1/(Ti*s)) = Kp + Ki/s

    Attributes
    ----------
    Kp, Ki : gains
    Ti     : integral time = Kp/Ki
    """

    def __init__(self, Kp: float, Ki: float):
        self.Kp = Kp
        self.Ki = Ki
        self.Ti = Kp / Ki if abs(Ki) > 1e-15 else np.inf

    @property
    def tf(self) -> control.TransferFunction:
        return control.tf([self.Kp, self.Ki], [1, 0])

    def __repr__(self):
        return (f"PIController(Kp={self.Kp:.6g}, Ki={self.Ki:.6g}, "
                f"Ti={self.Ti:.6g} s)")


# ---------------------------------------------------------------------------
# Method 1: Bandwidth-based pole cancellation
# ---------------------------------------------------------------------------

def design_bandwidth(R: float, L: float, T_delay: float,
                     omega_bw: float) -> PIController:
    """
    Cancel the plant pole (s = -R/L) with the PI zero.
    Set loop gain so that 0 dB crossover ≈ omega_bw.

    Plant:   G(s) = 1/(L*s + R)   [ignoring delay for gain calc]
    PI zero: Ti = L/R
    Gain at crossover (approx, ignoring delay):
        |C*G|(jω_bw) = 1  =>  Kp * (1/R) * (R/L) / ω_bw * sqrt(...) = 1
    Simplified: Kp = ω_bw * L
    """
    Ti = L / R
    Kp = omega_bw * L
    Ki = Kp / Ti
    return PIController(Kp, Ki)


# ---------------------------------------------------------------------------
# Method 2: Symmetrical Optimum
# ---------------------------------------------------------------------------

def design_symmetrical_optimum(R: float, L: float,
                                T_delay: float) -> PIController:
    """
    Symmetrical Optimum (Kessler method).

    For a first-order plant G(s)=1/(Ls+R) with total delay T_Σ:
        Ti = 4 * T_Σ
        Kp = L / (2 * R * T_Σ)  [or Kp = Ti/(2*a²*T_Σ) with a=2]
    Standard SO with a=2:
        Ti = a² * T_Σ = 4 * T_Σ
        Kp = Ti / (2 * a² * T_Σ * R/L) ... simplifies to L/(2*R*T_Σ)
    """
    T_s = max(T_delay, 1e-9)
    Ti = 4.0 * T_s
    Kp = L / (2.0 * R * T_s)
    Ki = Kp / Ti
    return PIController(Kp, Ki)


# ---------------------------------------------------------------------------
# Method 3: Magnitude Optimum
# ---------------------------------------------------------------------------

def design_magnitude_optimum(R: float, L: float,
                              T_delay: float) -> PIController:
    """
    Magnitude Optimum (MO, Bohl / Föllinger).

    For plant G(s)=1/(Ls+R) with small delay T_Σ approximated as
    an additional lag 1/(1+sT_Σ):
        Ti = L/R
        Kp = L / (2 * R * T_Σ)   (same Kp as SO, different Ti)
    """
    T_s = max(T_delay, 1e-9)
    Ti = L / R
    Kp = L / (2.0 * R * T_s)
    Ki = Kp / Ti
    return PIController(Kp, Ki)


# ---------------------------------------------------------------------------
# Method 4: Bandwidth + Phase Margin (iterative)
# ---------------------------------------------------------------------------

def design_bandwidth_pm(R: float, L: float, T_delay: float,
                        omega_bw: float, pm_target: float = 45.0,
                        max_iter: int = 200) -> PIController:
    """
    Iterative design:
    1. Start from bandwidth cancellation design.
    2. Compute actual PM of the loop L(s) = C(s)*G_plant(s).
    3. If PM < pm_target, reduce Kp.
    """
    pi = design_bandwidth(R, L, T_delay, omega_bw)
    Kp = pi.Kp
    Ki = pi.Ki

    G_plant = control.tf([1], [L, R])
    T_del   = pade_tf(T_delay, 2)

    def _pm(Kp_try):
        C = control.tf([Kp_try, Kp_try / (L / R)], [1, 0])
        L_s = control.series(C, G_plant, T_del)
        try:
            _, pm_v, _, _ = control.margin(L_s)
            return float(pm_v) if pm_v is not None else 0.0
        except Exception:
            return 0.0

    pm_act = _pm(Kp)
    if pm_act >= pm_target:
        return PIController(Kp, Ki)

    # Binary search on Kp
    Kp_lo, Kp_hi = 1e-6 * Kp, Kp
    for _ in range(max_iter):
        Kp_mid = 0.5 * (Kp_lo + Kp_hi)
        if _pm(Kp_mid) < pm_target:
            Kp_hi = Kp_mid
        else:
            Kp_lo = Kp_mid
        if (Kp_hi - Kp_lo) / (Kp_hi + 1e-30) < 1e-4:
            break

    Kp_final = Kp_lo
    Ti_final = L / R
    return PIController(Kp_final, Kp_final / Ti_final)


# ---------------------------------------------------------------------------
# Unified design dispatcher
# ---------------------------------------------------------------------------

def design_current_pi(R: float, L: float, T_delay: float,
                      method: str = "bandwidth",
                      omega_bw: float = None,
                      pm_target: float = 45.0) -> PIController:
    """
    Dispatch to the selected design method.

    Parameters
    ----------
    R        : effective resistance [Ω]
    L        : effective inductance [H]
    T_delay  : total equivalent delay [s]
    method   : 'bandwidth' | 'symmetrical_optimum' | 'magnitude_optimum'
               | 'bandwidth_pm'
    omega_bw : desired bandwidth [rad/s] (needed for bandwidth methods)
    pm_target: target phase margin [deg] (for bandwidth_pm)
    """
    if method == "bandwidth":
        if omega_bw is None:
            omega_bw = 0.5 / T_delay if T_delay > 0 else 2000.0
        return design_bandwidth(R, L, T_delay, omega_bw)

    elif method == "symmetrical_optimum":
        return design_symmetrical_optimum(R, L, T_delay)

    elif method == "magnitude_optimum":
        return design_magnitude_optimum(R, L, T_delay)

    elif method == "bandwidth_pm":
        if omega_bw is None:
            omega_bw = 0.5 / T_delay if T_delay > 0 else 2000.0
        return design_bandwidth_pm(R, L, T_delay, omega_bw, pm_target)

    else:
        raise ValueError(f"Unknown method: {method}")


# ---------------------------------------------------------------------------
# Speed / torque outer loop
# ---------------------------------------------------------------------------

def design_speed_pi(J: float, B: float, T_delay_speed: float,
                    omega_bw_speed: float,
                    pm_target: float = 50.0) -> PIController:
    """
    Mechanical plant (assuming perfect inner-loop torque tracking):
        G_mech(s) = 1 / (J*s + B)

    Bandwidth-based design with optional PM check.
    """
    return design_bandwidth_pm(B, J, T_delay_speed,
                               omega_bw_speed, pm_target)


# ---------------------------------------------------------------------------
# Closed-loop loop gain construction
# ---------------------------------------------------------------------------

def build_loop_tf(pi: PIController,
                  G_plant: control.TransferFunction) -> control.TransferFunction:
    """Return the open-loop transfer function L(s) = C(s)*G(s)."""
    return control.series(pi.tf, G_plant)


def build_closed_loop_tf(pi: PIController,
                          G_plant: control.TransferFunction) -> control.TransferFunction:
    """Return T(s) = L(s)/(1+L(s))."""
    L = build_loop_tf(pi, G_plant)
    return control.feedback(L, 1)


def build_sensitivity_tf(pi: PIController,
                          G_plant: control.TransferFunction) -> control.TransferFunction:
    """Return S(s) = 1/(1+L(s))."""
    L = build_loop_tf(pi, G_plant)
    return control.feedback(control.tf([1], [1]), L)
