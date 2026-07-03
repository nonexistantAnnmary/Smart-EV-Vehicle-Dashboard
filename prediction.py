# prediction.py
import os
import logging
from typing import Dict, Tuple, Optional, Any

# Third-party analytical libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# Attempt to import joblib for efficient array serialization; fallback to standard pickle
try:
    import joblib
    _HAS_JOBLIB = True
except ImportError:
    import pickle
    _HAS_JOBLIB = False

# Configure local module logger
logger = logging.getLogger("SDV.Prediction")
logging.basicConfig(level=logging.INFO)

class RangePredictor:
    """
    Onboard predictive machine learning model for EV range estimation.
    Uses an ensemble Random Forest Regressor to map real-time telemetry variables
    to powertrain efficiency, with physical boundary protection and automated caching.
    """
    
    # Class-level Constants (Physical and Software Constraints)
    BATTERY_CAPACITY_WH: float = 60000.0   # 60 kWh standard pack capacity
    MIN_TRAINING_SAMPLES: int = 30         # Minimum dataset size required to fit the model
    MODEL_DIR: str = "models"
    MODEL_FILENAME: str = "range_predictor_model.joblib" if _HAS_JOBLIB else "range_predictor_model.pkl"
    
    # Physical boundaries to prevent mathematical extrapolation anomalies (Wh/km limits)
    PHYSICAL_MIN_EFFICIENCY: float = 100.0  # Theoretical limit for ultra-efficient EVs
    PHYSICAL_MAX_EFFICIENCY: float = 450.0  # High-load limit (climbing, heavy sport usage)
    
    # Qualitative driving profiles mapped to ordinal integers for model input
    DRIVE_MODE_MAP: Dict[str, int] = {
        "Eco": 0,
        "Normal": 1,
        "Sport": 2
    }
    
    # Hardcoded physical fallback efficiencies (Wh/km) used during cold-starts
    DEFAULT_EFFICIENCIES: Dict[str, float] = {
        "Eco": 130.0,
        "Normal": 160.0,
        "Sport": 220.0
    }

    def __init__(self, models_dir: Optional[str] = None) -> None:
        self.model: Optional[RandomForestRegressor] = None
        self._is_trained: bool = False
        
        # Track metric performance from the most recent training run
        self.last_training_metrics: Dict[str, float] = {}
        
        # Initialize model storage paths
        self.model_directory: str = models_dir or self.MODEL_DIR
        self.model_path: str = os.path.join(self.model_directory, self.MODEL_FILENAME)
        
        # Cold-start load sequence
        self._attempt_model_restore()

    def _attempt_model_restore(self) -> None:
        """Attempts to load a pre-trained serialized model from disk."""
        if not os.path.exists(self.model_path):
            logger.info("No cached model found. Operating in cold-start default physics mode.")
            return

        try:
            if _HAS_JOBLIB:
                self.model = joblib.load(self.model_path)
            else:
                with open(self.model_path, "rb") as file:
                    self.model = pickle.load(file)
            
            self._is_trained = True
            logger.info(f"Pre-trained model loaded successfully from: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to restore cached model weights: {e}. Falling back to default.")
            self.model = None
            self._is_trained = False

    def _save_model_to_disk(self) -> None:
        """Serializes the active model object to disk."""
        try:
            os.makedirs(self.model_directory, exist_ok=True)
            if _HAS_JOBLIB:
                joblib.dump(self.model, self.model_path)
            else:
                with open(self.model_path, "wb") as file:
                    pickle.dump(self.model, file)
            logger.info(f"Model serialized successfully to {self.model_path}")
        except Exception as e:
            logger.error(f"Serialization failed: {e}")

    def train_model(self, csv_filepath: str) -> Tuple[bool, str]:
        """
        Loads telemetry files, executes a train/test split, fits a regularized
        Random Forest Regressor, and saves model metrics and weights.
        
        Returns:
            Tuple[bool, str]: (Success status flag, Detail message)
        """
        if not os.path.exists(csv_filepath):
            return False, f"Telemetry file '{csv_filepath}' does not exist."
            
        try:
            # 1. Read historical CSV log
            df = pd.read_csv(csv_filepath)
            
            # 2. Check sample density constraint
            if len(df) < self.MIN_TRAINING_SAMPLES:
                return False, f"Insufficient datasets for model validation ({len(df)}/{self.MIN_TRAINING_SAMPLES} frames)."

            # 3. Data Cleaning and Sanitization
            required_cols = ["drive_mode", "speed", "avg_speed", "motor_temp", "efficiency"]
            df = df.dropna(subset=required_cols)
            
            # Exclude abnormal data bounds (e.g., stationary charging or extreme regen periods)
            df = df[(df["efficiency"] >= self.PHYSICAL_MIN_EFFICIENCY) & 
                    (df["efficiency"] <= self.PHYSICAL_MAX_EFFICIENCY)]
            
            if len(df) < self.MIN_TRAINING_SAMPLES:
                return False, f"Insufficient valid records remain after filtering out anomalous points."

            # 4. Feature Encoding
            df["drive_mode_code"] = df["drive_mode"].map(self.DRIVE_MODE_MAP).fillna(1).astype(int)
            
            # Feature matrix (X) and Target vector (y)
            X = df[["drive_mode_code", "speed", "avg_speed", "motor_temp"]].values
            y = df["efficiency"].values

            # 5. Model Validation Split (80% Train, 20% Test validation)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

            # 6. Instantiate Regularized RandomForest to prevent overfitting on low-density tables
            new_model = RandomForestRegressor(
                n_estimators=50,
                max_depth=4,
                min_samples_split=5,
                random_state=42
            )
            
            # Train the ensemble regressor
            new_model.fit(X_train, y_train)

            # 7. Evaluate Generalization Metrics
            y_pred = new_model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            # Store computed metrics internally for dashboard diagnostic readouts
            self.last_training_metrics = {
                "r2": round(float(r2), 3),
                "mae": round(float(mae), 2),
                "rmse": round(float(rmse), 2)
            }

            # Update working memory model reference
            self.model = new_model
            self._is_trained = True
            
            # Persist model weights to disk for future launches
            self._save_model_to_disk()

            metric_summary = f"R²: {self.last_training_metrics['r2']}, MAE: {self.last_training_metrics['mae']} Wh/km"
            logger.info(f"Model training success. {metric_summary}")
            return True, f"Training complete. ({metric_summary})"
            
        except Exception as e:
            logger.error(f"Execution error during training phase: {e}")
            return False, f"Training error: {str(e)}"

    def predict_remaining_range(
        self, 
        soc: float, 
        soh: float, 
        drive_mode: str,
        speed: float,
        avg_speed: float, 
        motor_temp: float
    ) -> float:
        """
        Calculates remaining energy and maps vehicle states to efficiency
        using the ML model to predict range in kilometers.
        """
        # Calculate available energy capacity factoring current health degradation
        remaining_capacity_wh = self.BATTERY_CAPACITY_WH * (soc / 100.0) * (soh / 100.0)
        
        # Physical boundary check (battery depleted)
        if remaining_capacity_wh <= 0.0:
            return 0.0

        # Establish default baseline reference consumption
        predicted_efficiency = self.DEFAULT_EFFICIENCIES.get(drive_mode, 160.0)

        # Attempt machine learning inference if the model has loaded or finished training
        if self._is_trained and self.model is not None:
            try:
                drive_mode_code = self.DRIVE_MODE_MAP.get(drive_mode, 1)
                
                # Format 2D feature matrix
                feature_row = np.array([[drive_mode_code, speed, avg_speed, motor_temp]])
                
                # Model inference
                predicted_efficiency = float(self.model.predict(feature_row)[0])
                
                # Protect against invalid regression values
                predicted_efficiency = np.clip(
                    predicted_efficiency, 
                    self.PHYSICAL_MIN_EFFICIENCY, 
                    self.PHYSICAL_MAX_EFFICIENCY
                )
            except Exception as e:
                # Fallback to defaults on unexpected runtime exceptions
                logger.warning(f"Prediction inference failed: {e}. Reverting to baseline efficiency.")
                predicted_efficiency = self.DEFAULT_EFFICIENCIES.get(drive_mode, 160.0)

        # Range calculation: Available Energy (Wh) / Consumption Rate (Wh/km)
        estimated_range_km = remaining_capacity_wh / predicted_efficiency
        
        return round(max(0.0, estimated_range_km), 1)
