"""Result formatting helpers for DriveCalc."""
import streamlit as st


def show_result_card(label: str, value: float, unit: str, decimals: int = 4):
    """Display a single result as a Streamlit metric."""
    formatted = f"{value:.{decimals}g}"
    st.metric(label=f"{label} [{unit}]", value=formatted)


def show_formula(latex: str, explanation: str = ""):
    """Render a LaTeX formula with optional plain-text explanation."""
    st.latex(latex)
    if explanation:
        st.caption(explanation)


def show_warning(msg: str):
    st.warning(f"⚠️ {msg}")


def show_error(msg: str):
    st.error(f"🚫 {msg}")


def show_info(msg: str):
    st.info(f"ℹ️ {msg}")


def engineering_note(text: str):
    """Render an engineering note in a styled box."""
    st.markdown(
        f'<div style="background:#f0f4ff;border-left:4px solid #4a90d9;'
        f'padding:8px 12px;border-radius:4px;font-size:0.88rem">{text}</div>',
        unsafe_allow_html=True,
    )
