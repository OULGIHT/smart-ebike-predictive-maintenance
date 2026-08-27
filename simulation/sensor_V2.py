from dataclasses import dataclass
import random


@dataclass
class DigitalTwinSensor:
    """
    Représente les caractéristiques des capteurs embarqués.

    Les valeurs physiques réelles appartiennent au Digital Twin.
    Le capteur transforme ces valeurs en mesures observées avec
    une petite erreur de mesure.
    """

    # -----------------------------------------------------
    # ECARTS-TYPES DU BRUIT DE MESURE
    # -----------------------------------------------------

    speed_noise_std_mps: float = 0.08
    acceleration_noise_std_mps2: float = 0.04
    battery_noise_std_percent: float = 0.15
    temperature_noise_std_c: float = 0.10

    # -----------------------------------------------------
    # BIAIS DES CAPTEURS
    # -----------------------------------------------------

    speed_bias_mps: float = 0.0
    acceleration_bias_mps2: float = 0.0
    battery_bias_percent: float = 0.0
    temperature_bias_c: float = 0.0

    def __post_init__(self):

        if self.speed_noise_std_mps < 0:
            raise ValueError(
                "speed_noise_std_mps doit être positif ou nul."
            )

        if self.acceleration_noise_std_mps2 < 0:
            raise ValueError(
                "acceleration_noise_std_mps2 doit être positif ou nul."
            )

        if self.battery_noise_std_percent < 0:
            raise ValueError(
                "battery_noise_std_percent doit être positif ou nul."
            )

        if self.temperature_noise_std_c < 0:
            raise ValueError(
                "temperature_noise_std_c doit être positif ou nul."
            )

    # =====================================================
    # OUTIL
    # =====================================================

    @staticmethod
    def _clamp(value, minimum, maximum):

        return max(
            minimum,
            min(value, maximum)
        )

    # =====================================================
    # MESURE DE LA VITESSE
    # =====================================================

    def measure_speed(self, true_speed_mps):

        measured = (
            true_speed_mps
            + self.speed_bias_mps
            + random.gauss(
                0,
                self.speed_noise_std_mps
            )
        )

        return max(0.0, measured)

    # =====================================================
    # MESURE DE L'ACCELERATION
    # =====================================================

    def measure_acceleration(
        self,
        true_acceleration_mps2
    ):

        return (
            true_acceleration_mps2
            + self.acceleration_bias_mps2
            + random.gauss(
                0,
                self.acceleration_noise_std_mps2
            )
        )

    # =====================================================
    # MESURE BATTERIE
    # =====================================================

    def measure_battery_soc(
        self,
        true_battery_soc
    ):

        measured = (
            true_battery_soc
            + self.battery_bias_percent
            + random.gauss(
                0,
                self.battery_noise_std_percent
            )
        )

        return self._clamp(
            measured,
            0.0,
            100.0
        )

    # =====================================================
    # MESURE TEMPERATURE
    # =====================================================

    def measure_temperature(
        self,
        true_temperature_c
    ):

        return (
            true_temperature_c
            + self.temperature_bias_c
            + random.gauss(
                0,
                self.temperature_noise_std_c
            )
        )

    # =====================================================
    # MESURE COMPLETE
    # =====================================================

    def measure(
        self,
        true_speed_mps,
        true_acceleration_mps2,
        true_battery_soc,
        true_temperature_c
    ):

        return {
            "speed_mps":
                self.measure_speed(
                    true_speed_mps
                ),

            "acceleration_mps2":
                self.measure_acceleration(
                    true_acceleration_mps2
                ),

            "battery_soc":
                self.measure_battery_soc(
                    true_battery_soc
                ),

            "battery_temperature_c":
                self.measure_temperature(
                    true_temperature_c
                )
        }