#!/usr/bin/env python3
"""
Matplotlib Plot Canvas Module
Custom matplotlib canvas for environmental data visualization
"""

import logging
import traceback
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter
import pandas as pd


class MatplotlibCanvas(FigureCanvas):
    """Custom matplotlib canvas for PyQt5 with smoothing + hover support"""
    
    def __init__(self, parent=None):
        self.logger = logging.getLogger('MatplotlibCanvas')
        self.logger.debug("Initializing matplotlib canvas")
        
        self.figure = Figure(figsize=(12, 8))
        super().__init__(self.figure)
        self.setParent(parent)
        
        self.logger.debug("Creating 2x2 subplot layout")
        self.axes = None  # Will be created based on view mode
        self.view_mode = 'all'  # Default view mode
        self._create_subplots()
        
        self.current_df = None
        self.current_outdoor_df = None
        self.hover_annotation = None
        
        # Connect hover event
        self.mpl_connect('motion_notify_event', self.on_hover)
        
        self.clear_plots()
        self.logger.info("Matplotlib canvas initialized successfully")
    
    def _create_subplots(self):
        """Create subplots based on view mode"""
        self.figure.clear()
        if self.view_mode == 'all':
            self.axes = self.figure.subplots(2, 2)
            self.figure.tight_layout(pad=1.5)
        else:
            # Single plot mode - maximize space
            self.axes = self.figure.add_subplot(111)
            self.figure.tight_layout(pad=0.5)
    
    def set_view_mode(self, mode: str):
        """Set the view mode and recreate subplots"""
        self.logger.info(f"Setting view mode to: {mode}")
        self.view_mode = mode
        self._create_subplots()
    
    def clear_plots(self):
        """Clear all plots"""
        self.logger.debug("Clearing all plots")
        self.current_df = None
        self.current_outdoor_df = None
        try:
            if self.axes is None:
                self._create_subplots()
            
            if self.view_mode == 'all':
                for i, ax in enumerate(self.axes.flat):
                    ax.clear()
                    self.logger.debug(f"Cleared subplot {i}")
                
                self.axes[0, 0].set_title("No Data Available")
                self.axes[0, 0].text(0.5, 0.5, "Connect to FTP and select date range\nto view environmental data", 
                                    ha='center', va='center', transform=self.axes[0, 0].transAxes, fontsize=12)
                
                for i, ax in enumerate(self.axes.flat):
                    if i > 0:
                        ax.set_visible(False)
                        self.logger.debug(f"Hid subplot {i}")
            else:
                self.axes.clear()
                self.axes.set_title("No Data Available")
                self.axes.text(0.5, 0.5, "Connect to FTP and select date range\nto view environmental data", 
                              ha='center', va='center', transform=self.axes.transAxes, fontsize=12)
            
            self.draw()
            self.logger.info("Plots cleared and canvas updated")
        except Exception as e:
            self.logger.error(f"Error clearing plots: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")

    def on_hover(self, event):
        """Handle mouse hover events to show data point values"""
        if event.inaxes is None or self.current_df is None or len(self.current_df) == 0:
            if hasattr(self, 'hover_annotation') and self.hover_annotation:
                self.hover_annotation.set_visible(False)
                self.draw_idle()
            return

        if hasattr(self, 'hover_annotation') and self.hover_annotation:
            self.hover_annotation.set_visible(False)

        ax = event.inaxes
        x_pos = event.xdata
        y_pos = event.ydata

        if x_pos is None or y_pos is None:
            self.draw_idle()
            return

        try:
            from matplotlib.dates import num2date
            hover_time = num2date(x_pos)
            if hover_time.tzinfo is not None:
                hover_time = hover_time.replace(tzinfo=None)

            time_diffs = abs(self.current_df['datetime'] - hover_time)
            closest_idx = time_diffs.idxmin()
            closest_point = self.current_df.iloc[closest_idx]

            time_tolerance = pd.Timedelta(hours=2)
            if time_diffs.iloc[closest_idx] > time_tolerance:
                return

            annotation_text = ""
            display_x = closest_point['datetime']
            display_y = 0

            # Determine what data to show based on view mode and axes
            if self.view_mode == 'all':
                if ax == self.axes[0, 0]:
                    display_y = closest_point['temperature']
                    annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nIndoor Temp: {display_y:.1f}°C"
                elif ax == self.axes[0, 1]:
                    display_y = closest_point['humidity']
                    if pd.isna(display_y):
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nHumidity: N/A"
                    else:
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nHumidity: {display_y:.1f}%RH"
                elif ax == self.axes[1, 0]:
                    display_y = closest_point['pressure']
                    annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nIndoor Pressure: {display_y:.1f}hPa"
                elif ax == self.axes[1, 1]:
                    if 'feels_like' in closest_point:
                        display_y = closest_point['feels_like']
                        actual_temp = closest_point['temperature']
                        annotation_text = (f"Time: {display_x:%d/%m/%Y %H:%M}\n"
                                           f"Feels Like: {display_y:.1f}°C\nActual: {actual_temp:.1f}°C")
                    else:
                        display_y = closest_point['temperature']
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nTemp: {display_y:.1f}°C"
            else:
                # Single view mode
                if self.view_mode == 'temp':
                    display_y = closest_point['temperature']
                    annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nIndoor Temp: {display_y:.1f}°C"
                elif self.view_mode == 'humidity':
                    display_y = closest_point['humidity']
                    if pd.isna(display_y):
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nHumidity: N/A"
                    else:
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nHumidity: {display_y:.1f}%RH"
                elif self.view_mode == 'pressure':
                    display_y = closest_point['pressure']
                    annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nIndoor Pressure: {display_y:.1f}hPa"
                elif self.view_mode == 'feels_like':
                    if 'feels_like' in closest_point:
                        display_y = closest_point['feels_like']
                        actual_temp = closest_point['temperature']
                        annotation_text = (f"Time: {display_x:%d/%m/%Y %H:%M}\n"
                                           f"Feels Like: {display_y:.1f}°C\nActual: {actual_temp:.1f}°C")
                    else:
                        display_y = closest_point['temperature']
                        annotation_text = f"Time: {display_x:%d/%m/%Y %H:%M}\nTemp: {display_y:.1f}°C"

            if annotation_text:
                # Smart tooltip positioning to avoid boundary issues
                # Get axes bounds in data coordinates
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                
                # Convert display_x to numeric for comparison
                from matplotlib.dates import date2num
                x_numeric = date2num(display_x)
                
                # Calculate relative position (0-1)
                x_rel = (x_numeric - xlim[0]) / (xlim[1] - xlim[0])
                y_rel = (display_y - ylim[0]) / (ylim[1] - ylim[0])
                
                # Adjust tooltip position based on cursor location
                if x_rel > 0.7:  # Right side - shift tooltip left
                    xytext = (-120, 40)
                else:
                    xytext = (20, 40)
                
                if y_rel > 0.7:  # Top side - shift tooltip down
                    xytext = (xytext[0], -40)
                
                self.hover_annotation = ax.annotate(
                    annotation_text,
                    xy=(display_x, display_y),
                    xytext=xytext,
                    textcoords='offset points',
                    bbox={'boxstyle': 'round,pad=0.5', 'fc': 'lightyellow', 'alpha': 0.9, 'edgecolor': 'gray'},
                    arrowprops={'arrowstyle': '->', 'connectionstyle': 'arc3,rad=0', 'color': 'gray'},
                    fontsize=9,
                    zorder=1000
                )
            self.draw_idle()

        except Exception as e:
            self.logger.debug(f"Error in hover handler: {e}")

    def calculate_heat_index(self, temp_c: float, humidity: float) -> float:
        """Calculate heat index (feels like temperature) from temperature and humidity"""
        try:
            if pd.isna(humidity):
                return temp_c
            temp_f = (temp_c * 9/5) + 32
            if temp_f < 80.0:
                return temp_c
            T, R = temp_f, humidity
            HI = (-42.379 + 2.04901523*T + 10.14333127*R - 0.22475541*T*R
                  - 6.83783e-3*T*T - 5.481717e-2*R*R + 1.22874e-3*T*T*R
                  + 8.5282e-4*T*R*R - 1.99e-6*T*T*R*R)
            if R < 13 and 80 <= T <= 112:
                HI -= ((13-R)/4) * (((17-abs(T-95))/17)**0.5)
            elif R > 85 and 80 <= T <= 87:
                HI += ((R-85)/10) * ((87-T)/5)
            return (HI - 32) * 5/9
        except Exception as e:
            self.logger.warning(f"Error calculating heat index: {e}")
            return temp_c

    # ---------------- Smoothing Helpers ----------------
    def apply_smoothing(self, df: pd.DataFrame, window: int, method: str = "median") -> pd.DataFrame:
        """Apply smoothing to numeric columns using median or mean"""
        if window <= 1:
            return df
        
        df_smoothed = df.copy()
        for col in ["temperature", "humidity", "pressure"]:
            if col in df_smoothed.columns:
                if method.lower() == "median":
                    df_smoothed[col] = df_smoothed[col].rolling(window, min_periods=1, center=True).median()
                else:  # mean
                    df_smoothed[col] = df_smoothed[col].rolling(window, min_periods=1, center=True).mean()
        return df_smoothed
    # ---------------------------------------------------

    def create_time_series_plots(self, indoor_df: pd.DataFrame, outdoor_df: pd.DataFrame = None, 
                                smoothing_window: int = 1, smoothing_method: str = "median"):
        """Create time series plots with user-controlled smoothing"""
        self.logger.info(f"Creating time series plots for {len(indoor_df)} indoor data points")
        if outdoor_df is not None and not outdoor_df.empty:
            self.logger.info(f"Also plotting {len(outdoor_df)} outdoor data points")
        
        # Apply smoothing based on user selection
        if smoothing_window > 1:
            self.logger.info(f"Applying {smoothing_method} smoothing with window={smoothing_window}")
            indoor_df = self.apply_smoothing(indoor_df, smoothing_window, smoothing_method)
            if outdoor_df is not None and not outdoor_df.empty:
                outdoor_df = self.apply_smoothing(outdoor_df, smoothing_window, smoothing_method)
        
        # Store DataFrame for hover functionality
        self.current_df = indoor_df.copy()
        self.current_outdoor_df = outdoor_df
        
        try:
            # Calculate feels like temperature
            feels_like_temp = []
            for _, row in indoor_df.iterrows():
                feels_like = self.calculate_heat_index(row['temperature'], row['humidity'])
                feels_like_temp.append(feels_like)
            self.current_df['feels_like'] = feels_like_temp
            
            if self.view_mode == 'all':
                self._plot_all_views(indoor_df, outdoor_df, feels_like_temp)
            else:
                self._plot_single_view(indoor_df, outdoor_df, feels_like_temp)
            
            self.figure.tight_layout(pad=0.5 if self.view_mode != 'all' else 1.5)
            self.draw()
            self.logger.info("Time series plots created and displayed successfully")
        except Exception as e:
            self.logger.error(f"Error creating time series plots: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _plot_all_views(self, indoor_df: pd.DataFrame, outdoor_df: pd.DataFrame, feels_like_temp: list):
        """Plot all 4 graphs in 2x2 grid"""
        self.logger.debug("Clearing previous plots")
        for ax in self.axes.flat:
            ax.clear()
            ax.set_visible(True)
        
        # Plot 1: Temperature (Indoor and Outdoor)
        self.logger.debug("Creating temperature plot")
        self.axes[0, 0].plot(indoor_df['datetime'], indoor_df['temperature'], 'r-', linewidth=1.5, label='Indoor Temperature')
        if outdoor_df is not None and not outdoor_df.empty:
            self.axes[0, 0].plot(outdoor_df['datetime'], outdoor_df['temperature'], 'orange', linewidth=1.5, label='Outdoor Temperature')
        
        self.axes[0, 0].set_title('Temperature Over Time', fontsize=10)
        self.axes[0, 0].set_ylabel('Temperature (°C)', fontsize=9)
        self.axes[0, 0].grid(True, alpha=0.3)
        self.axes[0, 0].tick_params(axis='x', rotation=45, labelsize=8)
        self.axes[0, 0].tick_params(axis='y', labelsize=8)
        self.axes[0, 0].legend(fontsize=8)
        
        # Plot 2: Humidity (Indoor only)
        self.logger.debug("Creating humidity plot")
        self.axes[0, 1].plot(indoor_df['datetime'], indoor_df['humidity'], 'b-', linewidth=1.5, label='Indoor Humidity')
        self.axes[0, 1].set_title('Humidity Over Time (Indoor Only)', fontsize=10)
        self.axes[0, 1].set_ylabel('Humidity (%RH)', fontsize=9)
        self.axes[0, 1].grid(True, alpha=0.3)
        self.axes[0, 1].tick_params(axis='x', rotation=45, labelsize=8)
        self.axes[0, 1].tick_params(axis='y', labelsize=8)
        self.axes[0, 1].legend(fontsize=8)
        
        # Plot 3: Pressure (Indoor and Outdoor)
        self.logger.debug("Creating pressure plot")
        self.axes[1, 0].plot(indoor_df['datetime'], indoor_df['pressure'], 'g-', linewidth=1.5, label='Indoor Pressure')
        if outdoor_df is not None and not outdoor_df.empty:
            # Subtract 1 from outdoor pressure values for calibration
            self.axes[1, 0].plot(outdoor_df['datetime'], outdoor_df['pressure'] - 1, 'purple', linewidth=1.5, label='Outdoor Pressure')
        
        self.axes[1, 0].set_title('Atmospheric Pressure Over Time', fontsize=10)
        self.axes[1, 0].set_ylabel('Pressure (hPa)', fontsize=9)
        self.axes[1, 0].grid(True, alpha=0.3)
        self.axes[1, 0].tick_params(axis='x', rotation=45, labelsize=8)
        self.axes[1, 0].tick_params(axis='y', labelsize=8)
        self.axes[1, 0].legend(fontsize=8)
        
        # Fix Y-axis formatting to prevent scientific notation
        pressure_formatter = ScalarFormatter(useOffset=False)
        pressure_formatter.set_scientific(False)
        self.axes[1, 0].yaxis.set_major_formatter(pressure_formatter)
        
        # Set Y-axis limits to show proper pressure range
        all_pressure_values = indoor_df['pressure'].dropna().tolist()
        if outdoor_df is not None and not outdoor_df.empty:
            all_pressure_values.extend(outdoor_df['pressure'].dropna().tolist())
        if all_pressure_values:
            min_pressure = min(all_pressure_values)
            max_pressure = max(all_pressure_values)
            pressure_range = max_pressure - min_pressure
            padding = max(pressure_range * 0.05, 1)  # 5% padding or minimum 1 hPa
            self.axes[1, 0].set_ylim(min_pressure - padding, max_pressure + padding)
        
        # Plot 4: Feels Like Temperature (Heat Index)
        self.logger.debug("Creating feels like temperature plot")
        indoor_df_copy = indoor_df.copy()
        indoor_df_copy['feels_like'] = feels_like_temp
        
        self.axes[1, 1].plot(indoor_df_copy['datetime'], indoor_df_copy['feels_like'], 'darkred', linewidth=1.5, marker='o', markersize=1, label='Feels Like')
        self.axes[1, 1].plot(indoor_df_copy['datetime'], indoor_df_copy['temperature'], 'lightcoral', linewidth=1, alpha=0.7, label='Actual Temp')
        self.axes[1, 1].set_title('Feels Like Temperature Over Time', fontsize=10)
        self.axes[1, 1].set_ylabel('Temperature (°C)', fontsize=9)
        self.axes[1, 1].set_xlabel('Date/Time', fontsize=9)
        self.axes[1, 1].grid(True, alpha=0.3)
        self.axes[1, 1].tick_params(axis='x', rotation=45, labelsize=8)
        self.axes[1, 1].tick_params(axis='y', labelsize=8)
        self.axes[1, 1].legend(fontsize=8)
    
    def _plot_single_view(self, indoor_df: pd.DataFrame, outdoor_df: pd.DataFrame, feels_like_temp: list):
        """Plot a single graph in full view"""
        self.logger.debug(f"Creating single view plot for: {self.view_mode}")
        self.axes.clear()
        
        if self.view_mode == 'temp':
            self.axes.plot(indoor_df['datetime'], indoor_df['temperature'], 'r-', linewidth=2, label='Indoor Temperature')
            if outdoor_df is not None and not outdoor_df.empty:
                self.axes.plot(outdoor_df['datetime'], outdoor_df['temperature'], 'orange', linewidth=2, label='Outdoor Temperature')
            self.axes.set_title('Temperature Over Time', fontsize=14, fontweight='bold')
            self.axes.set_ylabel('Temperature (°C)', fontsize=12)
            
        elif self.view_mode == 'humidity':
            self.axes.plot(indoor_df['datetime'], indoor_df['humidity'], 'b-', linewidth=2, label='Indoor Humidity')
            self.axes.set_title('Humidity Over Time (Indoor Only)', fontsize=14, fontweight='bold')
            self.axes.set_ylabel('Humidity (%RH)', fontsize=12)
            
        elif self.view_mode == 'pressure':
            self.axes.plot(indoor_df['datetime'], indoor_df['pressure'], 'g-', linewidth=2, label='Indoor Pressure')
            if outdoor_df is not None and not outdoor_df.empty:
                self.axes.plot(outdoor_df['datetime'], outdoor_df['pressure'] - 1, 'purple', linewidth=2, label='Outdoor Pressure')
            self.axes.set_title('Atmospheric Pressure Over Time', fontsize=14, fontweight='bold')
            self.axes.set_ylabel('Pressure (hPa)', fontsize=12)
            
            # Fix Y-axis formatting
            pressure_formatter = ScalarFormatter(useOffset=False)
            pressure_formatter.set_scientific(False)
            self.axes.yaxis.set_major_formatter(pressure_formatter)
            
            # Set Y-axis limits
            all_pressure_values = indoor_df['pressure'].dropna().tolist()
            if outdoor_df is not None and not outdoor_df.empty:
                all_pressure_values.extend(outdoor_df['pressure'].dropna().tolist())
            if all_pressure_values:
                min_pressure = min(all_pressure_values)
                max_pressure = max(all_pressure_values)
                pressure_range = max_pressure - min_pressure
                padding = max(pressure_range * 0.05, 1)
                self.axes.set_ylim(min_pressure - padding, max_pressure + padding)
                
        elif self.view_mode == 'feels_like':
            indoor_df_copy = indoor_df.copy()
            indoor_df_copy['feels_like'] = feels_like_temp
            self.axes.plot(indoor_df_copy['datetime'], indoor_df_copy['feels_like'], 'darkred', linewidth=2, marker='o', markersize=2, label='Feels Like')
            self.axes.plot(indoor_df_copy['datetime'], indoor_df_copy['temperature'], 'lightcoral', linewidth=1.5, alpha=0.7, label='Actual Temp')
            self.axes.set_title('Feels Like Temperature Over Time', fontsize=14, fontweight='bold')
            self.axes.set_ylabel('Temperature (°C)', fontsize=12)
        
        self.axes.set_xlabel('Date/Time', fontsize=12)
        self.axes.grid(True, alpha=0.3)
        self.axes.tick_params(axis='x', rotation=45, labelsize=10)
        self.axes.tick_params(axis='y', labelsize=10)
        self.axes.legend(fontsize=10)
