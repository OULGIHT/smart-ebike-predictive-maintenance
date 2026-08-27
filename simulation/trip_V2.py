from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DigitalTwinTrip:

    trip_id: str
    bike_id: str

    origin_station_id: str
    destination_station_id: str

    planned_distance_m: float

    start_time: datetime

    # -----------------------------------------------------
    # ETAT DU TRAJET
    # -----------------------------------------------------

    travelled_distance_m: float = 0.0

    initial_battery_soc: float = 100.0
    final_battery_soc: Optional[float] = None

    total_energy_consumed_wh: float = 0.0

    end_time: Optional[datetime] = None

    status: str = "ACTIVE"


    def __post_init__(self):

        if (
            self.origin_station_id
            == self.destination_station_id
        ):
            raise ValueError(
                "La station de départ et la destination "
                "doivent être différentes."
            )

        if self.planned_distance_m <= 0:
            raise ValueError(
                "La distance prévue doit être positive."
            )

        if not 0 <= self.initial_battery_soc <= 100:
            raise ValueError(
                "initial_battery_soc doit être compris "
                "entre 0 et 100."
            )


    # =====================================================
    # PROGRESSION
    # =====================================================

    @property
    def remaining_distance_m(self):

        return max(
            0.0,
            self.planned_distance_m
            - self.travelled_distance_m
        )


    @property
    def progress_percent(self):

        progress = (
            self.travelled_distance_m
            / self.planned_distance_m
        ) * 100

        return min(100.0, progress)


    @property
    def is_finished(self):

        return (
            self.travelled_distance_m
            >= self.planned_distance_m
        )


    # =====================================================
    # MISE A JOUR
    # =====================================================

    def update(
        self,
        distance_m,
        energy_consumed_wh
    ):

        if self.status != "ACTIVE":
            raise ValueError(
                "Impossible de modifier un trajet terminé."
            )

        if distance_m < 0:
            raise ValueError(
                "distance_m ne peut pas être négatif."
            )

        if energy_consumed_wh < 0:
            raise ValueError(
                "energy_consumed_wh ne peut pas être négatif."
            )

        self.travelled_distance_m += distance_m

        self.total_energy_consumed_wh += (
            energy_consumed_wh
        )

        if self.travelled_distance_m > self.planned_distance_m:
            self.travelled_distance_m = (
                self.planned_distance_m
            )


    # =====================================================
    # FIN DU TRAJET
    # =====================================================

    def finish(
        self,
        final_battery_soc,
        end_time=None
    ):

        if not 0 <= final_battery_soc <= 100:
            raise ValueError(
                "final_battery_soc doit être compris "
                "entre 0 et 100."
            )

        self.travelled_distance_m = (
            self.planned_distance_m
        )

        self.final_battery_soc = (
            final_battery_soc
        )

        self.end_time = (
            end_time
            if end_time is not None
            else datetime.now()
        )

        self.status = "COMPLETED"


    # =====================================================
    # DUREE
    # =====================================================

    @property
    def duration_seconds(self):

        if self.end_time is None:
            return None

        return (
            self.end_time
            - self.start_time
        ).total_seconds()


    # =====================================================
    # EXPORT
    # =====================================================

    def to_dict(self):

        return {
            "trip_id":
                self.trip_id,

            "bike_id":
                self.bike_id,

            "origin_station_id":
                self.origin_station_id,

            "destination_station_id":
                self.destination_station_id,

            "planned_distance_m":
                self.planned_distance_m,

            "travelled_distance_m":
                self.travelled_distance_m,

            "remaining_distance_m":
                self.remaining_distance_m,

            "progress_percent":
                self.progress_percent,

            "initial_battery_soc":
                self.initial_battery_soc,

            "final_battery_soc":
                self.final_battery_soc,

            "total_energy_consumed_wh":
                self.total_energy_consumed_wh,

            "start_time":
                self.start_time,

            "end_time":
                self.end_time,

            "duration_seconds":
                self.duration_seconds,

            "status":
                self.status
        }