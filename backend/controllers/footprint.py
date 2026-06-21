from datetime import datetime, timezone
from bson import ObjectId

from services.carbon_calc import CarbonCalculatorService
from services.gamification_svc import GamificationService
from ml.predictor import EmissionPredictionService
from repositories.footprint import FootprintRepository
from schemas.footprint import FootprintLogCreate, FootprintLogResponse, SimulationRequest, SimulationResponse

class FootprintController:
    @staticmethod
    async def log_footprint(log_data: FootprintLogCreate, db, current_user: dict) -> FootprintLogResponse:
        repo = FootprintRepository(db)
        total_co2 = 0.0
        categories = {}

        # 1. Energy
        if log_data.energy:
            energy_co2 = CarbonCalculatorService.calculate_energy(log_data.energy.kwh)
            categories["energy"] = {"kwh": log_data.energy.kwh, "co2_kg": energy_co2}
            total_co2 += energy_co2

        # 2. Transport
        if log_data.transport:
            trans_co2 = CarbonCalculatorService.calculate_transport(log_data.transport.distance_km, log_data.transport.mode)
            categories["transport"] = {
                "mode": log_data.transport.mode,
                "distance_km": log_data.transport.distance_km,
                "co2_kg": trans_co2
            }
            total_co2 += trans_co2

        # 3. Food
        if log_data.food:
            food_co2 = CarbonCalculatorService.calculate_food(log_data.food.diet_type)
            categories["food"] = {"diet_type": log_data.food.diet_type, "co2_kg": food_co2}
            total_co2 += food_co2

        # 4. Waste
        if log_data.waste:
            waste_co2 = CarbonCalculatorService.calculate_waste(log_data.waste.waste_weight_kg, log_data.waste.recycled)
            categories["waste"] = {
                "waste_weight_kg": log_data.waste.waste_weight_kg,
                "recycled": log_data.waste.recycled,
                "co2_kg": waste_co2
            }
            total_co2 += waste_co2

        log_entry = {
            "user_id": ObjectId(current_user["id"]),
            "date": log_data.date or datetime.now(timezone.utc),
            "categories": categories,
            "total_co2_kg": round(total_co2, 2)
        }

        inserted_id = await repo.log_footprint(log_entry)
        log_entry["_id"] = inserted_id
        log_entry["user_id"] = str(log_entry["user_id"])

        # Award points for daily tracking
        try:
            await GamificationService.award_points(current_user["id"], "daily_tracking", db)
        except Exception as e:
            import logging
            logging.getLogger("ecopilot.footprint").error(f"Failed to award daily tracking points: {e}")

        return FootprintLogResponse(**log_entry)

    @staticmethod
    async def get_history(db, current_user: dict) -> list:
        repo = FootprintRepository(db)
        return await repo.get_history(current_user["id"])

    @staticmethod
    async def predict_trends(db, current_user: dict) -> list:
        predictor = EmissionPredictionService(db)
        return await predictor.predict_future_trend(current_user["id"], months_ahead=6)

    @staticmethod
    async def run_lifestyle_simulation(sim_data: SimulationRequest, db, current_user: dict) -> SimulationResponse:
        repo = FootprintRepository(db)
        # Find user's last logged footprint or assign default
        logs = await repo.get_history(current_user["id"], limit=100)
        
        if logs:
            total = sum(log["total_co2_kg"] for log in logs)
            current_co2 = total / len(logs)
        else:
            current_co2 = 450.0

        projected_co2 = current_co2
        recs = []

        # Simulate changes
        # 1. Transport Swap
        if sim_data.change_transport_mode:
            old_transport = CarbonCalculatorService.calculate_transport(25, "petrol")
            new_transport = CarbonCalculatorService.calculate_transport(25, sim_data.change_transport_mode)
            diff = old_transport - new_transport
            projected_co2 -= (diff * 30)  # monthly savings
            recs.append(f"Changing commute to {sim_data.change_transport_mode} reduces transport footprint.")

        # 2. Diet shift
        if sim_data.diet_change:
            old_food = CarbonCalculatorService.calculate_food("omnivore")
            new_food = CarbonCalculatorService.calculate_food(sim_data.diet_change)
            diff = old_food - new_food
            projected_co2 -= (diff * 30)
            recs.append(f"Transitioning to a {sim_data.diet_change} diet reduces culinary footprint.")

        # 3. Solar Installation
        if sim_data.solar_installation:
            energy_co2 = CarbonCalculatorService.calculate_energy(350.0)
            offset = energy_co2 * 0.80
            projected_co2 -= offset
            recs.append("Solar installation will offset approximately 80% of residential energy draw.")

        projected_co2 = max(projected_co2, 0.0)
        
        saving_pct = 0.0
        if current_co2 > 0:
            saving_pct = round(((current_co2 - projected_co2) / current_co2) * 100, 2)
            saving_pct = max(saving_pct, 0.0)

        return SimulationResponse(
            original_co2_kg=round(current_co2, 2),
            projected_co2_kg=round(projected_co2, 2),
            potential_saving_percentage=saving_pct,
            recommendations=recs
        )
