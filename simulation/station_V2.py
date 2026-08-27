from dataclasses import dataclass


@dataclass
class Station:
    station_id: str
    name: str
    latitude: float
    longitude: float
    capacity: int
    charging_slots: int

    def __post_init__(self):

        if self.capacity <= 0:
            raise ValueError(
                "La capacité d'une station doit être positive."
            )

        if self.charging_slots < 0:
            raise ValueError(
                "Le nombre de bornes de recharge ne peut pas être négatif."
            )

        if self.charging_slots > self.capacity:
            raise ValueError(
                "Le nombre de bornes ne peut pas dépasser la capacité."
            )

    def to_dict(self):

        return {
            "station_id": self.station_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity": self.capacity,
            "charging_slots": self.charging_slots
        }


@dataclass
class StationConnection:
    origin_station_id: str
    destination_station_id: str
    distance_km: float
    average_slope_percent: float
    traffic_factor: float = 1.0

    def __post_init__(self):

        if self.origin_station_id == self.destination_station_id:
            raise ValueError(
                "Une connexion doit relier deux stations différentes."
            )

        if self.distance_km <= 0:
            raise ValueError(
                "La distance doit être strictement positive."
            )

        if not -15 <= self.average_slope_percent <= 15:
            raise ValueError(
                "La pente moyenne semble irréaliste."
            )

        if self.traffic_factor <= 0:
            raise ValueError(
                "traffic_factor doit être positif."
            )

    def to_dict(self):

        return {
            "origin_station_id": self.origin_station_id,
            "destination_station_id": self.destination_station_id,
            "distance_km": self.distance_km,
            "average_slope_percent": self.average_slope_percent,
            "traffic_factor": self.traffic_factor
        }