# logger.py
import csv
import os
from datetime import datetime
from typing import Dict, Any

class TelemetryLogger:
    """
    Manages filesystem-based rolling database records. Logs incoming telemetry 
    frames dynamically into distinct, date-stamped CSV documents inside a /logs folder.
    """
    
    def __init__(self, log_directory: str = "logs") -> None:
        self.log_directory: str = log_directory
        self._headers = [
            "timestamp", 
            "speed", 
            "soc", 
            "soh",
            "motor_temp", 
            "drive_mode", 
            "is_charging",
            "fault_active", 
            "fault_message", 
            "odometer", 
            "consumption",
            "estimated_range",
            "trip_distance",
            "trip_time",
            "avg_speed",
            "energy_used",
            "efficiency"
        ]
        # Create output log folder structures if missing
        os.makedirs(self.log_directory, exist_ok=True)

    def _get_current_log_filepath(self) -> str:
        """Constructs the date-stamped filepath dynamically based on current system date."""
        current_date_str = datetime.now().strftime("%Y-%m-%d") # Format: YYYY-MM-DD [1]
        filename = f"vehicle_{current_date_str}.csv"
        return os.path.join(self.log_directory, filename)

    def _ensure_file_headers(self, filepath: str) -> None:
        """Verifies target log file is active and initialized with structural headers."""
        if not os.path.exists(filepath):
            try:
                with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(self._headers)
            except IOError as e:
                print(f"[LOGGER ERROR] Failed to create log index structure: {e}")

    def log_frame(self, telemetry: Dict[str, Any]) -> None:
        """
        Appends a modern EV high-resolution telemetry packet to the rolling file stream.
        """
        target_path = self._get_current_log_filepath()
        self._ensure_file_headers(target_path)
        
        try:
            with open(target_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self._headers)
                # Ensure we only attempt to write declared telemetry fields
                filtered_data = {key: telemetry[key] for key in self._headers if key in telemetry}
                writer.writerow(filtered_data)
        except IOError as e:
            print(f"[LOGGER ERROR] Failed writing data segment block to active stream: {e}")
            
    def get_log_size(self) -> int:
        """Counts historical lines captured inside today's active logger file."""
        target_path = self._get_current_log_filepath()
        if not os.path.exists(target_path):
            return 0
        try:
            with open(target_path, mode='r', encoding='utf-8') as file:
                return sum(1 for _ in file) - 1
        except IOError:
            return 0
