import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# RISK MONITORING
# ============================================================

def render_risk_monitoring(
    api_get,
    api_post,
):

    # ========================================================
    # HEADER
    # ========================================================

    st.title("↗ Risk Monitoring")

    st.caption(
        "30-day predictive maintenance · "
        "Probability evolution · "
        "Automatic inference · Model V4.2"
    )


    # ========================================================
    # LOAD BIKES
    # ========================================================

    try:

        bikes = api_get("/bikes")

    except Exception as error:

        st.error(
            f"Fleet unavailable: {error}"
        )

        return


    if not bikes:

        st.info(
            "No bikes are currently available. "
            "Risk monitoring will start when telemetry "
            "enters the platform."
        )

        return


    bike_ids = [
        bike["bike_id"]
        for bike in bikes
    ]


    # ========================================================
    # BIKE SELECTOR
    # ========================================================

    selector_col, info_col = st.columns(
        [3, 1]
    )

    with selector_col:

        selected_bike = st.selectbox(
            "Select monitored bike",
            bike_ids,
            key="risk_bike_selector",
        )

    with info_col:

        st.metric(
            "Forecast Horizon",
            "+30 days",
        )


    # ========================================================
    # LOAD PREDICTIONS
    # ========================================================

    try:

        predictions = api_get(
            f"/predictions/{selected_bike}?limit=100"
        )

    except Exception as error:

        st.warning(
            f"Prediction history unavailable: {error}"
        )

        predictions = []


    # ========================================================
    # MANUAL PREDICTION
    # ========================================================

    title_col, button_col = st.columns(
        [3, 1]
    )

    with title_col:

        st.subheader(
            f"Predictive Risk · {selected_bike}"
        )

    with button_col:

        if st.button(
            "Run Prediction",
            type="primary",
            use_container_width=True,
        ):

            try:

                result = api_post(
                    f"/predict/{selected_bike}"
                )

                st.success(
                    f"Prediction created · "
                    f"{result['predicted_risk']}. "
                    f"ID {result['prediction_id']}"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    f"Prediction failed: {error}"
                )


    # ========================================================
    # RELOAD AFTER MANUAL PREDICTION
    # ========================================================

    try:

        predictions = api_get(
            f"/predictions/{selected_bike}?limit=100"
        )

    except Exception:

        pass


    if not predictions:

        st.info(
            "No prediction is available for this bike yet. "
            "The model requires sufficient telemetry history."
        )

        return


    # ========================================================
    # DATAFRAME
    # ========================================================

    prediction_df = pd.DataFrame(
        predictions
    )

    prediction_df[
        "prediction_timestamp"
    ] = pd.to_datetime(
        prediction_df[
            "prediction_timestamp"
        ],
        errors="coerce",
    )

    prediction_df = (
        prediction_df
        .sort_values(
            "prediction_timestamp"
        )
        .reset_index(
            drop=True
        )
    )


    latest = (
        prediction_df
        .iloc[-1]
    )


    # ========================================================
    # CURRENT RISK
    # ========================================================

    st.divider()

    st.subheader(
        "Current 30-Day Risk"
    )


    risk = latest[
        "predicted_risk"
    ]


    if risk == "NORMAL":

        st.success(
            "● NORMAL — No immediate predictive alert"
        )

    elif risk == "WARNING":

        st.warning(
            "● WARNING — Increased future risk detected"
        )

    else:

        st.error(
            "● CRITICAL — High predicted maintenance risk"
        )


    # ========================================================
    # PROBABILITY KPI
    # ========================================================

    normal_probability = (
        float(
            latest[
                "probability_normal"
            ]
        )
        * 100
    )

    warning_probability = (
        float(
            latest[
                "probability_warning"
            ]
        )
        * 100
    )

    critical_probability = (
        float(
            latest[
                "probability_critical"
            ]
        )
        * 100
    )


    p1, p2, p3 = st.columns(3)


    with p1:

        st.metric(
            "NORMAL Probability",
            f"{normal_probability:.2f} %",
        )

    with p2:

        st.metric(
            "WARNING Probability",
            f"{warning_probability:.2f} %",
        )

    with p3:

        st.metric(
            "CRITICAL Probability",
            f"{critical_probability:.2f} %",
        )


    # ========================================================
    # PREDICTION METADATA
    # ========================================================

    m1, m2, m3 = st.columns(3)

    with m1:

        st.metric(
            "Model",
            latest[
                "model_version"
            ],
        )

    with m2:

        st.metric(
            "Prediction ID",
            int(
                latest[
                    "prediction_id"
                ]
            ),
        )

    with m3:

        st.metric(
            "Prediction Time",
            str(
                latest[
                    "prediction_timestamp"
                ]
            ),
        )


    # ========================================================
    # RISK INTERPRETATION
    # ========================================================

    st.subheader(
        "Operational Interpretation"
    )


    if critical_probability >= 70:

        st.error(
            "High critical probability. "
            "The bike should be prioritized for inspection."
        )

    elif critical_probability >= 40:

        st.warning(
            "Critical probability is increasing. "
            "Closer monitoring is recommended."
        )

    elif risk == "WARNING":

        st.warning(
            "The model detects a warning pattern. "
            "Continue monitoring future telemetry."
        )

    else:

        st.success(
            "Current predictive profile remains stable."
        )


    # ========================================================
    # RISK EVOLUTION
    # ========================================================

    st.divider()

    st.subheader(
        "Risk Probability Evolution"
    )


    if len(
        prediction_df
    ) >= 2:

        plot_df = (
            prediction_df
            .copy()
        )


        plot_df[
            "NORMAL"
        ] = (
            plot_df[
                "probability_normal"
            ]
            * 100
        )


        plot_df[
            "WARNING"
        ] = (
            plot_df[
                "probability_warning"
            ]
            * 100
        )


        plot_df[
            "CRITICAL"
        ] = (
            plot_df[
                "probability_critical"
            ]
            * 100
        )


        fig = go.Figure()


        fig.add_trace(
            go.Scatter(
                x=plot_df[
                    "prediction_timestamp"
                ],
                y=plot_df[
                    "NORMAL"
                ],
                mode="lines+markers",
                name="NORMAL",
            )
        )


        fig.add_trace(
            go.Scatter(
                x=plot_df[
                    "prediction_timestamp"
                ],
                y=plot_df[
                    "WARNING"
                ],
                mode="lines+markers",
                name="WARNING",
            )
        )


        fig.add_trace(
            go.Scatter(
                x=plot_df[
                    "prediction_timestamp"
                ],
                y=plot_df[
                    "CRITICAL"
                ],
                mode="lines+markers",
                name="CRITICAL",
            )
        )


        fig.update_layout(
            height=460,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis_title=(
                "Prediction Time"
            ),
            yaxis_title=(
                "Probability (%)"
            ),
            yaxis=dict(
                range=[
                    0,
                    100,
                ]
            ),
            hovermode=(
                "x unified"
            ),
            paper_bgcolor=(
                "rgba(0,0,0,0)"
            ),
            plot_bgcolor=(
                "rgba(0,0,0,0)"
            ),
        )


        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:

        st.info(
            "At least two predictions are required "
            "to display risk evolution."
        )


    # ========================================================
    # CRITICAL RISK TREND
    # ========================================================

    if len(
        prediction_df
    ) >= 2:

        st.subheader(
            "Critical Risk Trend"
        )

        critical_df = (
            prediction_df
            .copy()
        )

        critical_df[
            "critical_percent"
        ] = (
            critical_df[
                "probability_critical"
            ]
            * 100
        )


        fig_critical = (
            go.Figure()
        )


        fig_critical.add_trace(
            go.Scatter(
                x=critical_df[
                    "prediction_timestamp"
                ],
                y=critical_df[
                    "critical_percent"
                ],
                mode="lines+markers",
                fill="tozeroy",
                name="Critical Risk",
            )
        )


        fig_critical.update_layout(
            height=350,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis_title="Time",
            yaxis_title=(
                "Critical Probability (%)"
            ),
            yaxis=dict(
                range=[
                    0,
                    100,
                ]
            ),
            paper_bgcolor=(
                "rgba(0,0,0,0)"
            ),
            plot_bgcolor=(
                "rgba(0,0,0,0)"
            ),
            showlegend=False,
        )


        st.plotly_chart(
            fig_critical,
            use_container_width=True,
        )


    # ========================================================
    # PREDICTION HISTORY
    # ========================================================

    st.divider()

    st.subheader(
        "Prediction History"
    )


    history = (
        prediction_df
        .copy()
    )


    history[
        "Normal %"
    ] = (
        history[
            "probability_normal"
        ]
        * 100
    ).round(2)


    history[
        "Warning %"
    ] = (
        history[
            "probability_warning"
        ]
        * 100
    ).round(2)


    history[
        "Critical %"
    ] = (
        history[
            "probability_critical"
        ]
        * 100
    ).round(2)


    history = (
        history
        .sort_values(
            "prediction_timestamp",
            ascending=False,
        )
    )


    columns = [
        "prediction_id",
        "prediction_timestamp",
        "predicted_risk",
        "Normal %",
        "Warning %",
        "Critical %",
        "model_version",
    ]


    st.dataframe(
        history[
            columns
        ],
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # FOOTER
    # ========================================================

    st.caption(
        f"Asset {selected_bike} · "
        "30-day predictive maintenance · "
        "Automatic inference enabled · "
        "Model V4.2"
    )