"""Shared plotting utilities using Plotly."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


THEME = dict(
    paper_bgcolor="white",
    plot_bgcolor="#f8f9fa",
    font=dict(family="Arial, sans-serif", size=12),
    margin=dict(l=50, r=30, t=40, b=50),
)


def make_fig(title: str = "", x_label: str = "", y_label: str = "") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        **THEME,
    )
    return fig


def svpwm_hexagon_plot(v_mag: float, v_angle_deg: float, vdc: float) -> go.Figure:
    """Plot the SVM voltage hexagon with the reference vector."""
    p = 6  # hexagon vertices
    angles = np.linspace(0, 2 * np.pi, p + 1)
    v_hex = vdc / np.sqrt(3)  # inscribed circle radius (max linear for SVPWM)
    hx = v_hex * np.cos(angles + np.pi / 6)
    hy = v_hex * np.sin(angles + np.pi / 6)

    theta = np.radians(v_angle_deg)
    vx = v_mag * np.cos(theta)
    vy = v_mag * np.sin(theta)

    # sector boundary lines
    sector_x, sector_y = [], []
    for k in range(6):
        ang = np.radians(k * 60)
        sector_x += [0, vdc / np.sqrt(3) * np.cos(ang), None]
        sector_y += [0, vdc / np.sqrt(3) * np.sin(ang), None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hx, y=hy, mode="lines", name="Hexagon",
                             line=dict(color="#1f77b4", width=2)))
    fig.add_trace(go.Scatter(x=sector_x, y=sector_y, mode="lines", name="Sectors",
                             line=dict(color="#aaa", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=[0, vx], y=[0, vy], mode="lines+markers",
                             name="Ref. Vector",
                             line=dict(color="#d62728", width=2.5),
                             marker=dict(size=[0, 8])))
    fig.update_layout(
        title="SVPWM Voltage Hexagon",
        xaxis_title="Vα [V]", yaxis_title="Vβ [V]",
        xaxis=dict(scaleanchor="y", scaleratio=1),
        **THEME,
    )
    return fig


def torque_speed_envelope(speed_rpm: np.ndarray, torque: np.ndarray,
                          power_limit_kw: float) -> go.Figure:
    """Plot torque-speed envelope with constant-power curve."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=speed_rpm, y=torque, mode="lines",
                             name="Torque envelope",
                             line=dict(color="#2ca02c", width=2)))
    p_speeds = np.linspace(speed_rpm[0] + 1, speed_rpm[-1], 200)
    p_torques = (power_limit_kw * 1000) / (p_speeds * 2 * np.pi / 60)
    fig.add_trace(go.Scatter(x=p_speeds, y=p_torques, mode="lines",
                             name=f"Constant power ({power_limit_kw:.1f} kW)",
                             line=dict(color="#ff7f0e", width=2, dash="dash")))
    fig.update_layout(title="Torque-Speed Envelope",
                      xaxis_title="Speed [rpm]", yaxis_title="Torque [Nm]",
                      **THEME)
    return fig


def thermal_transient_plot(times: np.ndarray, temps: np.ndarray,
                           t_max: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=temps, mode="lines",
                             name="Temperature",
                             line=dict(color="#d62728", width=2)))
    fig.add_hline(y=t_max, line_dash="dash", line_color="orange",
                  annotation_text=f"T_max = {t_max}°C")
    fig.update_layout(title="Thermal Transient Response",
                      xaxis_title="Time [s]", yaxis_title="Temperature [°C]",
                      **THEME)
    return fig


def bode_like_plot(freqs: np.ndarray, gains: np.ndarray,
                   title: str = "Gain vs Frequency") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=gains, mode="lines",
                             line=dict(color="#1f77b4", width=2)))
    fig.update_layout(title=title,
                      xaxis_title="Frequency [Hz]",
                      xaxis_type="log",
                      yaxis_title="Gain [dB]",
                      **THEME)
    return fig
