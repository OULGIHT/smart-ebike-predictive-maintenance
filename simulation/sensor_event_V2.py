from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DigitalTwinSensorEvent:

    event_id: str
    bike_id: str
    trip_id: Optional[str]

    timestamp: datetime

    # =====================================================
    # POSITION / TRAJET
    # =====================================================

    origin_station_id: Optional[str]
    destination_station_id: Optional[str]

    distance_travelled_m: float
    remaining_distance_m: float
    trip_progress_percent: float

    latitude: Optional[float]
    longitude: Optional[float]

    # =====================================================
    # CINEMATIQUE
    # =====================================================

    speed_mps: float
    acceleration_mps2: float

    slope_percent: float

    # =====================================================
    # ENERGIE
    # =====================================================

    battery_soc: float

    initial_soc: float
    final_soc: float

    mechanical_power_w: float
    battery_power_w: float

    energy_consumed_wh: float

    # =====================================================
    # THERMIQUE
    # =====================================================

    battery_temperature_c: float
    ambient_temperature_c: float

    # =====================================================
    # CONTEXTE
    # =====================================================

    traffic_factor: float

    operational_status: str

    # =====================================================
    # ETAT LATENT DU SIMULATEUR
    # =====================================================

    true_health_index: float

    true_risk_class: str


    def __post_init__(self):

        if self.distance_travelled_m < 0:
            raise ValueError(
                "distance_travelled_m ne peut pas être négatif."
            )

        if self.remaining_distance_m < 0:
            raise ValueError(
                "remaining_distance_m ne peut pas être négatif."
            )

        if not 0 <= self.trip_progress_percent <= 100:
            raise ValueError(
                "trip_progress_percent doit être compris entre 0 et 100."
            )

        if self.speed_mps < 0:
            raise ValueError(
                "speed_mps ne peut pas être négatif."
            )

        if not -25 <= self.slope_percent <= 25:
            raise ValueError(
                "slope_percent semble irréaliste."
            )

        if not 0 <= self.battery_soc <= 100:
            raise ValueError(
                "battery_soc doit être compris entre 0 et 100."
            )

        if not 0 <= self.initial_soc <= 100:
            raise ValueError(
                "initial_soc doit être compris entre 0 et 100."
            )

        if not 0 <= self.final_soc <= 100:
            raise ValueError(
                "final_soc doit être compris entre 0 et 100."
            )

        if self.mechanical_power_w < 0:
            raise ValueError(
                "mechanical_power_w ne peut pas être négatif."
            )

        if self.battery_power_w < 0:
            raise ValueError(
                "battery_power_w ne peut pas être négatif."
            )

        if self.energy_consumed_wh < 0:
            raise ValueError(
                "energy_consumed_wh ne peut pas être négatif."
            )

        if self.traffic_factor <= 0:
            raise ValueError(
                "traffic_factor doit être positif."
            )

        if not 0 <= self.true_health_index <= 1:
            raise ValueError(
                "true_health_index doit être compris entre 0 et 1."
            )

        allowed_risk_classes = {
            "NORMAL",
            "WARNING",
            "CRITICAL",
        }

        if self.true_risk_class not in allowed_risk_classes:
            raise ValueError(
                "true_risk_class doit être NORMAL, WARNING ou CRITICAL."
            )


    # =====================================================
    # CONVERSIONS
    # =====================================================

    @property
    def speed_kmh(self):

        return self.speed_mps * 3.6


    # =====================================================
    # EXPORT
    # =====================================================

    def to_dict(self):

        return {
            "event_id":
                self.event_id,

            "bike_id":
                self.bike_id,

            "trip_id":
                self.trip_id,

            "timestamp":
                self.timestamp,

            "origin_station_id":
                self.origin_station_id,

            "destination_station_id":
                self.destination_station_id,

            "distance_travelled_m":
                self.distance_travelled_m,

            "remaining_distance_m":
                self.remaining_distance_m,

            "trip_progress_percent":
                self.trip_progress_percent,

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "speed_mps":
                self.speed_mps,

            "speed_kmh":
                self.speed_kmh,

            "acceleration_mps2":
                self.acceleration_mps2,

            "slope_percent":
                self.slope_percent,

            "battery_soc":
                self.battery_soc,

            "initial_soc":
                self.initial_soc,

            "final_soc":
                self.final_soc,

            "mechanical_power_w":
                self.mechanical_power_w,

            "battery_power_w":
                self.battery_power_w,

            "energy_consumed_wh":
                self.energy_consumed_wh,

            "battery_temperature_c":
                self.battery_temperature_c,

            "ambient_temperature_c":
                self.ambient_temperature_c,

            "traffic_factor":
                self.traffic_factor,

            "operational_status":
                self.operational_status,

            "true_health_index":
                self.true_health_index,

            "true_risk_class":
                self.true_risk_class,
        }