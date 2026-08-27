import json
import os

import numpy as np
import pandas as pd

from sqlalchemy import text

from database.db import engine


# ============================================================
# CONFIGURATION
# ============================================================

HISTORY_DAYS = 7

MODEL_FILE = os.path.join(
    "models",
    "logistic_temporal_V42.joblib",
)

SCHEMA_FILE = os.path.join(
    "data",
    "processed",
    "temporal_feature_schema_V4.json",
)


# ============================================================
# SENSOR FEATURES
# EXACTLY AS TRAINING V4.2
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
# TREND FEATURES
# EXACTLY AS TRAINING V4.2
# ============================================================

TREND_FEATURES = [
    "battery_temperature_c",
    "consumption_wh_km",
    "battery_power_w",
    "final_soc",
]


# ============================================================
# RAW TELEMETRY COLUMNS
# ============================================================

RAW_COLUMNS = [
    "bike_id",
    "timestamp",
    "distance_km",
    "duration_minutes",
    "slope_percent",
    "ambient_temperature_c",
    "traffic_factor",
    "average_speed_kmh",
    "acceleration_mps2",
    "mechanical_power_w",
    "battery_power_w",
    "battery_temperature_c",
    "energy_consumed_wh",
    "consumption_wh_km",
    "initial_soc",
    "final_soc",
]


# ============================================================
# LOAD FEATURE SCHEMA
# ============================================================

def load_feature_schema():

    if not os.path.exists(
        SCHEMA_FILE
    ):
        raise FileNotFoundError(
            f"Feature schema not found: "
            f"{SCHEMA_FILE}"
        )

    with open(
        SCHEMA_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        schema = json.load(
            file
        )

    features = schema[
        "features"
    ]

    if len(features) != 57:

        raise RuntimeError(
            f"Expected 57 features, "
            f"found {len(features)}."
        )

    return features


# ============================================================
# INSTANTANEOUS FEATURES
# EXACTLY AS TRAINING
# ============================================================

def create_instantaneous_features(
    df,
):

    df = df.copy()

    df[
        "soc_drop"
    ] = (
        df[
            "initial_soc"
        ]
        -
        df[
            "final_soc"
        ]
    )

    df[
        "power_gap_w"
    ] = (
        df[
            "battery_power_w"
        ]
        -
        df[
            "mechanical_power_w"
        ]
    )

    df[
        "thermal_gap_c"
    ] = (
        df[
            "battery_temperature_c"
        ]
        -
        df[
            "ambient_temperature_c"
        ]
    )

    return df


# ============================================================
# TEMPORAL SLOPE
# EXACTLY AS TRAINING
# ============================================================

def temporal_slope(
    window,
):

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
        dtype=float,
    )

    valid = (
        np.isfinite(
            values
        )
        &
        np.isfinite(
            times
        )
    )

    values = values[
        valid
    ]

    times = times[
        valid
    ]

    if len(values) < 3:

        return np.nan

    if np.ptp(times) == 0:

        return np.nan

    return np.polyfit(
        times,
        values,
        1,
    )[0]


# ============================================================
# HISTORICAL FEATURES
#
# FULL TRAINING / OFFLINE IMPLEMENTATION
#
# Window:
# [t - 7 days, t[
#
# Current observation is NOT included.
#
# This function is intentionally preserved because it reproduces
# the original training logic for every timestamp.
# It is NOT used by the optimized live inference path.
# ============================================================

def create_history_features(
    df,
):

    if df.empty:

        raise ValueError(
            "Cannot build features "
            "from an empty DataFrame."
        )

    result_parts = []

    for (
        bike_id,
        bike_df,
    ) in df.groupby(
        "bike_id",
        sort=False,
    ):

        bike_df = (
            bike_df
            .sort_values(
                "timestamp"
            )
            .copy()
        )

        indexed = (
            bike_df
            .set_index(
                "timestamp"
            )
        )

        # ====================================================
        # ROLLING STATISTICS
        # ====================================================

        for column in SENSOR_FEATURES:

            series = indexed[
                column
            ]

            rolling = series.rolling(
                window=
                    f"{HISTORY_DAYS}D",

                min_periods=
                    3,

                closed=
                    "left",
            )

            bike_df[
                f"{column}_mean_7d"
            ] = (
                rolling
                .mean()
                .to_numpy()
            )

            bike_df[
                f"{column}_std_7d"
            ] = (
                rolling
                .std()
                .to_numpy()
            )

            bike_df[
                f"{column}_min_7d"
            ] = (
                rolling
                .min()
                .to_numpy()
            )

            bike_df[
                f"{column}_max_7d"
            ] = (
                rolling
                .max()
                .to_numpy()
            )

            bike_df[
                f"{column}_count_7d"
            ] = (
                rolling
                .count()
                .to_numpy()
            )

        # ====================================================
        # TEMPORAL SLOPES
        # ====================================================

        timestamps = bike_df[
            "timestamp"
        ]

        for column in TREND_FEATURES:

            values = bike_df[
                column
            ]

            slopes = []

            for i in range(
                len(bike_df)
            ):

                current_time = (
                    timestamps.iloc[
                        i
                    ]
                )

                start_time = (
                    current_time
                    -
                    pd.Timedelta(
                        days=
                            HISTORY_DAYS
                    )
                )

                mask = (
                    (
                        timestamps
                        >=
                        start_time
                    )
                    &
                    (
                        timestamps
                        <
                        current_time
                    )
                )

                history = pd.Series(
                    values.loc[
                        mask
                    ].to_numpy(),

                    index=
                        timestamps.loc[
                            mask
                        ],
                )

                slopes.append(
                    temporal_slope(
                        history
                    )
                )

            bike_df[
                f"{column}_slope_7d"
            ] = slopes

        # ====================================================
        # TRIP COUNT 7D
        # ====================================================

        indexed_count = (
            indexed[
                "bike_id"
            ]
            .rolling(
                window=
                    f"{HISTORY_DAYS}D",

                closed=
                    "left",
            )
            .count()
        )

        bike_df[
            "trip_count_7d"
        ] = (
            indexed_count
            .to_numpy()
        )

        result_parts.append(
            bike_df
        )

    result = pd.concat(
        result_parts,
        ignore_index=True,
    )

    result = (
        result
        .sort_values(
            [
                "bike_id",
                "timestamp",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# DATABASE HISTORY
# ============================================================

def load_bike_history(
    bike_id,
    prediction_timestamp=None,
):

    if prediction_timestamp is None:

        query = text(
            """
            SELECT
                bike_id,
                timestamp,
                distance_km,
                duration_minutes,
                slope_percent,
                ambient_temperature_c,
                traffic_factor,
                average_speed_kmh,
                acceleration_mps2,
                mechanical_power_w,
                battery_power_w,
                battery_temperature_c,
                energy_consumed_wh,
                consumption_wh_km,
                initial_soc,
                final_soc

            FROM telemetry

            WHERE bike_id = :bike_id

            ORDER BY timestamp ASC;
            """
        )

        params = {
            "bike_id":
                bike_id,
        }

    else:

        prediction_timestamp = (
            pd.Timestamp(
                prediction_timestamp
            )
        )

        # We need:
        #
        # previous 7 days
        # +
        # current prediction observation

        history_start = (
            prediction_timestamp
            -
            pd.Timedelta(
                days=
                    HISTORY_DAYS
            )
        )

        query = text(
            """
            SELECT
                bike_id,
                timestamp,
                distance_km,
                duration_minutes,
                slope_percent,
                ambient_temperature_c,
                traffic_factor,
                average_speed_kmh,
                acceleration_mps2,
                mechanical_power_w,
                battery_power_w,
                battery_temperature_c,
                energy_consumed_wh,
                consumption_wh_km,
                initial_soc,
                final_soc

            FROM telemetry

            WHERE bike_id = :bike_id

              AND timestamp >= :history_start

              AND timestamp <= :prediction_timestamp

            ORDER BY timestamp ASC;
            """
        )

        params = {
            "bike_id":
                bike_id,

            "history_start":
                history_start.to_pydatetime(),

            "prediction_timestamp":
                prediction_timestamp.to_pydatetime(),
        }

    with engine.connect() as connection:

        df = pd.read_sql(
            query,
            connection,
            params=params,
        )

    if df.empty:

        raise ValueError(
            f"No telemetry found "
            f"for bike {bike_id}."
        )

    df[
        "timestamp"
    ] = pd.to_datetime(
        df[
            "timestamp"
        ]
    )

    return df


# ============================================================
# BUILD ALL FEATURES
#
# OFFLINE / TRAINING-COMPATIBLE PATH
# ============================================================

def build_feature_dataframe(
    df,
):

    df = df.copy()

    missing_raw = [
        column
        for column in RAW_COLUMNS
        if column not in df.columns
    ]

    if missing_raw:

        raise RuntimeError(
            "Missing raw telemetry columns:\n"
            +
            "\n".join(
                missing_raw
            )
        )

    df[
        "timestamp"
    ] = pd.to_datetime(
        df[
            "timestamp"
        ]
    )

    df = create_instantaneous_features(
        df
    )

    df = create_history_features(
        df
    )

    return df


# ============================================================
# LIVE FEATURE BUILDER
#
# OPTIMIZED FOR ONE PREDICTION POINT
#
# Instead of calculating rolling features for every historical
# timestamp, this computes only the final feature vector needed
# for real-time inference.
#
# Training semantics remain:
#
# [t - 7 days, t[
# ============================================================

def build_features_for_bike(
    bike_id,
    prediction_timestamp=None,
):

    # ========================================================
    # FEATURE CONTRACT
    # ========================================================

    feature_names = (
        load_feature_schema()
    )

    # ========================================================
    # LOAD HISTORY
    # ========================================================

    history = load_bike_history(
        bike_id=
            bike_id,

        prediction_timestamp=
            prediction_timestamp,
    )

    if len(history) < 4:

        raise ValueError(
            f"Bike {bike_id} has only "
            f"{len(history)} telemetry rows. "
            f"At least 4 are required."
        )

    history = (
        history
        .sort_values(
            "timestamp"
        )
        .reset_index(
            drop=True
        )
        .copy()
    )

    history[
        "timestamp"
    ] = pd.to_datetime(
        history[
            "timestamp"
        ]
    )

    # ========================================================
    # INSTANTANEOUS FEATURES
    # ========================================================

    history = (
        create_instantaneous_features(
            history
        )
    )

    # ========================================================
    # CURRENT PREDICTION POINT
    # ========================================================

    latest = history.iloc[
        [-1]
    ].copy()

    current_time = (
        latest[
            "timestamp"
        ]
        .iloc[0]
    )

    history_start = (
        current_time
        -
        pd.Timedelta(
            days=
                HISTORY_DAYS
        )
    )

    # ========================================================
    # EXACT TRAINING WINDOW
    #
    # [t - 7 days, t[
    #
    # Current observation excluded.
    # ========================================================

    historical_window = (
        history.loc[
            (
                history[
                    "timestamp"
                ]
                >=
                history_start
            )
            &
            (
                history[
                    "timestamp"
                ]
                <
                current_time
            )
        ]
        .copy()
    )

    # ========================================================
    # ROLLING STATISTICS
    #
    # Equivalent to training rolling stats at the final point.
    # min_periods = 3
    # ========================================================

    for column in SENSOR_FEATURES:

        values = (
            historical_window[
                column
            ]
        )

        valid_values = (
            values
            .dropna()
        )

        valid_count = len(
            valid_values
        )

        if valid_count < 3:

            latest[
                f"{column}_mean_7d"
            ] = np.nan

            latest[
                f"{column}_std_7d"
            ] = np.nan

            latest[
                f"{column}_min_7d"
            ] = np.nan

            latest[
                f"{column}_max_7d"
            ] = np.nan

            latest[
                f"{column}_count_7d"
            ] = np.nan

        else:

            latest[
                f"{column}_mean_7d"
            ] = (
                valid_values
                .mean()
            )

            latest[
                f"{column}_std_7d"
            ] = (
                valid_values
                .std()
            )

            latest[
                f"{column}_min_7d"
            ] = (
                valid_values
                .min()
            )

            latest[
                f"{column}_max_7d"
            ] = (
                valid_values
                .max()
            )

            latest[
                f"{column}_count_7d"
            ] = float(
                valid_count
            )

    # ========================================================
    # TEMPORAL SLOPES
    #
    # Same temporal_slope() used during training.
    # Only one slope per trend feature is required.
    # ========================================================

    for column in TREND_FEATURES:

        slope_series = pd.Series(
            historical_window[
                column
            ].to_numpy(),

            index=
                historical_window[
                    "timestamp"
                ],
        )

        latest[
            f"{column}_slope_7d"
        ] = temporal_slope(
            slope_series
        )

    # ========================================================
    # TRIP COUNT 7D
    #
    # Training rolling count does not use min_periods=3.
    # ========================================================

    latest[
        "trip_count_7d"
    ] = float(
        historical_window[
            "bike_id"
        ].count()
    )

    # ========================================================
    # STRICT FEATURE CONTRACT
    # ========================================================

    missing_features = [
        feature
        for feature in feature_names
        if feature not in latest.columns
    ]

    if missing_features:

        raise RuntimeError(
            "Feature builder is incompatible "
            "with training schema:\n"
            +
            "\n".join(
                missing_features
            )
        )

    X = latest[
        feature_names
    ].copy()

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if X.shape != (
        1,
        57,
    ):

        raise RuntimeError(
            f"Expected feature shape "
            f"(1, 57), received {X.shape}."
        )

    # Missing historical values are allowed.
    # The sklearn pipeline contains its median imputer.

    return X


# ============================================================
# DIAGNOSTIC
# ============================================================

def diagnose_bike(
    bike_id,
):

    print()
    print("=" * 90)
    print(
        "FEATURE BUILDER V4.2 DIAGNOSTIC"
    )
    print("=" * 90)

    history = load_bike_history(
        bike_id
    )

    print()

    print(
        f"Bike          : {bike_id}"
    )

    print(
        f"History rows  : {len(history)}"
    )

    print(
        f"First event   : "
        f"{history['timestamp'].min()}"
    )

    print(
        f"Latest event  : "
        f"{history['timestamp'].max()}"
    )

    X = build_features_for_bike(
        bike_id
    )

    print(
        f"Feature count : "
        f"{X.shape[1]}"
    )

    print(
        f"Missing values: "
        f"{int(X.isna().sum().sum())}"
    )

    print()

    print(
        "FEATURE VECTOR"
    )

    print(
        "-" * 90
    )

    print(
        X.T.to_string(
            header=False
        )
    )

    if X.shape[1] != 57:

        raise RuntimeError(
            f"Expected 57 features, "
            f"found {X.shape[1]}."
        )

    print()

    print(
        "Feature schema validation : PASSED"
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    import sys

    if len(
        sys.argv
    ) < 2:

        print(
            "Usage:"
        )

        print(
            "python -m "
            "services.feature_builder_V42 "
            "DTB0001"
        )

        raise SystemExit(
            1
        )

    diagnose_bike(
        sys.argv[
            1
        ]
    )