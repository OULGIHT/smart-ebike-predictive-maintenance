import requests
import streamlit as st

from pages_V42.fleet_overview import (
    render_fleet_overview,
)

from pages_V42.bike_intelligence import (
    render_bike_intelligence,
)

from pages_V42.risk_monitoring import (
    render_risk_monitoring,
)

from pages_V42.system_architecture import (
    render_system_architecture,
)


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="E-Bike Sentinel",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# API HELPERS
# ============================================================

def api_get(endpoint):

    response = requests.get(
        f"{API_URL}{endpoint}",
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


def api_post(endpoint):

    response = requests.post(
        f"{API_URL}{endpoint}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# API STATUS
# ============================================================

try:

    health = api_get(
        "/health"
    )

    api_online = True

except Exception:

    health = None
    api_online = False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "E-Bike Sentinel"
    )

    st.caption(
        "Predictive Maintenance Platform"
    )

    st.divider()

    if api_online:

        st.success(
            "API ONLINE"
        )

    else:

        st.warning(
            "API OFFLINE"
        )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Fleet Overview",
            "Bike Intelligence",
            "Risk Monitoring",
            "System Architecture",
        ],
    )

    st.divider()

    st.markdown(
        "### Predictive Engine"
    )

    st.write(
        "Model: V4.2"
    )

    st.write(
        "Features: 57 temporal features"
    )

    st.write(
        "Horizon: +30 days"
    )

    st.write(
        "Classes: NORMAL / WARNING / CRITICAL"
    )

    st.divider()

    st.caption(
        "Live refresh: every 5 seconds"
    )


# ============================================================
# API OFFLINE
# ============================================================

if not api_online:

    st.title(
        "E-Bike Sentinel"
    )

    st.warning(
        "FastAPI is currently offline."
    )

    st.code(
        (
            "python -m uvicorn "
            "api.main_V42:app "
            "--host 127.0.0.1 "
            "--port 8000"
        ),
        language="powershell",
    )

    st.caption(
        "System Architecture remains available "
        "without the API."
    )

    if page == "System Architecture":

        render_system_architecture()

    st.stop()


# ============================================================
# LIVE PAGE RENDERING
#
# Streamlit native fragment.
# The selected page is refreshed every 5 seconds.
# Producer / Consumer / FastAPI remain independent.
# ============================================================

@st.fragment(
    run_every="5s"
)
def render_live_page():

    if page == "Fleet Overview":

        render_fleet_overview(
            api_get=api_get,
        )


    elif page == "Bike Intelligence":

        render_bike_intelligence(
            api_get=api_get,
        )


    elif page == "Risk Monitoring":

        render_risk_monitoring(
            api_get=api_get,
            api_post=api_post,
        )


    elif page == "System Architecture":

        render_system_architecture()


# ============================================================
# RUN LIVE PAGE
# ============================================================

render_live_page()
