from simulation.health_degradation_V2 import HealthDegradationV2


SCENARIOS = {

    "BASELINE": {
        "battery_power_w": 100.0,
        "battery_temperature_c": 25.0,
    },

    "HIGH_POWER": {
        "battery_power_w": 450.0,
        "battery_temperature_c": 25.0,
    },

    "HIGH_TEMPERATURE": {
        "battery_power_w": 100.0,
        "battery_temperature_c": 42.0,
    },

    "HIGH_POWER_AND_TEMP": {
        "battery_power_w": 450.0,
        "battery_temperature_c": 42.0,
    },
}


PROFILES = [
    "HEALTHY",
    "SLOW_DEGRADATION",
    "BATTERY_DEGRADATION",
    "THERMAL_DEGRADATION",
    "SEVERE_DEGRADATION",
]


def simulate(profile, scenario):

    model = HealthDegradationV2(
        profile=profile,
        seed=42
    )

    initial_health = model.health_index

    # 100 heures seulement pour éviter la saturation.
    for _ in range(100):

        model.update(
            dt_seconds=3600,

            battery_power_w=
                scenario["battery_power_w"],

            battery_temperature_c=
                scenario["battery_temperature_c"],

            battery_soc=60.0,

            acceleration_mps2=0.10,

            slope_percent=1.0,

            traffic_factor=1.0
        )

    final_health = model.health_index

    return (
        initial_health,
        final_health,
        final_health - initial_health
    )


def main():

    print()
    print("=" * 105)
    print("HEALTH DEGRADATION V2 - SENSITIVITY ANALYSIS")
    print("=" * 105)

    print(
        f"{'PROFILE':22s} | "
        f"{'SCENARIO':22s} | "
        f"{'INITIAL':>8s} | "
        f"{'FINAL':>8s} | "
        f"{'DELTA H':>8s}"
    )

    print("-" * 105)

    results = {}

    for profile in PROFILES:

        results[profile] = {}

        for scenario_name, scenario in SCENARIOS.items():

            initial, final, delta = simulate(
                profile,
                scenario
            )

            results[profile][scenario_name] = delta

            print(
                f"{profile:22s} | "
                f"{scenario_name:22s} | "
                f"{initial:8.4f} | "
                f"{final:8.4f} | "
                f"{delta:8.4f}"
            )

        print("-" * 105)

    print()
    print("=" * 105)
    print("DIAGNOSTIC")
    print("=" * 105)

    battery = results["BATTERY_DEGRADATION"]

    thermal = results["THERMAL_DEGRADATION"]

    print()
    print("BATTERY_DEGRADATION")
    print(
        f"High power delta       : "
        f"{battery['HIGH_POWER']:.4f}"
    )
    print(
        f"High temperature delta : "
        f"{battery['HIGH_TEMPERATURE']:.4f}"
    )

    print()
    print("THERMAL_DEGRADATION")
    print(
        f"High power delta       : "
        f"{thermal['HIGH_POWER']:.4f}"
    )
    print(
        f"High temperature delta : "
        f"{thermal['HIGH_TEMPERATURE']:.4f}"
    )

    print()
    print("=" * 105)


if __name__ == "__main__":
    main()