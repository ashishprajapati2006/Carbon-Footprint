#!/usr/bin/env python3
"""
Evaluation Script for Carbon Footprint Predictor.
Loads a trained model and evaluates it against the test partition,
reporting MAE, RMSE, R2, and feature importances.
"""

import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("evaluate_pipeline")

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

TARGET = 'CarbonEmission'


def load_model(model_path: str) -> dict:
    """Loads the model artifact from disk."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at '{model_path}'. Please run training first.")
        
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    return model_data


def _clean_feature_name(name: str) -> str:
    """Cleans up encoded feature names for better readability."""
    if name.startswith('cat__'):
        parts = name[5:].split('_')
        col_name = parts[0]
        val_name = '_'.join(parts[1:])
        return f"{col_name}: {val_name}"
    elif name.startswith('num__'):
        return name[5:]
    return name


def get_feature_importances(pipeline) -> pd.DataFrame:
    """Extracts and formats feature importances from the pipeline."""
    try:
        preprocessor = pipeline.named_steps['preprocessor']
        regressor = pipeline.named_steps['regressor']
        feature_names = preprocessor.get_feature_names_out()
        
        if not hasattr(regressor, 'feature_importances_'):
            logger.warning("Regressor does not expose feature_importances_.")
            return pd.DataFrame()
            
        importances = regressor.feature_importances_
        clean_names = [_clean_feature_name(name) for name in feature_names]
                
        importance_df = pd.DataFrame({
            'Encoded Feature': feature_names,
            'Display Feature': clean_names,
            'Importance': importances
        }).sort_values(by='Importance', ascending=False)
        return importance_df
    except Exception as e:
        logger.error(f"Failed to extract feature importances: {str(e)}")
        return pd.DataFrame()


def _print_performance_table(selected_model: str, mae: float, rmse: float, r2: float, training_metrics: dict) -> None:
    """Prints a neat metric summary table to stdout."""
    print("\n" + "="*50)
    print(f" MODEL PERFORMANCE METRICS: {selected_model}")
    print("="*50)
    print(f"{'Metric':<15} | {'Test Set Score':<18} | {'Train-Time Test Score':<18}")
    print("-"*50)
    
    m_rf_test = training_metrics.get(selected_model, {})
    print(f"{'MAE':<15} | {mae:<18.4f} | {m_rf_test.get('mae', 0.0):<18.4f}")
    print(f"{'RMSE':<15} | {rmse:<18.4f} | {m_rf_test.get('rmse', 0.0):<18.4f}")
    print(f"{'R-squared':<15} | {r2:<18.4f} | {m_rf_test.get('r2', 0.0):<18.4f}")
    print("="*50)


def _print_comparison_report(training_metrics: dict, selected_model: str) -> None:
    """Prints comparison details of trained models."""
    if len(training_metrics) <= 1:
        return
    print("\n" + "="*50)
    print(" TRAINING COMPARISON REPORT")
    print("="*50)
    print(f"{'Model Name':<25} | {'MAE':<8} | {'RMSE':<8} | {'R2':<8}")
    print("-"*50)
    for m_name, scores in training_metrics.items():
        best_marker = " [SELECTED]" if m_name == selected_model else ""
        print(f"{m_name + best_marker:<25} | {scores['mae']:<8.2f} | {scores['rmse']:<8.2f} | {scores['r2']:<8.4f}")
    print("="*50)


def _print_top_features(importance_df: pd.DataFrame) -> None:
    """Prints Top 15 predictive feature importances."""
    if importance_df.empty:
        return
    print("\n" + "="*50)
    print(" TOP 15 PREDICTIVE FEATURES (ENCODED)")
    print("="*50)
    print(f"{'Rank':<5} | {'Feature Name':<30} | {'Relative Importance':<20}")
    print("-"*50)
    for rank, row in enumerate(importance_df.head(15).itertuples(), 1):
        print(f"{rank:<5} | {row._2:<30} | {row.Importance:<20.4%}")
    print("="*50)


def _save_evaluation_json(eval_report_path: str, selected_model: str, mae: float,
                            rmse: float, r2: float, training_metrics: dict, importance_df: pd.DataFrame) -> None:
    """Saves evaluation metrics and top features to a JSON report."""
    try:
        report_data = {
            "selected_model": selected_model,
            "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
            "all_models_metrics": training_metrics,
            "top_features": importance_df.head(20)[['Display Feature', 'Importance']].to_dict(orient='records') if not importance_df.empty else []
        }
        with open(eval_report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"Saved JSON evaluation report to '{eval_report_path}'")
    except Exception as e:
        logger.warning(f"Could not save JSON report: {str(e)}")


def _load_and_prepare_test_data(dataset_name: str, cache_dir: str) -> tuple[pd.DataFrame, pd.Series]:
    """Loads dataset from cache, cleans it, and returns the test partition features and target."""
    logger.info(f"Loading dataset from cache...")
    try:
        dataset = load_dataset(dataset_name, cache_dir=cache_dir)
        df = dataset['train'].to_pandas()
    except Exception as e:
        logger.error(f"Failed to load dataset: {str(e)}")
        raise e
        
    df = df.drop_duplicates().dropna(subset=[TARGET])
    df[TARGET] = pd.to_numeric(df[TARGET], errors='coerce')
    df = df.dropna(subset=[TARGET])
    
    X = df[CATEGORICAL_FEATURES + NUMERICAL_FEATURES]
    y = df[TARGET]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    logger.info(f"Evaluation dataset split complete. Test shape: {X_test.shape}")
    return X_test, y_test


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate a trained carbon predictor model.")
    parser.add_argument("--model-path", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "carbon_predictor.pkl"))
    parser.add_argument("--dataset", default="We-Bears/Individual-Carbon-Footprint-Calculation")
    parser.add_argument("--cache-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache"))
    args = parser.parse_args()
    
    logger.info(f"Loading model from '{args.model_path}'...")
    try:
        model_data = load_model(args.model_path)
    except Exception as e:
        logger.error(str(e))
        return
        
    pipeline = model_data['pipeline']
    selected_model = model_data.get('model_name', 'Unknown')
    training_metrics = model_data.get('metrics', {})
    
    try:
        X_test, y_test = _load_and_prepare_test_data(args.dataset, args.cache_dir)
    except Exception:
        return
    
    logger.info(f"Evaluating model '{selected_model}' on test split...")
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    _print_performance_table(selected_model, mae, rmse, r2, training_metrics)
    _print_comparison_report(training_metrics, selected_model)
    
    importance_df = get_feature_importances(pipeline)
    _print_top_features(importance_df)
    
    eval_report_path = os.path.join(os.path.dirname(args.model_path), "evaluation_report.json")
    _save_evaluation_json(eval_report_path, selected_model, mae, rmse, r2, training_metrics, importance_df)


if __name__ == '__main__':
    main()
