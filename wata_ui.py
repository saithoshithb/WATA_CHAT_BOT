"""Shared chat screen for Wata. Used by wata_app.py (standalone) and pages/4_Hydrolytics_Chatbot.py."""
import json
import os
import urllib.request

import streamlit as st

import chatbot_logic as bot


def _secret(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def _llm_answer(question):
    """Optional: ask Google Gemini, limited to our own facts. Returns None on any problem.

    Uses plain HTTPS (no extra library needed). Key: GEMINI_API_KEY (or GOOGLE_API_KEY).
    Model: GEMINI_MODEL if set, else gemini-2.5-flash.
    """
    key = _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")
    if not key:
        return None
    model = _secret("GEMINI_MODEL") or "gemini-2.5-flash"
    facts = "\n".join(f"- {a}" for _, a in bot.KNOWLEDGE)
    body = {
        "system_instruction": {"parts": [{"text": (
            "You are Wata, the Hydrolytics project assistant. Answer briefly using ONLY these facts. "
            "If the answer is not in them, say you don't know. Never give medical advice.\n" + facts)}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.2},
    }
    try:
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip() or None
    except Exception:
        return None


BURGUNDY, BURGUNDY_DARK = "#6D1A36", "#4A1024"
BEIGE, BEIGE_DARK, CREAM, INK = "#F5EBDC", "#E8D6BC", "#FFF8EC", "#3B1A1F"

CSS = f"""
<style>
.stApp, [data-testid="stAppViewContainer"] {{ background: {BEIGE}; color: {INK}; }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
.block-container {{ max-width: 760px; padding-top: 2rem; }}
h1, h2, h3, p, label, span, div {{ color: {INK}; }}

.wata-hero {{ background: {BURGUNDY}; border-radius: 18px; padding: 22px 26px; margin-bottom: 18px;
  box-shadow: 0 6px 18px rgba(74,16,36,.25); }}
.wata-hero h1 {{ color: {BEIGE} !important; margin: 0; font-size: 2.2rem; letter-spacing: .5px; }}
.wata-hero p {{ color: {BEIGE_DARK} !important; margin: 4px 0 0 0; font-size: 1rem; }}

.stButton > button {{ background: {CREAM}; color: {BURGUNDY}; border: 1.5px solid {BURGUNDY};
  border-radius: 999px; font-weight: 600; transition: all .15s; }}
.stButton > button:hover {{ background: {BURGUNDY}; color: {BEIGE}; border-color: {BURGUNDY}; }}
.stButton > button:focus {{ box-shadow: 0 0 0 3px rgba(109,26,54,.25); color: {BURGUNDY}; }}

[data-testid="stChatMessage"] {{ background: {BEIGE_DARK}; border-radius: 16px; padding: 12px 16px;
  border: 1px solid rgba(109,26,54,.15); }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{ background: {BURGUNDY}; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * {{ color: {BEIGE} !important; }}
[data-testid="stChatMessageAvatarAssistant"] {{ background: {BURGUNDY}; color: {BEIGE}; }}
[data-testid="stChatMessageAvatarUser"] {{ background: {BEIGE}; }}

[data-testid="stChatInput"] {{ background: {CREAM}; border: 2px solid {BURGUNDY}; border-radius: 14px; }}
[data-testid="stChatInput"] textarea {{ color: {INK}; background: {CREAM}; }}
[data-testid="stChatInput"] button {{ background: {BURGUNDY}; color: {BEIGE}; }}
[data-testid="stBottom"], [data-testid="stBottom"] > div {{ background: {BEIGE}; }}

[data-testid="stExpander"] {{ background: {CREAM}; border: 1px solid rgba(109,26,54,.3); border-radius: 12px; }}
[data-testid="stExpander"] summary:hover {{ color: {BURGUNDY}; }}
input[type=number] {{ background: {CREAM}; color: {INK}; }}
a {{ color: {BURGUNDY}; }}
</style>
"""

HIDE_SIDEBAR = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stSidebarNav"] { display: none !important; }
</style>
"""


def render(hide_sidebar=False):
    st.markdown(CSS, unsafe_allow_html=True)
    if hide_sidebar:
        st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
    st.markdown(
        '<div class="wata-hero"><h1>Wata</h1>'
        "<p>Your Hydrolytics guide: microplastics, our detection method, and the water tools.</p></div>",
        unsafe_allow_html=True)

    # Settings live on the page itself (no sidebar menu).
    with st.expander("Leak-check settings"):
        warn = st.number_input("Warning at loss % >=", 1.0, 99.0, 20.0)
        crit = st.number_input("Critical at loss % >=", 1.0, 99.0, 30.0)

    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": bot.GREETING}]

    # Quick-question buttons
    cols = st.columns(2)
    clicked = None
    for i, q in enumerate(bot.SUGGESTIONS):
        if cols[i % 2].button(q, key=f"sg{i}", use_container_width=True):
            clicked = q

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    typed = st.chat_input("Type your question...")
    question = typed or clicked
    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        answer = bot.reply(question, warn, crit)
        if answer.startswith("I'm not sure about that one"):
            answer = _llm_answer(question) or answer
        st.session_state.chat.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

    if len(st.session_state.chat) > 1 and st.button("Clear chat"):
        st.session_state.pop("chat", None)
        st.rerun()
