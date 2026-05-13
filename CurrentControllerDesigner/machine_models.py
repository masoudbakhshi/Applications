"""
machine_models.py — Electrical plant models for EESM, IPMSM, and IM
Author: Masoud Bakhshi

All plant transfer functions are expressed in the dq-frame.
For each current channel the open-loop plant is:

    G_plant(s) = 1 / (L_eff * s + R_eff)

augmented with inverter + computational delays.
"""

import numpy as np
from scipy.signal import TransferFunction
import control


# ---------------------------------------------------------------------------
# Delay model
# ---------------------------------------------------------------------------

def total_delay_s(params: dict) -> float:
    """
    Total effective delay in seconds.
    Typically:  T_delay = T_comp + T_pwm/2  (ZOH + one-step computation)
    Additional: T_adc + T_filter
    """
    T_comp   = params.get("T_comp",   0.0)
    T_pwm    = params.get("T_pwm",    0.0)   # = 1/f_pwm
    T_adc    = params.get("T_adc",    0.0)
    T_filter = params.get("T_filter", 0.0)
    return T_comp + 0.5 * T_pwm + T_adc + T_filter


def pade_tf(T: float, order: int = 2) -> control.TransferFunction:
    """
    Padé approximant of e^{-sT} as a control.TransferFunction.
    Implemented without scipy.signal.pade (removed in SciPy ≥ 1.9).

    [n/n] Padé of e^{-s}, then substitute s → sT:
      order 1:  N=[-T/2, 1],          D=[T/2, 1]
      order 2:  N=[T²/12, -T/2, 1],   D=[T²/12, T/2, 1]
      order 3:  N=[-T³/120, T²/10, -T/2, 1],
                D=[ T³/120, T²/10,  T/2, 1]
    """
    if T <= 1e-12:
        return control.tf([1], [1])
    if order == 1:
        num = [-T / 2.0, 1.0]
        den = [ T / 2.0, 1.0]
    elif order == 2:
        num = [ T**2 / 12.0, -T / 2.0,  1.0]
        den = [ T**2 / 12.0,  T / 2.0,  1.0]
    elif order == 3:
        num = [-T**3 / 120.0, T**2 / 10.0, -T / 2.0, 1.0]
        den = [ T**3 / 120.0, T**2 / 10.0,  T / 2.0, 1.0]
    else:
        # Fall back to order-2 for unsupported orders
        num = [ T**2 / 12.0, -T / 2.0, 1.0]
        den = [ T**2 / 12.0,  T / 2.0, 1.0]
    return control.tf(num, den)


def inverter_tf(T_pwm: float) -> control.TransferFunction:
    """
    Inverter modelled as a first-order ZOH equivalent:
        G_inv(s) ≈ 1 / (1 + s * T_pwm/2)
    """
    T = T_pwm / 2.0
    if T <= 1e-12:
        return control.tf([1], [1])
    return control.tf([1], [T, 1])


# ---------------------------------------------------------------------------
# EESM
# ---------------------------------------------------------------------------

class EESMModel:
    """
    Voltage equations (dq-frame, motor convention):

        v_d = R_s*i_d + L_d*di_d/dt - ω_e*L_q*i_q
        v_q = R_s*i_q + L_q*di_q/dt + ω_e*(L_d*i_d + ψ_f(i_f))
        v_f = R_f*i_f + L_f*di_f/dt  (+ mutual terms, simplified)

    Torque:
        T_e = (3/2)*p*(ψ_f(i_f)*i_q + (L_d - L_q)*i_d*i_q)
    """

    def __init__(self, p: dict):
        self.Rs   = p["Rs"]
        self.Ld   = p["Ld"]
        self.Lq   = p["Lq"]
        self.Rf   = p["Rf"]
        self.Lf   = p["Lf"]
        self.pole_pairs = p["pole_pairs"]
        self.Vdc  = p["Vdc"]
        self.f_pwm = p["f_pwm"]
        self.T_pwm = 1.0 / self.f_pwm
        self.params = p

    # --- d-axis plant (stator) ---
    def plant_d(self, omega_e: float = 0.0,
                delay_order: int = 2) -> control.TransferFunction:
        """
        G_d(s) = [1/(L_d*s + R_s)] * G_inv(s) * G_delay(s)
        Cross-coupling from ω_e*L_q*i_q is treated as a disturbance
        (compensated via feedforward).
        """
        G_elec = control.tf([1], [self.Ld, self.Rs])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    # --- q-axis plant (stator) ---
    def plant_q(self, omega_e: float = 0.0,
                delay_order: int = 2) -> control.TransferFunction:
        G_elec = control.tf([1], [self.Lq, self.Rs])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    # --- Rotor excitation plant ---
    def plant_field(self, delay_order: int = 2) -> control.TransferFunction:
        """
        G_f(s) = 1 / (L_f * s + R_f)
        No PWM inverter on the field side (DC chopper model).
        """
        T_del_f = self.params.get("T_comp_field", self.params.get("T_comp", 0.0))
        G_elec = control.tf([1], [self.Lf, self.Rf])
        G_del  = pade_tf(T_del_f, delay_order)
        return control.series(G_elec, G_del)

    def torque(self, id_: float, iq: float, psi_f: float) -> float:
        """T_e = (3/2)*p*(ψ_f*i_q + (Ld-Lq)*id*iq)"""
        return 1.5 * self.pole_pairs * (
            psi_f * iq + (self.Ld - self.Lq) * id_ * iq
        )

    def psi_f_linear(self, i_f: float) -> float:
        """Linear model: ψ_f = Lm * i_f"""
        Lm = self.params.get("Lm", 0.04)
        return Lm * i_f


# ---------------------------------------------------------------------------
# IPMSM
# ---------------------------------------------------------------------------

class IPMSMModel:
    """
    Voltage equations:
        v_d = R_s*i_d + L_d*di_d/dt - ω_e*L_q*i_q
        v_q = R_s*i_q + L_q*di_q/dt + ω_e*(L_d*i_d + ψ_pm)

    Torque:
        T_e = (3/2)*p*(ψ_pm*i_q + (L_d - L_q)*i_d*i_q)
    """

    def __init__(self, p: dict):
        self.Rs    = p["Rs"]
        self.Ld    = p["Ld"]
        self.Lq    = p["Lq"]
        self.psi_pm = p["psi_pm"]
        self.pole_pairs = p["pole_pairs"]
        self.Vdc   = p["Vdc"]
        self.f_pwm = p["f_pwm"]
        self.T_pwm = 1.0 / self.f_pwm
        self.params = p

    def plant_d(self, delay_order: int = 2) -> control.TransferFunction:
        G_elec = control.tf([1], [self.Ld, self.Rs])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    def plant_q(self, delay_order: int = 2) -> control.TransferFunction:
        G_elec = control.tf([1], [self.Lq, self.Rs])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    def torque(self, id_: float, iq: float) -> float:
        return 1.5 * self.pole_pairs * (
            self.psi_pm * iq + (self.Ld - self.Lq) * id_ * iq
        )


# ---------------------------------------------------------------------------
# Induction Machine (Rotor-Flux-Oriented Control)
# ---------------------------------------------------------------------------

class IMModel:
    """
    Rotor-flux-oriented (RFOC) model.

    Stator voltage equations in the rotor-flux frame (d aligned with ψ_r):

        v_sd = R_s*i_sd + σ*Ls*di_sd/dt - ω_s*σ*Ls*i_sq
        v_sq = R_s*i_sq + σ*Ls*di_sq/dt + ω_s*(σ*Ls*i_sd + ψ_r/Ls)

    Rotor flux dynamics:
        dψ_r/dt = (Lm/Tr)*i_sd - (1/Tr)*ψ_r

    Torque:
        T_e = (3/2)*p*(Lm/Lr)*(ψ_r * i_sq)

    Slip:
        ω_slip = (Lm/Tr) * i_sq / ψ_r
    """

    def __init__(self, p: dict):
        self.Rs  = p["Rs"]
        self.Rr  = p["Rr"]
        self.Ls  = p["Ls"]
        self.Lr  = p["Lr"]
        self.Lm  = p["Lm"]
        self.pole_pairs = p["pole_pairs"]
        self.Vdc = p["Vdc"]
        self.f_pwm = p["f_pwm"]
        self.T_pwm = 1.0 / self.f_pwm
        self.params = p

        self.sigma = 1.0 - self.Lm ** 2 / (self.Ls * self.Lr)
        self.Tr    = self.Lr / self.Rr
        self.R_eff = self.Rs + (self.Lm ** 2 / self.Lr ** 2) * self.Rr
        self.L_eff = self.sigma * self.Ls

    def plant_sd(self, delay_order: int = 2) -> control.TransferFunction:
        """d-axis (flux-producing) current plant."""
        G_elec = control.tf([1], [self.L_eff, self.R_eff])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    def plant_sq(self, delay_order: int = 2) -> control.TransferFunction:
        """q-axis (torque-producing) current plant."""
        G_elec = control.tf([1], [self.L_eff, self.R_eff])
        T_del = total_delay_s(self.params)
        G_del = pade_tf(T_del, delay_order)
        G_inv = inverter_tf(self.T_pwm)
        return control.series(G_elec, G_del, G_inv)

    def torque(self, i_sq: float, psi_r: float) -> float:
        return 1.5 * self.pole_pairs * (self.Lm / self.Lr) * psi_r * i_sq

    def slip_freq(self, i_sq: float, psi_r: float) -> float:
        if abs(psi_r) < 1e-6:
            return 0.0
        return (self.Lm / self.Tr) * i_sq / psi_r
