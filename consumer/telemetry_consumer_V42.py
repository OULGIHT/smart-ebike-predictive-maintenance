import json
from collections import defaultdict
from datetime import datetime

from kafka import KafkaConsumer
from sqlalchemy import text

from database.db import engine
from services.prediction_service_V42 import predict_and_save


# ============================================================
# CONFIGURATION
# ============================================================

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

TOPIC_NAME = "bike_telemetry"

CONSUMER_GROUP = "smart-ebike-postgres-v42-live-v2"

COMMIT_EVERY_N_MESSAGES = 100


# ============================================================
# AUTOMATIC INFERENCE
# ============================================================

PREDICTION_EVERY_N_EVENTS = 10

# Compteur indépendant pour chaque vélo.
#
# Exemple :
# DTB0001 -> 7 événements
# DTB0002 -> 3 événements
# DTB0003 -> 9 événements
#
# Lorsqu'un vélo atteint 10 nouveaux événements,
# une nouvelle prédiction est calculée.

bike_event_counters = defaultdict(int)


# ============================================================
# SQL
# ============================================================

INSERT_BIKE_SQL = text("""
    INSERT INTO bikes (
        bike_id,
        status,
        created_at
    )
    VALUES (
        :bike_id,
        'ACTIVE',
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (bike_id)
    DO NOTHING
""")


INSERT_TELEMETRY_SQL = text("""
    INSERT INTO telemetry (
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
        final_soc,
        created_at
    )
    VALUES (
        :bike_id,
        :timestamp,
        :distance_km,
        :duration_minutes,
        :slope_percent,
        :ambient_temperature_c,
        :traffic_factor,
        :average_speed_kmh,
        :acceleration_mps2,
        :mechanical_power_w,
        :battery_power_w,
        :battery_temperature_c,
        :energy_consumed_wh,
        :consumption_wh_km,
        :initial_soc,
        :final_soc,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (bike_id, timestamp)
    DO NOTHING
    RETURNING telemetry_id
""")


# ============================================================
# VALIDATION
# ============================================================

REQUIRED_FIELDS = [
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


def validate_event(event):

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in event
    ]

    if missing:

        raise ValueError(
            f"Missing fields: {missing}"
        )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_event(event):

    validate_event(event)

    return {

        "bike_id":
            str(
                event["bike_id"]
            ),

        "timestamp":
            datetime.fromisoformat(
                event["timestamp"]
            ),

        "distance_km":
            float(
                event["distance_km"]
            ),

        "duration_minutes":
            float(
                event["duration_minutes"]
            ),

        "slope_percent":
            float(
                event["slope_percent"]
            ),

        "ambient_temperature_c":
            float(
                event[
                    "ambient_temperature_c"
                ]
            ),

        "traffic_factor":
            float(
                event["traffic_factor"]
            ),

        "average_speed_kmh":
            float(
                event[
                    "average_speed_kmh"
                ]
            ),

        "acceleration_mps2":
            float(
                event[
                    "acceleration_mps2"
                ]
            ),

        "mechanical_power_w":
            float(
                event[
                    "mechanical_power_w"
                ]
            ),

        "battery_power_w":
            float(
                event[
                    "battery_power_w"
                ]
            ),

        "battery_temperature_c":
            float(
                event[
                    "battery_temperature_c"
                ]
            ),

        "energy_consumed_wh":
            float(
                event[
                    "energy_consumed_wh"
                ]
            ),

        "consumption_wh_km":
            float(
                event[
                    "consumption_wh_km"
                ]
            ),

        "initial_soc":
            float(
                event["initial_soc"]
            ),

        "final_soc":
            float(
                event["final_soc"]
            ),
    }


# ============================================================
# DATABASE INSERT
# ============================================================

def save_event(event):

    clean_event = normalize_event(
        event
    )

    with engine.begin() as connection:

        # ----------------------------------------------------
        # CREATE BIKE IF NECESSARY
        # ----------------------------------------------------

        connection.execute(
            INSERT_BIKE_SQL,
            {
                "bike_id":
                    clean_event[
                        "bike_id"
                    ]
            },
        )

        # ----------------------------------------------------
        # INSERT TELEMETRY
        #
        # RETURNING telemetry_id permet de savoir si
        # PostgreSQL a réellement inséré la ligne.
        #
        # Si bike_id + timestamp existe déjà :
        #
        # telemetry_id = None
        # ----------------------------------------------------

        telemetry_id = (
            connection.execute(
                INSERT_TELEMETRY_SQL,
                clean_event,
            )
            .scalar()
        )

    inserted = (
        telemetry_id
        is not None
    )

    return (
        clean_event,
        inserted,
    )


# ============================================================
# AUTOMATIC PREDICTION
# ============================================================

def process_automatic_prediction(
    bike_id,
):

    bike_event_counters[
        bike_id
    ] += 1

    current_count = (
        bike_event_counters[
            bike_id
        ]
    )

    # --------------------------------------------------------
    # Pas encore suffisamment de nouvelles observations.
    # --------------------------------------------------------

    if (
        current_count
        <
        PREDICTION_EVERY_N_EVENTS
    ):

        return

    # --------------------------------------------------------
    # Le vélo vient d'atteindre le seuil.
    # --------------------------------------------------------

    try:

        prediction = (
            predict_and_save(
                bike_id=bike_id
            )
        )

        print()
        print("=" * 70)
        print(
            "AUTOMATIC 30-DAY RISK PREDICTION"
        )
        print("=" * 70)

        print(
            f"Bike     : {bike_id}"
        )

        print(
            f"Risk     : "
            f"{prediction['predicted_risk']}"
        )

        print(
            f"NORMAL   : "
            f"{prediction['probability_normal'] * 100:.2f}%"
        )

        print(
            f"WARNING  : "
            f"{prediction['probability_warning'] * 100:.2f}%"
        )

        print(
            f"CRITICAL : "
            f"{prediction['probability_critical'] * 100:.2f}%"
        )

        print(
            f"Horizon  : +"
            f"{prediction['prediction_horizon_days']} days"
        )

        print(
            f"Model    : "
            f"{prediction['model_version']}"
        )

        print("=" * 70)
        print()

        # ----------------------------------------------------
        # La prédiction a réussi.
        # On recommence un nouveau cycle de 10 observations.
        # ----------------------------------------------------

        bike_event_counters[
            bike_id
        ] = 0

    except Exception as error:

        print()
        print("=" * 70)
        print(
            "AUTOMATIC PREDICTION ERROR"
        )
        print("=" * 70)

        print(
            f"Bike  : {bike_id}"
        )

        print(
            f"Error : {error}"
        )

        print("=" * 70)
        print()

        # IMPORTANT :
        #
        # On remet également le compteur à zéro ici.
        # Sinon chaque événement suivant déclencherait
        # immédiatement une nouvelle tentative.

        bike_event_counters[
            bike_id
        ] = 0


# ============================================================
# KAFKA CONSUMER
# ============================================================

def create_consumer():

    print()
    print("=" * 90)
    print(
        "CONNECTING TO KAFKA"
    )
    print("=" * 90)

    consumer = KafkaConsumer(

        TOPIC_NAME,

        bootstrap_servers=[
            KAFKA_BOOTSTRAP_SERVERS
        ],

        group_id=
            CONSUMER_GROUP,

        auto_offset_reset=
            "earliest",

        enable_auto_commit=
            False,

        value_deserializer=
            lambda value:
                json.loads(
                    value.decode(
                        "utf-8"
                    )
                ),
    )

    print(
        f"Broker : "
        f"{KAFKA_BOOTSTRAP_SERVERS}"
    )

    print(
        f"Topic  : "
        f"{TOPIC_NAME}"
    )

    print(
        f"Group  : "
        f"{CONSUMER_GROUP}"
    )

    print()

    print(
        "Kafka consumer : READY"
    )

    return consumer


# ============================================================
# CONSUME LOOP
# ============================================================

def consume():

    consumer = create_consumer()

    total_received = 0
    total_inserted = 0
    total_duplicates = 0
    total_errors = 0
    messages_since_commit = 0

    print()
    print("=" * 90)
    print(
        "WAITING FOR TELEMETRY"
    )
    print("=" * 90)

    print()

    print(
        f"Automatic prediction every "
        f"{PREDICTION_EVERY_N_EVENTS} "
        f"new events per bike."
    )

    print()

    print(
        "Press CTRL+C to stop."
    )

    print()

    try:

        for message in consumer:

            total_received += 1

            try:

                # ------------------------------------------------
                # KAFKA EVENT
                # ------------------------------------------------

                event = (
                    message.value
                )

                # ------------------------------------------------
                # POSTGRESQL
                # ------------------------------------------------

                (
                    clean_event,
                    inserted,
                ) = save_event(
                    event
                )

                bike_id = (
                    clean_event[
                        "bike_id"
                    ]
                )

                # ------------------------------------------------
                # ONLY NEW TELEMETRY
                # ------------------------------------------------

                if inserted:

                    total_inserted += 1

                    # --------------------------------------------
                    # AUTOMATIC ML INFERENCE
                    # --------------------------------------------

                    process_automatic_prediction(
                        bike_id=bike_id
                    )

                    # --------------------------------------------
                    # TERMINAL LOG
                    # --------------------------------------------

                    if (
                        total_inserted == 1
                        or
                        total_inserted % 100 == 0
                    ):

                        print(
                            f"Inserted : "
                            f"{total_inserted:6d} "
                            f"| bike="
                            f"{bike_id} "
                            f"| timestamp="
                            f"{clean_event['timestamp']}"
                        )

                else:

                    total_duplicates += 1

                    if (
                        total_duplicates == 1
                        or
                        total_duplicates % 1000 == 0
                    ):

                        print(
                            f"Duplicate ignored : "
                            f"{total_duplicates}"
                        )

                # ------------------------------------------------
                # KAFKA OFFSET
                #
                # Commit seulement après traitement correct
                # de l'événement.
                # ------------------------------------------------

                messages_since_commit += 1
                if messages_since_commit >= COMMIT_EVERY_N_MESSAGES:
                    try:
                        consumer.commit()
                        messages_since_commit = 0
                    except Exception as commit_error:
                        print()
                        print("=" * 70)
                        print("KAFKA OFFSET COMMIT WARNING")
                        print("=" * 70)
                        print(f"Error : {commit_error}")
                        print("Telemetry is already persisted in PostgreSQL. Consumer continues; Kafka may replay uncommitted events.")
                        print("=" * 70)
                        print()

            except Exception as exc:

                total_errors += 1

                print()
                print(
                    "EVENT PROCESSING ERROR"
                )

                print(
                    f"Partition : "
                    f"{message.partition}"
                )

                print(
                    f"Offset    : "
                    f"{message.offset}"
                )

                print(
                    f"Error     : "
                    f"{exc}"
                )

                print(
                    f"Event     : "
                    f"{message.value}"
                )

                # ------------------------------------------------
                # IMPORTANT
                #
                # On ne commit pas l'offset Kafka lorsque
                # le traitement principal échoue.
                # ------------------------------------------------

                raise

    except KeyboardInterrupt:

        print()

        print(
            "Consumer stopped by user."
        )

    finally:

        if messages_since_commit > 0:
            try:
                consumer.commit()
            except Exception as commit_error:
                print()
                print("=" * 70)
                print("FINAL KAFKA COMMIT WARNING")
                print("=" * 70)
                print(f"Error : {commit_error}")
                print("PostgreSQL data remains persisted. Some Kafka events may be replayed on restart.")
                print("=" * 70)
                print()

        consumer.close()

        print()
        print("=" * 90)
        print(
            "CONSUMER SUMMARY"
        )
        print("=" * 90)

        print(
            f"Received   : "
            f"{total_received}"
        )

        print(
            f"Inserted   : "
            f"{total_inserted}"
        )

        print(
            f"Duplicates : "
            f"{total_duplicates}"
        )

        print(
            f"Errors     : "
            f"{total_errors}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)

    print(
        "SMART E-BIKE "
        "KAFKA -> POSTGRESQL "
        "CONSUMER V4.2"
    )

    print("=" * 90)

    consume()


if __name__ == "__main__":

    main()