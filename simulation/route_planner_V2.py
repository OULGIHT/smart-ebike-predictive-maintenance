import heapq


class RoutePlannerV2:

    def __init__(self, network):

        self.network = network


    # =====================================================
    # PLUS COURT CHEMIN PAR DISTANCE
    # =====================================================

    def shortest_path(
        self,
        origin_station_id,
        destination_station_id
    ):

        if origin_station_id == destination_station_id:

            return {
                "stations": [
                    origin_station_id
                ],
                "segments": [],
                "total_distance_km": 0.0
            }


        if origin_station_id not in self.network.stations:

            raise ValueError(
                f"Station inconnue : {origin_station_id}"
            )


        if destination_station_id not in self.network.stations:

            raise ValueError(
                f"Station inconnue : {destination_station_id}"
            )


        # -------------------------------------------------
        # DIJKSTRA
        # -------------------------------------------------

        queue = [
            (
                0.0,
                origin_station_id,
                []
            )
        ]


        best_distance = {
            origin_station_id: 0.0
        }


        while queue:

            current_distance, current_station, path = (
                heapq.heappop(
                    queue
                )
            )


            # -------------------------------------------------
            # ARRIVEE
            # -------------------------------------------------

            if current_station == destination_station_id:

                station_path = (
                    [
                        origin_station_id
                    ]
                )

                segments = []


                for connection in path:

                    station_path.append(
                        connection.destination_station_id
                    )

                    segments.append(
                        {
                            "origin_station_id":
                                connection.origin_station_id,

                            "destination_station_id":
                                connection.destination_station_id,

                            "distance_km":
                                connection.distance_km,

                            "distance_m":
                                connection.distance_km
                                * 1000,

                            "average_slope_percent":
                                connection.average_slope_percent,

                            "traffic_factor":
                                connection.traffic_factor
                        }
                    )


                return {
                    "stations":
                        station_path,

                    "segments":
                        segments,

                    "total_distance_km":
                        current_distance,

                    "total_distance_m":
                        current_distance
                        * 1000
                }


            # -------------------------------------------------
            # CONNEXIONS SORTANTES
            # -------------------------------------------------

            connections = (
                self.network.get_connections_from(
                    current_station
                )
            )


            for connection in connections:

                next_station = (
                    connection.destination_station_id
                )


                new_distance = (
                    current_distance
                    + connection.distance_km
                )


                previous_best = (
                    best_distance.get(
                        next_station
                    )
                )


                if (
                    previous_best is None
                    or
                    new_distance < previous_best
                ):

                    best_distance[
                        next_station
                    ] = new_distance


                    new_path = (
                        path
                        + [
                            connection
                        ]
                    )


                    heapq.heappush(
                        queue,
                        (
                            new_distance,
                            next_station,
                            new_path
                        )
                    )


        # -------------------------------------------------
        # PAS DE ROUTE
        # -------------------------------------------------

        raise ValueError(
            f"Aucune route entre "
            f"{origin_station_id} "
            f"et "
            f"{destination_station_id}"
        )