from simulation.station_V2 import Station, StationConnection

class NetworkV2:

    def __init__(self):

        self.stations = {}
        self.connections = []


    # =====================================================
    # AJOUT STATION
    # =====================================================

    def add_station(self, station):

        if not isinstance(station, Station):
            raise TypeError(
                "station doit être une instance de Station."
            )

        if station.station_id in self.stations:
            raise ValueError(
                f"La station {station.station_id} existe déjà."
            )

        self.stations[
            station.station_id
        ] = station


    # =====================================================
    # AJOUT CONNEXION
    # =====================================================

    def add_connection(self, connection):

        if not isinstance(
            connection,
            StationConnection
        ):
            raise TypeError(
                "connection doit être une instance "
                "de StationConnection."
            )

        if (
            connection.origin_station_id
            not in self.stations
        ):
            raise ValueError(
                f"Station inconnue : "
                f"{connection.origin_station_id}"
            )

        if (
            connection.destination_station_id
            not in self.stations
        ):
            raise ValueError(
                f"Station inconnue : "
                f"{connection.destination_station_id}"
            )

        self.connections.append(
            connection
        )


    # =====================================================
    # RECUPERER UNE STATION
    # =====================================================

    def get_station(
        self,
        station_id
    ):

        if station_id not in self.stations:
            raise ValueError(
                f"Station inconnue : {station_id}"
            )

        return self.stations[
            station_id
        ]


    # =====================================================
    # CONNEXIONS DEPUIS UNE STATION
    # =====================================================

    def get_connections_from(
        self,
        station_id
    ):

        return [
            connection
            for connection
            in self.connections
            if (
                connection.origin_station_id
                == station_id
            )
        ]


    # =====================================================
    # TROUVER CONNEXION DIRECTE
    # =====================================================

    def get_direct_connection(
        self,
        origin_station_id,
        destination_station_id
    ):

        for connection in self.connections:

            if (
                connection.origin_station_id
                == origin_station_id
                and
                connection.destination_station_id
                == destination_station_id
            ):

                return connection

        return None


    # =====================================================
    # EXPORT
    # =====================================================

    def to_dict(self):

        return {
            "stations": [
                station.to_dict()
                for station
                in self.stations.values()
            ],

            "connections": [
                connection.to_dict()
                for connection
                in self.connections
            ]
        }


# =========================================================
# RESEAU PAR DEFAUT
# =========================================================

def build_default_network():

    network = NetworkV2()


    # =====================================================
    # STATIONS
    # =====================================================

    stations = [

        Station(
            station_id="ST001",
            name="Central",
            latitude=48.8566,
            longitude=2.3522,
            capacity=30,
            charging_slots=6
        ),

        Station(
            station_id="ST002",
            name="North",
            latitude=48.8750,
            longitude=2.3500,
            capacity=25,
            charging_slots=5
        ),

        Station(
            station_id="ST003",
            name="East",
            latitude=48.8600,
            longitude=2.3900,
            capacity=25,
            charging_slots=5
        ),

        Station(
            station_id="ST004",
            name="South",
            latitude=48.8300,
            longitude=2.3500,
            capacity=30,
            charging_slots=6
        ),

        Station(
            station_id="ST005",
            name="West",
            latitude=48.8580,
            longitude=2.3100,
            capacity=25,
            charging_slots=5
        ),

        Station(
            station_id="ST006",
            name="University",
            latitude=48.8460,
            longitude=2.3800,
            capacity=20,
            charging_slots=4
        ),

        Station(
            station_id="ST007",
            name="Business",
            latitude=48.8700,
            longitude=2.3200,
            capacity=25,
            charging_slots=5
        ),

        Station(
            station_id="ST008",
            name="Park",
            latitude=48.8400,
            longitude=2.3200,
            capacity=20,
            charging_slots=4
        )

    ]


    for station in stations:

        network.add_station(
            station
        )


    # =====================================================
    # CONNEXIONS
    # =====================================================

    connections = [

        StationConnection(
            origin_station_id="ST001",
            destination_station_id="ST002",
            distance_km=2.4,
            average_slope_percent=0.8,
            traffic_factor=1.20
        ),

        StationConnection(
            origin_station_id="ST002",
            destination_station_id="ST001",
            distance_km=2.4,
            average_slope_percent=-0.8,
            traffic_factor=1.15
        ),

        StationConnection(
            origin_station_id="ST001",
            destination_station_id="ST003",
            distance_km=3.1,
            average_slope_percent=1.4,
            traffic_factor=1.10
        ),

        StationConnection(
            origin_station_id="ST003",
            destination_station_id="ST001",
            distance_km=3.1,
            average_slope_percent=-1.4,
            traffic_factor=1.05
        ),

        StationConnection(
            origin_station_id="ST001",
            destination_station_id="ST004",
            distance_km=3.5,
            average_slope_percent=-0.6,
            traffic_factor=1.15
        ),

        StationConnection(
            origin_station_id="ST004",
            destination_station_id="ST001",
            distance_km=3.5,
            average_slope_percent=0.6,
            traffic_factor=1.10
        ),

        StationConnection(
            origin_station_id="ST001",
            destination_station_id="ST005",
            distance_km=3.2,
            average_slope_percent=0.3,
            traffic_factor=1.00
        ),

        StationConnection(
            origin_station_id="ST005",
            destination_station_id="ST001",
            distance_km=3.2,
            average_slope_percent=-0.3,
            traffic_factor=1.00
        ),

        StationConnection(
            origin_station_id="ST003",
            destination_station_id="ST006",
            distance_km=2.0,
            average_slope_percent=1.8,
            traffic_factor=0.90
        ),

        StationConnection(
            origin_station_id="ST006",
            destination_station_id="ST003",
            distance_km=2.0,
            average_slope_percent=-1.8,
            traffic_factor=0.90
        ),

        StationConnection(
            origin_station_id="ST005",
            destination_station_id="ST007",
            distance_km=2.3,
            average_slope_percent=1.0,
            traffic_factor=1.25
        ),

        StationConnection(
            origin_station_id="ST007",
            destination_station_id="ST005",
            distance_km=2.3,
            average_slope_percent=-1.0,
            traffic_factor=1.20
        ),

        StationConnection(
            origin_station_id="ST004",
            destination_station_id="ST008",
            distance_km=1.9,
            average_slope_percent=0.7,
            traffic_factor=0.85
        ),

        StationConnection(
            origin_station_id="ST008",
            destination_station_id="ST004",
            distance_km=1.9,
            average_slope_percent=-0.7,
            traffic_factor=0.85
        ),

        StationConnection(
            origin_station_id="ST007",
            destination_station_id="ST002",
            distance_km=2.1,
            average_slope_percent=0.4,
            traffic_factor=1.30
        ),

        StationConnection(
            origin_station_id="ST002",
            destination_station_id="ST007",
            distance_km=2.1,
            average_slope_percent=-0.4,
            traffic_factor=1.30
        ),

        StationConnection(
            origin_station_id="ST006",
            destination_station_id="ST004",
            distance_km=2.6,
            average_slope_percent=-0.5,
            traffic_factor=1.00
        ),

        StationConnection(
            origin_station_id="ST004",
            destination_station_id="ST006",
            distance_km=2.6,
            average_slope_percent=0.5,
            traffic_factor=1.00
        )
    ]


    for connection in connections:

        network.add_connection(
            connection
        )


    return network