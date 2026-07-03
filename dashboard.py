# dashboard.py
import customtkinter as ctk
from typing import Dict, Any, Callable, Optional

class EVDashboardView(ctk.CTkFrame):
    """
    Main UI view for the EV Dashboard. Displays vehicle telemetry, 
    controls, and status indicators using CustomTkinter.
    """
    
    def __init__(self, parent: ctk.CTk, callbacks: Dict[str, Callable]) -> None:
        super().__init__(parent)
        self.parent = parent
        self.callbacks = callbacks
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid layout
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        
        # Store references to UI components for external updates
        self.graph_card: Optional[ctk.CTkFrame] = None
        self.diag_card: Optional[ctk.CTkFrame] = None
        self.range_card: Optional[ctk.CTkFrame] = None
        self.mode_selector: Optional[ctk.CTkComboBox] = None
        self.range_val_label: Optional[ctk.CTkLabel] = None
        self.fault_banner: Optional[ctk.CTkLabel] = None
        self.graph_placeholder_label: Optional[ctk.CTkLabel] = None
        
        # Build UI layout
        self._create_header()
        self._create_main_content()
        self._create_footer()
    
    def _create_header(self) -> None:
        """Creates the header section with title."""
        header_frame = ctk.CTkFrame(self, fg_color="#1F2C3F")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ Smart EV Dashboard",
            font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"),
            text_color="#00FF66"
        )
        title_label.pack(pady=10)
    
    def _create_main_content(self) -> None:
        """Creates the main content area with telemetry displays and graphs."""
        # Left Panel - Telemetry Gauges
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        left_panel.grid_rowconfigure((0, 1, 2, 3), weight=1)
        
        # Battery SOC Card
        soc_card = ctk.CTkFrame(left_panel, fg_color="#0F1419", border_width=2, border_color="#00FF66")
        soc_card.pack(fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(
            soc_card,
            text="Battery SOC",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            text_color="#00FF66"
        ).pack(pady=(10, 0))
        
        self.soc_label = ctk.CTkLabel(
            soc_card,
            text="90.0%",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#FFFFFF"
        )
        self.soc_label.pack(pady=10)
        
        # Speed Card
        speed_card = ctk.CTkFrame(left_panel, fg_color="#0F1419", border_width=2, border_color="#00A8FF")
        speed_card.pack(fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(
            speed_card,
            text="Speed",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            text_color="#00A8FF"
        ).pack(pady=(10, 0))
        
        self.speed_label = ctk.CTkLabel(
            speed_card,
            text="0.0 km/h",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#FFFFFF"
        )
        self.speed_label.pack(pady=10)
        
        # Motor Temperature Card
        temp_card = ctk.CTkFrame(left_panel, fg_color="#0F1419", border_width=2, border_color="#FF6B00")
        temp_card.pack(fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(
            temp_card,
            text="Motor Temp",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            text_color="#FF6B00"
        ).pack(pady=(10, 0))
        
        self.temp_label = ctk.CTkLabel(
            temp_card,
            text="30.0°C",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#FFFFFF"
        )
        self.temp_label.pack(pady=10)
        
        # Range Card (ML-powered)
        self.range_card = ctk.CTkFrame(left_panel, fg_color="#0F1419", border_width=2, border_color="#1F2C3F")
        self.range_card.pack(fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(
            self.range_card,
            text="Predicted Range",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            text_color="#9D4EDD"
        ).pack(pady=(10, 0))
        
        self.range_val_label = ctk.CTkLabel(
            self.range_card,
            text="--- km",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#FFFFFF"
        )
        self.range_val_label.pack(pady=10)
        
        # Right Panel - Graph and Controls
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Graph Card
        self.graph_card = ctk.CTkFrame(right_panel, fg_color="#0F1419", border_width=2, border_color="#00FF66")
        self.graph_card.grid(row=0, column=0, sticky="nsew")
        self.graph_card.grid_rowconfigure(0, weight=1)
        self.graph_card.grid_columnconfigure(0, weight=1)
        
        self.graph_placeholder_label = ctk.CTkLabel(
            self.graph_card,
            text="📊 Live Energy Consumption Graph",
            font=ctk.CTkFont(family="Helvetica", size=14),
            text_color="#00FF66"
        )
        self.graph_placeholder_label.pack(pady=100)
    
    def _create_footer(self) -> None:
        """Creates the footer section with controls and diagnostics."""
        footer_frame = ctk.CTkFrame(self)
        footer_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        footer_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Left footer - Controls
        control_frame = ctk.CTkFrame(footer_frame, fg_color="#0F1419", border_width=2, border_color="#00A8FF")
        control_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkLabel(
            control_frame,
            text="Drive Mode",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            text_color="#00A8FF"
        ).pack(pady=(10, 5), padx=10)
        
        self.mode_selector = ctk.CTkComboBox(
            control_frame,
            values=["Eco", "Normal", "Sport"],
            command=self._on_mode_change,
            font=ctk.CTkFont(family="Helvetica", size=11),
            state="readonly"
        )
        self.mode_selector.set("Normal")
        self.mode_selector.pack(pady=(0, 10), padx=10, fill="x")
        
        # Right footer - Diagnostics/Fault Banner
        self.diag_card = ctk.CTkFrame(footer_frame, fg_color="#0F1419", border_width=2, border_color="#FF6B00")
        self.diag_card.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        self.fault_banner = ctk.CTkLabel(
            self.diag_card,
            text="SYSTEM NOMINAL\n\nTRIP STATS:\nOdometer: 0.0 km\nTrip Distance: 0.0 km\nTrip Duration: 0.0 s\nAvg Speed: 0.0 km/h\nRolling Efficiency: 0.0 Wh/km",
            font=ctk.CTkFont(family="Helvetica", size=10),
            text_color="#FFFFFF",
            justify="left"
        )
        self.fault_banner.pack(pady=10, padx=10, fill="both", expand=True)
    
    def _on_mode_change(self, selected_mode: str) -> None:
        """Handle drive mode selection change."""
        if "on_mode_change" in self.callbacks:
            self.callbacks["on_mode_change"](selected_mode)
    
    def update_telemetry_view(self, telemetry: Dict[str, Any]) -> None:
        """Updates all UI labels with new telemetry data."""
        try:
            # Update SOC
            self.soc_label.configure(text=f"{telemetry['soc']:.1f}%")
            
            # Update Speed
            self.speed_label.configure(text=f"{telemetry['speed']:.1f} km/h")
            
            # Update Motor Temperature
            self.temp_label.configure(text=f"{telemetry['motor_temp']:.1f}°C")
            
            # Update fault/diagnostics banner color based on fault status
            if telemetry.get("fault_active", False):
                self.diag_card.configure(border_color="#FF0000")
                self.fault_banner.configure(text_color="#FF6B00")
            else:
                self.diag_card.configure(border_color="#FF6B00")
                self.fault_banner.configure(text_color="#FFFFFF")
                
        except Exception as e:
            print(f"Error updating telemetry view: {e}")
