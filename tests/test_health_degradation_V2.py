from simulation.health_degradation_V2 import (
    HealthDegradationV2
)

def run_profile(
    profile
):

    health = HealthDegradationV2(
        profile=profile,
        seed=42
    )


    print()
    print(
        "=========================================================="
    )

    print(
        f"PROFILE : {profile}"
    )

    print(
        "=========================================================="
    )

    print(
        "Hour | Health | Capacity | Efficiency | Thermal | Resistance"
    )

    print(
        "-" * 72
    )


    # --------------------------------------------------------
    # On simule 1000 heures équivalentes
    #
    # Un pas = 1 heure.
    # --------------------------------------------------------

    for hour in range(
        1,
        1001
    ):

        state = health.update(

            dt_seconds=
                3600,

            battery_power_w=
                250.0,

            battery_temperature_c=
                34.0,

            battery_soc=
                45.0,

            acceleration_mps2=
                0.25,

            slope_percent=
                2.0,

            traffic_factor=
                1.25
        )


        if (
            hour == 1
            or
            hour % 100 == 0
        ):

            print(
                f"{hour:4d} | "
                f"{state.health_index:6.3f} | "
                f"{state.capacity_factor:8.3f} | "
                f"{state.efficiency_factor:10.3f} | "
                f"{state.thermal_factor:7.3f} | "
                f"{state.resistance_factor:10.3f}"
            )


def main():

    profiles = [

        "HEALTHY",

        "SLOW_DEGRADATION",

        "BATTERY_DEGRADATION",

        "THERMAL_DEGRADATION",

        "SEVERE_DEGRADATION",
    ]


    for profile in profiles:

        run_profile(
            profile
        )


if __name__ == "__main__":

    main()