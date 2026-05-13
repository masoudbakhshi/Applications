import html
import streamlit as st
from google import genai

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Professional Email Rephrase Agent",
    page_icon="✉️",
    layout="centered"
)

# -------------------------------------------------
# Custom CSS
# -------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f7f8fc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }

    .title-box {
        background: linear-gradient(135deg, #eef2ff, #f8f5ff);
        padding: 1.3rem 1.5rem;
        border-radius: 18px;
        border: 1px solid #e6e8f0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        margin-bottom: 1.4rem;
    }

    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #2b2d42;
        margin-bottom: 0.4rem;
    }

    .author-line {
        font-size: 0.95rem;
        color: #6c757d;
        margin-bottom: 1rem;
    }

    .subtitle {
        font-size: 1rem;
        color: #495057;
        line-height: 1.6;
    }

    .result-box {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
        margin-top: 0.7rem;
        white-space: pre-wrap;
        color: #212529;
        font-size: 1rem;
        line-height: 1.7;
    }

    .footer-note {
        text-align: center;
        font-size: 0.9rem;
        color: #7a7f87;
        margin-top: 2rem;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #6c63ff, #8b80f9);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        font-size: 1rem;
        box-shadow: 0 4px 12px rgba(108, 99, 255, 0.25);
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #5b52e8, #7b70f0);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Gemini client
# -------------------------------------------------
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error(
        "GEMINI_API_KEY is missing. Please add it to .streamlit/secrets.toml"
    )
    st.stop()

# -------------------------------------------------
# AI function
# -------------------------------------------------
def rephrase_email(email_text: str, tone: str, model_name: str) -> str:
    if not email_text.strip():
        return "Please paste an email first."

    prompt = f"""
You are an expert professional communication assistant.

Rewrite the user's email so that it is:
- professional
- psychologically safe
- polite
- clear
- human-written
- workplace-appropriate
- assertive without sounding aggressive
- suitable for communication with managers, HR, colleagues, recruiters, or external stakeholders

Rules:
1. Keep the original meaning.
2. Do not add false claims, promises, or unsupported facts.
3. Reduce emotional, defensive, blaming, or risky wording.
4. Make the message easier for the receiver to accept.
5. Keep the language upper-intermediate and natural.
6. Keep it concise unless the original message needs clarification.
7. Return only the final improved email text.
8. Do not include explanations, bullet points, or analysis.

Tone preference:
{tone}

Original email:
{email_text}
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    if not response.text:
        return "No response was generated. Please try again."

    return response.text.strip()

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown("""
<div class="title-box">
    <div class="main-title">✉️ Professional Email Rephrase Agent</div>
    <div class="author-line">Author: Masoud Bakhshi</div>
    <div class="subtitle">
        Paste your draft email below. The AI will rewrite it in a professional,
        polite, and psychologically safe format.
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Controls
# -------------------------------------------------
tone = st.selectbox(
    "Choose tone",
    [
        "Professional and polite",
        "Assertive but safe",
        "Warm and diplomatic",
        "Short and direct",
        "Manager-level formal",
        "HR-safe and neutral",
        "Diplomatic but clear"
    ]
)

model_name = st.selectbox(
    "Choose Gemini model",
    [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview"
    ],
    index=0
)

email_input = st.text_area(
    "Paste your email draft here",
    height=230,
    placeholder="Write or paste your email here..."
)

# -------------------------------------------------
# Output
# -------------------------------------------------
if st.button("Rephrase Email"):
    try:
        with st.spinner("Rephrasing your email with Gemini..."):
            improved_email = rephrase_email(email_input, tone, model_name)

        st.subheader("Improved Email")

        # Escape generated text before placing it inside custom HTML
        safe_output = html.escape(improved_email)

        st.markdown(
            f'<div class="result-box">{safe_output}</div>',
            unsafe_allow_html=True
        )

        st.download_button(
            label="Download improved email as TXT",
            data=improved_email,
            file_name="improved_email.txt",
            mime="text/plain"
        )

    except Exception as e:
        error_text = str(e)

        if "API key" in error_text or "GEMINI_API_KEY" in error_text:
            st.error(
                "Gemini API key issue. Please check your GEMINI_API_KEY in secrets.toml."
            )
        elif "quota" in error_text.lower() or "429" in error_text:
            st.error(
                "Gemini quota or rate-limit issue. You may have reached the free-tier limit. "
                "Try again later or use another Gemini model."
            )
        elif "model" in error_text.lower() and "not found" in error_text.lower():
            st.error(
                "The selected Gemini model is not available for your account or region. "
                "Try gemini-2.5-flash or gemini-2.5-flash-lite."
            )
        else:
            st.error("An unexpected error occurred. Please check the terminal for details.")
            st.code(error_text)

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown(
    '<div class="footer-note">Created by Masoud Bakhshi</div>',
    unsafe_allow_html=True
)