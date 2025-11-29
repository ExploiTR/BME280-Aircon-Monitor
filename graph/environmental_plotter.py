#!/usr/bin/env python3
"""
Environmental Data Plotter - PyQt5 Version
Downloads data from FTP server and creates time series plots
"""

import sys
import logging
import traceback
from datetime import datetime as dt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QGridLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QProgressBar, QMessageBox,
                             QFileDialog, QGroupBox, QStatusBar)
import pandas as pd
from datetime import datetime, timedelta
import os

# Import from new modules
from ftp_manager import FTPDownloadThread
from plot_canvas import MatplotlibCanvas

# Configure logging
def setup_logging():
    """Setup comprehensive logging for the application"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | Line:%(lineno)-4d | %(message)s'
    )
    
    # Console handler only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Create application logger
    logger = logging.getLogger('EnvironmentalPlotter')
    logger.info("Logging initialized - Console output only")
    logger.info(f"Application started at {dt.now()}")
    
    return logger

# Initialize logging
logger = setup_logging()


class EnvironmentalDataPlotter(QMainWindow):
    """Main application class"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('EnvironmentalDataPlotter')
        self.logger.info("Starting Environmental Data Plotter application")
        
        self.logger.debug("Initializing main window properties")
        self.setWindowTitle("Environmental Data Plotter")
        self.setGeometry(100, 100, 1200, 800)
        
        self.data_cache = {}  # Cache downloaded indoor data
        self.outdoor_data_cache = {}  # Cache downloaded outdoor data
        self.available_dates = []
        
        self.logger.debug("Setting up user interface")
        self.setup_ui()
        
        self.logger.info("Application initialization complete")
    
    def setup_ui(self):
        """Create the user interface"""
        self.logger.debug("Creating central widget and main layout")
        
        try:
            # Central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Main layout
            main_layout = QVBoxLayout(central_widget)
            
            # FTP Connection Group
            self.logger.debug("Setting up FTP connection group")
            self.setup_ftp_group(main_layout)
            
            # Date Selection Group
            self.logger.debug("Setting up date selection group")
            self.setup_date_group(main_layout)
            
            # Plot Area
            self.logger.debug("Setting up plot area")
            self.setup_plot_area(main_layout)
            
            # Status Bar
            self.logger.debug("Setting up status bar")
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.status_bar.showMessage("Ready")
            
            self.logger.info("UI setup completed successfully")
        except Exception as e:
            self.logger.error(f"Error setting up UI: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def setup_ftp_group(self, parent_layout):
        """Setup FTP connection controls"""
        self.logger.debug("Creating FTP connection group")
        
        try:
            ftp_group = QGroupBox("FTP Connection")
            ftp_layout = QGridLayout(ftp_group)
            
            self.logger.debug("Adding FTP form fields")
            
            # Server
            ftp_layout.addWidget(QLabel("Server:"), 0, 0)
            self.server_edit = QLineEdit("192.168.0.1")
            ftp_layout.addWidget(self.server_edit, 0, 1)
            
            # Username
            ftp_layout.addWidget(QLabel("Username:"), 0, 2)
            self.username_edit = QLineEdit("admin")
            ftp_layout.addWidget(self.username_edit, 0, 3)
            
            # Password
            ftp_layout.addWidget(QLabel("Password:"), 0, 4)
            self.password_edit = QLineEdit("f6a3067773")
            self.password_edit.setEchoMode(QLineEdit.Password)
            ftp_layout.addWidget(self.password_edit, 0, 5)
            
            # Directory
            ftp_layout.addWidget(QLabel("Directory:"), 1, 0)
            self.directory_edit = QLineEdit("/G/USD_TPL/")
            ftp_layout.addWidget(self.directory_edit, 1, 1)
            
            # Connect button
            self.logger.debug("Adding connect button and progress bar")
            self.connect_btn = QPushButton("Connect & Download Files")
            self.connect_btn.clicked.connect(self.connect_and_download)
            ftp_layout.addWidget(self.connect_btn, 1, 2, 1, 2)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            ftp_layout.addWidget(self.progress_bar, 1, 4, 1, 2)
            
            parent_layout.addWidget(ftp_group)
            self.logger.debug("FTP connection group created successfully")
        except Exception as e:
            self.logger.error(f"Error setting up FTP group: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def setup_date_group(self, parent_layout):
        """Setup date selection controls"""
        self.logger.debug("Creating date selection group")
        
        try:
            date_group = QGroupBox("Date Range Selection")
            date_layout = QGridLayout(date_group)
            
            self.logger.debug("Adding date selection components")
            
            # Available dates info
            date_layout.addWidget(QLabel("Available Dates:"), 0, 0)
            self.dates_info_label = QLabel("No data loaded")
            self.dates_info_label.setStyleSheet("color: blue;")
            date_layout.addWidget(self.dates_info_label, 0, 1)
            
            # Start date
            date_layout.addWidget(QLabel("Start Date:"), 1, 0)
            self.start_date_combo = QComboBox()
            date_layout.addWidget(self.start_date_combo, 1, 1)
            
            # End date
            date_layout.addWidget(QLabel("End Date:"), 1, 2)
            self.end_date_combo = QComboBox()
            date_layout.addWidget(self.end_date_combo, 1, 3)
            
            # Plot button
            self.plot_btn = QPushButton("Generate Plot")
            self.plot_btn.clicked.connect(self.generate_plot)
            self.plot_btn.setEnabled(False)
            date_layout.addWidget(self.plot_btn, 1, 4)
            
            # Export button
            self.export_btn = QPushButton("Export Data")
            self.export_btn.clicked.connect(self.export_data)
            self.export_btn.setEnabled(False)
            date_layout.addWidget(self.export_btn, 1, 5)
            
            parent_layout.addWidget(date_group)
            self.logger.debug("Date selection group created successfully")
            
            # Smoothing controls
            date_layout.addWidget(QLabel("Smoothing:"), 2, 0)
            self.smoothing_combo = QComboBox()
            self.smoothing_combo.addItems(["None","Low (10 points)","Medium (50 points)","High (100 points)","Very High (250 points)","Extreme (500 points)"])
            date_layout.addWidget(self.smoothing_combo, 2, 1)
            
            date_layout.addWidget(QLabel("Method:"), 2, 2)
            self.smoothing_method_combo = QComboBox()
            self.smoothing_method_combo.addItems(["Median", "Mean"])
            date_layout.addWidget(self.smoothing_method_combo, 2, 3)

        except Exception as e:
            self.logger.error(f"Error setting up date group: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def setup_plot_area(self, parent_layout):
        """Setup matplotlib plot area"""
        self.logger.debug("Creating plot area")
        
        try:
            plot_group = QGroupBox("Environmental Data Plot")
            plot_layout = QVBoxLayout(plot_group)
            
            # Create matplotlib canvas
            self.logger.debug("Initializing matplotlib canvas")
            self.canvas = MatplotlibCanvas()
            plot_layout.addWidget(self.canvas)
            
            parent_layout.addWidget(plot_group)
            self.logger.debug("Plot area created successfully")
        except Exception as e:
            self.logger.error(f"Error setting up plot area: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def connect_and_download(self):
        """Connect to FTP and download all CSV files"""
        self.logger.info("Starting FTP connection and download process")
        
        try:
            server = self.server_edit.text()
            username = self.username_edit.text()
            directory = self.directory_edit.text()
            self.logger.debug(f"FTP connection details - Server: {server}, Username: {username}, Directory: {directory}")
            
            self.connect_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            
            # Start download thread
            self.logger.debug("Creating and starting FTP download thread")
            self.download_thread = FTPDownloadThread(
                server,
                username,
                self.password_edit.text(),
                directory
            )
            
            # Connect signals
            self.logger.debug("Connecting thread signals")
            self.download_thread.progress_updated.connect(self.progress_bar.setValue)
            self.download_thread.status_updated.connect(self.status_bar.showMessage)
            self.download_thread.download_complete.connect(self.on_download_complete)
            self.download_thread.download_error.connect(self.on_download_error)
            
            # Start download
            self.download_thread.start()
            self.logger.info("FTP download thread started successfully")
        except Exception as e:
            self.logger.error(f"Error starting FTP download: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            self.connect_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Failed to start download: {str(e)}")
    
    def on_download_complete(self, data_cache, outdoor_data_cache, available_dates):
        """Handle successful download completion"""
        self.logger.info(f"Download completed successfully - {len(available_dates)} files downloaded")
        self.logger.debug(f"Available dates: {available_dates}")
        
        try:
            self.data_cache = data_cache
            self.outdoor_data_cache = outdoor_data_cache
            self.available_dates = available_dates
            
            self.logger.debug("Updating date selection dropdowns")
            self.update_date_selection()
            self.connect_btn.setEnabled(True)
            
            indoor_count = len(data_cache)
            outdoor_count = len(outdoor_data_cache)
            total_files = indoor_count + outdoor_count
            
            self.logger.info("Download process completed and UI updated")
            QMessageBox.information(self, "Success", f"Downloaded {total_files} data files ({indoor_count} indoor, {outdoor_count} outdoor)")
        except Exception as e:
            self.logger.error(f"Error handling download completion: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Error processing downloaded data: {str(e)}")
    
    def on_download_error(self, error_message):
        """Handle download error"""
        self.logger.error(f"Download failed: {error_message}")
        
        try:
            self.connect_btn.setEnabled(True)
            self.status_bar.showMessage("Download failed")
            QMessageBox.critical(self, "Download Error", error_message)
        except Exception as e:
            self.logger.error(f"Error handling download error: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    def update_date_selection(self):
        """Update date selection dropdowns"""
        self.logger.debug("Updating date selection dropdowns")
        
        if not self.available_dates:
            self.logger.warning("No available dates to update selection")
            return
        
        try:
            # Update info label
            start_date = self.available_dates[0]
            end_date = self.available_dates[-1]
            self.logger.debug(f"Date range: {start_date} to {end_date} ({len(self.available_dates)} days)")
            self.dates_info_label.setText(f"{start_date} to {end_date} ({len(self.available_dates)} days)")
            
            # Update dropdowns
            self.logger.debug("Populating date dropdowns")
            self.start_date_combo.clear()
            self.end_date_combo.clear()
            self.start_date_combo.addItems(self.available_dates)
            self.end_date_combo.addItems(self.available_dates)
            
            # Set default selection
            self.start_date_combo.setCurrentText(start_date)
            self.end_date_combo.setCurrentText(end_date)
            
            # Enable buttons
            self.plot_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            
            self.logger.info("Date selection updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating date selection: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    def parse_csv_content(self, content: str) -> pd.DataFrame:
        """Parse CSV content into pandas DataFrame"""
        self.logger.debug(f"Parsing CSV content ({len(content)} characters)")
        
        try:
            lines = content.strip().split('\n')
            self.logger.debug(f"CSV has {len(lines)} lines")
            
            # Skip header if present
            data_lines = []
            for line in lines:
                if line.strip() and not line.startswith('Date,Sample'):
                    data_lines.append(line.strip())
            
            self.logger.debug(f"Found {len(data_lines)} data lines after filtering")
            
            if not data_lines:
                self.logger.warning("No data lines found in CSV content")
                return pd.DataFrame()
            
            # Parse data
            parsed_data = []
            for i, line in enumerate(data_lines):
                try:
                    parts = line.split(',')
                    if len(parts) >= 4:  # Changed from 5 to 4 to handle outdoor format
                        # Format: "DD/MM/YYYY HH:MM,sample_size,temperature,pressure[,humidity]"
                        datetime_str = parts[0].strip()  # Already contains both date and time
                        sample_size = int(parts[1].strip())
                        temperature = float(parts[2].strip())
                        pressure = float(parts[3].strip())
                        
                        # Handle humidity - might be missing or "N/A" for outdoor data
                        humidity = None
                        if len(parts) >= 5:
                            humidity_str = parts[4].strip()
                            if humidity_str.upper() not in ['N/A', 'NA', '']:
                                try:
                                    humidity = float(humidity_str)
                                except ValueError:
                                    humidity = None
                        
                        parsed_data.append({
                            'datetime': datetime_str,
                            'sample_size': sample_size,
                            'temperature': temperature,
                            'pressure': pressure,
                            'humidity': humidity if humidity is not None else pd.NA
                        })
                    else:
                        self.logger.warning(f"Line {i+1} has insufficient data ({len(parts)} parts): {line}")
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error parsing line {i+1}: {line} - {e}")
                    continue
            
            if not parsed_data:
                self.logger.warning("No valid data parsed from CSV")
                return pd.DataFrame()
            
            df = pd.DataFrame(parsed_data)
            df['datetime'] = pd.to_datetime(df['datetime'], format='%d/%m/%Y %H:%M')
            self.logger.info(f"Successfully parsed {len(df)} records from CSV")
            self.logger.debug(f"Data range: {df['datetime'].min()} to {df['datetime'].max()}")
            return df
        except Exception as e:
            self.logger.error(f"Error parsing CSV content: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def generate_plot(self):
        """Generate time series plots for selected date range"""
        self.logger.info("Starting plot generation")
        
        start_date = self.start_date_combo.currentText()
        end_date = self.end_date_combo.currentText()
        
        self.logger.debug(f"Selected date range: {start_date} to {end_date}")
        
        if not start_date or not end_date:
            self.logger.warning("No start or end date selected")
            QMessageBox.warning(self, "Selection Error", "Please select both start and end dates")
            return
        
        try:
            # Validate date range
            start_dt = datetime.strptime(start_date, "%d/%m/%Y")
            end_dt = datetime.strptime(end_date, "%d/%m/%Y")
            
            if start_dt > end_dt:
                self.logger.warning(f"Invalid date range: start ({start_date}) > end ({end_date})")
                QMessageBox.warning(self, "Date Error", "Start date must be before or equal to end date")
                return
            
            self.status_bar.showMessage("Processing data and generating plots...")
            self.logger.debug("Collecting data for selected date range")
            
            # Collect indoor data for selected range
            indoor_data = []
            outdoor_data = []
            dates_to_process = []
            
            # Find all dates in range
            current_dt = start_dt
            while current_dt <= end_dt:
                date_str = current_dt.strftime("%d/%m/%Y")
                if date_str in self.data_cache:
                    dates_to_process.append(date_str)
                current_dt += timedelta(days=1)
            
            self.logger.debug(f"Found {len(dates_to_process)} dates with indoor data in selected range")
            
            # Parse indoor data for each date
            for date_str in dates_to_process:
                self.logger.debug(f"Processing indoor data for {date_str}")
                content = self.data_cache[date_str]
                df = self.parse_csv_content(content)
                if not df.empty:
                    indoor_data.append(df)
                else:
                    self.logger.warning(f"No valid indoor data found for {date_str}")
            
            # Parse outdoor data for each date (if available)
            for date_str in dates_to_process:
                if date_str in self.outdoor_data_cache:
                    self.logger.debug(f"Processing outdoor data for {date_str}")
                    content = self.outdoor_data_cache[date_str]
                    df = self.parse_csv_content(content)
                    if not df.empty:
                        outdoor_data.append(df)
            
            self.logger.info(f"Total outdoor data files processed: {len(outdoor_data)}")
            
            if not indoor_data:
                self.logger.warning("No indoor data found in selected date range")
                QMessageBox.warning(self, "No Data", "No indoor data available for the selected date range")
                self.status_bar.showMessage("Ready")
                return
            
            # Combine indoor data
            combined_indoor_df = pd.concat(indoor_data, ignore_index=True)
            combined_indoor_df = combined_indoor_df.sort_values('datetime')
            
            # Combine outdoor data if available
            combined_outdoor_df = None
            if outdoor_data:
                combined_outdoor_df = pd.concat(outdoor_data, ignore_index=True)
                combined_outdoor_df = combined_outdoor_df.sort_values('datetime')
                self.logger.info(f"Combined outdoor data: {len(combined_outdoor_df)} total records")
            
            self.logger.info(f"Combined indoor data: {len(combined_indoor_df)} total records")
            
            # Get smoothing parameters from UI
            smoothing_text = self.smoothing_combo.currentText()
            smoothing_method = self.smoothing_method_combo.currentText().lower()
            
            # Parse window size from selection
            smoothing_map = {
                "None": 1,
                "Low (10 points)": 10,
                "Medium (50 points)": 50,
                "High (100 points)": 100,
                "Very High (250 points)": 250,
                "Extreme (500 points)": 500
            }
            smoothing_window = smoothing_map.get(smoothing_text, 1)
            
            # Create plots with smoothing
            self.logger.debug(f"Creating time series plots with {smoothing_method} smoothing (window={smoothing_window})")
            self.canvas.create_time_series_plots(combined_indoor_df, combined_outdoor_df, 
                                     smoothing_window, smoothing_method)

            
            plot_info = f"Plot generated successfully - {len(combined_indoor_df)} indoor data points"
            if combined_outdoor_df is not None:
                plot_info += f", {len(combined_outdoor_df)} outdoor data points"
            
            self.status_bar.showMessage(plot_info)
            self.logger.info("Plot generation completed successfully")
        except Exception as e:
            error_msg = f"Error generating plot: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Plot Error", error_msg)
            self.status_bar.showMessage("Plot generation failed")
    
    def export_data(self):
        """Export selected data to CSV file"""
        self.logger.info("Starting data export")
        
        start_date = self.start_date_combo.currentText()
        end_date = self.end_date_combo.currentText()
        
        self.logger.debug(f"Export date range: {start_date} to {end_date}")
        
        if not start_date or not end_date:
            self.logger.warning("No start or end date selected for export")
            QMessageBox.warning(self, "Selection Error", "Please select both start and end dates")
            return
        
        try:
            # Get save location
            self.logger.debug("Opening file save dialog")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Environmental Data", "", "CSV files (*.csv);;All files (*.*)"
            )
            
            if not filename:
                self.logger.info("Export cancelled by user")
                return
            
            self.logger.info(f"Exporting data to: {filename}")
            
            # Validate date range
            start_dt = datetime.strptime(start_date, "%d/%m/%Y")
            end_dt = datetime.strptime(end_date, "%d/%m/%Y")
            
            # Collect and combine indoor data
            indoor_data = []
            outdoor_data = []
            current_date = start_dt
            
            while current_date <= end_dt:
                date_str = current_date.strftime("%d/%m/%Y")
                if date_str in self.data_cache:
                    df = self.parse_csv_content(self.data_cache[date_str])
                    if not df.empty:
                        indoor_data.append(df)
                
                # Check for outdoor data
                if date_str in self.outdoor_data_cache:
                    df_outdoor = self.parse_csv_content(self.outdoor_data_cache[date_str])
                    if not df_outdoor.empty:
                        outdoor_data.append(df_outdoor)
                
                current_date += timedelta(days=1)
            
            if not indoor_data:
                QMessageBox.warning(self, "No Data", "No indoor data available for selected date range")
                return
            
            # Combine indoor data
            combined_indoor_df = pd.concat(indoor_data, ignore_index=True)
            combined_indoor_df = combined_indoor_df.sort_values('datetime')
            
            # Add feels like temperature to indoor data
            feels_like_temp = []
            temp_canvas = MatplotlibCanvas()  # Temporary instance for calculation
            for _, row in combined_indoor_df.iterrows():
                feels_like = temp_canvas.calculate_heat_index(row['temperature'], row['humidity'])
                feels_like_temp.append(feels_like)
            combined_indoor_df['feels_like'] = feels_like_temp
            
            # Format datetime for export
            combined_indoor_df['Date/Time'] = combined_indoor_df['datetime'].dt.strftime('%d/%m/%Y %H:%M')
            
            # Prepare export dataframe
            export_columns = ['Date/Time', 'sample_size', 'temperature', 'pressure', 'humidity', 'feels_like']
            export_df = combined_indoor_df[export_columns].copy()
            export_df.columns = ['Date/Time', 'Sample Size', 'Indoor Temperature (°C)', 'Indoor Pressure (hPa)', 'Humidity (%RH)', 'Feels Like (°C)']
            
            # Add outdoor data if available
            if outdoor_data:
                combined_outdoor_df = pd.concat(outdoor_data, ignore_index=True)
                combined_outdoor_df = combined_outdoor_df.sort_values('datetime')
                combined_outdoor_df['Date/Time'] = combined_outdoor_df['datetime'].dt.strftime('%d/%m/%Y %H:%M')
                
                outdoor_export = combined_outdoor_df[['Date/Time', 'temperature', 'pressure']]
                outdoor_export.columns = ['Date/Time', 'Outdoor Temperature (°C)', 'Outdoor Pressure (hPa)']
                
                export_df = pd.merge(export_df, outdoor_export, on='Date/Time', how='left')
            
            export_df.to_csv(filename, index=False)
            
            export_info = f"Data exported successfully to {filename}"
            if outdoor_data:
                export_info += f" (includes {len(indoor_data)} indoor and {len(outdoor_data)} outdoor data files)"
            else:
                export_info += f" (includes {len(indoor_data)} indoor data files)"
            
            QMessageBox.information(self, "Export Success", export_info)
            self.status_bar.showMessage(f"Data exported to {os.path.basename(filename)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting data: {str(e)}")


def main():
    """Main application entry point"""
    logger = logging.getLogger('main')
    logger.info("Starting Environmental Data Plotter application")
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Environmental Data Plotter")
        app.setOrganizationName("ESP32 Environmental Monitor")
        
        logger.debug("Setting application style")
        app.setStyle('Fusion')
        
        logger.debug("Creating main window")
        window = EnvironmentalDataPlotter()
        window.show()
        
        logger.info("Application started successfully, entering event loop")
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Fatal error starting application: {e}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        if 'app' in locals():
            QMessageBox.critical(None, "Fatal Error", f"Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()