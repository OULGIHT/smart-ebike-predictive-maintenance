import random
from dataclasses import dataclass


# ============================================================
# ETAT DE SANTE
# ============================================================

@dataclass
class HealthStateV2:

    health_index: float

    capacity_factor: float
    efficiency_factor: float
    thermal_factor: float
    resistance_factor: float

    profile: str


# ============================================================
# MOTEUR DE DEGRADATION
# ============================================================

class HealthDegradationV2:
    """
    Modèle temporel simplifié de vieillissement d'un vélo électrique.

    Convention :

        health_index = 0.0  -> excellent état
        health_index = 1.0  -> état extrêmement dégradé

    L'évolution dépend de :

        - temps
        - puissance batterie
        - température
        - profondeur de décharge
        - accélérations
        - trafic
        - pente
        - profil de vieillissement

    IMPORTANT :
    Ce modèle simule un état latent de santé.
    Il ne constitue PAS directement la cible ML.
    """

    PROFILES = {

        "HEALTHY": {
            "initial_range": (0.03, 0.12),
            "aging_rate": 0.20,
            "thermal_sensitivity": 0.40,
            "power_sensitivity": 0.40,
        },

        "SLOW_DEGRADATION": {
            "initial_range": (0.10, 0.25),
            "aging_rate": 0.70,
            "thermal_sensitivity": 0.70,
            "power_sensitivity": 0.70,
        },

        "BATTERY_DEGRADATION": {
            "initial_range": (0.20, 0.40),
            "aging_rate": 1.10,
            "thermal_sensitivity": 0.80,
            "power_sensitivity": 1.40,
        },

        "THERMAL_DEGRADATION": {
            "initial_range": (0.20, 0.40),
            "aging_rate": 1.20,
            "thermal_sensitivity": 1.70,
            "power_sensitivity": 0.80,
        },

        "SEVERE_DEGRADATION": {
            "initial_range": (0.45, 0.68),
            "aging_rate": 1.80,
            "thermal_sensitivity": 1.50,
            "power_sensitivity": 1.50,
        },
    }


    def __init__(
        self,
        profile="HEALTHY",
        seed=None
    ):

        if profile not in self.PROFILES:

            raise ValueError(
                f"Profil inconnu : {profile}"
            )

        self.profile = profile

        self.parameters = (
            self.PROFILES[profile]
        )

        self.rng = random.Random(seed)

        low, high = (
            self.parameters[
                "initial_range"
            ]
        )

        self.health_index = (
            self.rng.uniform(
                low,
                high
            )
        )

        # ----------------------------------------------------
        # Vieillissement historique équivalent
        # ----------------------------------------------------

        self.equivalent_age_hours = (
            self.health_index * 2500.0
        )


    # ========================================================
    # OUTILS
    # ========================================================

    @staticmethod
    def clamp(
        value,
        minimum,
        maximum
    ):

        return max(
            minimum,
            min(
                value,
                maximum
            )
        )


    # ========================================================
    # STRESS THERMIQUE
    # ========================================================

    def thermal_stress(
        self,
        temperature_c
    ):

        if temperature_c <= 30.0:

            return 0.0

        if temperature_c <= 40.0:

            return (
                temperature_c - 30.0
            ) / 10.0

        return (
            1.0
            +
            0.15
            *
            (
                temperature_c - 40.0
            )
        )


    # ========================================================
    # STRESS PUISSANCE
    # ========================================================

    def power_stress(
        self,
        battery_power_w
    ):

        power = abs(
            battery_power_w
        )

        # Pas de stress significatif
        # sous environ 100 W.

        if power <= 100.0:

            return 0.0

        return self.clamp(
            (
                power - 100.0
            )
            / 400.0,
            0.0,
            2.0
        )


    # ========================================================
    # STRESS SOC
    # ========================================================

    def soc_stress(
        self,
        battery_soc
    ):

        if battery_soc >= 30.0:

            return 0.0

        return self.clamp(
            (
                30.0
                -
                battery_soc
            )
            / 30.0,
            0.0,
            1.0
        )


    # ========================================================
    # STRESS DYNAMIQUE
    # ========================================================

    def dynamic_stress(
        self,
        acceleration_mps2,
        slope_percent,
        traffic_factor
    ):

        acceleration_component = (
            min(
                abs(
                    acceleration_mps2
                )
                / 1.5,
                1.0
            )
        )

        slope_component = (
            min(
                abs(
                    slope_percent
                )
                / 8.0,
                1.0
            )
        )

        traffic_component = (
            self.clamp(
                traffic_factor - 1.0,
                0.0,
                1.0
            )
        )

        return (
            0.45
            *
            acceleration_component
            +
            0.35
            *
            slope_component
            +
            0.20
            *
            traffic_component
        )


    # ========================================================
    # EVOLUTION TEMPORELLE
    # ========================================================

    def update(
        self,
        dt_seconds,
        battery_power_w,
        battery_temperature_c,
        battery_soc,
        acceleration_mps2,
        slope_percent,
        traffic_factor
    ):

        dt_hours = (
            dt_seconds
            / 3600.0
        )


        # ----------------------------------------------------
        # Contraintes
        # ----------------------------------------------------

        thermal = (
            self.thermal_stress(
                battery_temperature_c
            )
        )

        power = (
            self.power_stress(
                battery_power_w
            )
        )

        soc = (
            self.soc_stress(
                battery_soc
            )
        )

        dynamic = (
            self.dynamic_stress(
                acceleration_mps2,
                slope_percent,
                traffic_factor
            )
        )


        # ----------------------------------------------------
        # Stress total
        # ----------------------------------------------------

        total_stress = (

            1.0

            +

            self.parameters[
                "thermal_sensitivity"
            ]
            *
            thermal

            +

            self.parameters[
                "power_sensitivity"
            ]
            *
            power

            +

            0.60
            *
            soc

            +

            0.40
            *
            dynamic
        )


        # ----------------------------------------------------
        # Age équivalent
        # ----------------------------------------------------

        age_increment = (

            dt_hours

            *

            self.parameters[
                "aging_rate"
            ]

            *

            total_stress
        )


        self.equivalent_age_hours += (
            age_increment
        )


        # ----------------------------------------------------
        # Conversion âge -> health_index
        #
        # Ce coefficient est volontairement accéléré :
        # nous simulons des mois/années d'usure sans attendre
        # réellement plusieurs milliers d'heures.
        # ----------------------------------------------------

        degradation_increment = (

            age_increment
            / 2500.0
        )


        self.health_index += (
            degradation_increment
        )


        self.health_index = (
            self.clamp(
                self.health_index,
                0.0,
                0.98
            )
        )


        return self.get_state()


    # ========================================================
    # IMPACT PHYSIQUE DE LA DEGRADATION
    # ========================================================

    def get_state(
        self
    ):

        h = self.health_index


        # Capacité réellement disponible
        capacity_factor = (
            1.0
            -
            0.35
            *
            h
        )


        # Rendement énergétique
        efficiency_factor = (
            1.0
            -
            0.18
            *
            h
        )


        # Echauffement
        thermal_factor = (
            1.0
            +
            0.65
            *
            h
        )


        # Résistance interne équivalente
        resistance_factor = (
            1.0
            +
            1.20
            *
            h
        )


        return HealthStateV2(

            health_index=
                h,

            capacity_factor=
                capacity_factor,

            efficiency_factor=
                efficiency_factor,

            thermal_factor=
                thermal_factor,

            resistance_factor=
                resistance_factor,

            profile=
                self.profile
        )