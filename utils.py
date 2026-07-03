# utils.py
import os
import math
import logging

# Configure module-level logger
logger = logging.getLogger("SDV.Utils")

# Time conversion constants (PEP 8 naming)
SECONDS_IN_HOUR: int = 3600
SECONDS_IN_MINUTE: int = 60

def ensure_directory_structure(directory_path: str) -> None:
    """
    Creates directory structures on the filesystem if they do not exist.
    Ensures critical filesystem exceptions are re-raised so they are not
    silently ignored by the calling application.
    """
    if not isinstance(directory_path, str) or not directory_path.strip():
        raise ValueError("Directory path must be a non-empty string.")

    try:
        os.makedirs(directory_path, exist_ok=True)
    except OSError as e:
        logger.exception(f"Critical: Failed to create directory structure at '{directory_path}'")
        raise

def format_duration(seconds: int | float) -> str:
    """
    Converts raw seconds into standard duration format HH:MM:SS.
    Clamps negative or invalid values to zero to prevent visual layout issues.
    """
    # Guard against non-numeric types, NaN, Inf, and negative values
    if (not isinstance(seconds, (int, float)) or 
            not math.isfinite(seconds) or 
            seconds <= 0):
        return "00:00:00"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, SECONDS_IN_HOUR)
    minutes, secs = divmod(remainder, SECONDS_IN_MINUTE)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def format_efficiency(efficiency_wh_km: int | float) -> str:
    """
    Formats the vehicle consumption rate (Wh/km) to exactly 1 decimal place.
    Handles invalid, zero, or negative metrics gracefully.
    """
    # Guard against non-numeric types, NaN, Inf, and non-positive metrics
    if (not isinstance(efficiency_wh_km, (int, float)) or 
            not math.isfinite(efficiency_wh_km) or 
            efficiency_wh_km <= 0.0):
        return "0.0 Wh/km"

    return f"{efficiency_wh_km:.1f} Wh/km"

def format_distance(distance_km: int | float) -> str:
    """
    Formats odometer and trip distances to exactly 2 decimal places.
    Clamps negative values to zero to prevent physical anomalies.
    """
    # Guard against non-numeric types, NaN, Inf, and negative mileage
    if (not isinstance(distance_km, (int, float)) or 
            not math.isfinite(distance_km) or 
            distance_km <= 0.0):
        return "0.00 km"

    return f"{distance_km:.2f} km"
