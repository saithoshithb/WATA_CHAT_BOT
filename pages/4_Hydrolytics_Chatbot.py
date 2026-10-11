"""Wata chatbot page inside the multipage Clean Water app."""
import streamlit as st

try:  # water_app.py already sets it
    st.set_page_config(page_title="Wata", layout="centered")
except Exception:
    pass

import wata_ui

wata_ui.render()
