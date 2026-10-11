"""Shared chat screen for Wata. Used by wata_app.py (standalone) and pages/4_Hydrolytics_Chatbot.py."""
import os

import streamlit as st

import chatbot_logic as bot


def _api_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def _llm_answer(question):
    """Optional: ask an AI model, grounded in our knowledge base. Returns None on any problem."""
    key = _api_key()
    if not key:
        return None
    try:
        import anthropic
        facts = "\n".join(f"- {a}" for _, a in bot.KNOWLEDGE)
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-5-5", max_tokens=400,
            system=("You are Wata, the Hydrolytics project assistant. Answer briefly using ONLY these facts. "
                    "If the answer is not in them, say you don't know. Never give medical advice.\n" + facts),
            messages=[{"role": "user", "content": question}],
        )
        return msg.content[0].text
    except Exception:
        return None


def render():
    st.title("Wata")
    st.caption("Ask about microplastics, how our detection works, or the complaint, usage and leakage tools.")

    with st.sidebar:
        st.header("Leak thresholds")
        warn = st.number_input("Warning at loss % >=", 1.0, 99.0, 20.0)
        crit = st.number_input("Critical at loss % >=", 1.0, 99.0, 30.0)
        if st.button("Clear chat"):
            st.session_state.pop("chat", None)
            st.rerun()

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
