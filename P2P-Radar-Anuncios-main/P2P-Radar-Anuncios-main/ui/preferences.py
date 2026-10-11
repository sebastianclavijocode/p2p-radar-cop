"""Load and save personal settings in this browser, never a shared server file."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from core.preferences import clean_preferences
_component=components.declare_component('cop_user_preferences',path=str(Path(__file__).parent/'preferences_component'))

def mount():
    loaded=st.session_state.get('_preferences_loaded',False)
    saved=dict(st.session_state.get('_personal_preferences',{}))
    saved.update(clean_preferences(dict(st.session_state)))
    payload=_component(preferences=saved,hydrated=loaded,key='browser-preferences',default=None)
    if not loaded:
        if not isinstance(payload,dict) or 'preferences' not in payload:
            st.caption('Cargando tus ajustes guardados…')
            st.stop()
        saved=clean_preferences(payload['preferences'])
        st.session_state['_preferences_loaded']=True
    st.session_state['_personal_preferences']=saved
    for key,value in saved.items():
        if key not in st.session_state:st.session_state[key]=value
    if isinstance(payload,dict) and payload.get('storageError'):
        st.caption('Este navegador no permite guardar ajustes. Se conservarán solo durante esta sesión.')
