from dataclasses import dataclass
from typing import Optional


@dataclass
class DigitalTwinBike:
    bike_id: str

    # -----------------------------------------------------
    # PARAMETRES PHYSIQUES
    # -----------------------------------------------------

    mass_kg: float
    battery_capacity_wh: float
    drivetrain_efficiency: float

    # -----------------------------------------------------
    # ETAT COURANT
    # -----------------------------------------------------

    speed_mps: float = 0.0
    acceleration_mps2: float = 0.0

    battery_soc: float = 100.0
    battery_temperature_c: float = 22.0

    distance_travelled_m: float = 0.0

    # -----------------------------------------------------
    # LOCALISATION / TRAJET
    # -----------------------------------------------------

    current_station_id: Optional[str] = None

    origin_station_id: Optional[str] = None
    destination_station_id: Optional[str] = None

    active_trip_id: Optional[str] = None

    # -----------------------------------------------------
    # ETAT OPERATIONNEL
    # -----------------------------------------------------

    status: str = "AVAILABLE"

    # -----------------------------------------------------
    # ETAT LATENT DE SANTE
    # -----------------------------------------------------

    health_index: float = 0.0


    def __post_init__(self):

        if self.mass_kg <= 0:
            raise ValueError(
                "La masse du vélo doit être positive."
            )

        if self.battery_capacity_wh <= 0:
            raise ValueError(
                "La capacité batterie doit être positive."
            )

        if not 0 < self.drivetrain_efficiency <= 1:
            raise ValueError(
                "Le rendement doit être compris entre 0 et 1."
            )

        if not 0 <= self.battery_soc <= 100:
            raise ValueError(
                "battery_soc doit être compris entre 0 et 100."
            )

        if not 0 <= self.health_index <= 1:
            raise ValueError(
                "health_index doit être compris entre 0 et 1."
            )


    # =====================================================
    # CONVERSIONS
    # =====================================================

    @property
    def speed_kmh(self):

        return self.speed_mps * 3.6


    @property
    def remaining_energy_wh(self):

        return (
            self.battery_capacity_wh
            * self.battery_soc
            / 100
        )


    # =====================================================
    # TRAJET
    # =====================================================

    def start_trip(
        self,
        trip_id,
        origin_station_id,
        destination_station_id
    ):

        if self.status not in {
            "AVAILABLE",
            "STOPPED"
        }:

            raise ValueError(
                f"Le vélo {self.bike_id} "
                f"ne peut pas démarrer un trajet "
                f"depuis l'état {self.status}."
            )

        self.active_trip_id = trip_id

        self.origin_station_id = (
            origin_station_id
        )

        self.destination_station_id = (
            destination_station_id
        )

        self.current_station_id = None

        self.status = "RIDING"

        self.distance_travelled_m = 0.0


    def finish_trip(self):

        if self.destination_station_id is None:

            raise ValueError(
                "Aucune destination définie."
            )

        self.current_station_id = (
            self.destination_station_id
        )

        self.origin_station_id = None
        self.destination_station_id = None

        self.active_trip_id = None

        self.speed_mps = 0.0
        self.acceleration_mps2 = 0.0

        self.status = "AVAILABLE"


    # =====================================================
    # BATTERIE
    # =====================================================

    def consume_energy(
        self,
        energy_wh
    ):

        if energy_wh < 0:
            raise ValueError(
                "energy_wh ne peut pas être négatif."
            )

        remaining_wh = max(
            0.0,
            self.remaining_energy_wh
            - energy_wh
        )

        self.battery_soc = (
            100
            * remaining_wh
            / self.battery_capacity_wh
        )


    # =====================================================
    # ETAT
    # =====================================================

    def to_dict(self):

        return {
            "bike_id": self.bike_id,

            "mass_kg": self.mass_kg,

            "battery_capacity_wh":
                self.battery_capacity_wh,

            "drivetrain_efficiency":
                self.drivetrain_efficiency,

            "speed_mps":
                self.speed_mps,

            "speed_kmh":
                self.speed_kmh,

            "acceleration_mps2":
                self.acceleration_mps2,

            "battery_soc":
                self.battery_soc,

            "battery_temperature_c":
                self.battery_temperature_c,

            "distance_travelled_m":
                self.distance_travelled_m,

            "current_station_id":
                self.current_station_id,

            "origin_station_id":
                self.origin_station_id,

            "destination_station_id":
                self.destination_station_id,

            "active_trip_id":
                self.active_trip_id,

            "status":
                self.status,

            "health_index":
                self.health_index
        }