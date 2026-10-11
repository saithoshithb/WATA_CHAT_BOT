"""Wata, the Hydrolytics chatbot, as its own hostable Streamlit app.

Run locally:  python -m streamlit run wata_app.py
Deploy:       share.streamlit.io -> Main file path: wata_app.py
Needs only:   wata_app.py, wata_ui.py, chatbot_logic.py and requirements.txt (streamlit, pandas).
"""
import streamlit as st

st.set_page_config(page_title="Wata", page_icon="💧", layout="centered", initial_sidebar_state="collapsed")

import wata_ui

wata_ui.render(hide_sidebar=True)
