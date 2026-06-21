class CarbonCalculatorService:
    """
    Computes emissions in kg of CO2 equivalent based on user lifestyle metrics.
    Coefficients are based on Greenhouse Gas Protocol standards.
    """
    # Average global grid emission factor: kg CO2e per kWh
    GRID_EMISSION_FACTOR = 0.40

    # Transport emission coefficients in kg CO2 per km
    TRANSPORT_FACTORS = {
        "ev": 0.05,
        "petrol": 0.18,
        "diesel": 0.20,
        "public": 0.04,  # Bus or Train average
        "flight": 0.25,  # Per passenger km
        "bicycle": 0.0,
        "none": 0.0
    }

    # Food footprint estimates in kg CO2 per day
    FOOD_FACTORS = {
        "vegan": 2.0,
        "vegetarian": 3.5,
        "omnivore": 5.0,
        "high_meat": 8.0
    }
    DEFAULT_FOOD_FACTOR = 5.0

    # Waste footprint estimates in kg CO2 per kg
    WASTE_RECYCLED_FACTOR = 0.10
    WASTE_NON_RECYCLED_FACTOR = 0.50

    @staticmethod
    def calculate_energy(kwh: float) -> float:
        return kwh * CarbonCalculatorService.GRID_EMISSION_FACTOR

    @staticmethod
    def calculate_transport(distance_km: float, vehicle_type: str) -> float:
        factor = CarbonCalculatorService.TRANSPORT_FACTORS.get(
            vehicle_type.lower(), 0.0
        )
        return distance_km * factor

    @staticmethod
    def calculate_food(diet_type: str, days: float = 1.0) -> float:
        factor = CarbonCalculatorService.FOOD_FACTORS.get(
            diet_type.lower(), CarbonCalculatorService.DEFAULT_FOOD_FACTOR
        )
        return factor * days

    @staticmethod
    def calculate_waste(weight_kg: float, recycled: bool) -> float:
        factor = (
            CarbonCalculatorService.WASTE_RECYCLED_FACTOR
            if recycled
            else CarbonCalculatorService.WASTE_NON_RECYCLED_FACTOR
        )
        return weight_kg * factor
