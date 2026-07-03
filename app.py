# app.py
import sys
import logging
import threading
from typing import Dict, Tuple, Optional, Final, Any

# CustomTkinter graphical framework
import customtkinter as ctk

# Modular system layers
from vehicle import VehicleSimulator
from logger import TelemetryLogger
from prediction import RangePredictor
from graph import LiveEnergyGraph
from dashboard import EVDashboardView
from utils import ensure_directory_structure, format_duration, format_distance, format_efficiency

# Configure high-fidelity log structures
logger = logging.getLogger("SDV.AppController")
logging.basicConfig(level=logging.INFO)

class SDVApplication(ctk.CTk):
    """
    Main application controller and orchestrator for the SDV Cockpit.
    Coordinates physical simulator models, background machine learning pipelines,
    file-system diagnostics, and real-time visualization canvas states.
    """
    
    # Timing Intervals (Milliseconds)
    PHYSICS_TICK_RATE_MS: Final[int] = 100         # 10 Hz refresh rate for physics and logs
    ML_TRAINING_RATE_MS: Final[int] = 10000        # Train model every 10 seconds
    
    # Visual Theme Styling Constants (Safe MVC UI Tints)
    ML_ACTIVE_CARD_COLOR: Final[str] = "#1F2C3F"   # Accent blue card state on active ML
    ML_ACTIVE_TEXT_COLOR: Final[str] = "#00FF66"   # Healthy green text
    
    def __init__(self) -> None:
        super().__init__()
        
        # Configure Main Application Frame Window
        self.title("SDV Cockpit - Electric Vehicle Diagnostic & Telemetry System")
        self.geometry("1150x680")
        self.minsize(1050, 620)
        
        # Track pending scheduled tasks to prevent zombie loops on exit
        self._telemetry_task_id: Optional[str] = None
        self._ml_task_id: Optional[str] = None
        
        # Background worker state trackers for thread-safe ML operations
        self._is_training_active: bool = False
        self._training_result: Optional[Tuple[bool, str]] = None

        # 1. Initialize Safe OS Directories
        try:
            ensure_directory_structure("logs")
            ensure_directory_structure("models")
        except Exception as e:
            logger.critical(f"Failed to verify local system folder structures: {e}")
            sys.exit(1)

        # 2. Instantiate Analytical and Powertrain Business Models
        self.simulator: VehicleSimulator = VehicleSimulator()
        self.logger_module: TelemetryLogger = TelemetryLogger()
        self.range_predictor: RangePredictor = RangePredictor()

        # 3. Instantiate Visual Presentation HMI View
        # Establish events to bridge view interactions back to business layers
        callbacks: Dict[str, Any] = {
            "on_mode_change": self._handle_drive_mode_selection,
            "on_fault_toggle": self._handle_fault_injection
        }
        self.view: EVDashboardView = EVDashboardView(parent=self, callbacks=callbacks)

        # 4. Bind Live Plotting Elements to View Hooks
        try:
            self.live_graph: LiveEnergyGraph = LiveEnergyGraph(parent_frame=self.view.graph_card)
            # Destroy the visual loading block once plot is initialized
            if hasattr(self.view, 'graph_placeholder_label') and self.view.graph_placeholder_label:
                self.view.graph_placeholder_label.destroy()
        except Exception as e:
            logger.error(f"Visualization component initiation failed: {e}")
            self.live_graph = None

        # 5. Inject Charging UI controls
        self.charge_switch: Optional[ctk.CTkSwitch] = None
        self._inject_charging_controls()

        # 6. Kick off scheduled tasks
        self._schedule_telemetry_tick()
        self._schedule_ml_training_tick()
        
        logger.info("SDV Cockpit Controller active. Event loops started.")

    def _inject_charging_controls(self) -> None:
        """Injects charging toggles inside the diagnostics panel."""
        try:
            self.charge_switch = ctk.CTkSwitch(
                self.view.diag_card,
                text="Toggle DC Fast Charging (120kW)",
                command=self._handle_charging_toggle,
                font=ctk.CTkFont(family="Helvetica", size=12)
            )
            self.charge_switch.pack(anchor="w", padx=15, pady=(5, 10))
        except AttributeError as e:
            logger.error(f"HMI card target unavailable during layout injection: {e}")

    # --- HMI Presentation Callbacks ---
    def _handle_drive_mode_selection(self, selected_mode: str) -> None:
        """Sets drive profile configuration."""
        try:
            self.simulator.set_drive_mode(selected_mode)
            logger.info(f"HMI Shifted vehicle profile to: {selected_mode}")
        except Exception as e:
            logger.error(f"Failed drive mode swap: {e}")

    def _handle_fault_injection(self, active: bool) -> None:
        """Forces manual fault injections to test Limp-Home routines."""
        try:
            if active:
                self.simulator.trigger_fault(True, "Motor Cooling Pump Failure - Speed Limited")
                logger.warning("Diagnostics Override: Injected cooling system failure.")
            else:
                self.simulator.trigger_fault(False)
                logger.info("Diagnostics Override: Cleared injected fault.")
        except Exception as e:
            logger.error(f"Fault injector communication failure: {e}")

    def _handle_charging_toggle(self) -> None:
        """Toggles the vehicle's electrical charging state machine."""
        if self.charge_switch is None:
            return
            
        try:
            is_charging_active = self.charge_switch.get() == 1
            self.simulator.toggle_charging(is_charging_active)
            
            # Disable speed selector controls during battery charging
            if is_charging_active:
                self.view.mode_selector.configure(state="disabled")
                logger.info("Grid connection active. Powertrain locked.")
            else:
                self.view.mode_selector.configure(state="normal")
                logger.info("Grid connection terminated. Powertrain unlocked.")
        except Exception as e:
            logger.error(f"Failed to adjust charging hardware state: {e}")

    # --- Cyclic Timing Tasks ---
    def _schedule_telemetry_tick(self) -> None:
        """
        Updates the physics state and refreshes indicators.
        Uses defensive execution blocks to keep the loop running if a component fails.
        """
        # 1. State Progression
        telemetry: Optional[dict] = None
        try:
            telemetry = self.simulator.get_telemetry()
        except Exception as e:
            logger.critical(f"Critical error in vehicle simulation model state progression: {e}")

        # If we failed to get telemetry, attempt to recover by scheduling the next tick and exiting
        if telemetry is None:
            self._telemetry_task_id = self.after(self.PHYSICS_TICK_RATE_MS, self._schedule_telemetry_tick)
            return

        # 2. Update Gauges and Text Fields
        try:
            self.view.update_telemetry_view(telemetry)
        except Exception as e:
            logger.error(f"Gauges UI refresh failed: {e}")

        # 3. Update Plots
        if self.live_graph is not None:
            try:
                self.live_graph.update_data(telemetry["consumption"])
            except Exception as e:
                logger.error(f"Failed to update visualization canvas: {e}")

        # 4. Append Telemetry Frames to Storage
        try:
            self.logger_module.log_frame(telemetry)
        except Exception as e:
            logger.error(f"Failsafe triggered. Disk logger failed: {e}")

        # 5. Check and Apply Background ML Model Status Changes
        if self._training_result is not None:
            success, message = self._training_result
            self._training_result = None  # Clear thread transfer state
            
            if success:
                logger.info(f"Range model trained successfully. Updating UI layout indicators: {message}")
                try:
                    self.view.range_card.configure(fg_color=self.ML_ACTIVE_CARD_COLOR)
                    self.view.range_val_label.configure(text_color=self.ML_ACTIVE_TEXT_COLOR)
                except Exception as e:
                    logger.error(f"Failed to update ML card style attributes: {e}")
            else:
                logger.info(f"Deferring predictive range update: {message}")

        # 6. Evaluate Range Calculations
        try:
            predicted_range = self.range_predictor.predict_remaining_range(
                soc=telemetry["soc"],
                soh=telemetry["soh"],
                drive_mode=telemetry["drive_mode"],
                speed=telemetry["speed"],
                avg_speed=telemetry["avg_speed"],
                motor_temp=telemetry["motor_temp"]
            )
            self.view.range_val_label.configure(text=f"{predicted_range} km")
        except Exception as e:
            logger.error(f"Range prediction step error: {e}")

        # 7. Update Text Status Displays
        try:
            self._update_trip_diagnostics(telemetry)
        except Exception as e:
            logger.error(f"Failed to write diagnostic text: {e}")

        # Schedule next loop step
        self._telemetry_task_id = self.after(self.PHYSICS_TICK_RATE_MS, self._schedule_telemetry_tick)

    def _schedule_ml_training_tick(self) -> None:
        """
        Schedules background model training if not already active.
        Spawns a thread to keep the UI running at a smooth 60 FPS.
        """
        if self._is_training_active:
            # Re-queue check for later if worker thread is running
            self._ml_task_id = self.after(self.ML_TRAINING_RATE_MS, self._schedule_ml_training_tick)
            return

        try:
            active_filepath = self.logger_module._get_current_log_filepath()
            self._is_training_active = True
            
            # Spawn training thread
            training_thread = threading.Thread(
                target=self._run_training_worker,
                args=(active_filepath,),
                daemon=True
            )
            training_thread.start()
        except Exception as e:
            logger.error(f"Failed to dispatch background training worker thread: {e}")
            self._is_training_active = False

        self._ml_task_id = self.after(self.ML_TRAINING_RATE_MS, self._schedule_ml_training_tick)

    def _run_training_worker(self, filepath: str) -> None:
        """Background thread worker to train the ML model."""
        try:
            success, message = self.range_predictor.train_model(filepath)
            self._training_result = (success, message)
        except Exception as e:
            logger.error(f"Background training worker error: {e}")
            self._training_result = (False, f"Thread error: {str(e)}")
        finally:
            self._is_training_active = False

    def _update_trip_diagnostics(self, telemetry: dict) -> None:
        """Binds rolling trip measurements dynamically to UI status overlays."""
        trip_metrics_str = (
            f"Odometer: {format_distance(telemetry['odometer'])}\n"
            f"Trip Distance: {format_distance(telemetry['trip_distance'])}\n"
            f"Trip Duration: {format_duration(telemetry['trip_time'])}\n"
            f"Avg Speed: {round(telemetry['avg_speed'], 1)} km/h\n"
            f"Rolling Efficiency: {format_efficiency(telemetry['efficiency'])}"
        )
        self.view.fault_banner.configure(
            text=f"{telemetry['fault_message'].upper()}\n\n"
                 f"TRIP STATS:\n{trip_metrics_str}"
        )

    def destroy(self) -> None:
        """Clean release of scheduled loops and graphic handles on exit."""
        logger.info("Shutdown sequence initiated. Safely releasing memory resources...")
        
        # 1. Cancel pending scheduled Tkinter after tasks
        if self._telemetry_task_id is not None:
            try:
                self.after_cancel(self._telemetry_task_id)
                self._telemetry_task_id = None
            except Exception as e:
                logger.error(f"Failed to cancel telemetry tick task ID: {e}")
                
        if self._ml_task_id is not None:
            try:
                self.after_cancel(self._ml_task_id)
                self._ml_task_id = None
            except Exception as e:
                logger.error(f"Failed to cancel ML training task ID: {e}")

        # 2. Clean Matplotlib canvas memory leaks
        if self.live_graph is not None:
            try:
                self.live_graph.destroy()
            except Exception as e:
                logger.error(f"Failed to destroy plotting canvas: {e}")

        # 3. Destroy view structures and window frames
        try:
            super().destroy()
        except Exception as e:
            logger.error(f"Error during window destruction cycle: {e}")
            
        logger.info("Application closed.")


if __name__ == "__main__":
    # Launch main application loop
    try:
        app = SDVApplication()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Unhandled critical system crash on startup thread: {e}")
