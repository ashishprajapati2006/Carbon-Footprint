#!/usr/bin/env python3
"""
Training Pipeline for Carbon Footprint Predictor.
Downloads We-Bears/Individual-Carbon-Footprint-Calculation from Hugging Face,
caches it locally, validates, cleans, encodes categorical columns, trains
RandomForestRegressor and XGBoostRegressor, and saves the best model.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("train_pipeline")

# Configuration
DATASET_NAME = "We-Bears/Individual-Carbon-Footprint-Calculation"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "carbon_predictor.pkl")

# Feature definitions
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


def download_and_cache_dataset(dataset_name: str, cache_dir: str) -> pd.DataFrame:
    """Downloads the Hugging Face dataset and caches it locally, returning a pandas DataFrame."""
    logger.info(f"Downloading dataset '{dataset_name}' with local cache at '{cache_dir}'...")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Load dataset
    dataset = load_dataset(dataset_name, cache_dir=cache_dir)
    
    # Hugging Face dataset splits check
    if 'train' not in dataset:
        raise KeyError(f"Expected split 'train' not found in downloaded dataset. Available splits: {list(dataset.keys())}")
        
    df = dataset['train'].to_pandas()
    logger.info(f"Dataset loaded successfully. Shape: {df.shape}")
    return df


def validate_schema(df: pd.DataFrame):
    """Validates that the dataset conforms to the expected feature schema and target column."""
    logger.info("Validating schema...")
    
    missing_cols = []
    for col in CATEGORICAL_FEATURES + NUMERICAL_FEATURES:
        if col not in df.columns:
            missing_cols.append(col)
            
    if TARGET not in df.columns:
        missing_cols.append(TARGET)
        
    if missing_cols:
        raise ValueError(f"Schema validation failed! Missing columns: {missing_cols}")
        
    logger.info("Schema validation passed.")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Performs data cleaning on the dataset."""
    logger.info("Cleaning data...")
    initial_shape = df.shape
    
    # Drop exact duplicates
    df = df.drop_duplicates()
    if len(df) < initial_shape[0]:
        logger.info(f"Removed {initial_shape[0] - len(df)} duplicate rows.")
        
    # Drop rows with null target
    null_targets = df[TARGET].isnull().sum()
    if null_targets > 0:
        logger.warning(f"Found {null_targets} rows with missing target '{TARGET}'. Dropping them.")
        df = df.dropna(subset=[TARGET])
        
    # Ensure target is numeric
    df[TARGET] = pd.to_numeric(df[TARGET], errors='coerce')
    df = df.dropna(subset=[TARGET])
    
    logger.info(f"Data cleaning complete. Cleaned shape: {df.shape}")
    return df


def build_preprocessing_pipeline() -> ColumnTransformer:
    """Builds a scikit-learn ColumnTransformer for preprocessing input features."""
    logger.info("Building preprocessing pipeline...")
    
    # Numerical Preprocessing: Impute missing values with median, then scale
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    # Categorical Preprocessing: Impute missing values with 'None' constant, then One-Hot encode
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='None')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    # Bundle preprocessing
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, NUMERICAL_FEATURES),
            ('cat', categorical_transformer, CATEGORICAL_FEATURES)
        ]
    )
    
    return preprocessor


def train_and_evaluate(X_train: pd.DataFrame, X_test: pd.DataFrame, 
                       y_train: pd.Series, y_test: pd.Series, 
                       preprocessor: ColumnTransformer) -> dict:
    """Trains RandomForestRegressor and XGBoostRegressor models and evaluates them."""
    logger.info("Starting model training and evaluation...")
    
    models = {
        'RandomForestRegressor': RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        ),
        'XGBoostRegressor': XGBRegressor(
            n_estimators=100,
            learning_rate=0.08,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )
    }
    
    trained_pipelines = {}
    evaluation_results = {}
    
    for name, regressor in models.items():
        logger.info(f"Training {name}...")
        
        # Create final pipeline
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', regressor)
        ])
        
        # Fit pipeline
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline
        
        # Predict & Evaluate
        y_pred = pipeline.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        evaluation_results[name] = {
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2)
        }
        
        logger.info(f"{name} Evaluation -> MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.4f}")
        
    return trained_pipelines, evaluation_results


def main():
    logger.info("Starting training pipeline execution...")
    
    # 1 & 2. Download automatically and cache locally
    df = download_and_cache_dataset(DATASET_NAME, CACHE_DIR)
    
    # 3. Validate schema
    validate_schema(df)
    
    # 4. Clean data
    df_clean = clean_data(df)
    
    # Separate features and target
    X = df_clean[CATEGORICAL_FEATURES + NUMERICAL_FEATURES]
    y = df_clean[TARGET]
    
    # 5. Split train/test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    logger.info(f"Train size: {X_train.shape}, Test size: {X_test.shape}")
    
    # Build preprocessor (encodes categorical columns under the hood)
    preprocessor = build_preprocessing_pipeline()
    
    # 6. Train model(s)
    pipelines, results = train_and_evaluate(X_train, X_test, y_train, y_test, preprocessor)
    
    # Select the best model based on R2 score
    best_model_name = max(results, key=lambda k: results[k]['r2'])
    best_pipeline = pipelines[best_model_name]
    logger.info(f"Selected Best Model: {best_model_name} with R2 = {results[best_model_name]['r2']:.4f}")
    
    # 7. Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    logger.info(f"Saving best model and pipeline to '{MODEL_PATH}'...")
    
    model_data = {
        'pipeline': best_pipeline,
        'model_name': best_model_name,
        'metrics': results,
        'features': {
            'categorical': CATEGORICAL_FEATURES,
            'numerical': NUMERICAL_FEATURES,
            'target': TARGET
        }
    }
    
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_data, f)
        
    logger.info("Model saved successfully. Pipeline execution complete.")


if __name__ == '__main__':
    main()
