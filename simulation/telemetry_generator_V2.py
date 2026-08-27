import uuid
from datetime import datetime, timedelta

from simulation.sensor_event_V2 import DigitalTwinSensorEvent


class TelemetryGeneratorV2:

    def __init__(
        self,
        sensor,
        simulation_start_time=None
    ):

        self.sensor = sensor

        self.simulation_start_time = (
            simulation_start_time
            if simulation_start_time is not None
            else datetime.now()
        )


    # =====================================================
    # TIMESTAMP
    # =====================================================

    def build_timestamp(
        self,
        simulation_seconds
    ):

        return (
            self.simulation_start_time
            +
            timedelta(
                seconds=simulation_seconds
            )
        )


    # =====================================================
    # TRUE RISK CLASS
    # =====================================================

    def compute_true_risk_class(
        self,
        health_index,
        battery_soc,
        battery_temperature_c
    ):
        """
        Ground-truth risk used by the Digital Twin simulation.

        This is NOT the operational ML prediction.

        The V4.2 predictive model remains responsible for
        predicting NORMAL / WARNING / CRITICAL from temporal
        telemetry features.
        """

        risk_score = (
            0.50
            *
            health_index
        )

        if battery_soc < 20:

            risk_score += 0.20

        if battery_temperature_c > 35:

            risk_score += 0.20

        if battery_temperature_c > 40:

            risk_score += 0.20


        if risk_score >= 0.70:

            return "CRITICAL"

        if risk_score >= 0.35:

            return "WARNING"

        return "NORMAL"


    # =====================================================
    # CREATE DIGITAL TWIN EVENT
    # =====================================================

    def create_event(
        self,
        bike,
        trip,
        segment,
        simulation_seconds,
        traffic_factor,
        slope_percent,
        mechanical_power_w,
        battery_power_w,
        energy_consumed_wh,
        ambient_temperature_c,
        initial_soc,
        urban_status
    ):

        # -------------------------------------------------
        # SENSOR MEASUREMENTS
        # -------------------------------------------------

        measured = (
            self.sensor.measure(
                true_speed_mps=
                    bike.speed_mps,

                true_acceleration_mps2=
                    bike.acceleration_mps2,

                true_battery_soc=
                    bike.battery_soc,

                true_temperature_c=
                    bike.battery_temperature_c
            )
        )


        # -------------------------------------------------
        # TRIP STATE
        # -------------------------------------------------

        remaining_distance_m = (
            trip.remaining_distance_m
        )

        progress_percent = (
            trip.progress_percent
        )


        # -------------------------------------------------
        # TRUE SIMULATION RISK
        # -------------------------------------------------

        true_risk_class = (
            self.compute_true_risk_class(
                health_index=
                    bike.health_index,

                battery_soc=
                    bike.battery_soc,

                battery_temperature_c=
                    bike.battery_temperature_c
            )
        )


        # -------------------------------------------------
        # SOC
        # -------------------------------------------------

        initial_soc = float(
            initial_soc
        )

        final_soc = float(
            bike.battery_soc
        )


        # -------------------------------------------------
        # DIGITAL TWIN EVENT
        # -------------------------------------------------

        event = DigitalTwinSensorEvent(

            event_id=
                f"EVT-{uuid.uuid4().hex[:16]}",

            bike_id=
                bike.bike_id,

            trip_id=
                trip.trip_id,

            timestamp=
                self.build_timestamp(
                    simulation_seconds
                ),

            origin_station_id=
                segment[
                    "origin_station_id"
                ],

            destination_station_id=
                segment[
                    "destination_station_id"
                ],

            distance_travelled_m=
                float(
                    trip.travelled_distance_m
                ),

            remaining_distance_m=
                float(
                    remaining_distance_m
                ),

            trip_progress_percent=
                float(
                    progress_percent
                ),

            latitude=None,

            longitude=None,

            speed_mps=
                float(
                    measured[
                        "speed_mps"
                    ]
                ),

            acceleration_mps2=
                float(
                    measured[
                        "acceleration_mps2"
                    ]
                ),

            slope_percent=
                float(
                    slope_percent
                ),

            battery_soc=
                float(
                    measured[
                        "battery_soc"
                    ]
                ),

            initial_soc=
                initial_soc,

            final_soc=
                final_soc,

            mechanical_power_w=
                float(
                    mechanical_power_w
                ),

            battery_power_w=
                float(
                    battery_power_w
                ),

            energy_consumed_wh=
                float(
                    energy_consumed_wh
                ),

            battery_temperature_c=
                float(
                    measured[
                        "battery_temperature_c"
                    ]
                ),

            ambient_temperature_c=
                float(
                    ambient_temperature_c
                ),

            traffic_factor=
                float(
                    traffic_factor
                ),

            operational_status=
                str(
                    urban_status
                ),

            true_health_index=
                float(
                    bike.health_index
                ),

            true_risk_class=
                true_risk_class
        )


        return event