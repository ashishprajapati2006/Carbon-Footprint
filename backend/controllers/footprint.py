"""
Footprint Controller — Carbon Footprint Tracking & Simulation.

Orchestrates the user's carbon footprint logging workflow:
  - Accepts per-category emission data (energy, transport, food, waste)
  - Calculates category-level CO2 using EPA/IPCC emission factors
  - Persists carbon logs to MongoDB for trend analysis
  - Awards gamification points to incentivize regular tracking
  - Runs lifestyle scenario simulations to project potential CO2 reductions

Aligned with the core sustainability goal: empowering users to understand
and reduce their personal carbon footprint.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId

from services.carbon_calc import CarbonCalculatorService
from services.gamification_svc import GamificationService
from ml.predictor import EmissionPredictionService
from repositories.footprint import FootprintRepository
from schemas.footprint import FootprintLogCreate, FootprintLogResponse, SimulationRequest, SimulationResponse

logger = logging.getLogger("ecopilot.footprint")


class FootprintController:
    @staticmethod
    def _calculate_categories_and_co2(log_data: FootprintLogCreate) -> tuple[dict[str, Any], float]:
        """Calculates carbon footprint for active categories and accumulates total CO2."""
        total_co2 = 0.0
        categories = {}

        if log_data.energy:
            energy_co2 = CarbonCalculatorService.calculate_energy(log_data.energy.kwh)
            categories["energy"] = {"kwh": log_data.energy.kwh, "co2_kg": energy_co2}
            total_co2 += energy_co2

        if log_data.transport:
            trans_co2 = CarbonCalculatorService.calculate_transport(log_data.transport.distance_km, log_data.transport.mode)
            categories["transport"] = {
                "mode": log_data.transport.mode,
                "distance_km": log_data.transport.distance_km,
                "co2_kg": trans_co2
            }
            total_co2 += trans_co2

        if log_data.food:
            food_co2 = CarbonCalculatorService.calculate_food(log_data.food.diet_type)
            categories["food"] = {"diet_type": log_data.food.diet_type, "co2_kg": food_co2}
            total_co2 += food_co2

        if log_data.waste:
            waste_co2 = CarbonCalculatorService.calculate_waste(log_data.waste.waste_weight_kg, log_data.waste.recycled)
            categories["waste"] = {
                "waste_weight_kg": log_data.waste.waste_weight_kg,
                "recycled": log_data.waste.recycled,
                "co2_kg": waste_co2
            }
            total_co2 += waste_co2

        return categories, total_co2

    @staticmethod
    async def log_footprint(log_data: FootprintLogCreate, db: Any, current_user: dict) -> FootprintLogResponse:
        repo = FootprintRepository(db)
        categories, total_co2 = FootprintController._calculate_categories_and_co2(log_data)

        log_entry = {
            "user_id": ObjectId(current_user["id"]),
            "date": log_data.date or datetime.now(timezone.utc),
            "categories": categories,
            "total_co2_kg": round(total_co2, 2)
        }

        inserted_id = await repo.log_footprint(log_entry)
        log_entry["_id"] = inserted_id
        log_entry["user_id"] = str(log_entry["user_id"])

        try:
            await GamificationService.award_points(current_user["id"], "daily_tracking", db)
        except Exception as e:
            logger.error("Failed to award daily tracking points: %s", e)

        return FootprintLogResponse(**log_entry)

    @staticmethod
    async def get_history(db: Any, current_user: dict) -> list:
        repo = FootprintRepository(db)
        return await repo.get_history(current_user["id"])

    @staticmethod
    async def predict_trends(db: Any, current_user: dict) -> list:
        predictor = EmissionPredictionService(db)
        return await predictor.predict_future_trend(current_user["id"], months_ahead=6)

    @staticmethod
    def _get_current_co2(logs: list) -> float:
        """Calculates current average CO2 from logs, or returns default baseline."""
        if logs:
            total = sum(log["total_co2_kg"] for log in logs)
            return total / len(logs)
        return 450.0

    @staticmethod
    def _simulate_changes(sim_data: SimulationRequest, current_co2: float) -> tuple[float, list[str]]:
        """Simulates carbon offset values based on requested lifestyle changes."""
        projected_co2 = current_co2
        recs = []

        if sim_data.change_transport_mode:
            old_transport = CarbonCalculatorService.calculate_transport(25, "petrol")
            new_transport = CarbonCalculatorService.calculate_transport(25, sim_data.change_transport_mode)
            diff = old_transport - new_transport
            projected_co2 -= (diff * 30)
            recs.append(f"Changing commute to {sim_data.change_transport_mode} reduces transport footprint.")

        if sim_data.diet_change:
            old_food = CarbonCalculatorService.calculate_food("omnivore")
            new_food = CarbonCalculatorService.calculate_food(sim_data.diet_change)
            diff = old_food - new_food
            projected_co2 -= (diff * 30)
            recs.append(f"Transitioning to a {sim_data.diet_change} diet reduces culinary footprint.")

        if sim_data.solar_installation:
            energy_co2 = CarbonCalculatorService.calculate_energy(350.0)
            offset = energy_co2 * 0.80
            projected_co2 -= offset
            recs.append("Solar installation will offset approximately 80% of residential energy draw.")

        return max(projected_co2, 0.0), recs

    @staticmethod
    async def run_lifestyle_simulation(sim_data: SimulationRequest, db: Any, current_user: dict) -> SimulationResponse:
        repo = FootprintRepository(db)
        logs = await repo.get_history(current_user["id"], limit=100)
        current_co2 = FootprintController._get_current_co2(logs)
        projected_co2, recs = FootprintController._simulate_changes(sim_data, current_co2)
        
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

