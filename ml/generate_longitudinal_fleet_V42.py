import os
import uuid

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = os.path.join(
    "data",
    "raw",
    "fleet_longitudinal_V42.csv",
)

RANDOM_STATE = 42

N_BIKES = 30

START_DATE = pd.Timestamp(
    "2026-01-01 07:00:00"
)

SIMULATION_DAYS = 180

MIN_TRIPS_PER_DAY = 3
MAX_TRIPS_PER_DAY = 7


# ============================================================
# RISK THRESHOLDS
# ============================================================

WARNING_THRESHOLD = 0.35
CRITICAL_THRESHOLD = 0.65

HEALTH_MAX = 0.98


# ============================================================
# INDIVIDUAL BIKE HETEROGENEITY
# ============================================================

# sigma = 0.22 :
# moderate individual variability around profile drift.
#
# Median factor is approximately 1.0.
# Some bikes degrade slower, others faster.
#
# IMPORTANT:
# this is latent simulation configuration.
# It must NEVER become an ML feature.

BIKE_DEGRADATION_SIGMA = 0.22

# V4.2: slow time-varying bike degradation and temporary stress episodes.
TEMPORAL_DRIFT_SIGMA = 0.10
TEMPORAL_DRIFT_PERSISTENCE = 0.985
STRESS_EPISODE_PROBABILITY = 0.012
STRESS_EPISODE_MIN_TRIPS = 8
STRESS_EPISODE_MAX_TRIPS = 30
STRESS_EPISODE_MIN_MULTIPLIER = 1.15
STRESS_EPISODE_MAX_MULTIPLIER = 1.65


# ============================================================
# PROFILES
# ============================================================

PROFILE_CONFIG = {

    "HEALTHY": {
        "initial_min": 0.03,
        "initial_max": 0.12,
        "daily_drift": 0.00045,
        "volatility": 0.00025,
        "temp_sensitivity": 0.20,
        "power_sensitivity": 0.15,
    },

    "SLOW_DEGRADATION": {
        "initial_min": 0.10,
        "initial_max": 0.25,
        "daily_drift": 0.00175,
        "volatility": 0.00045,
        "temp_sensitivity": 0.35,
        "power_sensitivity": 0.30,
    },

    "BATTERY_DEGRADATION": {
        "initial_min": 0.20,
        "initial_max": 0.40,
        "daily_drift": 0.00280,
        "volatility": 0.00060,
        "temp_sensitivity": 0.45,
        "power_sensitivity": 0.50,
    },

    "THERMAL_DEGRADATION": {
        "initial_min": 0.20,
        "initial_max": 0.40,
        "daily_drift": 0.00290,
        "volatility": 0.00065,
        "temp_sensitivity": 0.65,
        "power_sensitivity": 0.25,
    },

    "SEVERE_DEGRADATION": {
        "initial_min": 0.45,
        "initial_max": 0.65,
        "daily_drift": 0.00420,
        "volatility": 0.00080,
        "temp_sensitivity": 0.70,
        "power_sensitivity": 0.55,
    },
}


PROFILE_POOL = (
    ["HEALTHY"] * 11
    +
    ["SLOW_DEGRADATION"] * 4
    +
    ["BATTERY_DEGRADATION"] * 6
    +
    ["THERMAL_DEGRADATION"] * 5
    +
    ["SEVERE_DEGRADATION"] * 4
)


# ============================================================
# HELPERS
# ============================================================

def clip(
    value,
    low,
    high,
):

    return float(
        np.clip(
            value,
            low,
            high,
        )
    )


def sigmoid(x):

    return 1.0 / (
        1.0
        +
        np.exp(
            -x
        )
    )


# ============================================================
# RISK CLASS
# ============================================================

def health_to_risk(
    health,
):

    if health < WARNING_THRESHOLD:

        return "NORMAL"

    if health < CRITICAL_THRESHOLD:

        return "WARNING"

    return "CRITICAL"


# ============================================================
# PRECURSOR INTENSITY
# ============================================================

def precursor_intensity(
    health,
):

    """
    Gradual observable response before risk thresholds.

    Health remains latent and is NEVER directly used
    as a machine-learning feature.
    """

    distance_warning = (
        health
        -
        0.22
    )

    distance_critical = (
        health
        -
        0.50
    )

    warning_signal = sigmoid(
        12.0
        *
        distance_warning
    )

    critical_signal = sigmoid(
        14.0
        *
        distance_critical
    )

    return (
        warning_signal,
        critical_signal,
    )


# ============================================================
# ENVIRONMENT
# ============================================================

def ambient_temperature(
    timestamp,
    rng,
):

    day = timestamp.dayofyear

    seasonal = (
        12.0
        +
        6.0
        *
        np.sin(
            2.0
            *
            np.pi
            *
            day
            /
            365.0
        )
    )

    hourly = (
        2.5
        *
        np.sin(
            2.0
            *
            np.pi
            *
            timestamp.hour
            /
            24.0
        )
    )

    noise = rng.normal(
        0.0,
        1.5,
    )

    return clip(
        seasonal
        +
        hourly
        +
        noise,
        -2.0,
        32.0,
    )


def traffic_factor(
    timestamp,
    rng,
):

    hour = timestamp.hour

    if (
        7 <= hour <= 9
        or
        17 <= hour <= 19
    ):

        base = 1.35

    elif (
        10 <= hour <= 16
    ):

        base = 1.15

    else:

        base = 1.05

    return clip(
        base
        +
        rng.normal(
            0.0,
            0.10,
        ),
        0.85,
        1.70,
    )


# ============================================================
# TRIP GENERATION
# ============================================================

def generate_trip_context(
    timestamp,
    rng,
):

    duration_minutes = clip(
        rng.normal(
            26.0,
            8.0,
        ),
        8.0,
        60.0,
    )

    distance_km = clip(
        rng.normal(
            6.0,
            2.0,
        ),
        1.0,
        15.0,
    )

    slope_percent = clip(
        rng.normal(
            1.25,
            0.65,
        ),
        -1.0,
        4.5,
    )

    ambient = ambient_temperature(
        timestamp,
        rng,
    )

    traffic = traffic_factor(
        timestamp,
        rng,
    )

    return {

        "duration_minutes":
            duration_minutes,

        "distance_km":
            distance_km,

        "slope_percent":
            slope_percent,

        "ambient_temperature_c":
            ambient,

        "traffic_factor":
            traffic,
    }


# ============================================================
# HEALTH UPDATE
# ============================================================

def update_health(
    current_health,
    profile,
    trip_context,
    rng,
    bike_degradation_factor,
    temporal_degradation_factor=1.0,
    stress_episode_multiplier=1.0,
):

    cfg = PROFILE_CONFIG[
        profile
    ]

    ambient = (
        trip_context[
            "ambient_temperature_c"
        ]
    )

    slope = (
        trip_context[
            "slope_percent"
        ]
    )

    traffic = (
        trip_context[
            "traffic_factor"
        ]
    )

    duration = (
        trip_context[
            "duration_minutes"
        ]
    )

    # ========================================================
    # PHYSICAL STRESS
    # ========================================================

    thermal_stress = max(
        0.0,
        ambient - 20.0,
    ) / 15.0

    route_stress = max(
        0.0,
        slope,
    ) / 4.5

    traffic_stress = max(
        0.0,
        traffic - 1.0,
    )

    duration_stress = (
        duration
        /
        60.0
    )

    # ========================================================
    # V4.1 INDIVIDUAL DEGRADATION RATE
    # ========================================================

    base_increment = (
        cfg[
            "daily_drift"
        ]
        *
        bike_degradation_factor
        *
        temporal_degradation_factor
        *
        stress_episode_multiplier
        /
        5.0
    )

    # ========================================================
    # OPERATING CONDITIONS
    # ========================================================

    stress_multiplier = (

        1.0

        +

        cfg[
            "temp_sensitivity"
        ]
        *
        thermal_stress

        +

        cfg[
            "power_sensitivity"
        ]
        *
        (
            0.5
            *
            route_stress

            +

            0.3
            *
            traffic_stress

            +

            0.2
            *
            duration_stress
        )
    )

    # ========================================================
    # STOCHASTIC DEGRADATION
    # ========================================================

    noise = rng.normal(
        0.0,
        cfg[
            "volatility"
        ]
        /
        5.0,
    )

    increment = max(
        0.0,

        base_increment
        *
        stress_multiplier

        +

        noise,
    )

    new_health = clip(
        current_health
        +
        increment,
        0.0,
        HEALTH_MAX,
    )

    return (
        new_health,
        increment,
    )


# ============================================================
# OBSERVABLE TELEMETRY
# ============================================================

def generate_observable_signals(
    health,
    profile,
    trip_context,
    rng,
):

    (
        warning_signal,
        critical_signal,
    ) = precursor_intensity(
        health
    )

    ambient = (
        trip_context[
            "ambient_temperature_c"
        ]
    )

    traffic = (
        trip_context[
            "traffic_factor"
        ]
    )

    slope = (
        trip_context[
            "slope_percent"
        ]
    )

    distance = (
        trip_context[
            "distance_km"
        ]
    )

    duration = (
        trip_context[
            "duration_minutes"
        ]
    )

    # ========================================================
    # SPEED
    # ========================================================

    base_speed = (
        15.8
        -
        1.7
        *
        (
            traffic - 1.0
        )
        -
        0.45
        *
        max(
            slope,
            0.0,
        )
    )

    degradation_speed_penalty = (
        0.45
        *
        warning_signal
        +
        0.70
        *
        critical_signal
    )

    average_speed_kmh = clip(
        base_speed
        -
        degradation_speed_penalty
        +
        rng.normal(
            0.0,
            1.1,
        ),
        5.0,
        25.0,
    )

    # ========================================================
    # MECHANICAL POWER
    # ========================================================

    mechanical_power_w = (
        145.0
        +
        22.0
        *
        max(
            slope,
            0.0,
        )
        +
        20.0
        *
        (
            traffic - 1.0
        )
        +
        rng.normal(
            0.0,
            25.0,
        )
    )

    mechanical_power_w = clip(
        mechanical_power_w,
        70.0,
        360.0,
    )

    # ========================================================
    # EFFICIENCY
    # ========================================================

    base_efficiency = 0.86

    efficiency_loss = (
        0.045
        *
        warning_signal
        +
        0.095
        *
        critical_signal
    )

    profile_efficiency_penalty = {

        "HEALTHY":
            0.000,

        "SLOW_DEGRADATION":
            0.005,

        "BATTERY_DEGRADATION":
            0.012,

        "THERMAL_DEGRADATION":
            0.009,

        "SEVERE_DEGRADATION":
            0.018,

    }[
        profile
    ]

    effective_efficiency = clip(
        base_efficiency
        -
        efficiency_loss
        -
        profile_efficiency_penalty
        +
        rng.normal(
            0.0,
            0.018,
        ),
        0.60,
        0.92,
    )

    # ========================================================
    # BATTERY POWER
    # ========================================================

    battery_power_w = (
        mechanical_power_w
        /
        effective_efficiency
    )

    battery_power_w += (
        8.0
        *
        warning_signal
        +
        18.0
        *
        critical_signal
        +
        rng.normal(
            0.0,
            14.0,
        )
    )

    battery_power_w = clip(
        battery_power_w,
        80.0,
        520.0,
    )

    # ========================================================
    # BATTERY TEMPERATURE
    # ========================================================

    thermal_profile_effect = {

        "HEALTHY":
            0.0,

        "SLOW_DEGRADATION":
            0.3,

        "BATTERY_DEGRADATION":
            0.7,

        "THERMAL_DEGRADATION":
            1.4,

        "SEVERE_DEGRADATION":
            1.7,

    }[
        profile
    ]

    battery_temperature_c = (
        ambient
        +
        3.0
        +
        0.015
        *
        battery_power_w
        +
        thermal_profile_effect
        +
        2.5
        *
        warning_signal
        +
        5.5
        *
        critical_signal
        +
        rng.normal(
            0.0,
            1.5,
        )
    )

    battery_temperature_c = clip(
        battery_temperature_c,
        ambient,
        55.0,
    )

    # ========================================================
    # ENERGY CONSUMPTION
    # ========================================================

    duration_hours = (
        duration
        /
        60.0
    )

    energy_consumed_wh = (
        battery_power_w
        *
        duration_hours
    )

    energy_consumed_wh *= (
        1.0
        +
        0.035
        *
        warning_signal
        +
        0.075
        *
        critical_signal
    )

    energy_consumed_wh *= (
        rng.normal(
            1.0,
            0.035,
        )
    )

    energy_consumed_wh = max(
        energy_consumed_wh,
        1.0,
    )

    # ========================================================
    # CONSUMPTION PER KM
    # ========================================================

    consumption_wh_km = (
        energy_consumed_wh
        /
        max(
            distance,
            0.5,
        )
    )

    consumption_wh_km = clip(
        consumption_wh_km,
        5.0,
        80.0,
    )

    # ========================================================
    # SOC
    # ========================================================

    initial_soc = clip(
        rng.normal(
            76.0,
            11.0,
        ),
        45.0,
        100.0,
    )

    nominal_capacity_wh = 500.0

    effective_capacity_factor = (
        1.0
        -
        0.08
        *
        warning_signal
        -
        0.18
        *
        critical_signal
    )

    effective_capacity_wh = (
        nominal_capacity_wh
        *
        effective_capacity_factor
    )

    soc_drop = (
        energy_consumed_wh
        /
        effective_capacity_wh
        *
        100.0
    )

    soc_drop *= rng.normal(
        1.0,
        0.035,
    )

    final_soc = clip(
        initial_soc
        -
        soc_drop,
        5.0,
        100.0,
    )

    # ========================================================
    # ACCELERATION
    # ========================================================

    acceleration_mps2 = clip(
        rng.normal(
            0.0,
            0.15,
        ),
        -0.6,
        0.6,
    )

    return {

        "average_speed_kmh":
            average_speed_kmh,

        "mechanical_power_w":
            mechanical_power_w,

        "battery_power_w":
            battery_power_w,

        "battery_temperature_c":
            battery_temperature_c,

        "energy_consumed_wh":
            energy_consumed_wh,

        "consumption_wh_km":
            consumption_wh_km,

        "initial_soc":
            initial_soc,

        "final_soc":
            final_soc,

        "effective_efficiency":
            effective_efficiency,

        "acceleration_mps2":
            acceleration_mps2,

        "warning_precursor_strength":
            warning_signal,

        "critical_precursor_strength":
            critical_signal,
    }


# ============================================================
# BIKE PROFILE ASSIGNMENT
# ============================================================

def assign_profiles(
    rng,
):

    profiles = list(
        PROFILE_POOL
    )

    rng.shuffle(
        profiles
    )

    return profiles


# ============================================================
# GENERATE ONE BIKE
# ============================================================

def generate_bike(
    bike_number,
    profile,
    rng,
):

    bike_id = (
        f"DTB{bike_number:04d}"
    )

    cfg = (
        PROFILE_CONFIG[
            profile
        ]
    )

    # ========================================================
    # INITIAL HEALTH
    # ========================================================

    health = rng.uniform(
        cfg[
            "initial_min"
        ],
        cfg[
            "initial_max"
        ],
    )

    initial_health = health

    # ========================================================
    # V4.1 BIKE-SPECIFIC DEGRADATION FACTOR
    # ========================================================

    bike_degradation_factor = rng.lognormal(
        mean=0.0,
        sigma=BIKE_DEGRADATION_SIGMA,
    )

    # V4.2 dynamic latent degradation state. It is simulation-only.
    temporal_log_factor = 0.0
    stress_episode_remaining = 0
    stress_episode_multiplier = 1.0

    rows = []

    trip_counter = 0

    # ========================================================
    # SIMULATION
    # ========================================================

    for day_offset in range(
        SIMULATION_DAYS
    ):

        day = (
            START_DATE
            +
            pd.Timedelta(
                days=day_offset
            )
        )

        trips_today = int(
            rng.integers(
                MIN_TRIPS_PER_DAY,
                MAX_TRIPS_PER_DAY + 1,
            )
        )

        trip_hours = np.sort(
            rng.uniform(
                7.0,
                20.0,
                size=trips_today,
            )
        )

        for trip_hour in trip_hours:

            hour = int(
                trip_hour
            )

            minute = int(
                (
                    trip_hour
                    -
                    hour
                )
                *
                60
            )

            second = int(
                rng.integers(
                    0,
                    60,
                )
            )

            timestamp = (
                day
                +
                pd.Timedelta(
                    hours=hour,
                    minutes=minute,
                    seconds=second,
                )
            )

            trip_counter += 1

            trip_id = (
                f"{bike_id}_TRIP_{trip_counter:05d}"
            )

            # =================================================
            # TRIP ENVIRONMENT
            # =================================================

            context = (
                generate_trip_context(
                    timestamp,
                    rng,
                )
            )

            health_before = (
                health
            )

            # =================================================
            # V4.2 TIME-VARYING LATENT DEGRADATION
            # =================================================
            temporal_log_factor = (
                TEMPORAL_DRIFT_PERSISTENCE * temporal_log_factor
                + rng.normal(0.0, TEMPORAL_DRIFT_SIGMA * 0.10)
            )
            temporal_degradation_factor = float(
                np.clip(np.exp(temporal_log_factor), 0.70, 1.45)
            )

            if stress_episode_remaining <= 0:
                if rng.random() < STRESS_EPISODE_PROBABILITY:
                    stress_episode_remaining = int(
                        rng.integers(
                            STRESS_EPISODE_MIN_TRIPS,
                            STRESS_EPISODE_MAX_TRIPS + 1,
                        )
                    )
                    stress_episode_multiplier = float(
                        rng.uniform(
                            STRESS_EPISODE_MIN_MULTIPLIER,
                            STRESS_EPISODE_MAX_MULTIPLIER,
                        )
                    )
                else:
                    stress_episode_multiplier = 1.0
            else:
                stress_episode_remaining -= 1

            # =================================================
            # HEALTH EVOLUTION
            # =================================================

            (
                health,
                health_increment,
            ) = update_health(

                current_health=
                    health,

                profile=
                    profile,

                trip_context=
                    context,

                rng=
                    rng,

                bike_degradation_factor=
                    bike_degradation_factor,

                temporal_degradation_factor=
                    temporal_degradation_factor,

                stress_episode_multiplier=
                    stress_episode_multiplier,
            )

            # =================================================
            # OBSERVABLE SIGNALS
            # =================================================

            observable = (
                generate_observable_signals(
                    health=health,
                    profile=profile,
                    trip_context=context,
                    rng=rng,
                )
            )

            risk_class = (
                health_to_risk(
                    health
                )
            )

            # =================================================
            # SAVE ROW
            # =================================================

            rows.append(
                {

                    "event_id":
                        "EVT-"
                        +
                        uuid.uuid4().hex[:16],

                    "bike_id":
                        bike_id,

                    "trip_id":
                        trip_id,

                    "timestamp":
                        timestamp,

                    "distance_km":
                        context[
                            "distance_km"
                        ],

                    "duration_minutes":
                        context[
                            "duration_minutes"
                        ],

                    "slope_percent":
                        context[
                            "slope_percent"
                        ],

                    "ambient_temperature_c":
                        context[
                            "ambient_temperature_c"
                        ],

                    "traffic_factor":
                        context[
                            "traffic_factor"
                        ],

                    "average_speed_kmh":
                        observable[
                            "average_speed_kmh"
                        ],

                    "acceleration_mps2":
                        observable[
                            "acceleration_mps2"
                        ],

                    "mechanical_power_w":
                        observable[
                            "mechanical_power_w"
                        ],

                    "battery_power_w":
                        observable[
                            "battery_power_w"
                        ],

                    "battery_temperature_c":
                        observable[
                            "battery_temperature_c"
                        ],

                    "energy_consumed_wh":
                        observable[
                            "energy_consumed_wh"
                        ],

                    "consumption_wh_km":
                        observable[
                            "consumption_wh_km"
                        ],

                    "initial_soc":
                        observable[
                            "initial_soc"
                        ],

                    "final_soc":
                        observable[
                            "final_soc"
                        ],

                    "effective_efficiency":
                        observable[
                            "effective_efficiency"
                        ],

                    # =========================================
                    # SIMULATION-ONLY / DIAGNOSTIC VARIABLES
                    # =========================================

                    "degradation_profile":
                        profile,

                    "bike_degradation_factor":
                        bike_degradation_factor,

                    "temporal_degradation_factor":
                        temporal_degradation_factor,

                    "stress_episode_multiplier":
                        stress_episode_multiplier,

                    "latent_health_before":
                        health_before,

                    "latent_health_after":
                        health,

                    "health_increment":
                        health_increment,

                    "current_risk_class":
                        risk_class,

                    "warning_precursor_strength":
                        observable[
                            "warning_precursor_strength"
                        ],

                    "critical_precursor_strength":
                        observable[
                            "critical_precursor_strength"
                        ],
                }
            )

    return (
        rows,
        initial_health,
        health,
        trip_counter,
        bike_degradation_factor,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(
    df,
):

    print()
    print("=" * 100)
    print(
        "V4.2 DATA VALIDATION"
    )
    print("=" * 100)

    print(
        f"Shape : {df.shape}"
    )

    print()

    # ========================================================
    # RISK DISTRIBUTION
    # ========================================================

    print(
        "RISK DISTRIBUTION"
    )

    print("-" * 65)

    print(
        df[
            "current_risk_class"
        ]
        .value_counts()
    )

    print()

    print(
        "RISK (%)"
    )

    print("-" * 65)

    print(
        (
            df[
                "current_risk_class"
            ]
            .value_counts(
                normalize=True
            )
            *
            100
        ).round(
            2
        )
    )

    # ========================================================
    # HEALTH BY PROFILE
    # ========================================================

    print()

    print(
        "HEALTH BY PROFILE"
    )

    print("-" * 65)

    print(
        df
        .groupby(
            "degradation_profile"
        )[
            "latent_health_after"
        ]
        .agg(
            [
                "min",
                "mean",
                "max",
            ]
        )
        .round(
            3
        )
    )

    # ========================================================
    # BIKE FACTOR
    # ========================================================

    print()

    print(
        "BIKE DEGRADATION FACTORS"
    )

    print("-" * 65)

    bike_factors = (
        df
        .groupby(
            [
                "bike_id",
                "degradation_profile",
            ],
            as_index=False,
        )
        .agg(
            bike_degradation_factor=(
                "bike_degradation_factor",
                "first",
            ),
            initial_health=(
                "latent_health_before",
                "first",
            ),
            final_health=(
                "latent_health_after",
                "last",
            ),
        )
    )

    print(
        bike_factors
        .sort_values(
            "bike_degradation_factor"
        )
        .round(
            3
        )
        .to_string(
            index=False
        )
    )

    print()

    print(
        "Factor distribution"
    )

    print("-" * 65)

    print(
        bike_factors[
            "bike_degradation_factor"
        ]
        .describe()
        .round(
            3
        )
    )

    # ========================================================
    # OBSERVABLE CORRELATION
    # ========================================================

    print()

    print(
        "OBSERVABLE CORRELATIONS WITH LATENT HEALTH"
    )

    print("-" * 65)

    correlation_features = [

        "latent_health_after",

        "battery_temperature_c",

        "battery_power_w",

        "mechanical_power_w",

        "consumption_wh_km",

        "effective_efficiency",

        "final_soc",
    ]

    correlation = (
        df[
            correlation_features
        ]
        .corr()
        [
            "latent_health_after"
        ]
        .sort_values(
            ascending=False
        )
    )

    print(
        correlation.round(
            3
        )
    )

    # ========================================================
    # SATURATION
    # ========================================================

    saturation = (
        df[
            "latent_health_after"
        ]
        >=
        0.95
    ).mean()

    print()

    print(
        f"Health saturation >=0.95 : "
        f"{saturation * 100:.2f}%"
    )

    # ========================================================
    # TRANSITIONS
    # ========================================================

    transitions = (

        df

        .sort_values(
            [
                "bike_id",
                "timestamp",
            ]
        )

        .groupby(
            "bike_id"
        )[
            "current_risk_class"
        ]

        .apply(
            lambda s:
            (
                s
                !=
                s.shift()
            ).sum()
            -
            1
        )
    )

    print()

    print(
        "TRANSITIONS PER BIKE"
    )

    print("-" * 65)

    print(
        transitions.describe()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)
    print(
        "DIGITAL TWIN V4.2 - LONGITUDINAL FLEET"
    )
    print("=" * 100)

    rng = np.random.default_rng(
        RANDOM_STATE
    )

    profiles = assign_profiles(
        rng
    )

    all_rows = []

    summary_rows = []

    print()

    print(
        "Bike     | Profile               "
        "| Factor | Initial H | Final H | Trips"
    )

    print("-" * 100)

    for bike_number in range(
        1,
        N_BIKES + 1
    ):

        profile = (
            profiles[
                bike_number - 1
            ]
        )

        (
            rows,
            initial_health,
            final_health,
            trips,
            degradation_factor,
        ) = generate_bike(

            bike_number=
                bike_number,

            profile=
                profile,

            rng=
                rng,
        )

        all_rows.extend(
            rows
        )

        summary_rows.append(
            {

                "bike_id":
                    f"DTB{bike_number:04d}",

                "profile":
                    profile,

                "bike_degradation_factor":
                    degradation_factor,

                "initial_health":
                    initial_health,

                "final_health":
                    final_health,

                "trips":
                    trips,
            }
        )

        print(
            f"DTB{bike_number:04d} "
            f"| {profile:21s} "
            f"| {degradation_factor:6.3f} "
            f"| {initial_health:9.3f} "
            f"| {final_health:7.3f} "
            f"| {trips:5d}"
        )

    print("-" * 100)

    # ========================================================
    # DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        all_rows
    )

    df = (
        df
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

    # ========================================================
    # SAVE
    # ========================================================

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()

    print(
        f"Total observations : "
        f"{len(df)}"
    )

    print(
        f"File               : "
        f"{OUTPUT_FILE}"
    )

    # ========================================================
    # VALIDATE
    # ========================================================

    validate_dataset(
        df
    )

    print()
    print("=" * 100)
    print("DONE")
    print("=" * 100)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()