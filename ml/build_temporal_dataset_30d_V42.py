import os
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = os.path.join(
    "data",
    "raw",
    "fleet_longitudinal_V42.csv"
)

OUTPUT_FILE = os.path.join(
    "data",
    "processed",
    "temporal_dataset_30d_V42.csv"
)

HISTORY_DAYS = 7
FUTURE_HORIZON_DAYS = 30


# ============================================================
# VARIABLES OBSERVABLES
# ============================================================

SENSOR_FEATURES = [
    "battery_temperature_c",
    "battery_power_w",
    "mechanical_power_w",
    "consumption_wh_km",
    "average_speed_kmh",
    "final_soc",
    "traffic_factor",
]


# ============================================================
# VARIABLES INTERDITES COMME FEATURES
# ============================================================

FORBIDDEN_FEATURES = [
    "degradation_profile",
    "latent_health_before",
    "latent_health_after",
    "current_risk_class",
    "target_risk_30d",
    "target_timestamp_30d",
]


# ============================================================
# CHARGEMENT
# ============================================================

def load_dataset():

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Fichier introuvable : {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="mixed",
        errors="raise"
    )

    df = df.sort_values(
        ["bike_id", "timestamp"]
    ).reset_index(drop=True)

    print(f"Raw rows : {len(df)}")
    print(f"Bikes    : {df['bike_id'].nunique()}")

    return df


# ============================================================
# VARIABLES INSTANTANEES OBSERVABLES
# ============================================================

def create_instantaneous_features(df):

    df = df.copy()

    df["soc_drop"] = (
        df["initial_soc"]
        -
        df["final_soc"]
    )

    df["power_gap_w"] = (
        df["battery_power_w"]
        -
        df["mechanical_power_w"]
    )

    df["thermal_gap_c"] = (
        df["battery_temperature_c"]
        -
        df["ambient_temperature_c"]
    )

    return df


# ============================================================
# PENTE TEMPORELLE
# ============================================================

def temporal_slope(window):

    if len(window) < 3:
        return np.nan

    values = window.to_numpy(
        dtype=float
    )

    times = (
        window.index
        -
        window.index[0]
    ).total_seconds() / 86400.0

    times = np.asarray(
        times,
        dtype=float
    )

    valid = (
        np.isfinite(values)
        &
        np.isfinite(times)
    )

    values = values[valid]
    times = times[valid]

    if len(values) < 3:
        return np.nan

    if np.ptp(times) == 0:
        return np.nan

    return np.polyfit(
        times,
        values,
        1
    )[0]


# ============================================================
# FEATURES SUR LES 7 JOURS PASSES
# ============================================================

def create_history_features(df):

    result_parts = []

    for bike_id, bike_df in df.groupby(
        "bike_id",
        sort=False
    ):

        bike_df = bike_df.sort_values(
            "timestamp"
        ).copy()

        # ----------------------------------------------------
        # IMPORTANT
        #
        # On utilise closed="left".
        #
        # Donc pour une observation au temps t :
        #
        # [t - 7 jours, t[
        #
        # L'observation actuelle n'entre PAS dans son propre
        # historique.
        # ----------------------------------------------------

        indexed = bike_df.set_index(
            "timestamp"
        )

        for column in SENSOR_FEATURES:

            series = indexed[column]

            rolling = series.rolling(
                window=f"{HISTORY_DAYS}D",
                min_periods=3,
                closed="left"
            )

            bike_df[
                f"{column}_mean_7d"
            ] = rolling.mean().to_numpy()

            bike_df[
                f"{column}_std_7d"
            ] = rolling.std().to_numpy()

            bike_df[
                f"{column}_min_7d"
            ] = rolling.min().to_numpy()

            bike_df[
                f"{column}_max_7d"
            ] = rolling.max().to_numpy()

            # ------------------------------------------------
            # Nombre d'observations dans la fenêtre
            # ------------------------------------------------

            bike_df[
                f"{column}_count_7d"
            ] = rolling.count().to_numpy()

        # ----------------------------------------------------
        # TENDANCES
        # ----------------------------------------------------

        trend_columns = [
            "battery_temperature_c",
            "consumption_wh_km",
            "battery_power_w",
            "final_soc",
        ]

        for column in trend_columns:

            slopes = []

            timestamps = bike_df[
                "timestamp"
            ]

            values = bike_df[
                column
            ]

            for i in range(
                len(bike_df)
            ):

                current_time = (
                    timestamps.iloc[i]
                )

                start_time = (
                    current_time
                    -
                    pd.Timedelta(
                        days=HISTORY_DAYS
                    )
                )

                mask = (
                    (timestamps >= start_time)
                    &
                    (timestamps < current_time)
                )

                history = pd.Series(
                    values.loc[mask].to_numpy(),
                    index=timestamps.loc[mask]
                )

                slopes.append(
                    temporal_slope(
                        history
                    )
                )

            bike_df[
                f"{column}_slope_7d"
            ] = slopes

        # ----------------------------------------------------
        # NOMBRE DE TRAJETS OBSERVES SUR 7 JOURS
        # ----------------------------------------------------

        indexed_count = (
            indexed["bike_id"]
            .rolling(
                window=f"{HISTORY_DAYS}D",
                closed="left"
            )
            .count()
        )

        bike_df[
            "trip_count_7d"
        ] = indexed_count.to_numpy()

        result_parts.append(
            bike_df
        )

    result = pd.concat(
        result_parts,
        ignore_index=True
    )

    result = result.sort_values(
        ["bike_id", "timestamp"]
    ).reset_index(drop=True)

    return result


# ============================================================
# CIBLE FUTURE A +30 JOURS
# ============================================================

def create_future_target(df):

    df = df.copy()

    df["target_risk_30d"] = None

    df["target_timestamp_30d"] = pd.NaT

    horizon = pd.Timedelta(
        days=FUTURE_HORIZON_DAYS
    )

    for bike_id, bike_df in df.groupby(
        "bike_id"
    ):

        bike_df = bike_df.sort_values(
            "timestamp"
        )

        indices = (
            bike_df.index.to_numpy()
        )

        timestamps = (
            bike_df["timestamp"]
            .to_numpy(
                dtype="datetime64[ns]"
            )
        )

        risks = (
            bike_df["current_risk_class"]
            .to_numpy()
        )

        for local_i in range(
            len(bike_df)
        ):

            current_time = (
                bike_df.iloc[
                    local_i
                ]["timestamp"]
            )

            target_time = (
                current_time
                +
                horizon
            )

            future_position = (
                timestamps.searchsorted(
                    np.datetime64(
                        target_time
                    ),
                    side="left"
                )
            )

            if future_position >= len(
                bike_df
            ):
                continue

            current_index = (
                indices[
                    local_i
                ]
            )

            future_index = (
                indices[
                    future_position
                ]
            )

            df.at[
                current_index,
                "target_risk_30d"
            ] = (
                risks[
                    future_position
                ]
            )

            df.at[
                current_index,
                "target_timestamp_30d"
            ] = (
                df.at[
                    future_index,
                    "timestamp"
                ]
            )

    return df


# ============================================================
# TRANSITIONS
# ============================================================

def create_transition_column(df):

    df = df.copy()

    df["future_transition_30d"] = (

        df[
            "current_risk_class"
        ].astype(str)

        +

        "->"

        +

        df[
            "target_risk_30d"
        ].astype(str)
    )

    return df


# ============================================================
# FILTRAGE
# ============================================================

def filter_dataset(df):

    df = df.copy()

    # --------------------------------------------------------
    # Il faut une cible future
    # --------------------------------------------------------

    df = df[
        df[
            "target_risk_30d"
        ].notna()
    ].copy()

    # --------------------------------------------------------
    # Il faut suffisamment d'historique réel
    # --------------------------------------------------------

    required = [
        "battery_temperature_c_mean_7d",
        "battery_temperature_c_slope_7d",
        "consumption_wh_km_mean_7d",
        "consumption_wh_km_slope_7d",
        "battery_power_w_mean_7d",
        "battery_power_w_slope_7d",
        "final_soc_mean_7d",
        "final_soc_slope_7d",
    ]

    df = df.dropna(
        subset=required
    ).copy()

    # Au moins 3 trajets historiques
    df = df[
        df["trip_count_7d"] >= 3
    ].copy()

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(df):

    print()
    print("=" * 75)
    print("TEMPORAL VALIDATION")
    print("=" * 75)

    target_time = pd.to_datetime(
        df["target_timestamp_30d"]
    )

    horizon = (
        target_time
        -
        df["timestamp"]
    ).dt.total_seconds() / 86400.0

    invalid = (
        horizon
        <
        FUTURE_HORIZON_DAYS
    ).sum()

    print(
        f"Target horizon < 30 days : {invalid}"
    )

    if invalid != 0:
        raise ValueError(
            "Temporal leakage detected."
        )

    print(
        f"Minimum real horizon      : "
        f"{horizon.min():.3f} days"
    )

    print(
        f"Mean real horizon         : "
        f"{horizon.mean():.3f} days"
    )

    print(
        f"Maximum real horizon      : "
        f"{horizon.max():.3f} days"
    )

    # --------------------------------------------------------
    # Vérification du nombre de trajets historiques
    # --------------------------------------------------------

    print(
        f"Minimum history trips     : "
        f"{df['trip_count_7d'].min():.0f}"
    )

    print(
        f"Mean history trips        : "
        f"{df['trip_count_7d'].mean():.2f}"
    )


# ============================================================
# DIAGNOSTIC
# ============================================================

def diagnostics(df):

    print()
    print("=" * 75)
    print("FINAL TEMPORAL DATASET V4.2")
    print("=" * 75)

    print(
        f"Rows    : {len(df)}"
    )

    print(
        f"Columns : {len(df.columns)}"
    )

    print(
        f"Bikes   : {df['bike_id'].nunique()}"
    )

    print()
    print("TARGET +30 DAYS")
    print("-" * 50)

    print(
        df[
            "target_risk_30d"
        ].value_counts()
    )

    print()
    print("TARGET DISTRIBUTION (%)")
    print("-" * 50)

    print(
        (
            df[
                "target_risk_30d"
            ]
            .value_counts(
                normalize=True
            )
            *
            100
        ).round(2)
    )

    print()
    print("TRANSITIONS +30 DAYS")
    print("-" * 50)

    print(
        df[
            "future_transition_30d"
        ].value_counts()
    )

    changed = (
        df[
            "current_risk_class"
        ]
        !=
        df[
            "target_risk_30d"
        ]
    )

    print()
    print(
        f"Future changes      : "
        f"{changed.sum()}"
    )

    print(
        f"Future change rate  : "
        f"{100 * changed.mean():.2f}%"
    )

    print(
        f"Persistence baseline: "
        f"{100 * (1 - changed.mean()):.2f}%"
    )


# ============================================================
# SAUVEGARDE
# ============================================================

def save_dataset(df):

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        f"Saved : {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("BUILD TEMPORAL DATASET 30D V4.2")
    print("=" * 75)

    print()
    print("Loading data...")

    df = load_dataset()

    print(
        "Creating instantaneous features..."
    )

    df = create_instantaneous_features(
        df
    )

    print(
        "Creating 7-day historical features..."
    )

    df = create_history_features(
        df
    )

    print(
        "Creating +30-day target..."
    )

    df = create_future_target(
        df
    )

    print(
        "Creating transitions..."
    )

    df = create_transition_column(
        df
    )

    print(
        "Filtering dataset..."
    )

    df = filter_dataset(
        df
    )

    validate_dataset(
        df
    )

    diagnostics(
        df
    )

    save_dataset(
        df
    )

    print()
    print("=" * 75)
    print("DONE")
    print("=" * 75)


if __name__ == "__main__":
    main()
