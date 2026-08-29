import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# FLEET OVERVIEW
# ============================================================

def render_fleet_overview(api_get):

    # ========================================================
    # HEADER
    # ========================================================

    title_col, status_col = st.columns(
        [4, 1]
    )

    with title_col:

        st.markdown(
            "## ⚡ Fleet Intelligence Center"
        )

        st.caption(
            "Real-time fleet operations · "
            "Predictive maintenance · "
            "30-day risk intelligence"
        )

    with status_col:

        st.success(
            "● LIVE SYSTEM"
        )


    # ========================================================
    # LOAD SUMMARY
    # ========================================================

    try:

        summary = api_get(
            "/fleet/summary"
        )

    except Exception as error:

        st.error(
            f"Fleet data unavailable: {error}"
        )

        return


    # ========================================================
    # SUMMARY VALUES
    # ========================================================

    risk_distribution = summary.get(
        "risk_distribution",
        {},
    )

    total_bikes = summary.get(
        "total_bikes",
        0,
    )

    total_telemetry = summary.get(
        "total_telemetry",
        0,
    )

    total_predictions = summary.get(
        "total_predictions",
        0,
    )

    last_telemetry = summary.get(
        "last_telemetry"
    )

    last_prediction = summary.get(
        "last_prediction"
    )

    normal = risk_distribution.get(
        "NORMAL",
        0,
    )

    warning = risk_distribution.get(
        "WARNING",
        0,
    )

    critical = risk_distribution.get(
        "CRITICAL",
        0,
    )


    # ========================================================
    # FLEET HEALTH
    # ========================================================

    st.subheader(
        "Fleet Health"
    )

    c1, c2, c3, c4 = st.columns(
        4
    )


    with c1:

        st.metric(
            "🚲 Total Fleet",
            f"{total_bikes:,}",
        )


    with c2:

        st.markdown(
            "### 🟢 NORMAL"
        )

        st.metric(
            "Healthy bikes",
            normal,
        )


    with c3:

        st.markdown(
            "### 🟠 WARNING"
        )

        st.metric(
            "Monitoring required",
            warning,
        )


    with c4:

        st.markdown(
            "### 🔴 CRITICAL"
        )

        st.metric(
            "Priority inspection",
            critical,
        )


    st.divider()


    # ========================================================
    # PREDICTIVE ENGINE
    # ========================================================

    st.subheader(
        "🟣 Predictive Engine"
    )

    st.caption(
        "Machine-learning layer transforming "
        "temporal telemetry into 30-day risk estimates"
    )


    p1, p2, p3, p4 = st.columns(
        4
    )


    with p1:

        st.metric(
            "ML Model",
            summary.get(
                "model_version",
                "V4.2",
            ),
        )


    with p2:

        st.metric(
            "Temporal Features",
            "57",
        )


    with p3:

        horizon = summary.get(
            "prediction_horizon_days",
            30,
        )

        st.metric(
            "Forecast Horizon",
            f"+{horizon} days",
        )


    with p4:

        st.metric(
            "Inference Mode",
            "Automatic",
        )


    st.info(
        "57 temporal features  →  "
        "ML Model V4.2  →  "
        "NORMAL / WARNING / CRITICAL  →  "
        "30-day predictive maintenance"
    )


    # ========================================================
    # PLATFORM ACTIVITY
    # ========================================================

    st.subheader(
        "🔵 Platform Activity"
    )


    a1, a2, a3 = st.columns(
        3
    )


    with a1:

        st.metric(
            "Telemetry Processed",
            f"{total_telemetry:,}",
        )


    with a2:

        st.metric(
            "Risk Assessments",
            f"{total_predictions:,}",
        )


    with a3:

        st.metric(
            "Prediction Classes",
            "3",
        )


    # ========================================================
    # LIVE TIMESTAMPS
    # ========================================================

    live1, live2 = st.columns(
        2
    )


    with live1:

        if last_telemetry:

            st.caption(
                f"Latest telemetry: "
                f"{last_telemetry}"
            )

        else:

            st.caption(
                "Latest telemetry: unavailable"
            )


    with live2:

        if last_prediction:

            st.caption(
                f"Latest prediction: "
                f"{last_prediction}"
            )

        else:

            st.caption(
                "Latest prediction: unavailable"
            )


    st.caption(
        "Live monitoring data refreshed automatically "
        "every 5 seconds."
    )


    st.divider()


    # ========================================================
    # LOAD BIKES
    # ========================================================

    try:

        bikes = api_get(
            "/bikes"
        )

    except Exception as error:

        st.warning(
            f"Fleet unavailable: {error}"
        )

        bikes = []


    # ========================================================
    # EMPTY PLATFORM
    # ========================================================

    if not bikes:

        st.info(
            "No telemetry has been received yet. "
            "The platform is ready for incoming e-bike events."
        )

        return


    # ========================================================
    # DATAFRAME
    # ========================================================

    fleet_df = pd.DataFrame(
        bikes
    )


    if (
        "last_telemetry"
        in fleet_df.columns
    ):

        fleet_df[
            "last_telemetry"
        ] = pd.to_datetime(
            fleet_df[
                "last_telemetry"
            ],
            errors="coerce",
        )


    # ========================================================
    # ANALYTICS
    # ========================================================

    left, right = st.columns(
        [1, 1.7]
    )


    # ========================================================
    # RISK DISTRIBUTION
    # ========================================================

    with left:

        st.subheader(
            "Fleet Risk Distribution"
        )


        values = [
            normal,
            warning,
            critical,
        ]

        labels = [
            "NORMAL",
            "WARNING",
            "CRITICAL",
        ]


        if sum(values) > 0:

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.67,
                        textinfo=(
                            "label+percent"
                        ),
                        marker=dict(
                            colors=[
                                "#22c55e",
                                "#f59e0b",
                                "#ef4444",
                            ]
                        ),
                    )
                ]
            )


            fig.update_layout(
                height=390,

                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10,
                ),

                paper_bgcolor=(
                    "rgba(0,0,0,0)"
                ),

                showlegend=False,
            )


            st.plotly_chart(
                fig,
                width="stretch",
            )

        else:

            st.info(
                "Risk distribution will appear "
                "after the first ML predictions."
            )


    # ========================================================
    # FLEET TABLE
    # ========================================================

    with right:

        st.subheader(
            "Fleet Operations"
        )


        st.dataframe(
            fleet_df,
            width="stretch",
            hide_index=True,
            height=390,
        )


    # ========================================================
    # ALERT
    # ========================================================

    st.divider()


    if critical > 0:

        st.error(
            f"🔴 {critical} bike(s) currently classified "
            f"as CRITICAL."
        )

    elif warning > 0:

        st.warning(
            f"🟠 {warning} bike(s) currently require monitoring."
        )

    else:

        st.success(
            "🟢 No active fleet-level predictive alerts."
        )


    # ========================================================
    # FOOTER
    # ========================================================

    st.caption(
        "Smart E-Bike Platform V4.2 · "
        "Streaming telemetry · "
        "Temporal feature engineering · "
        "30-day predictive maintenance"
    )