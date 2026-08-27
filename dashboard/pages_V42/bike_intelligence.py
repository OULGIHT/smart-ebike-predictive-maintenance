import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# BIKE INTELLIGENCE
# ============================================================

def render_bike_intelligence(api_get):

    # ========================================================
    # HEADER
    # ========================================================

    st.title("🚲 Bike Intelligence")

    st.caption(
        "Individual asset monitoring · "
        "Live telemetry · Operational behavior"
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
            "No bikes are currently registered. "
            "Bike monitoring will start when telemetry arrives."
        )

        return


    bike_ids = [
        bike["bike_id"]
        for bike in bikes
    ]


    # ========================================================
    # BIKE SELECTOR
    # ========================================================

    selector_col, status_col = st.columns(
        [3, 1]
    )

    with selector_col:

        selected_bike = st.selectbox(
            "Select monitored bike",
            bike_ids,
            key="bike_intelligence_selector",
        )


    # ========================================================
    # LOAD CURRENT STATE
    # ========================================================

    try:

        bike = api_get(
            f"/bikes/{selected_bike}"
        )

    except Exception as error:

        st.error(
            f"Bike data unavailable: {error}"
        )

        return


    with status_col:

        st.metric(
            "Operational Status",
            bike.get(
                "status",
                "UNKNOWN",
            ),
        )


    st.caption(
        f"Latest telemetry · "
        f"{bike.get('timestamp', 'N/A')}"
    )


    # ========================================================
    # CURRENT STATE
    # ========================================================

    st.subheader("Current Operating State")


    c1, c2, c3 = st.columns(3)

    with c1:

        value = bike.get(
            "battery_temperature_c"
        )

        st.metric(
            "Battery Temperature",
            (
                f"{value:.1f} °C"
                if value is not None
                else "N/A"
            ),
        )

    with c2:

        value = bike.get(
            "final_soc"
        )

        st.metric(
            "State of Charge",
            (
                f"{value:.1f} %"
                if value is not None
                else "N/A"
            ),
        )

    with c3:

        value = bike.get(
            "battery_power_w"
        )

        st.metric(
            "Battery Power",
            (
                f"{value:.1f} W"
                if value is not None
                else "N/A"
            ),
        )


    c4, c5, c6 = st.columns(3)

    with c4:

        value = bike.get(
            "consumption_wh_km"
        )

        st.metric(
            "Energy Consumption",
            (
                f"{value:.1f} Wh/km"
                if value is not None
                else "N/A"
            ),
        )

    with c5:

        value = bike.get(
            "average_speed_kmh"
        )

        st.metric(
            "Average Speed",
            (
                f"{value:.1f} km/h"
                if value is not None
                else "N/A"
            ),
        )

    with c6:

        value = bike.get(
            "mechanical_power_w"
        )

        st.metric(
            "Mechanical Power",
            (
                f"{value:.1f} W"
                if value is not None
                else "N/A"
            ),
        )


    # ========================================================
    # ENVIRONMENT
    # ========================================================

    st.subheader("Operating Conditions")

    e1, e2, e3 = st.columns(3)

    with e1:

        value = bike.get(
            "ambient_temperature_c"
        )

        st.metric(
            "Ambient Temperature",
            (
                f"{value:.1f} °C"
                if value is not None
                else "N/A"
            ),
        )

    with e2:

        value = bike.get(
            "traffic_factor"
        )

        st.metric(
            "Traffic Factor",
            (
                f"{value:.2f}"
                if value is not None
                else "N/A"
            ),
        )

    with e3:

        value = bike.get(
            "slope_percent"
        )

        st.metric(
            "Slope",
            (
                f"{value:.1f} %"
                if value is not None
                else "N/A"
            ),
        )


    # ========================================================
    # LOAD TELEMETRY
    # ========================================================

    st.divider()

    try:

        telemetry = api_get(
            f"/bikes/{selected_bike}/telemetry?limit=200"
        )

    except Exception as error:

        st.warning(
            f"Telemetry history unavailable: {error}"
        )

        telemetry = []


    if not telemetry:

        st.info(
            "No telemetry history is available "
            "for this bike."
        )

        return


    telemetry_df = pd.DataFrame(
        telemetry
    )

    telemetry_df["timestamp"] = pd.to_datetime(
        telemetry_df["timestamp"],
        errors="coerce",
    )

    telemetry_df = (
        telemetry_df
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


    # ========================================================
    # BATTERY INTELLIGENCE
    # ========================================================

    st.subheader("Battery Intelligence")


    fig_battery = go.Figure()


    fig_battery.add_trace(
        go.Scatter(
            x=telemetry_df["timestamp"],
            y=telemetry_df[
                "battery_temperature_c"
            ],
            mode="lines+markers",
            name="Battery Temperature",
        )
    )


    fig_battery.update_layout(
        height=360,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )


    st.plotly_chart(
        fig_battery,
        use_container_width=True,
    )


    # ========================================================
    # SOC
    # ========================================================

    left, right = st.columns(2)


    with left:

        st.subheader("State of Charge")

        fig_soc = go.Figure()

        fig_soc.add_trace(
            go.Scatter(
                x=telemetry_df["timestamp"],
                y=telemetry_df["final_soc"],
                mode="lines+markers",
                name="SOC",
            )
        )

        fig_soc.update_layout(
            height=340,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis_title="Time",
            yaxis_title="SOC (%)",
            yaxis=dict(
                range=[0, 100]
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        st.plotly_chart(
            fig_soc,
            use_container_width=True,
        )


    # ========================================================
    # CONSUMPTION
    # ========================================================

    with right:

        st.subheader("Energy Consumption")

        fig_consumption = go.Figure()

        fig_consumption.add_trace(
            go.Scatter(
                x=telemetry_df["timestamp"],
                y=telemetry_df[
                    "consumption_wh_km"
                ],
                mode="lines+markers",
                name="Consumption",
            )
        )

        fig_consumption.update_layout(
            height=340,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis_title="Time",
            yaxis_title="Wh/km",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        st.plotly_chart(
            fig_consumption,
            use_container_width=True,
        )


    # ========================================================
    # SIGNAL EXPLORER
    # ========================================================

    st.divider()

    st.subheader("Telemetry Signal Explorer")


    signal_labels = {

        "Battery Temperature":
            "battery_temperature_c",

        "Battery Power":
            "battery_power_w",

        "State of Charge":
            "final_soc",

        "Energy Consumption":
            "consumption_wh_km",

        "Average Speed":
            "average_speed_kmh",

        "Mechanical Power":
            "mechanical_power_w",

        "Ambient Temperature":
            "ambient_temperature_c",

        "Traffic Factor":
            "traffic_factor",

        "Slope":
            "slope_percent",
    }


    selected_signal = st.selectbox(
        "Signal",
        list(signal_labels.keys()),
        key="bike_signal_explorer",
    )


    signal_column = signal_labels[
        selected_signal
    ]


    if signal_column in telemetry_df.columns:

        fig_signal = go.Figure()

        fig_signal.add_trace(
            go.Scatter(
                x=telemetry_df["timestamp"],
                y=telemetry_df[
                    signal_column
                ],
                mode="lines",
                name=selected_signal,
            )
        )

        fig_signal.update_layout(
            height=390,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis_title="Time",
            yaxis_title=selected_signal,
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        st.plotly_chart(
            fig_signal,
            use_container_width=True,
        )


    # ========================================================
    # RECENT TELEMETRY
    # ========================================================

    with st.expander(
        "Inspect recent telemetry events"
    ):

        columns = [
            "timestamp",
            "battery_temperature_c",
            "final_soc",
            "consumption_wh_km",
            "battery_power_w",
            "average_speed_kmh",
            "traffic_factor",
            "slope_percent",
        ]

        available_columns = [
            column
            for column in columns
            if column in telemetry_df.columns
        ]


        recent = (
            telemetry_df[
                available_columns
            ]
            .sort_values(
                "timestamp",
                ascending=False,
            )
            .head(25)
        )


        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # FOOTER
    # ========================================================

    st.caption(
        f"Asset {selected_bike} · "
        "Live telemetry monitoring · "
        "Smart E-Bike Platform V4.2"
    )