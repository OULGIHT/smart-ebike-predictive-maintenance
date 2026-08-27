import streamlit as st


# ============================================================
# SYSTEM ARCHITECTURE
# ============================================================

def render_system_architecture():

    # ========================================================
    # HEADER
    # ========================================================

    st.title("◈ System Architecture")

    st.caption(
        "Digital Twin · Streaming Data Engineering · "
        "Machine Learning · Model Serving · Monitoring"
    )


    # ========================================================
    # PLATFORM OVERVIEW
    # ========================================================

    st.subheader("Smart E-Bike End-to-End Pipeline")

    st.markdown(
        """
The platform combines a physics-informed Digital Twin,
real-time Kafka streaming, PostgreSQL persistence,
temporal feature engineering and 30-day predictive maintenance.
        """
    )


    # ========================================================
    # ARCHITECTURE FLOW
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.info(
            """
**① DIGITAL TWIN**

Virtual E-Bike Fleet

Physics  
Urban dynamics  
Battery degradation  
Sensors
            """
        )

    with c2:

        st.info(
            """
**② STREAMING**

Apache Kafka

`bike_telemetry`
            """
        )

    with c3:

        st.info(
            """
**③ PROCESSING**

Kafka Consumer

Validation  
Normalization  
Automatic inference trigger
            """
        )

    with c4:

        st.info(
            """
**④ STORAGE**

PostgreSQL

Telemetry  
Fleet state  
Predictions
            """
        )


    st.markdown(
        "<h2 style='text-align:center;'>↓</h2>",
        unsafe_allow_html=True,
    )


    c5, c6, c7, c8 = st.columns(4)

    with c5:

        st.info(
            """
**⑤ FEATURES**

Temporal Feature Engineering

57 ML features
            """
        )

    with c6:

        st.info(
            """
**⑥ MACHINE LEARNING**

Model V4.2

NORMAL  
WARNING  
CRITICAL

30-day horizon
            """
        )

    with c7:

        st.info(
            """
**⑦ MODEL SERVING**

FastAPI

Fleet snapshot  
Telemetry history  
Prediction API
            """
        )

    with c8:

        st.info(
            """
**⑧ MONITORING**

Streamlit + Plotly

Fleet Intelligence  
Bike Intelligence  
Risk Monitoring
            """
        )


    # ========================================================
    # DIGITAL TWIN
    # ========================================================

    st.divider()

    st.subheader("Digital Twin Simulation Layer")

    st.code(
        """
Network + Route Planner
          │
          ▼
    Urban Dynamics
Traffic · Slope · Stops
          │
          ▼
     Physics Engine
Speed · Distance · Power
          │
          ▼
  Battery Degradation
   Latent Health Index
          │
          ▼
       E-Bike State
 SOC · Temperature · Trip
          │
          ▼
      Virtual Sensors
          │
          ▼
    Telemetry Generator
""",
        language=None,
    )


    # ========================================================
    # END-TO-END DATA FLOW
    # ========================================================

    st.divider()

    st.subheader("End-to-End Data Flow")

    st.code(
        """
Digital Twin E-Bike Fleet
          │
          ▼
     Sensor Telemetry
          │
          ▼
      Apache Kafka
      bike_telemetry
          │
          ▼
      Kafka Consumer
          │
   Validation / Normalization
          │
          ▼
       PostgreSQL
          │
          ▼
 Temporal Feature Builder
      57 Features
          │
          ▼
      ML Model V4.2
          │
          ▼
 NORMAL / WARNING / CRITICAL
      Forecast: +30 days
          │
          ▼
       PostgreSQL
    Prediction History
          │
          ▼
        FastAPI
          │
          ▼
 Streamlit + Plotly Dashboard
""",
        language=None,
    )


    # ========================================================
    # TECHNOLOGY STACK
    # ========================================================

    st.divider()

    st.subheader("Engineering Stack")

    a, b, c = st.columns(3)

    with a:

        st.markdown("### Simulation & Data")

        st.markdown(
            """
**Digital Twin Simulation**  
Physics, routing, urban dynamics and degradation

**Apache Kafka**  
Real-time telemetry transport

**Kafka Consumer**  
Streaming event processing

**PostgreSQL**  
Telemetry and prediction persistence

**SQLAlchemy**  
Database integration
            """
        )

    with b:

        st.markdown("### Machine Learning")

        st.markdown(
            """
**Scikit-learn**  
Predictive-maintenance classifier

**57 Temporal Features**  
Current, historical and rolling operational signals

**30-Day Horizon**  
Future maintenance-risk classification

**3 Risk Classes**  
NORMAL · WARNING · CRITICAL
            """
        )

    with c:

        st.markdown("### Serving & Monitoring")

        st.markdown(
            """
**FastAPI**  
REST API and model serving

**Streamlit**  
Operational web application

**Plotly**  
Interactive telemetry and risk visualization

**Manual + Automatic Inference**  
Consumer-driven predictions with optional operator inference
            """
        )


    # ========================================================
    # AUTOMATIC INFERENCE
    # ========================================================

    st.divider()

    st.subheader("Automatic Inference")

    st.markdown(
        """
Telemetry events are consumed continuously.

After the configured number of new observations for a bike,
the consumer triggers the prediction service.

The temporal feature builder reconstructs the 57 model inputs
from PostgreSQL telemetry history, the V4.2 model produces a
30-day risk estimate, and the resulting probabilities are stored
in PostgreSQL.
        """
    )

    st.code(
        """
New telemetry
      ↓
Kafka
      ↓
Consumer
      ↓
PostgreSQL
      ↓
New-event counter
      ↓
57 temporal features
      ↓
Model V4.2
      ↓
30-day risk prediction
      ↓
Prediction history
      ↓
FastAPI
      ↓
Dashboard
""",
        language=None,
    )


    # ========================================================
    # PROJECT CAPABILITIES
    # ========================================================

    st.divider()

    st.subheader("Platform Capabilities")

    p1, p2, p3, p4 = st.columns(4)

    with p1:

        st.metric(
            "Streaming",
            "Kafka",
        )

    with p2:

        st.metric(
            "Digital Twin Fleet",
            "200 Bikes",
        )

    with p3:

        st.metric(
            "ML Features",
            "57",
        )

    with p4:

        st.metric(
            "Forecast Horizon",
            "30 Days",
        )


    st.divider()

    st.caption(
        "Smart E-Bike Platform V4.2 · "
        "Digital Twin · Streaming Data Engineering · "
        "Predictive Maintenance · ML Engineering"
    )