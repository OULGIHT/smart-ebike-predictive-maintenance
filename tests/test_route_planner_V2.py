from simulation.network_V2 import build_default_network
from simulation.route_planner_V2 import RoutePlannerV2

def main():

    network = build_default_network()

    planner = RoutePlannerV2(
        network
    )


    route = planner.shortest_path(
        origin_station_id="ST001",
        destination_station_id="ST006"
    )


    print()
    print("========================================")
    print("ROUTE PLANNER V2")
    print("========================================")

    print(
        "Route :",
        " -> ".join(
            route["stations"]
        )
    )

    print()

    print(
        f"Distance totale : "
        f"{route['total_distance_km']:.2f} km"
    )

    print()
    print("SEGMENTS")
    print("----------------------------------------")


    for i, segment in enumerate(
        route["segments"],
        start=1
    ):

        print(
            f"Segment {i} | "
            f"{segment['origin_station_id']} "
            f"-> "
            f"{segment['destination_station_id']} "
            f"| distance="
            f"{segment['distance_km']:.2f} km "
            f"| slope="
            f"{segment['average_slope_percent']:+.2f}% "
            f"| traffic="
            f"{segment['traffic_factor']:.2f}"
        )


    print()
    print("========================================")


if __name__ == "__main__":

    main()