"""
utils.py: Shared utilities for CurrentControllerDesigner
Author: Masoud Bakhshi
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io


# ---------------------------------------------------------------------------
# Physical / mathematical helpers
# ---------------------------------------------------------------------------

def rad_per_sec(rpm: float) -> float:
    return rpm * 2.0 * np.pi / 60.0


def rpm_from_rad(omega: float) -> float:
    return omega * 60.0 / (2.0 * np.pi)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def db(magnitude: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(magnitude), 1e-300))


def phase_deg(tf_resp: np.ndarray) -> np.ndarray:
    return np.angle(tf_resp, deg=True)


def pade_delay(T: float, order: int = 2):
    """Return (num, den) of [n/n] Padé approximation of e^{-sT}."""
    if T <= 0.0:
        return [1.0], [1.0]
    if order == 1:
        return [-T / 2.0, 1.0], [T / 2.0, 1.0]
    elif order == 2:
        return ([T**2 / 12.0, -T / 2.0, 1.0],
                [T**2 / 12.0,  T / 2.0, 1.0])
    else:  # order 3
        return ([-T**3 / 120.0, T**2 / 10.0, -T / 2.0, 1.0],
                [ T**3 / 120.0, T**2 / 10.0,  T / 2.0, 1.0])


def delay_tf(T_delay: float, method: str = "pade2"):
    """Return a scipy.signal.TransferFunction for a pure delay."""
    from scipy.signal import TransferFunction
    order = int(method[-1]) if method.startswith("pade") else 2
    num, den = pade_delay(T_delay, order)
    return TransferFunction(num, den)


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def fig_to_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


def bode_plot(sys_tf, title: str = "Bode Plot",
              freq_range=(1, 1e5), n_pts: int = 2000,
              show_margins: bool = True):
    """Return a matplotlib Figure with a Bode plot."""
    import control
    omega = np.logspace(np.log10(freq_range[0]),
                        np.log10(freq_range[1]), n_pts)
    mag, phase, omega_out = control.bode(sys_tf, omega,
                                         plot=False, Hz=False)
    mag_db = 20.0 * np.log10(mag + 1e-300)
    phase_d = np.degrees(phase)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    fig.suptitle(title, fontsize=11)

    ax1.semilogx(omega_out, mag_db, "b-", lw=1.5)
    ax1.axhline(0, color="k", lw=0.7, ls="--")
    ax1.set_ylabel("Magnitude (dB)")
    ax1.grid(True, which="both", ls=":", alpha=0.6)

    ax2.semilogx(omega_out, phase_d, "r-", lw=1.5)
    ax2.axhline(-180, color="k", lw=0.7, ls="--")
    ax2.set_ylabel("Phase (deg)")
    ax2.set_xlabel("Frequency (rad/s)")
    ax2.grid(True, which="both", ls=":", alpha=0.6)

    if show_margins:
        try:
            gm, pm, wpc, wgc = control.margin(sys_tf)
            if gm is not None and np.isfinite(gm) and gm > 0 and wpc is not None:
                ax1.axvline(wpc, color="m", lw=1, ls="--",
                            label=f"GM={20*np.log10(gm):.1f} dB")
            if pm is not None and np.isfinite(pm) and wgc is not None:
                ax2.axvline(wgc, color="g", lw=1, ls="--",
                            label=f"PM={pm:.1f} deg")
            ax1.legend(fontsize=8)
            ax2.legend(fontsize=8)
        except Exception:
            pass

    fig.tight_layout()
    return fig


def step_response_plot(sys_tf, t_end: float = None,
                       title: str = "Step Response"):
    """Return a matplotlib Figure with the step response."""
    import control
    T_arr, y_arr = control.step_response(sys_tf, T=t_end)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(T_arr * 1e3, y_arr, "b-", lw=1.5)
    ax.axhline(1.0, color="k", lw=0.7, ls="--")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    ax.grid(True, ls=":", alpha=0.6)
    fig.tight_layout()
    return fig


def pole_zero_plot(sys_tf, title: str = "Pole-Zero Map"):
    """Return a matplotlib Figure with a pole-zero map."""
    import control
    fig, ax = plt.subplots(figsize=(6, 5))
    poles = sys_tf.poles()
    zeros = sys_tf.zeros()
    ax.scatter(poles.real, poles.imag, marker="x",
               s=80, c="r", lw=2, label="Poles")
    if len(zeros):
        ax.scatter(zeros.real, zeros.imag, marker="o",
                   s=60, c="b", lw=1.5, facecolors="none", label="Zeros")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("Real")
    ax.set_ylabel("Imaginary")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, ls=":", alpha=0.6)
    fig.tight_layout()
    return fig


def nyquist_plot(sys_tf, title: str = "Nyquist Plot",
                 freq_range=(0.1, 1e5), n_pts: int = 3000):
    """Return a matplotlib Figure with the Nyquist plot."""
    import control
    omega = np.logspace(np.log10(freq_range[0]),
                        np.log10(freq_range[1]), n_pts)
    try:
        resp = control.evalfr(sys_tf, 1j * omega)
    except Exception:
        resp = np.zeros(n_pts, dtype=complex)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(resp.real, resp.imag, "b-", lw=1.2, label="L(jω)")
    ax.plot(resp.real, -resp.imag, "b--", lw=0.7, alpha=0.4,
            label="Conjugate")
    ax.plot(-1, 0, "r+", ms=14, mew=2.5, label="(-1,0)")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("Re")
    ax.set_ylabel("Im")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, ls=":", alpha=0.6)
    fig.tight_layout()
    return fig
