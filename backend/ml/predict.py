#!/usr/bin/env python3
"""
Prediction CLI for Carbon Footprint Predictor.
Loads a trained pipeline and scores input observations.
Supports:
1. JSON string of a single row or list of rows (--input-json)
2. File path (CSV or JSON) (--input-file)
3. Direct command line flags for individual features (e.g., --sex male --diet vegan)
"""

import os
import sys
import json
import pickle
import argparse
import logging
import numpy as np
import pandas as pd

# Suppress pandas future downcasting warnings
pd.set_option('future.no_silent_downcasting', True)

# Configure Logging
logging.basicConfig(
    level=logging.WARNING,  # We want prediction stdout to be clean JSON, so log info/warnings to stderr
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("predict_cli")

# Feature definitions (must match train.py)
CATEGORICAL_FEATURES = [
    'Body Type', 'Sex', 'Diet', 'How Often Shower', 
    'Heating Energy Source', 'Transport', 'Vehicle Type', 
    'Social Activity', 'Frequency of Traveling by Air', 
    'Waste Bag Size', 'Energy efficiency', 'Recycling', 'Cooking_With'
]

NUMERICAL_FEATURES = [
    'Monthly Grocery Bill', 'Vehicle Monthly Distance Km', 
    'Waste Bag Weekly Count', 'How Long TV PC Daily Hour', 
    'How Many New Clothes Monthly', 'How Long Internet Daily Hour'
]


def load_model(model_path: str) -> dict:
    """Loads the model artifact from disk."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at '{model_path}'. Please run training first.")
        
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    return model_data


def predict(pipeline, input_df: pd.DataFrame) -> list:
    """Runs predictions on input DataFrame using the loaded pipeline."""
    # Ensure all required features exist in the input DataFrame.
    # If a feature is missing, we fill it with NaN so that the pipeline's imputer handles it.
    all_features = CATEGORICAL_FEATURES + NUMERICAL_FEATURES
    for col in all_features:
        if col not in input_df.columns:
            input_df[col] = np.nan
            
    # Keep only target features in expected order
    X = input_df[all_features].copy()
    
    # Cast numerical columns to numeric types
    for col in NUMERICAL_FEATURES:
        X[col] = pd.to_numeric(X[col], errors='coerce')
        
    # Cast categorical columns to string
    for col in CATEGORICAL_FEATURES:
        X[col] = X[col].astype(str).replace('nan', np.nan).replace('None', np.nan)
        
    # Generate predictions
    predictions = pipeline.predict(X)
    return predictions.tolist()


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Predict Carbon Emissions using the trained RandomForest/XGBoost Regressor model.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "--model-path", 
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "carbon_predictor.pkl"),
        help="Path to the saved model file (default: backend/models/carbon_predictor.pkl)"
    )
    
    parser.add_argument(
        "--input-json",
        help="JSON string representing a single record or array of records.\n"
             "Example: --input-json '{\"Sex\": \"female\", \"Diet\": \"vegan\", \"Monthly Grocery Bill\": 120}'"
    )
    
    parser.add_argument(
        "--input-file",
        help="Path to a CSV or JSON file containing rows to predict."
    )
    
    # Dynamic options for direct CLI input flags
    group = parser.add_argument_group("Individual Features (Direct CLI input)")
    for feat in CATEGORICAL_FEATURES + NUMERICAL_FEATURES:
        cli_flag = "--" + feat.lower().replace(" ", "-").replace("_", "-")
        group.add_argument(cli_flag, type=str, help=f"Value for '{feat}'")
        
    return parser.parse_args()


def _prepare_df_from_json(input_json: str) -> pd.DataFrame:
    """Parses JSON string input and returns DataFrame."""
    try:
        parsed = json.loads(input_json)
        if isinstance(parsed, dict):
            return pd.DataFrame([parsed])
        elif isinstance(parsed, list):
            return pd.DataFrame(parsed)
        raise ValueError("JSON must be an object or an array of objects.")
    except Exception as e:
        print(json.dumps({"error": f"Failed to parse --input-json: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


def _prepare_df_from_file(input_file: str) -> pd.DataFrame:
    """Reads input file (CSV or JSON) and returns DataFrame."""
    try:
        if input_file.endswith('.csv'):
            return pd.read_csv(input_file)
        if input_file.endswith('.json'):
            return pd.read_json(input_file)
        try:
            return pd.read_json(input_file)
        except ValueError:
            return pd.read_csv(input_file)
    except Exception as e:
        print(json.dumps({"error": f"Failed to read file '{input_file}': {str(e)}"}), file=sys.stderr)
        sys.exit(1)


def _prepare_df_from_cli(args: Any) -> pd.DataFrame:
    """Builds input DataFrame from individual direct CLI arguments."""
    cli_inputs = {}
    has_input = False
    for feat in CATEGORICAL_FEATURES + NUMERICAL_FEATURES:
        attr_name = feat.lower().replace(" ", "_").replace("-", "_")
        val = getattr(args, attr_name, None)
        if val is not None:
            has_input = True
            cli_inputs[feat] = val
            
    if has_input:
        return pd.DataFrame([cli_inputs])
    print(json.dumps({
        "error": "No input provided. Use --input-json, --input-file, or individual feature flags (e.g. --sex male)."
    }), file=sys.stderr)
    sys.exit(1)


def _print_predictions(preds: list, input_df: pd.DataFrame, model_name: str) -> None:
    """Formats and prints predictions list to stdout in JSON format."""
    results = []
    for idx, pred in enumerate(preds):
        res = {
            "prediction_index": idx,
            "predicted_carbon_emission_co2_kg": round(pred, 2)
        }
        if len(input_df) == 1:
            res["input_features"] = input_df.iloc[idx].replace({np.nan: None}).to_dict()
        results.append(res)
        
    output = {
        "model_used": model_name,
        "predictions": results
    }
    print(json.dumps(output, indent=2))


def main():
    args = parse_cli_args()
    try:
        model_data = load_model(args.model_path)
        pipeline = model_data['pipeline']
        model_name = model_data.get('model_name', 'Unknown model')
    except Exception as e:
        print(json.dumps({"error": f"Failed to load model: {str(e)}"}), file=sys.stderr)
        sys.exit(1)
        
    if args.input_json:
        input_df = _prepare_df_from_json(args.input_json)
    elif args.input_file:
        input_df = _prepare_df_from_file(args.input_file)
    else:
        input_df = _prepare_df_from_cli(args)
        
    try:
        preds = predict(pipeline, input_df)
        _print_predictions(preds, input_df, model_name)
    except Exception as e:
        print(json.dumps({"error": f"Prediction failed: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
