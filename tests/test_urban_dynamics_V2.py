from simulation.urban_dynamics_V2 import UrbanDynamicsV2

def main():

    dynamics = UrbanDynamicsV2(
        seed=42
    )

    current_speed_mps = 4.5

    base_target_speed_mps = 5.0
    base_traffic_factor = 1.10
    average_slope_percent = 1.40

    simulation_hour = 8
    dt_seconds = 5

    simulation_time = 0

    print()
    print("==============================================================")
    print("URBAN DYNAMICS V2 - TEMPORAL MODEL")
    print("==============================================================")

    print(
        "Time | Speed | Traffic | Slope | Target | "
        "Accel | State        | Stop"
    )

    print("-" * 90)

    for _ in range(120):

        state = dynamics.step(
            current_speed_mps=current_speed_mps,
            base_target_speed_mps=base_target_speed_mps,
            base_traffic_factor=base_traffic_factor,
            average_slope_percent=average_slope_percent,
            simulation_hour=simulation_hour,
            dt_seconds=dt_seconds
        )

        acceleration = (
            state["acceleration_mps2"]
        )

        current_speed_mps = max(
            0.0,
            current_speed_mps
            + acceleration
            * dt_seconds
        )

        simulation_time += dt_seconds

        print(
            f"{simulation_time:4d} | "
            f"{current_speed_mps * 3.6:5.1f} | "
            f"{state['traffic_factor']:7.2f} | "
            f"{state['slope_percent']:+5.2f}% | "
            f"{state['target_speed_mps'] * 3.6:6.1f} | "
            f"{acceleration:+5.2f} | "
            f"{state['urban_status']:12s} | "
            f"{state['stop_remaining_seconds']:5.1f}"
        )

    print()
    print("==============================================================")


if __name__ == "__main__":
    main()