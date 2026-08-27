from datetime import datetime

from simulation.bike_V2 import DigitalTwinBike
from simulation.trip_V2 import DigitalTwinTrip
from simulation.sensor_V2 import DigitalTwinSensor

from simulation.telemetry_generator_V2 import TelemetryGeneratorV2

def main():

    # =====================================================
    # VELO
    # =====================================================

    bike = DigitalTwinBike(
        bike_id="DTB0001",

        mass_kg=100.0,

        battery_capacity_wh=500.0,

        drivetrain_efficiency=0.85,

        speed_mps=4.5,

        acceleration_mps2=0.12,

        battery_soc=78.5,

        battery_temperature_c=27.3,

        current_station_id=None,

        health_index=0.25
    )


    # =====================================================
    # TRAJET
    # =====================================================

    trip = DigitalTwinTrip(
        trip_id="TRIP_TEST_001",

        bike_id=
            bike.bike_id,

        origin_station_id=
            "ST001",

        destination_station_id=
            "ST006",

        planned_distance_m=
            5100.0,

        start_time=
            datetime.now(),

        initial_battery_soc=
            bike.battery_soc
    )


    trip.travelled_distance_m = (
        1250.0
    )


    # =====================================================
    # SEGMENT
    # =====================================================

    segment = {
        "origin_station_id":
            "ST001",

        "destination_station_id":
            "ST003",

        "distance_km":
            3.1,

        "distance_m":
            3100.0,

        "average_slope_percent":
            1.4,

        "traffic_factor":
            1.1
    }


    # =====================================================
    # CAPTEUR
    # =====================================================

    sensor = DigitalTwinSensor()


    # =====================================================
    # GENERATEUR
    # =====================================================

    generator = TelemetryGeneratorV2(
        sensor=sensor,

        simulation_start_time=
            datetime(
                2026,
                8,
                22,
                8,
                0,
                0
            )
    )


    # =====================================================
    # EVENT
    # =====================================================

    event = generator.create_event(
        bike=bike,

        trip=trip,

        segment=segment,

        simulation_seconds=300,

        traffic_factor=1.18,

        slope_percent=1.55,

        mechanical_power_w=150.0,

        battery_power_w=178.0,

        energy_consumed_wh=0.25,

        ambient_temperature_c=22.0,

        urban_status="CRUISING"
    )


    # =====================================================
    # AFFICHAGE
    # =====================================================

    print()
    print(
        "================================================"
    )

    print(
        "TELEMETRY GENERATOR V2"
    )

    print(
        "================================================"
    )


    data = event.to_dict()


    for key, value in data.items():

        print(
            f"{key:30s} : {value}"
        )


    print(
        "================================================"
    )


if __name__ == "__main__":

    main()