from simulation.network_V2 import build_default_network


def main():

    network = build_default_network()

    print()
    print("========================================")
    print("NETWORK V2")
    print("========================================")

    print(
        f"Stations    : {len(network.stations)}"
    )

    print(
        f"Connexions  : {len(network.connections)}"
    )

    print()
    print("STATIONS")
    print("----------------------------------------")

    for station in network.stations.values():

        print(
            f"{station.station_id} | "
            f"{station.name} | "
            f"capacity={station.capacity} | "
            f"charging={station.charging_slots}"
        )

    print()
    print("CONNEXIONS DEPUIS ST001")
    print("----------------------------------------")

    connections = network.get_connections_from(
        "ST001"
    )

    for connection in connections:

        print(
            f"{connection.origin_station_id}"
            f" -> "
            f"{connection.destination_station_id}"
            f" | "
            f"{connection.distance_km:.1f} km"
            f" | slope="
            f"{connection.average_slope_percent:+.1f}%"
            f" | traffic="
            f"{connection.traffic_factor:.2f}"
        )

    print()
    print("========================================")


if __name__ == "__main__":
    main()