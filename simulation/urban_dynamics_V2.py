
import math
import random


class UrbanDynamicsV2:
    """
    Modèle de dynamique urbaine temporelle pour le Digital Twin.

    Objectifs :
    - trafic évoluant progressivement ;
    - pente locale continue ;
    - feux rouges moins fréquents ;
    - freinage puis arrêt puis redémarrage ;
    - reproductibilité grâce au seed.
    """

    def __init__(
        self,
        seed=42,
        traffic_memory=0.92,
        slope_memory=0.96,
        traffic_noise_std=0.025,
        slope_noise_std=0.08,
        red_light_rate_per_second=0.0015,
        min_stop_seconds=10.0,
        max_stop_seconds=25.0
    ):

        self.rng = random.Random(seed)

        # ---------------------------------------------
        # Mémoire temporelle
        # ---------------------------------------------

        self.traffic_memory = traffic_memory
        self.slope_memory = slope_memory

        self.traffic_noise_std = traffic_noise_std
        self.slope_noise_std = slope_noise_std

        # ---------------------------------------------
        # Feux rouges
        # ---------------------------------------------

        self.red_light_rate_per_second = (
            red_light_rate_per_second
        )

        self.min_stop_seconds = min_stop_seconds
        self.max_stop_seconds = max_stop_seconds

        # ---------------------------------------------
        # Etats dynamiques
        # ---------------------------------------------

        self.current_traffic_factor = None
        self.current_slope_percent = None

        self.driving_state = "CRUISING"

        self.stop_remaining_seconds = 0.0

        # Empêche d'avoir immédiatement un autre feu
        # après le redémarrage.
        self.red_light_cooldown_seconds = 0.0


    # =====================================================
    # UTILITAIRE
    # =====================================================

    @staticmethod
    def clamp(value, minimum, maximum):

        return max(
            minimum,
            min(value, maximum)
        )


    # =====================================================
    # HEURE / TRAFIC
    # =====================================================

    def compute_time_factor(
        self,
        simulation_hour
    ):

        if (
            7 <= simulation_hour < 10
            or
            16 <= simulation_hour < 19
        ):
            return 1.20

        if (
            simulation_hour < 6
            or
            simulation_hour >= 22
        ):
            return 0.80

        return 1.00


    # =====================================================
    # TRAFIC TEMPOREL LISSE
    # =====================================================

    def update_traffic(
        self,
        base_traffic_factor,
        simulation_hour
    ):

        target = (
            base_traffic_factor
            * self.compute_time_factor(
                simulation_hour
            )
        )

        target = self.clamp(
            target,
            0.65,
            1.80
        )

        if self.current_traffic_factor is None:

            self.current_traffic_factor = target

        noise = self.rng.gauss(
            0.0,
            self.traffic_noise_std
        )

        self.current_traffic_factor = (
            self.traffic_memory
            * self.current_traffic_factor
            +
            (1.0 - self.traffic_memory)
            * target
            +
            noise
        )

        self.current_traffic_factor = self.clamp(
            self.current_traffic_factor,
            0.65,
            1.80
        )

        return self.current_traffic_factor


    # =====================================================
    # PENTE TEMPORELLE LISSE
    # =====================================================

    def update_slope(
        self,
        average_slope_percent
    ):

        if self.current_slope_percent is None:

            self.current_slope_percent = (
                average_slope_percent
            )

        noise = self.rng.gauss(
            0.0,
            self.slope_noise_std
        )

        self.current_slope_percent = (
            self.slope_memory
            * self.current_slope_percent
            +
            (1.0 - self.slope_memory)
            * average_slope_percent
            +
            noise
        )

        self.current_slope_percent = self.clamp(
            self.current_slope_percent,
            -8.0,
            8.0
        )

        return self.current_slope_percent


    # =====================================================
    # NOUVEAU SEGMENT
    # =====================================================

    def start_segment(
        self,
        base_traffic_factor,
        average_slope_percent
    ):
        """
        Réinitialise doucement les états spatiaux
        lorsqu'on change de segment.
        """

        self.current_traffic_factor = (
            base_traffic_factor
        )

        self.current_slope_percent = (
            average_slope_percent
        )


    # =====================================================
    # PROBABILITE D'UN FEU
    # =====================================================

    def red_light_event(
        self,
        traffic_factor,
        dt_seconds
    ):

        if self.red_light_cooldown_seconds > 0:

            return False

        rate = (
            self.red_light_rate_per_second
            * traffic_factor
        )

        probability = (
            1.0
            - math.exp(
                -rate * dt_seconds
            )
        )

        return (
            self.rng.random()
            < probability
        )


    # =====================================================
    # DECLENCHER UN FEU
    # =====================================================

    def start_red_light(self):

        self.stop_remaining_seconds = (
            self.rng.uniform(
                self.min_stop_seconds,
                self.max_stop_seconds
            )
        )

        self.driving_state = "BRAKING"


    # =====================================================
    # VITESSE CIBLE
    # =====================================================

    def compute_target_speed(
        self,
        base_target_speed_mps,
        traffic_factor,
        slope_percent
    ):

        target_speed = (
            base_target_speed_mps
            / traffic_factor
        )

        # Pénalité montée
        target_speed -= (
            max(
                slope_percent,
                0.0
            )
            * 0.08
        )

        # Très petite variation comportementale
        target_speed += self.rng.gauss(
            0.0,
            0.08
        )

        return self.clamp(
            target_speed,
            2.5,
            7.0
        )


    # =====================================================
    # MACHINE D'ETAT
    # =====================================================

    def compute_driving_dynamics(
        self,
        current_speed_mps,
        target_speed_mps,
        traffic_factor,
        dt_seconds
    ):

        # -------------------------------------------------
        # BRAKING
        # -------------------------------------------------

        if self.driving_state == "BRAKING":

            if current_speed_mps <= 0.25:

                self.driving_state = "STOPPED"

                return (
                    -current_speed_mps
                    / max(
                        dt_seconds,
                        1e-6
                    )
                )

            braking = (
                -0.65
                - 0.10
                * min(
                    traffic_factor,
                    1.5
                )
            )

            return self.clamp(
                braking,
                -1.0,
                -0.40
            )


        # -------------------------------------------------
        # STOPPED
        # -------------------------------------------------

        if self.driving_state == "STOPPED":

            self.stop_remaining_seconds = max(
                0.0,
                self.stop_remaining_seconds
                - dt_seconds
            )

            if self.stop_remaining_seconds > 0:

                return (
                    -current_speed_mps
                    / max(
                        dt_seconds,
                        1e-6
                    )
                )

            self.driving_state = "ACCELERATING"

            self.red_light_cooldown_seconds = 45.0


        # -------------------------------------------------
        # ACCELERATING
        # -------------------------------------------------

        if self.driving_state == "ACCELERATING":

            speed_error = (
                target_speed_mps
                - current_speed_mps
            )

            acceleration = self.clamp(
                speed_error * 0.14,
                0.0,
                0.45
            )

            if (
                abs(speed_error) < 0.40
                or
                current_speed_mps
                >= target_speed_mps
            ):
                self.driving_state = "CRUISING"

            return acceleration


        # -------------------------------------------------
        # CRUISING
        # -------------------------------------------------

        speed_error = (
            target_speed_mps
            - current_speed_mps
        )

        acceleration = (
            0.08 * speed_error
            + self.rng.gauss(
                0.0,
                0.025
            )
        )

        acceleration = self.clamp(
            acceleration,
            -0.35,
            0.35
        )

        if acceleration > 0.18:

            display_state = "ACCELERATING"

        elif acceleration < -0.18:

            display_state = "BRAKING"

        else:

            display_state = "CRUISING"

        return acceleration, display_state


    # =====================================================
    # ETAPE COMPLETE
    # =====================================================

    def step(
        self,
        current_speed_mps,
        base_target_speed_mps,
        base_traffic_factor,
        average_slope_percent,
        simulation_hour,
        dt_seconds
    ):

        # Cooldown
        self.red_light_cooldown_seconds = max(
            0.0,
            self.red_light_cooldown_seconds
            - dt_seconds
        )

        # ---------------------------------------------
        # Etats continus
        # ---------------------------------------------

        traffic_factor = self.update_traffic(
            base_traffic_factor,
            simulation_hour
        )

        slope_percent = self.update_slope(
            average_slope_percent
        )

        target_speed_mps = (
            self.compute_target_speed(
                base_target_speed_mps,
                traffic_factor,
                slope_percent
            )
        )


        # ---------------------------------------------
        # Nouveau feu
        # ---------------------------------------------

        if self.driving_state == "CRUISING":

            if self.red_light_event(
                traffic_factor,
                dt_seconds
            ):

                self.start_red_light()


        # ---------------------------------------------
        # Machine d'état
        # ---------------------------------------------

        result = (
            self.compute_driving_dynamics(
                current_speed_mps,
                target_speed_mps,
                traffic_factor,
                dt_seconds
            )
        )


        # CRUISING retourne aussi un état d'affichage.
        if isinstance(result, tuple):

            acceleration_mps2 = result[0]
            display_state = result[1]

        else:

            acceleration_mps2 = result
            display_state = self.driving_state


        # Etat réellement observable
        if self.driving_state == "STOPPED":

            display_state = "STOPPED"

        elif self.driving_state == "BRAKING":

            display_state = "BRAKING"

        elif self.driving_state == "ACCELERATING":

            display_state = "ACCELERATING"


        return {
            "traffic_factor":
                traffic_factor,

            "slope_percent":
                slope_percent,

            "target_speed_mps":
                target_speed_mps,

            "acceleration_mps2":
                acceleration_mps2,

            "urban_status":
                display_state,

            "stop_remaining_seconds":
                self.stop_remaining_seconds
        }