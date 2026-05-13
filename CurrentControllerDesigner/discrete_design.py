"""
discrete_design.py — Discrete-time PI design and implementation coefficients
Author: Masoud Bakhshi

Supported discretization methods:
  ZOH     — Zero-Order Hold
  Tustin  — Bilinear / Tustin transform
  Forward Euler
  Backward Euler
  Matched Pole-Zero (MPZ)
"""

import numpy as np
import control
from dataclasses import dataclass
from typing import Tuple


@dataclass
class DiscretePIResult:
    """All discrete-time design data for one PI controller."""
    method: str
    Ts: float           # sampling period [s]
    Kp: float           # proportional gain (same as continuous)
    Ki_c: float         # continuous integral gain
    # Discrete difference-equation: u[k] = b0*e[k] + b1*e[k-1] + u[k-1]
    b0: float
    b1: float
    # Alternative form: u[k] = Kp*e[k] + I[k],  I[k] = I[k-1] + Ki_d*e[k-1]
    Ki_d: float         # discrete integral gain (= Ki_c * Ts for Euler)
    poles_z: np.ndarray
    zeros_z: np.ndarray
    stable: bool


# ---------------------------------------------------------------------------
# Discretize a continuous control.TransferFunction
# ---------------------------------------------------------------------------

def discretize_plant(G_ct: control.TransferFunction,
                     Ts: float, method: str = "zoh") -> control.TransferFunction:
    """
    Convert a continuous-time plant to discrete time.
    method: 'zoh', 'tustin', 'euler_forward', 'euler_backward', 'mpz'
    """
    _method_map = {
        "zoh":            "zoh",
        "tustin":         "tustin",
        "bilinear":       "tustin",
        "euler_forward":  "euler",       # control library key
        "forward_euler":  "euler",
        "euler_backward": "backward_diff",
        "backward_euler": "backward_diff",
        "mpz":            "matched",
        "matched":        "matched",
    }
    key = _method_map.get(method.lower(), "zoh")
    try:
        G_dt = control.c2d(G_ct, Ts, method=key)
    except Exception:
        # fallback
        G_dt = control.c2d(G_ct, Ts, method="zoh")
    return G_dt


# ---------------------------------------------------------------------------
# Discrete PI difference equation
# ---------------------------------------------------------------------------

def discretize_pi(Kp: float, Ki: float, Ts: float,
                  method: str = "tustin") -> DiscretePIResult:
    """
    Derive the discrete PI difference equation.

    Continuous PI:  C(s) = Kp + Ki/s

    --- Tustin (bilinear) ---
    s → 2/Ts * (z-1)/(z+1)
    C(z) = Kp + Ki*Ts/2 * (z+1)/(z-1)
         = [Kp*(z-1) + Ki*Ts/2*(z+1)] / (z-1)
    Numerator:  (Kp + Ki*Ts/2)*z + (-Kp + Ki*Ts/2)
    u[k] = u[k-1] + (Kp + Ki*Ts/2)*e[k] + (-Kp + Ki*Ts/2)*e[k-1]
    b0 = Kp + Ki*Ts/2,  b1 = -Kp + Ki*Ts/2

    --- Forward Euler ---
    s → (z-1)/Ts
    C(z) = Kp + Ki*Ts/(z-1)
    u[k] = u[k-1] + Kp*(e[k]-e[k-1]) + Ki*Ts*e[k-1]
    b0 = Kp, b1 = -Kp + Ki*Ts   ... but needs 2-sample history

    --- Backward Euler ---
    s → (z-1)/(Ts*z)
    C(z) = Kp + Ki*Ts*z/(z-1)
    u[k] = u[k-1] + (Kp + Ki*Ts)*e[k] - Kp*e[k-1]
    b0 = Kp + Ki*Ts, b1 = -Kp

    --- ZOH ---
    Exact for piecewise-constant input.  For a pure integrator:
    s → Ts/(z-1) (same as Forward Euler in practice).
    Uses Tustin here as a practical approximation.
    """
    m = method.lower()

    if m in ("tustin", "bilinear", "zoh"):
        b0 = Kp + Ki * Ts / 2.0
        b1 = -Kp + Ki * Ts / 2.0
        Ki_d = Ki * Ts  # approximate equivalent
    elif m in ("forward_euler", "euler_forward", "euler"):
        b0 = Kp
        b1 = -Kp + Ki * Ts
        Ki_d = Ki * Ts
    elif m in ("backward_euler", "euler_backward", "backward_diff"):
        b0 = Kp + Ki * Ts
        b1 = -Kp
        Ki_d = Ki * Ts
    elif m in ("mpz", "matched"):
        # Matched pole-zero: pole at z=1 (integrator), zero at z=exp(-R/L*Ts)
        # For a generic PI we approximate with Tustin
        b0 = Kp + Ki * Ts / 2.0
        b1 = -Kp + Ki * Ts / 2.0
        Ki_d = Ki * Ts
    else:
        b0 = Kp + Ki * Ts / 2.0
        b1 = -Kp + Ki * Ts / 2.0
        Ki_d = Ki * Ts

    # Poles and zeros of the discrete controller
    # C(z) = (b0*z + b1) / (z - 1)   [position form]
    poles_z = np.array([1.0])
    zeros_z = np.array([-b1 / b0]) if abs(b0) > 1e-15 else np.array([])

    stable = True  # PI controller itself is marginally stable (pole at z=1)

    return DiscretePIResult(
        method=method,
        Ts=Ts,
        Kp=Kp,
        Ki_c=Ki,
        b0=b0,
        b1=b1,
        Ki_d=Ki_d,
        poles_z=poles_z,
        zeros_z=zeros_z,
        stable=stable,
    )


# ---------------------------------------------------------------------------
# Discrete closed-loop poles
# ---------------------------------------------------------------------------

def closed_loop_discrete_poles(Kp: float, Ki: float,
                                G_dt: control.TransferFunction) -> np.ndarray:
    """Return closed-loop poles of the digitally controlled system."""
    b0 = Kp + Ki * G_dt.dt / 2.0
    b1 = -Kp + Ki * G_dt.dt / 2.0
    C_z = control.tf([b0, b1], [1, -1], G_dt.dt)
    L_z = control.series(C_z, G_dt)
    try:
        T_z = control.feedback(L_z, 1)
        return T_z.poles()
    except Exception:
        return np.array([])


def check_discrete_stability(poles_z: np.ndarray) -> Tuple[bool, float]:
    """Return (is_stable, worst_pole_magnitude)."""
    if len(poles_z) == 0:
        return True, 0.0
    mags = np.abs(poles_z)
    worst = float(np.max(mags))
    return worst < 1.0, worst


# ---------------------------------------------------------------------------
# C code snippet generator
# ---------------------------------------------------------------------------

def generate_c_snippet(name: str, result: DiscretePIResult,
                        i_max: float) -> str:
    """
    Generate an ANSI-C difference-equation snippet for embedded use.
    u[k] = u[k-1] + b0*e[k] + b1*e[k-1]
    with output saturation and anti-windup (back-calculation).
    """
    Ka = 1.0 / result.Kp if result.Kp != 0 else 1.0  # anti-windup gain
    snippet = f"""\
/* ---------------------------------------------------------------
 * Discrete PI controller: {name}
 * Method : {result.method}
 * Ts     : {result.Ts*1e6:.2f} us
 * Kp     : {result.Kp:.6g}
 * Ki_c   : {result.Ki_c:.6g}  (continuous)
 * b0     : {result.b0:.6g}
 * b1     : {result.b1:.6g}
 * Author : Masoud Bakhshi
 * --------------------------------------------------------------- */
static float {name}_e_prev  = 0.0f;
static float {name}_u_prev  = 0.0f;

float PI_{name}(float ref, float meas)
{{
    float e     = ref - meas;
    float u_raw = {name}_u_prev
                + {result.b0:.6g}f * e
                + {result.b1:.6g}f * {name}_e_prev;

    /* Output saturation */
    float u_sat = u_raw;
    if (u_sat >  {i_max:.4g}f) u_sat =  {i_max:.4g}f;
    if (u_sat < -{i_max:.4g}f) u_sat = -{i_max:.4g}f;

    /* Anti-windup (back-calculation) */
    float aw = {Ka:.6g}f * (u_sat - u_raw);
    {name}_u_prev = u_sat + aw;   /* or integrate aw into integral state */
    {name}_e_prev = e;

    return u_sat;
}}
"""
    return snippet
