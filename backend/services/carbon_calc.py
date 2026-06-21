class CarbonCalculatorService:
    """
    Computes emissions in kg of CO2 equivalent based on user lifestyle metrics.
    Coefficients are based on Greenhouse Gas Protocol standards.
    """

    @staticmethod
    def calculate_energy(kwh: float) -> float:
        # Average global grid emission factor: ~0.4 kg CO2e per kWh
        return kwh * 0.40

    @staticmethod
    def calculate_transport(distance_km: float, vehicle_type: str) -> float:
        # Transport emission coefficients in kg CO2 per km
        factors = {
            "ev": 0.05,
            "petrol": 0.18,
            "diesel": 0.20,
            "public": 0.04,  # Bus or Train average
            "flight": 0.25,  # Per passenger km
            "bicycle": 0.0,
            "none": 0.0
        }
        factor = factors.get(vehicle_type.lower(), 0.0)
        return distance_km * factor

    @staticmethod
    def calculate_food(diet_type: str, days: float = 1.0) -> float:
        # Food footprint estimates in kg CO2 per day
        factors = {
            "vegan": 2.0,
            "vegetarian": 3.5,
            "omnivore": 5.0,
            "high_meat": 8.0
        }
        factor = factors.get(diet_type.lower(), 5.0)
        return factor * days

    @staticmethod
    def calculate_waste(weight_kg: float, recycled: bool) -> float:
        # Waste footprint estimates in kg CO2 per kg
        factor = 0.10 if recycled else 0.50
        return weight_kg * factor
