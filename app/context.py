"""Context shared by registered Streamlit file pages."""
import streamlit as st

def current_context():
    context=st.session_state.get('_windgrid_context')
    if context is None:
        st.error('Launch app/dashboard.py to initialise the WindGrid research platform.')
        st.stop()
    return context
