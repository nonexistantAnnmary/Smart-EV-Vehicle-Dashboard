# vehicle.py
import random
import time
from typing import Dict, Any

class VehicleSimulator:
    """
    An advanced EV simulation model incorporating battery chemistry degradation (SoH),
    regenerative braking energy recovery, dynamic environmental shifts, charging states,
    and rolling trip analytics.
    """
    
    DRIVE_MODES = {
        "Eco": {"acceleration": 1.0, "max_speed": 90.0, "base_consumption": 120.0},
        "Normal": {"acceleration": 1.8, "max_speed": 130.0, "base_consumption": 150.0},
        "Sport": {"acceleration": 3.2, "max_speed": 180.0, "base_consumption": 210.0}
    }

    # Physical Constants
    BATTERY_CAPACITY_WH = 60000.0  # 60 kWh pack

    def __init__(self) -> None:
        # Simulation controls
        self.is_charging: bool = False
        
        # Core State Variables
        self._drive_mode: str = "Normal"
        self._speed: float = 0.0          # km/h
        self._soc: float = 90.0           # Start at 90% for demo breathing room
        self._soh: float = 100.0          # State of Health (%)
        self._motor_temp: float = 30.0    # Celsius
        self._is_fault_active: bool = False
        self._fault_message: str = "System Nominal"
        self._odometer: float = 0.0       # Cumulative lifetime mileage (km)
        
        # Trip Statistics (Reset on class initialization)
        self._trip_distance: float = 0.0      # km
        self._trip_time: float = 0.0          # seconds
        self._energy_used_wh: float = 0.0     # Cumulative energy spent (positive)
        self._energy_recovered_wh: float = 0.0  # Cumulative energy regenerated (positive)
        self._sum_speed_samples: float = 0.0
        self._speed_sample_count: int = 0
        
        self._last_update_time: float = time.time()
        
    def set_drive_mode(self, mode: str) -> None:
        """Sets drive profile configuration."""
        if mode in self.DRIVE_MODES:
            self._drive_mode = mode
        else:
            raise ValueError(f"Invalid driving mode: {mode}")

    def toggle_charging(self, active: bool) -> None:
        """Toggles vehicle grid charging state."""
        self.is_charging = active

    def trigger_fault(self, active: bool, message: str = "System Nominal") -> None:
        """Explicit diagnostic override."""
        self._is_fault_active = active
        self._fault_message = message if active else "System Nominal"

    def _update_physics(self, dt: float) -> None:
        """Advanced step-wise physical state computer."""
        
        # 1. Handle Active Charging State
        if self.is_charging:
            # Vehicle must be stationary to charge
            speed_diff = 0.0 - self._speed
            self._speed += speed_diff * (0.8 * dt)  # Fast deceleration to halt
            if self._speed < 0.5:
                self._speed = 0.0
                
            # Simulate a 120 kW DC Fast Charger integration
            charge_power_w = 120000.0
            energy_added_wh = (charge_power_w / 3600.0) * dt
            
            # SoC growth limited by current battery State of Health
            max_soc_allowed = self._soh
            soc_added = (energy_added_wh / self.BATTERY_CAPACITY_WH) * 100.0
            self._soc = min(max_soc_allowed, self._soc + soc_added)
            
            # Motor cool-down profile during stationary charging
            ambient_temp = random.uniform(18.0, 38.0)
            self._motor_temp += (ambient_temp - self._motor_temp) * (0.02 * dt)
            
            # Log zero-load statistics
            self._trip_time += dt
            self._track_speed(self._speed)
            self._run_auto_diagnostics()
            return

        # 2. Drive Profile Physics
        mode_params = self.DRIVE_MODES[self._drive_mode]
        
        # Calculate target speed with pseudo-random driver inputs
        target_speed = mode_params["max_speed"] * (0.5 + 0.5 * random.uniform(0.7, 1.3))
        
        if self._is_fault_active:
            target_speed = min(target_speed, 30.0)  # Limp-home mode velocity ceiling

        speed_diff = target_speed - self._speed
        acceleration_coefficient = mode_params["acceleration"] * dt
        
        # Track previous speed to calculate acceleration trends
        previous_speed = self._speed

        if speed_diff > 0:
            self._speed += min(acceleration_coefficient * 4, speed_diff)
        else:
            self._speed += max(-acceleration_coefficient * 7, speed_diff)
            
        self._speed = max(0.0, self._speed)
        
        # Calculate actual delta-speed for regen calculations
        actual_speed_diff = self._speed - previous_speed

        # Calculate travel step
        distance_step = (self._speed / 3600.0) * dt
        self._odometer += distance_step
        self._trip_distance += distance_step
        self._trip_time += dt
        self._track_speed(self._speed)

        # 3. Regenerative Braking & State of Charge Calculation
        # Base consumption calculation based on speed and aerodynamic friction scaling
        speed_factor = (self._speed / 100.0) ** 1.6 if self._speed > 0 else 0.1
        current_consumption_wh_km = mode_params["base_consumption"] * (1.0 + speed_factor)
        
        # Consume energy
        energy_spent_wh = current_consumption_wh_km * distance_step
        self._energy_used_wh += energy_spent_wh
        soc_loss = (energy_spent_wh / self.BATTERY_CAPACITY_WH) * 100.0
        self._soc = max(0.0, self._soc - soc_loss)

        # Apply battery regeneration during braking deceleration (speed drop)
        if actual_speed_diff < 0:
            # Energy recovered is modeled proportional to the braking effort
            regen_soc_boost = 0.002 * abs(actual_speed_diff)
            # Cap maximum SoC dynamically to the battery's active State of Health
            self._soc = min(self._soh, self._soc + regen_soc_boost)
            
            # Track recovered Wh metrics
            recovered_wh = (regen_soc_boost / 100.0) * self.BATTERY_CAPACITY_WH
            self._energy_recovered_wh += recovered_wh

        # 4. State of Health (SoH) Micro-Degradation
        # Real-world battery packs lose lifetime capacity via cycling and continuous distance.
        # We simulate dynamic micro-degradation: 0.00005% lost per kilometer driven
        self._soh = max(70.0, self._soh - (distance_step * 0.00005))

        # 5. Motor Thermal Dynamics with dynamic ambient temperature shifts
        ambient_temp = random.uniform(18.0, 38.0)
        thermal_load = (self._speed * 0.35) + (25.0 if self._drive_mode == "Sport" else 4.0)
        
        if self._is_fault_active and "Overheated" in self._fault_message:
            thermal_load += 45.0  # Rapid thermal buildup during cooling fault condition
            
        target_temp = ambient_temp + thermal_load
        self._motor_temp += (target_temp - self._motor_temp) * (0.04 * dt)

        # 6. Evaluation of automated safety logic
        self._run_auto_diagnostics()

    def _track_speed(self, speed: float) -> None:
        """Appends current speed vector samples to calculate averages."""
        self._sum_speed_samples += speed
        self._speed_sample_count += 1

    def _run_auto_diagnostics(self) -> None:
        """Monitors onboard measurements to trigger DTC flags dynamically."""
        if self._motor_temp > 90.0:
            self.trigger_fault(True, "Motor Overheated")
        elif self._soc < 10.0:
            self.trigger_fault(True, "Critical Battery")
        else:
            # Clear critical software faults once systems stabilize
            if self._fault_message in ["Motor Overheated", "Critical Battery"]:
                self.trigger_fault(False)

    def get_telemetry(self) -> Dict[str, Any]:
        """Runs simulation update tick and exports metrics payload."""
        current_time = time.time()
        dt = current_time - self._last_update_time
        self._last_update_time = current_time

        # Bound safety limits on step time (e.g. from app minimization/freezing)
        if dt > 1.5:
            dt = 0.1

        self._update_physics(dt)

        # Real-time physical power measurements
        speed_factor = (self._speed / 100.0) ** 1.6 if self._speed > 0 else 0.1
        instantaneous_consumption = 0.0 if self.is_charging else (
            self.DRIVE_MODES[self._drive_mode]["base_consumption"] * (1.0 + speed_factor) * random.uniform(0.95, 1.05)
        )

        # Trip Analytics Calculations
        avg_speed = (self._sum_speed_samples / self._speed_sample_count) if self._speed_sample_count > 0 else 0.0
        
        # Net energy calculation (spent minus recovered)
        net_energy_used = max(0.0, self._energy_used_wh - self._energy_recovered_wh)
        
        # Efficiency (Wh/km) = Net Energy Used / Distance
        efficiency = (net_energy_used / self._trip_distance) if self._trip_distance > 0 else 0.0

        # High resolution range estimation calculation
        remaining_capacity_wh = self.BATTERY_CAPACITY_WH * (self._soc / 100.0) * (self._soh / 100.0)
        # Prevent division by zero when static, using base reference profile
        calc_consumption = instantaneous_consumption if instantaneous_consumption > 10.0 else self.DRIVE_MODES[self._drive_mode]["base_consumption"]
        estimated_range_km = remaining_capacity_wh / calc_consumption

        return {
            "timestamp": current_time,
            "speed": round(self._speed, 1),
            "soc": round(self._soc, 2),
            "soh": round(self._soh, 4),
            "motor_temp": round(self._motor_temp, 1),
            "drive_mode": self._drive_mode,
            "is_charging": self.is_charging,
            "fault_active": self._is_fault_active,
            "fault_message": self._fault_message,
            "odometer": round(self._odometer, 3),
            "consumption": round(instantaneous_consumption, 1),
            "estimated_range": round(estimated_range_km, 1),
            # New Diagnostic Trip Metrics
            "trip_distance": round(self._trip_distance, 3),
            "trip_time": round(self._trip_time, 1),
            "avg_speed": round(avg_speed, 1),
            "energy_used": round(self._energy_used_wh, 1),
            "efficiency": round(efficiency, 1)
        }
