import json
import math
import os
import random
import time
import uuid
from datetime import datetime

from kafka import KafkaProducer
from dotenv import load_dotenv


from simulation.bike_V2 import DigitalTwinBike
from simulation.trip_V2 import DigitalTwinTrip
from simulation.sensor_V2 import DigitalTwinSensor

from simulation.network_V2 import (
    build_default_network,
)

from simulation.route_planner_V2 import (
    RoutePlannerV2,
)

from simulation.urban_dynamics_V2 import (
    UrbanDynamicsV2,
)

from simulation.physics_engine_V2 import (
    PhysicsEngineV2,
)

from simulation.health_degradation_V2 import (
    HealthDegradationV2,
)

from simulation.telemetry_generator_V2 import (
    TelemetryGeneratorV2,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092"
)

TOPIC_NAME = os.getenv(
    "KAFKA_TOPIC",
    "bike_telemetry"
)


# ------------------------------------------------------------
# FLEET
# ------------------------------------------------------------

NUMBER_OF_BIKES = 200

BIKE_IDS = [
    f"DTB{i:04d}"
    for i in range(
        1,
        NUMBER_OF_BIKES + 1
    )
]


# ------------------------------------------------------------
# LIVE EXECUTION
#
# One complete fleet cycle generates one new observation
# for every virtual bike.
# ------------------------------------------------------------

EVENT_INTERVAL_SECONDS = 1.0


# ------------------------------------------------------------
# LONGITUDINAL TIME
#
# Each emitted observation represents +6 simulated hours.
#
# IMPORTANT:
# this is NOT the physical integration timestep.
# ------------------------------------------------------------

SIMULATED_STEP_HOURS = 6

SIMULATED_STEP_SECONDS = (
    SIMULATED_STEP_HOURS
    * 3600
)


# ------------------------------------------------------------
# PHYSICAL INTEGRATION
#
# The trip itself is simulated with small physical timesteps.
# ------------------------------------------------------------

PHYSICS_DT_SECONDS = 5.0


# ------------------------------------------------------------
# SAFETY
#
# Prevent an unexpected infinite trip simulation.
# ------------------------------------------------------------

MAX_TRIP_STEPS = 5000


# ------------------------------------------------------------
# SPEED
# ------------------------------------------------------------

BASE_TARGET_SPEED_MPS = 5.0


# ------------------------------------------------------------
# BATTERY
# ------------------------------------------------------------

RECHARGE_THRESHOLD_SOC = 25.0

RECHARGE_MIN_SOC = 85.0

RECHARGE_MAX_SOC = 98.0


# ============================================================
# DEGRADATION PROFILE DISTRIBUTION
#
# Same proportions as the longitudinal V4.2 training fleet:
#
# 11 HEALTHY
#  4 SLOW
#  6 BATTERY
#  5 THERMAL
#  4 SEVERE
#
# Total = 30
# ============================================================

PROFILE_PATTERN = (

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
# KAFKA PRODUCER
# ============================================================

def create_producer():

    return KafkaProducer(

        bootstrap_servers=[
            KAFKA_BOOTSTRAP_SERVERS
        ],

        key_serializer=
            lambda key:
                key.encode(
                    "utf-8"
                ),

        value_serializer=
            lambda value:
                json.dumps(
                    value
                ).encode(
                    "utf-8"
                ),

        acks="all",

        retries=5,

        linger_ms=20,

        batch_size=32768,
    )


# ============================================================
# EXTERNAL ENVIRONMENT
# ============================================================

def ambient_temperature(
    simulation_timestamp,
    rng,
):
    """
    Simple exogenous daily temperature cycle.

    PhysicsEngine remains responsible for battery temperature.
    """

    hour = (
        simulation_timestamp.hour
        +
        simulation_timestamp.minute
        / 60.0
    )

    daily_cycle = (
        4.5
        *
        math.sin(
            2.0
            *
            math.pi
            *
            (
                hour - 8.0
            )
            /
            24.0
        )
    )

    temperature = (
        21.0
        +
        daily_cycle
        +
        rng.gauss(
            0.0,
            0.8
        )
    )

    return max(
        5.0,
        min(
            35.0,
            temperature
        )
    )


# ============================================================
# DESTINATION
# ============================================================

def choose_destination(
    network,
    origin_station_id,
    rng,
):

    station_ids = [
        station_id
        for station_id
        in network.stations.keys()
        if station_id
        != origin_station_id
    ]

    return rng.choice(
        station_ids
    )


# ============================================================
# INITIALIZE ONE DIGITAL TWIN
# ============================================================

def create_bike_runtime(
    bike_id,
    bike_number,
    network,
    simulation_start_time,
):

    seed = (
        10_000
        +
        bike_number
    )

    rng = random.Random(
        seed
    )


    # --------------------------------------------------------
    # DEGRADATION PROFILE
    # --------------------------------------------------------

    profile = PROFILE_PATTERN[
        (
            bike_number - 1
        )
        %
        len(
            PROFILE_PATTERN
        )
    ]

    health_model = (
        HealthDegradationV2(
            profile=profile,
            seed=seed,
        )
    )


    # --------------------------------------------------------
    # INITIAL STATION
    # --------------------------------------------------------

    station_ids = sorted(
        network.stations.keys()
    )

    initial_station = (
        rng.choice(
            station_ids
        )
    )


    # --------------------------------------------------------
    # BIKE
    #
    # mass_kg represents bike + rider system mass.
    # --------------------------------------------------------

    bike = DigitalTwinBike(

        bike_id=
            bike_id,

        mass_kg=
            rng.uniform(
                90.0,
                115.0
            ),

        battery_capacity_wh=
            rng.uniform(
                450.0,
                550.0
            ),

        drivetrain_efficiency=
            rng.uniform(
                0.82,
                0.90
            ),

        speed_mps=
            0.0,

        acceleration_mps2=
            0.0,

        battery_soc=
            rng.uniform(
                75.0,
                95.0
            ),

        battery_temperature_c=
            rng.uniform(
                20.0,
                24.0
            ),

        current_station_id=
            initial_station,

        health_index=
            health_model.health_index,
    )


    # --------------------------------------------------------
    # SENSOR
    # --------------------------------------------------------

    sensor = DigitalTwinSensor()


    # --------------------------------------------------------
    # URBAN DYNAMICS
    #
    # One independent temporal process per bike.
    # --------------------------------------------------------

    urban_dynamics = (
        UrbanDynamicsV2(
            seed=seed
        )
    )


    # --------------------------------------------------------
    # TELEMETRY GENERATOR
    # --------------------------------------------------------

    telemetry_generator = (
        TelemetryGeneratorV2(

            sensor=sensor,

            simulation_start_time=
                simulation_start_time,
        )
    )


    return {

        "bike":
            bike,

        "health_model":
            health_model,

        "urban_dynamics":
            urban_dynamics,

        "telemetry_generator":
            telemetry_generator,

        "rng":
            rng,

        "event_number":
            0,

        "profile":
            profile,
    }


# ============================================================
# INITIALIZE COMPLETE FLEET
# ============================================================

def initialize_fleet(
    network,
    simulation_start_time,
):

    runtimes = {}

    for index, bike_id in enumerate(
        BIKE_IDS,
        start=1,
    ):

        runtimes[
            bike_id
        ] = create_bike_runtime(

            bike_id=
                bike_id,

            bike_number=
                index,

            network=
                network,

            simulation_start_time=
                simulation_start_time,
        )

    return runtimes


# ============================================================
# RECHARGE
# ============================================================

def recharge_if_required(
    bike,
    rng,
    ambient_temperature_c,
):

    if (
        bike.battery_soc
        >=
        RECHARGE_THRESHOLD_SOC
    ):

        return False


    bike.battery_soc = (
        rng.uniform(
            RECHARGE_MIN_SOC,
            RECHARGE_MAX_SOC,
        )
    )


    # Battery cools partially while parked / charging.

    bike.battery_temperature_c = (
        0.65
        *
        bike.battery_temperature_c

        +

        0.35
        *
        ambient_temperature_c
    )


    return True


# ============================================================
# SIMULATE ONE TRIP
# ============================================================

def simulate_trip(
    bike_id,
    runtime,
    network,
    route_planner,
    physics_engine,
    simulation_timestamp,
    simulation_seconds,
):

    bike = runtime[
        "bike"
    ]

    health_model = runtime[
        "health_model"
    ]

    urban_dynamics = runtime[
        "urban_dynamics"
    ]

    telemetry_generator = runtime[
        "telemetry_generator"
    ]

    rng = runtime[
        "rng"
    ]


    # ========================================================
    # ENVIRONMENT
    # ========================================================

    ambient_c = (
        ambient_temperature(
            simulation_timestamp=
                simulation_timestamp,

            rng=
                rng,
        )
    )


    # ========================================================
    # BATTERY RECHARGE
    # ========================================================

    recharge_if_required(

        bike=
            bike,

        rng=
            rng,

        ambient_temperature_c=
            ambient_c,
    )


    # ========================================================
    # ROUTE
    # ========================================================

    origin_station_id = (
        bike.current_station_id
    )

    if origin_station_id is None:

        origin_station_id = (
            rng.choice(
                sorted(
                    network.stations.keys()
                )
            )
        )

        bike.current_station_id = (
            origin_station_id
        )


    destination_station_id = (
        choose_destination(

            network=
                network,

            origin_station_id=
                origin_station_id,

            rng=
                rng,
        )
    )


    route = (
        route_planner.shortest_path(

            origin_station_id=
                origin_station_id,

            destination_station_id=
                destination_station_id,
        )
    )


    if not route["segments"]:

        raise RuntimeError(
            f"Empty route for bike {bike_id}."
        )


    # ========================================================
    # TRIP
    # ========================================================

    runtime[
        "event_number"
    ] += 1

    event_number = runtime[
        "event_number"
    ]


    trip_id = (
        f"{bike_id}_LIVE_"
        f"{event_number:08d}"
    )


    initial_soc = float(
        bike.battery_soc
    )


    trip = DigitalTwinTrip(

        trip_id=
            trip_id,

        bike_id=
            bike_id,

        origin_station_id=
            origin_station_id,

        destination_station_id=
            destination_station_id,

        planned_distance_m=
            float(
                route[
                    "total_distance_m"
                ]
            ),

        start_time=
            simulation_timestamp,

        initial_battery_soc=
            initial_soc,
    )


    bike.start_trip(

        trip_id=
            trip_id,

        origin_station_id=
            origin_station_id,

        destination_station_id=
            destination_station_id,
    )


    # ========================================================
    # AGGREGATES
    # ========================================================

    elapsed_seconds = 0.0

    total_mechanical_energy_j = 0.0

    total_battery_energy_j = 0.0

    traffic_integral = 0.0

    slope_distance_integral = 0.0

    acceleration_integral = 0.0

    integration_steps = 0


    # ========================================================
    # SIMULATE ROUTE SEGMENT BY SEGMENT
    # ========================================================

    last_segment = None

    for segment in route[
        "segments"
    ]:

        last_segment = segment


        urban_dynamics.start_segment(

            base_traffic_factor=
                segment[
                    "traffic_factor"
                ],

            average_slope_percent=
                segment[
                    "average_slope_percent"
                ],
        )


        segment_remaining_m = float(
            segment[
                "distance_m"
            ]
        )


        while (
            segment_remaining_m
            >
            0.01
        ):

            integration_steps += 1

            if (
                integration_steps
                >
                MAX_TRIP_STEPS
            ):

                raise RuntimeError(
                    f"Trip simulation exceeded "
                    f"{MAX_TRIP_STEPS} steps "
                    f"for {bike_id}."
                )


            simulation_hour = (
                (
                    simulation_timestamp
                ).hour
            )


            # ------------------------------------------------
            # URBAN DYNAMICS
            # ------------------------------------------------

            urban_state = (
                urban_dynamics.step(

                    current_speed_mps=
                        bike.speed_mps,

                    base_target_speed_mps=
                        BASE_TARGET_SPEED_MPS,

                    base_traffic_factor=
                        segment[
                            "traffic_factor"
                        ],

                    average_slope_percent=
                        segment[
                            "average_slope_percent"
                        ],

                    simulation_hour=
                        simulation_hour,

                    dt_seconds=
                        PHYSICS_DT_SECONDS,
                )
            )


            acceleration_mps2 = float(
                urban_state[
                    "acceleration_mps2"
                ]
            )

            traffic_factor = float(
                urban_state[
                    "traffic_factor"
                ]
            )

            slope_percent = float(
                urban_state[
                    "slope_percent"
                ]
            )


            # ------------------------------------------------
            # CINEMATICS
            # ------------------------------------------------

            old_speed_mps = float(
                bike.speed_mps
            )


            distance_step_m = (
                physics_engine.compute_distance(

                    speed_mps=
                        old_speed_mps,

                    acceleration_mps2=
                        acceleration_mps2,

                    dt_seconds=
                        PHYSICS_DT_SECONDS,
                )
            )


            new_speed_mps = (
                physics_engine.update_speed(

                    speed_mps=
                        old_speed_mps,

                    acceleration_mps2=
                        acceleration_mps2,

                    dt_seconds=
                        PHYSICS_DT_SECONDS,
                )
            )


            # ------------------------------------------------
            # Avoid zero-distance deadlock.
            # ------------------------------------------------

            if (
                distance_step_m
                <
                0.01
                and
                urban_state[
                    "urban_status"
                ]
                !=
                "STOPPED"
            ):

                distance_step_m = (
                    max(
                        0.01,
                        new_speed_mps
                        *
                        PHYSICS_DT_SECONDS
                    )
                )


            actual_distance_m = min(

                distance_step_m,

                segment_remaining_m,

                trip.remaining_distance_m,
            )


            # ------------------------------------------------
            # PHYSICS
            # ------------------------------------------------

            representative_speed_mps = (
                max(
                    0.0,
                    (
                        old_speed_mps
                        +
                        new_speed_mps
                    )
                    /
                    2.0
                )
            )


            mechanical_power_w = (
                physics_engine.compute_mechanical_power(

                    mass_kg=
                        bike.mass_kg,

                    speed_mps=
                        representative_speed_mps,

                    acceleration_mps2=
                        acceleration_mps2,

                    slope_percent=
                        slope_percent,
                )
            )


            battery_power_w = (
                physics_engine.compute_battery_power(

                    mechanical_power_w=
                        mechanical_power_w,

                    health_index=
                        bike.health_index,
                )
            )


            energy_consumed_wh = (
                physics_engine.compute_energy_consumed_wh(

                    battery_power_w=
                        battery_power_w,

                    dt_seconds=
                        PHYSICS_DT_SECONDS,
                )
            )


            # ------------------------------------------------
            # BIKE STATE
            # ------------------------------------------------

            bike.speed_mps = (
                new_speed_mps
            )

            bike.acceleration_mps2 = (
                acceleration_mps2
            )


            bike.consume_energy(
                energy_consumed_wh
            )


            bike.battery_temperature_c = (
                physics_engine.update_temperature(

                    current_temperature_c=
                        bike.battery_temperature_c,

                    ambient_temperature_c=
                        ambient_c,

                    battery_power_w=
                        battery_power_w,

                    mechanical_power_w=
                        mechanical_power_w,

                    health_index=
                        bike.health_index,

                    dt_seconds=
                        PHYSICS_DT_SECONDS,
                )
            )


            trip.update(

                distance_m=
                    actual_distance_m,

                energy_consumed_wh=
                    energy_consumed_wh,
            )


            bike.distance_travelled_m = (
                trip.travelled_distance_m
            )


            segment_remaining_m = max(

                0.0,

                segment_remaining_m
                -
                actual_distance_m
            )


            # ------------------------------------------------
            # AGGREGATES
            # ------------------------------------------------

            elapsed_seconds += (
                PHYSICS_DT_SECONDS
            )

            total_mechanical_energy_j += (
                mechanical_power_w
                *
                PHYSICS_DT_SECONDS
            )

            total_battery_energy_j += (
                battery_power_w
                *
                PHYSICS_DT_SECONDS
            )

            traffic_integral += (
                traffic_factor
                *
                PHYSICS_DT_SECONDS
            )

            slope_distance_integral += (
                slope_percent
                *
                actual_distance_m
            )

            acceleration_integral += (
                acceleration_mps2
                *
                PHYSICS_DT_SECONDS
            )


    # ========================================================
    # FINAL AGGREGATES
    # ========================================================

    distance_km = (
        trip.planned_distance_m
        /
        1000.0
    )


    duration_minutes = (
        elapsed_seconds
        /
        60.0
    )


    if duration_minutes <= 0:

        raise RuntimeError(
            "Trip duration is invalid."
        )


    average_speed_kmh = (

        distance_km

        /

        (
            duration_minutes
            /
            60.0
        )
    )


    total_energy_wh = float(
        trip.total_energy_consumed_wh
    )


    consumption_wh_km = (

        total_energy_wh
        /
        distance_km

        if distance_km > 0

        else 0.0
    )


    average_mechanical_power_w = (

        total_mechanical_energy_j
        /
        elapsed_seconds

        if elapsed_seconds > 0

        else 0.0
    )


    average_battery_power_w = (

        total_battery_energy_j
        /
        elapsed_seconds

        if elapsed_seconds > 0

        else 0.0
    )


    average_traffic_factor = (

        traffic_integral
        /
        elapsed_seconds

        if elapsed_seconds > 0

        else 1.0
    )


    average_slope_percent = (

        slope_distance_integral
        /
        trip.planned_distance_m

        if trip.planned_distance_m > 0

        else 0.0
    )


    average_acceleration_mps2 = (

        acceleration_integral
        /
        elapsed_seconds

        if elapsed_seconds > 0

        else 0.0
    )


    # ========================================================
    # LONGITUDINAL HEALTH UPDATE
    #
    # IMPORTANT:
    #
    # The physical trip lasts minutes.
    #
    # But each emitted observation represents +6 simulated
    # hours in the longitudinal timeline.
    #
    # Therefore degradation is updated once per observation
    # using the longitudinal simulated interval.
    # ========================================================

    health_state = (
        health_model.update(

            dt_seconds=
                SIMULATED_STEP_SECONDS,

            battery_power_w=
                average_battery_power_w,

            battery_temperature_c=
                bike.battery_temperature_c,

            battery_soc=
                bike.battery_soc,

            acceleration_mps2=
                average_acceleration_mps2,

            slope_percent=
                average_slope_percent,

            traffic_factor=
                average_traffic_factor,
        )
    )


    bike.health_index = float(
        health_state.health_index
    )


    # ========================================================
    # COMPLETE TRIP
    # ========================================================

    trip.finish(

        final_battery_soc=
            bike.battery_soc,

        end_time=
            (
                simulation_timestamp
            ),
    )


    # ========================================================
    # DIGITAL TWIN SENSOR EVENT
    # ========================================================

    sensor_event = (
        telemetry_generator.create_event(

            bike=
                bike,

            trip=
                trip,

            segment=
                last_segment,

            simulation_seconds=
                simulation_seconds,

            traffic_factor=
                average_traffic_factor,

            slope_percent=
                average_slope_percent,

            mechanical_power_w=
                average_mechanical_power_w,

            battery_power_w=
                average_battery_power_w,

            energy_consumed_wh=
                total_energy_wh,

            ambient_temperature_c=
                ambient_c,

            initial_soc=
                initial_soc,

            urban_status=
                urban_dynamics.driving_state,
        )
    )


    # ========================================================
    # SENSOR-BASED AVERAGE SPEED
    # ========================================================

    measured_average_speed_kmh = (

        runtime[
            "telemetry_generator"
        ]
        .sensor
        .measure_speed(
            average_speed_kmh
            /
            3.6
        )

        *
        3.6
    )


    # ========================================================
    # KAFKA V4.2 CONTRACT
    #
    # These are the fields expected by telemetry_consumer_V42.
    # ========================================================

    kafka_event = {

        "event_id":
            sensor_event.event_id,

        "bike_id":
            bike_id,

        "trip_id":
            trip.trip_id,

        "timestamp":
            sensor_event.timestamp.isoformat(),

        "distance_km":
            float(
                distance_km
            ),

        "duration_minutes":
            float(
                duration_minutes
            ),

        "slope_percent":
            float(
                sensor_event.slope_percent
            ),

        "ambient_temperature_c":
            float(
                sensor_event.ambient_temperature_c
            ),

        "traffic_factor":
            float(
                sensor_event.traffic_factor
            ),

        "average_speed_kmh":
            float(
                measured_average_speed_kmh
            ),

        "acceleration_mps2":
            float(
                sensor_event.acceleration_mps2
            ),

        "mechanical_power_w":
            float(
                sensor_event.mechanical_power_w
            ),

        "battery_power_w":
            float(
                sensor_event.battery_power_w
            ),

        "battery_temperature_c":
            float(
                sensor_event.battery_temperature_c
            ),

        "energy_consumed_wh":
            float(
                sensor_event.energy_consumed_wh
            ),

        "consumption_wh_km":
            float(
                consumption_wh_km
            ),

        "initial_soc":
            float(
                initial_soc
            ),

        "final_soc":
            float(
                bike.battery_soc
            ),


        # ----------------------------------------------------
        # EXTRA DIGITAL-TWIN INFORMATION
        #
        # Consumer V4.2 ignores these fields for PostgreSQL,
        # but they remain available on Kafka.
        # ----------------------------------------------------

        "origin_station_id":
            origin_station_id,

        "destination_station_id":
            destination_station_id,

        "true_health_index":
            float(
                bike.health_index
            ),

        "true_risk_class":
            sensor_event.true_risk_class,

        "degradation_profile":
            runtime[
                "profile"
            ],

        "operational_status":
            sensor_event.operational_status,
    }


    # ========================================================
    # RETURN BIKE TO DESTINATION STATION
    # ========================================================

    bike.finish_trip()


    return kafka_event


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 100
    )

    print(
        "SMART E-BIKE DIGITAL TWIN "
        "STREAMING PRODUCER V4.2"
    )

    print(
        "=" * 100
    )


    # ========================================================
    # SIMULATION START
    # ========================================================

    simulation_start_time = (
        datetime.now()
        .replace(
            microsecond=0
        )
    )


    # ========================================================
    # DIGITAL TWIN COMPONENTS
    # ========================================================

    network = (
        build_default_network()
    )

    route_planner = (
        RoutePlannerV2(
            network
        )
    )

    physics_engine = (
        PhysicsEngineV2()
    )


    fleet = (
        initialize_fleet(

            network=
                network,

            simulation_start_time=
                simulation_start_time,
        )
    )


    # ========================================================
    # KAFKA
    # ========================================================

    producer = (
        create_producer()
    )


    # ========================================================
    # MONITORING
    # ========================================================

    total_sent = 0

    fleet_cycle = 0

    real_start_time = (
        time.time()
    )


    print()

    print(
        f"Virtual bikes       : "
        f"{NUMBER_OF_BIKES}"
    )

    print(
        f"Bike IDs            : "
        f"{BIKE_IDS[0]} -> "
        f"{BIKE_IDS[-1]}"
    )

    print(
        f"Stations            : "
        f"{len(network.stations)}"
    )

    print(
        f"Network connections : "
        f"{len(network.connections)}"
    )

    print(
        f"Longitudinal step   : "
        f"+{SIMULATED_STEP_HOURS} hours / observation"
    )

    print(
        f"Physics timestep    : "
        f"{PHYSICS_DT_SECONDS:.1f} seconds"
    )

    print(
        f"Kafka topic         : "
        f"{TOPIC_NAME}"
    )

    print(
        f"Fleet-cycle pause   : "
        f"{EVENT_INTERVAL_SECONDS:.1f} seconds"
    )

    print()

    print(
        "Press CTRL+C to stop."
    )

    print()


    # ========================================================
    # CONTINUOUS STREAMING
    # ========================================================

    try:

        while True:

            fleet_cycle += 1


            # ------------------------------------------------
            # Same longitudinal timestamp for the whole fleet.
            # ------------------------------------------------

            simulation_seconds = (

                fleet_cycle

                *

                SIMULATED_STEP_SECONDS
            )


            simulation_timestamp = (

                simulation_start_time

                +

                (
                    datetime.fromtimestamp(
                        simulation_start_time.timestamp()
                        +
                        simulation_seconds
                    )
                    -
                    simulation_start_time
                )
            )


            futures = []


            # =================================================
            # GENERATE ONE NEW OBSERVATION PER BIKE
            # =================================================

            for bike_id in BIKE_IDS:

                runtime = fleet[
                    bike_id
                ]


                event = (
                    simulate_trip(

                        bike_id=
                            bike_id,

                        runtime=
                            runtime,

                        network=
                            network,

                        route_planner=
                            route_planner,

                        physics_engine=
                            physics_engine,

                        simulation_timestamp=
                            simulation_timestamp,

                        simulation_seconds=
                            simulation_seconds,
                    )
                )


                future = (
                    producer.send(

                        TOPIC_NAME,

                        key=
                            bike_id,

                        value=
                            event,
                    )
                )


                futures.append(
                    future
                )


            # =================================================
            # WAIT FOR KAFKA ACKNOWLEDGEMENTS
            #
            # Messages are first queued asynchronously,
            # then acknowledgements are collected.
            # =================================================

            for future in futures:

                future.get(
                    timeout=15
                )


            producer.flush()


            total_sent += (
                len(
                    futures
                )
            )


            # =================================================
            # MONITORING
            # =================================================

            elapsed_real = (

                time.time()

                -

                real_start_time
            )


            event_rate = (

                total_sent

                /

                elapsed_real

                if elapsed_real > 0

                else 0.0
            )


            sample_bike_id = (

                BIKE_IDS[
                    (
                        fleet_cycle - 1
                    )
                    %
                    NUMBER_OF_BIKES
                ]
            )


            sample_runtime = (
                fleet[
                    sample_bike_id
                ]
            )

            sample_bike = (
                sample_runtime[
                    "bike"
                ]
            )


            print(

                f"Cycle={fleet_cycle:06d} "

                f"| SimTime="
                f"{simulation_timestamp} "

                f"| Sent="
                f"{total_sent:09d} "

                f"| Rate="
                f"{event_rate:7.2f} evt/s "

                f"| Sample="
                f"{sample_bike_id} "

                f"| SOC="
                f"{sample_bike.battery_soc:6.2f}% "

                f"| Temp="
                f"{sample_bike.battery_temperature_c:5.2f}C "

                f"| Health="
                f"{sample_bike.health_index:6.3f} "

                f"| Profile="
                f"{sample_runtime['profile']}"
            )


            time.sleep(
                EVENT_INTERVAL_SECONDS
            )


    # ========================================================
    # USER STOP
    # ========================================================

    except KeyboardInterrupt:

        print()

        print(
            "Producer stopped by user."
        )


    # ========================================================
    # CLEAN SHUTDOWN
    # ========================================================

    finally:

        producer.flush()

        producer.close()


    # ========================================================
    # SUMMARY
    # ========================================================

    elapsed_real = (

        time.time()

        -

        real_start_time
    )


    print()

    print(
        "=" * 100
    )

    print(
        "DIGITAL TWIN STREAMING SUMMARY"
    )

    print(
        "=" * 100
    )

    print(
        f"Virtual bikes : "
        f"{NUMBER_OF_BIKES}"
    )

    print(
        f"Fleet cycles  : "
        f"{fleet_cycle}"
    )

    print(
        f"Events sent   : "
        f"{total_sent}"
    )

    print(
        f"Elapsed       : "
        f"{elapsed_real:.2f} seconds"
    )


    if elapsed_real > 0:

        print(

            f"Average rate  : "

            f"{total_sent / elapsed_real:.2f} "

            f"events/s"
        )


    print(
        "=" * 100
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
