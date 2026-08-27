import math


class PhysicsEngineV2:

    def __init__(
        self,
        air_density=1.225,
        rolling_resistance_coefficient=0.006,
        drag_area=0.55,
        gravity=9.81,
        motor_efficiency=0.85,
        thermal_capacity_j_per_c=18000.0,
        cooling_coefficient_w_per_c=1.8
    ):

        self.air_density = air_density
        self.rolling_resistance_coefficient = (
            rolling_resistance_coefficient
        )

        self.drag_area = drag_area
        self.gravity = gravity

        self.motor_efficiency = motor_efficiency

        self.thermal_capacity_j_per_c = (
            thermal_capacity_j_per_c
        )

        self.cooling_coefficient_w_per_c = (
            cooling_coefficient_w_per_c
        )


    # =====================================================
    # CINEMATIQUE
    # =====================================================

    def update_speed(
        self,
        speed_mps,
        acceleration_mps2,
        dt_seconds
    ):

        new_speed = (
            speed_mps
            + acceleration_mps2
            * dt_seconds
        )

        return max(
            0.0,
            new_speed
        )


    def compute_distance(
        self,
        speed_mps,
        acceleration_mps2,
        dt_seconds
    ):

        distance = (
            speed_mps
            * dt_seconds
            +
            0.5
            * acceleration_mps2
            * dt_seconds ** 2
        )

        return max(
            0.0,
            distance
        )


    # =====================================================
    # RESISTANCES
    # =====================================================

    def compute_resistance_power(
        self,
        mass_kg,
        speed_mps,
        slope_percent
    ):

        if speed_mps <= 0:

            return 0.0


        slope_ratio = (
            slope_percent
            / 100
        )

        theta = math.atan(
            slope_ratio
        )


        rolling_power = (
            self.rolling_resistance_coefficient
            * mass_kg
            * self.gravity
            * speed_mps
        )


        aerodynamic_power = (
            0.5
            * self.air_density
            * self.drag_area
            * speed_mps ** 3
        )


        slope_power = (
            mass_kg
            * self.gravity
            * speed_mps
            * math.sin(theta)
        )


        resistance_power = (
            rolling_power
            + aerodynamic_power
            + slope_power
        )


        return max(
            0.0,
            resistance_power
        )


    # =====================================================
    # PUISSANCE MECANIQUE
    # =====================================================

    def compute_mechanical_power(
        self,
        mass_kg,
        speed_mps,
        acceleration_mps2,
        slope_percent
    ):

        resistance_power = (
            self.compute_resistance_power(
                mass_kg=mass_kg,
                speed_mps=speed_mps,
                slope_percent=slope_percent
            )
        )


        # Si on accélère, il faut fournir
        # une puissance supplémentaire.

        if acceleration_mps2 > 0:

            acceleration_power = (
                mass_kg
                * acceleration_mps2
                * speed_mps
            )

        else:

            # Pas de récupération d'énergie
            # pour cette version.
            acceleration_power = 0.0


        mechanical_power = (
            resistance_power
            + acceleration_power
        )


        return max(
            0.0,
            mechanical_power
        )


    # =====================================================
    # BATTERIE
    # =====================================================

    def compute_effective_efficiency(
        self,
        health_index
    ):

        health_penalty = (
            1.0
            - 0.15
            * health_index
        )


        effective_efficiency = (
            self.motor_efficiency
            * health_penalty
        )


        return max(
            0.55,
            min(
                effective_efficiency,
                0.95
            )
        )


    def compute_battery_power(
        self,
        mechanical_power_w,
        health_index=0.0
    ):

        efficiency = (
            self.compute_effective_efficiency(
                health_index
            )
        )


        battery_power = (
            mechanical_power_w
            / efficiency
        )


        return max(
            0.0,
            battery_power
        )


    def compute_energy_consumed_wh(
        self,
        battery_power_w,
        dt_seconds
    ):

        return (
            battery_power_w
            * dt_seconds
            / 3600
        )


    # =====================================================
    # PERTES THERMIQUES
    # =====================================================

    def compute_power_loss(
        self,
        battery_power_w,
        mechanical_power_w
    ):

        return max(
            0.0,
            battery_power_w
            - mechanical_power_w
        )


    # =====================================================
    # TEMPERATURE
    # =====================================================

    def update_temperature(
        self,
        current_temperature_c,
        ambient_temperature_c,
        battery_power_w,
        mechanical_power_w,
        health_index,
        dt_seconds
    ):

        power_loss = (
            self.compute_power_loss(
                battery_power_w=battery_power_w,
                mechanical_power_w=mechanical_power_w
            )
        )


        # Une batterie dégradée
        # dissipe davantage de chaleur.

        degradation_factor = (
            1.0
            + 1.0
            * health_index
        )


        thermal_input_w = (
            power_loss
            * degradation_factor
        )


        cooling_w = (
            self.cooling_coefficient_w_per_c
            * (
                current_temperature_c
                - ambient_temperature_c
            )
        )


        net_heat_w = (
            thermal_input_w
            - cooling_w
        )


        temperature_change_c = (
            net_heat_w
            * dt_seconds
            / self.thermal_capacity_j_per_c
        )


        return (
            current_temperature_c
            + temperature_change_c
        )