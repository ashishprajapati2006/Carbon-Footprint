import os
import pickle
import logging
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
import pandas as pd

from schemas.twin import TwinSimulationRequest, TwinSimulationResponse, ChartDataPoint
from ai.gemini_ai import GeminiAIService
from repositories.twin import TwinRepository

logger = logging.getLogger("ecopilot.twin")

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "carbon_predictor.pkl"
)


def load_ml_model():
    """Loads the pickled machine learning pipeline model, training it if missing."""
    if not os.path.exists(MODEL_PATH):
        logger.warning(f"Predictor pickle not found at {MODEL_PATH}. Auto-training the model...")
        try:
            from ml.train import main as train_main
            train_main()
            logger.info("Auto-training finished successfully.")
        except Exception as e:
            logger.error(f"Auto-training failed: {e}")

    if not os.path.exists(MODEL_PATH):
        logger.error(f"Predictor pickle still not found at {MODEL_PATH} after auto-training attempt.")
        return None

    try:
        with open(MODEL_PATH, "rb") as f:
            model_data = pickle.load(f)
            logger.info("Successfully loaded ML model for Carbon Twin simulation.")
            return model_data
    except Exception as e:
        logger.error(f"Error loading predictor pickle: {e}")
        return None


# Load model globally on startup (or fallback)
ML_MODEL_DATA = load_ml_model()


class TwinController:
    @staticmethod
    async def _build_sim_profile(user_id: str, repo: TwinRepository) -> dict:
        """Constructs baseline user habit profile from defaults and recent carbon logs."""
        profile = {
            'Body Type': 'normal', 'Sex': 'female', 'Diet': 'omnivore',
            'How Often Shower': 'daily', 'Heating Energy Source': 'electricity',
            'Transport': 'private', 'Vehicle Type': 'petrol', 'Social Activity': 'sometimes',
            'Monthly Grocery Bill': 150, 'Frequency of Traveling by Air': 'rarely',
            'Vehicle Monthly Distance Km': 500, 'Waste Bag Size': 'medium',
            'Waste Bag Weekly Count': 2, 'How Long TV PC Daily Hour': 4,
            'How Many New Clothes Monthly': 2, 'How Long Internet Daily Hour': 3,
            'Energy efficiency': 'Sometimes', 'Recycling': "['Paper', 'Plastic']",
            'Cooking_With': "['Stove', 'Oven']"
        }
        try:
            logs = await repo.get_user_footprint_logs(user_id, limit=20)
            if logs:
                logs.sort(key=lambda x: x.get("date", datetime.min), reverse=True)
                latest_log = logs[0]
                categories = latest_log.get("categories", {})
                if "transport" in categories:
                    t_data = categories["transport"]
                    profile['Vehicle Type'] = t_data.get("mode", "petrol")
                    profile['Vehicle Monthly Distance Km'] = int(t_data.get("distance_km", 500))
                    profile['Transport'] = 'private' if t_data.get("mode") in ["petrol", "diesel", "hybrid", "electric"] else 'public'
                if "food" in categories:
                    profile['Diet'] = categories["food"].get("diet_type", "omnivore")
                if "waste" in categories:
                    profile['Recycling'] = "['Paper', 'Plastic', 'Glass', 'Metal']" if categories["waste"].get("recycled") else "[]"
        except Exception as e:
            logger.warning(f"Error fetching user footprint logs: {e}. Using default profile baseline.")
        return profile

    @staticmethod
    def _predict_co2(profile: dict, toggles: dict) -> tuple[float, float]:
        """Calculates baseline and projected carbon footprint utilizing ML model or heuristic fallbacks."""
        global ML_MODEL_DATA
        if ML_MODEL_DATA is None:
            ML_MODEL_DATA = load_ml_model()

        baseline_co2 = 500.0
        if ML_MODEL_DATA:
            try:
                baseline_co2 = float(ML_MODEL_DATA['pipeline'].predict(pd.DataFrame([profile]))[0])
            except Exception as e:
                logger.error(f"ML baseline prediction failed: {e}")

        sim_profile = profile.copy()
        if toggles.get("buy_ev"):
            sim_profile['Vehicle Type'] = 'electric'
            sim_profile['Transport'] = 'private'
        if toggles.get("install_solar"):
            sim_profile['Heating Energy Source'] = 'electricity'
            sim_profile['Energy efficiency'] = 'Yes'
        if toggles.get("stop_flying"):
            sim_profile['Frequency of Traveling by Air'] = 'never'
        if toggles.get("reduce_ac"):
            sim_profile['How Long TV PC Daily Hour'] = max(1, sim_profile['How Long TV PC Daily Hour'] - 2)

        projected_co2 = baseline_co2
        if ML_MODEL_DATA:
            try:
                projected_co2 = float(ML_MODEL_DATA['pipeline'].predict(pd.DataFrame([sim_profile]))[0])
            except Exception as e:
                logger.error(f"ML simulated prediction failed: {e}")
                projected_co2 = TwinController._heuristic_offset(baseline_co2, toggles)
        else:
            projected_co2 = TwinController._heuristic_offset(baseline_co2, toggles)

        return baseline_co2, max(50.0, projected_co2)

    @staticmethod
    def _heuristic_offset(baseline_co2: float, toggles: dict) -> float:
        """Helper to apply deterministic heuristics when model is unavailable."""
        projected = baseline_co2
        if toggles.get("buy_ev"): projected -= 120.0
        if toggles.get("install_solar"): projected -= 80.0
        if toggles.get("stop_flying"): projected -= 100.0
        if toggles.get("reduce_ac"): projected -= 30.0
        return projected

    @staticmethod
    def _generate_seasonal_chart(baseline_co2: float, projected_co2: float, toggles: dict) -> list[ChartDataPoint]:
        """Projects 6-month seasonal chart projection points based on active offsets."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_month_idx = datetime.now().month - 1
        
        chart_data = []
        for i in range(6):
            m_idx = (current_month_idx + i) % 12
            m_name = months[m_idx]
            
            if m_idx in [5, 6, 7]:
                season_factor = 1.18
                sim_season_factor = 1.03 if (toggles.get("install_solar") or toggles.get("reduce_ac")) else 1.18
            elif m_idx in [11, 0, 1]:
                season_factor = 1.10
                sim_season_factor = 1.05 if toggles.get("install_solar") else 1.10
            else:
                season_factor = 1.0
                sim_season_factor = 1.0
                
            chart_data.append(ChartDataPoint(
                month=m_name,
                current=round(baseline_co2 * season_factor, 1),
                simulated=round(projected_co2 * sim_season_factor, 1)
            ))
        return chart_data

    @staticmethod
    async def simulate_carbon_twin(payload: TwinSimulationRequest, db: Any, current_user: dict) -> TwinSimulationResponse:
        repo = TwinRepository(db)
        profile = await TwinController._build_sim_profile(current_user["id"], repo)
        
        toggles = {
            "buy_ev": payload.buy_ev, "install_solar": payload.install_solar,
            "stop_flying": payload.stop_flying, "reduce_ac": payload.reduce_ac
        }
        baseline_co2, projected_co2 = TwinController._predict_co2(profile, toggles)
        reduction_kg = max(0.0, baseline_co2 - projected_co2)
        reduction_pct = (reduction_kg / baseline_co2) * 100 if baseline_co2 > 0 else 0.0

        gemini_svc = GeminiAIService()
        try:
            gemini_result = await gemini_svc.analyze_twin_simulation(
                original_co2=baseline_co2, projected_co2=projected_co2,
                buy_ev=payload.buy_ev, install_solar=payload.install_solar,
                stop_flying=payload.stop_flying, reduce_ac=payload.reduce_ac
            )
        except Exception as e:
            logger.error(f"Gemini twin simulation analysis failed: {e}")
            gemini_result = {
                "savings_usd_desc": "$50 - $120 / month saved on resources",
                "lifestyle_impact": "Adopting these eco-friendly adjustments drives down your carbon score significantly.",
                "top_savings_sources": ["Simulated lifestyle improvements"]
            }

        chart_data = TwinController._generate_seasonal_chart(baseline_co2, projected_co2, toggles)

        simulation_record = {
            "user_id": ObjectId(current_user["id"]),
            "simulated_at": datetime.now(timezone.utc),
            "toggles": toggles,
            "results": {
                "original_co2_kg": round(baseline_co2, 2), "projected_co2_kg": round(projected_co2, 2),
                "reduction_kg": round(reduction_kg, 2), "reduction_pct": round(reduction_pct, 2),
                "savings_usd_desc": gemini_result.get("savings_usd_desc", ""),
                "lifestyle_impact": gemini_result.get("lifestyle_impact", ""),
                "top_savings_sources": gemini_result.get("top_savings_sources", []),
                "chart_data": [{"month": d.month, "current": d.current, "simulated": d.simulated} for d in chart_data]
            }
        }
        
        try:
            simulation_id = await repo.insert_simulation(simulation_record)
        except Exception as e:
            logger.error(f"Error storing twin simulation: {e}")
            simulation_id = "temp_simulation_id"

        return TwinSimulationResponse(
            id=simulation_id, original_co2_kg=round(baseline_co2, 2),
            projected_co2_kg=round(projected_co2, 2), reduction_kg=round(reduction_kg, 2),
            reduction_pct=round(reduction_pct, 2), savings_usd_desc=gemini_result.get("savings_usd_desc", ""),
            lifestyle_impact=gemini_result.get("lifestyle_impact", ""),
            top_savings_sources=gemini_result.get("top_savings_sources", []),
            chart_data=chart_data
        )
