"""Lazy page dispatch for the registered Streamlit pages."""
import importlib
import streamlit as st
from context import current_context
from platform_data import ArtifactError

def render_page(name):
    context=current_context()
    if context.get('block_id') is None and name not in ['command_center','reproducibility','results','real_data']:
        st.error('No valid evaluation block can be selected. Restore the saved docs/tables_v2 summaries; block identities are never invented.')
        st.caption(context.get('summary_error','Research summaries are unavailable.'))
        return
    try:
        if name in ['command_center','digital_twin']:
            module=importlib.import_module('views.operations')
            getattr(module,name)(context)
        elif name in ['results','reproducibility']:
            getattr(importlib.import_module('views.research'),name)(context)
        else:importlib.import_module('views.'+name).render(context)
    except ArtifactError as error:
        st.error('Research artifact unavailable or invalid: '+str(error))
        st.info('Restore the named local input or summary artifact. Original data is never replaced with example or synthetic observations.')
