# graph.py
import collections
from typing import List, Final, Optional

# Core GUI and plotting integrations
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")  # Establish non-interactive GUI backend directly
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D

class LiveEnergyGraph:
    """
    An optimized, memory-safe real-time graphing widget.
    Integrates with CustomTkinter and renders an EV's energy consumption timeline
    with hysteresis scaling, a dynamic average line, and warning thresholds.
    """
    
    # Visual and Architectural Constants
    DEFAULT_MAX_POINTS: Final[int] = 40
    BASE_Y_MIN: Final[float] = 0.0
    BASE_Y_MAX: Final[float] = 300.0
    Y_LIMIT_PAD_UP: Final[float] = 30.0
    Y_LIMIT_PAD_DOWN: Final[float] = 15.0
    Y_HYSTERESIS_THRESHOLD: Final[float] = 20.0  # Prevents tick recalculation jitter
    
    # Thresholds representing EV efficiency ratings
    WARNING_THRESHOLD_WH_KM: Final[float] = 250.0  # Inefficient driving mark
    
    # Color Palette matching the Dark Dashboard theme
    BG_COLOR: Final[str] = "#2A2A2A"          # Matches CTkFrame cards
    ACCENT_LINE_COLOR: Final[str] = "#00A8FF" # High-contrast blue line
    AVERAGE_LINE_COLOR: Final[str] = "#FF9500"# Vibrant amber line
    WARNING_LINE_COLOR: Final[str] = "#FF3B30"# Bright red indicator
    GRID_LINE_COLOR: Final[str] = "#444444"   # Dark gray gridlines
    TEXT_LABEL_COLOR: Final[str] = "#888888"  # Slate text

    def __init__(self, parent_frame: ctk.CTkFrame, max_data_points: int = DEFAULT_MAX_POINTS) -> None:
        self.parent_frame: ctk.CTkFrame = parent_frame
        self.max_data_points: int = max_data_points
        
        # O(1) append/pop sliding window
        self.data_history: collections.deque[float] = collections.deque(
            [0.0] * self.max_data_points, 
            maxlen=self.max_data_points
        )
        
        # Track active limits for the hysteresis scaling system
        self._current_y_min: float = self.BASE_Y_MIN
        self._current_y_max: float = self.BASE_Y_MAX
        
        # Embedded Canvas variables
        self.fig: Optional[Figure] = None
        self.ax: Optional[matplotlib.axes.Axes] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.canvas_widget: Optional[ctk.CTkCanvas] = None
        
        # Line objects modified in-place to prevent garbage collection sweeps
        self.primary_line: Optional[Line2D] = None
        self.avg_line: Optional[Line2D] = None
        
        # Initialize internal graphics structures
        self._init_graphics_stack()

    def _init_graphics_stack(self) -> None:
        """
        Creates the Matplotlib figure, sets styles, and maps canvas widgets.
        Bypasses pyplot to prevent memory retention bugs.
        """
        # 1. Pure OOP figure creation (Zero dependency on plt.subplots())
        self.fig = Figure(figsize=(5, 2.5), dpi=100, facecolor=self.BG_COLOR)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.BG_COLOR)

        # 2. Add static warning boundary
        self.ax.axhline(
            y=self.WARNING_THRESHOLD_WH_KM, 
            color=self.WARNING_LINE_COLOR, 
            linestyle="--", 
            linewidth=1.0, 
            alpha=0.6,
            label="Warning Limit"
        )

        # 3. Initialize primary plotting lines
        x_indices: List[int] = list(range(self.max_data_points))
        
        # Real-time telemetry consumption line
        self.primary_line, = self.ax.plot(
            x_indices,
            list(self.data_history),
            color=self.ACCENT_LINE_COLOR,
            linewidth=2.0,
            antialiased=True,
            label="Power Use"
        )
        
        # Dynamic rolling average indicator line
        self.avg_line, = self.ax.plot(
            [0, self.max_data_points - 1],
            [0.0, 0.0],
            color=self.AVERAGE_LINE_COLOR,
            linestyle=":",
            linewidth=1.5,
            antialiased=True,
            label="Rolling Avg"
        )

        # 4. Text styling and label maps
        self.ax.set_title("LIVE POWER CONSUMPTION", color="#FFFFFF", fontsize=9, weight="bold", pad=8)
        self.ax.set_ylabel("Wh / km", color=self.TEXT_LABEL_COLOR, fontsize=8)
        self.ax.tick_params(axis="both", colors=self.TEXT_LABEL_COLOR, labelsize=7)
        self.ax.grid(True, color=self.GRID_LINE_COLOR, linestyle="--", linewidth=0.5)
        
        # Suppress numerical x-axis ticks for cleaner display layout
        self.ax.set_xticks([])

        # Style chart bounding boxes
        for spine in ["top", "right", "bottom", "left"]:
            self.ax.spines[spine].set_color(self.GRID_LINE_COLOR)
            self.ax.spines[spine].set_linewidth(0.8)

        # Set physical window scales
        self.ax.set_ylim(self._current_y_min, self._current_y_max)
        
        # Optimize axes layouts to prevent cropping of labels
        self.fig.set_tight_layout(True)

        # 5. Bind structures directly to CustomTkinter container frames
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)

    def update_data(self, new_val: float) -> None:
        """
        Appends the newest telemetry frame, updates plot geometry, 
        evaluates hysteresis scaling, and triggers an asynchronous redraw.
        """
        if self.canvas is None or self.primary_line is None or self.avg_line is None or self.ax is None:
            return

        # 1. Update rolling memory collection
        self.data_history.append(new_val)

        # 2. Shift real-time plot coordinate arrays
        self.primary_line.set_ydata(list(self.data_history))

        # 3. Adjust dynamic average indicators
        avg_value: float = sum(self.data_history) / len(self.data_history)
        self.avg_line.set_ydata([avg_value, avg_value])

        # 4. Hysteresis Autoscaling (prevents constant tick recalculations and visual jumping)
        data_min: float = min(self.data_history)
        data_max: float = max(self.data_history)
        
        target_ymin: float = max(self.BASE_Y_MIN, data_min - self.Y_LIMIT_PAD_DOWN)
        target_ymax: float = max(self.BASE_Y_MAX, data_max + self.Y_LIMIT_PAD_UP)

        # Only shift graph limits if values exceed threshold boundary tolerances
        delta_min: float = abs(target_ymin - self._current_y_min)
        delta_max: float = abs(target_ymax - self._current_y_max)

        if delta_min > self.Y_HYSTERESIS_THRESHOLD or delta_max > self.Y_HYSTERESIS_THRESHOLD:
            self._current_y_min = target_ymin
            self._current_y_max = target_ymax
            self.ax.set_ylim(self._current_y_min, self._current_y_max)

        # 5. Schedule paint refresh
        self.canvas.draw_idle()

    def clear(self) -> None:
        """Resets plot geometries to baseline parameters."""
        if self.primary_line is None or self.avg_line is None or self.ax is None or self.canvas is None:
            return

        self.data_history = collections.deque(
            [0.0] * self.max_data_points, 
            maxlen=self.max_data_points
        )
        self.primary_line.set_ydata(list(self.data_history))
        self.avg_line.set_ydata([0.0, 0.0])
        
        self._current_y_min = self.BASE_Y_MIN
        self._current_y_max = self.BASE_Y_MAX
        self.ax.set_ylim(self._current_y_min, self._current_y_max)
        
        self.canvas.draw_idle()

    def destroy(self) -> None:
        """
        Clean release of Tkinter frames and Matplotlib memory handles.
        Precludes active memory leaks during panel swaps.
        """
        # Clear child reference hooks
        self.primary_line = None
        self.avg_line = None
        
        # Remove widgets from Tkinter memory stack
        if self.canvas_widget is not None:
            self.canvas_widget.destroy()
            self.canvas_widget = None

        # Wipe axes and figures
        if self.ax is not None:
            self.ax.clear()
            self.ax = None

        if self.fig is not None:
            self.fig.clear()
            self.fig = None

        self.canvas = None
