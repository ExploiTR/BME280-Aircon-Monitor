#!/usr/bin/env python3
"""
FTP Data Manager Module
Handles FTP connection and data download for environmental data
"""

import sys
import logging
import traceback
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
import pandas as pd
import ftplib
import io
import re
from typing import List, Optional


class FTPDataManager:
    """Handles FTP connection and data download"""
    
    def __init__(self):
        self.logger = logging.getLogger('FTPDataManager')
        self.logger.debug("FTPDataManager initialized")
        self.host = ""
        self.username = ""
        self.password = ""
        self.directory = ""
        self.connection = None
    
    def connect(self, host: str, username: str, password: str, directory: str = "") -> bool:
        """Connect to FTP server"""
        self.logger.info(f"Attempting FTP connection to {host}:21")
        self.logger.debug(f"Connection parameters - Host: {host}, Username: {username}, Directory: '{directory}'")
        
        try:
            self.host = host
            self.username = username
            self.password = password
            self.directory = directory
            
            self.logger.debug("Creating FTP connection object")
            self.connection = ftplib.FTP()
            
            self.logger.debug(f"Connecting to {host}:21 with 30s timeout")
            self.connection.connect(host, 21, timeout=30)
            self.logger.info("TCP connection to FTP server established")
            
            self.logger.debug(f"Logging in with username: {username}")
            self.connection.login(username, password)
            self.logger.info("FTP login successful")
            
            if directory:
                self.logger.debug(f"Changing to directory: {directory}")
                self.connection.cwd(directory)
                self.logger.info(f"Successfully changed to directory: {directory}")
            else:
                self.logger.debug("No directory specified, staying in root")
            
            self.logger.info("FTP connection fully established")
            return True
            
        except ftplib.error_perm as e:
            self.logger.error(f"FTP Permission error: {e}")
            return False
        except ftplib.error_temp as e:
            self.logger.error(f"FTP Temporary error: {e}")
            return False
        except ConnectionRefusedError as e:
            self.logger.error(f"Connection refused: {e}")
            return False
        except TimeoutError as e:
            self.logger.error(f"Connection timeout: {e}")
            return False
        except OSError as e:
            self.logger.error(f"Network error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected FTP connection error: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def disconnect(self):
        """Disconnect from FTP server"""
        self.logger.debug("Attempting to disconnect from FTP server")
        
        if self.connection:
            try:
                self.logger.debug("Sending QUIT command to FTP server")
                self.connection.quit()
                self.logger.info("FTP connection closed gracefully")
            except (ftplib.error_temp, ftplib.error_perm, OSError) as e:
                self.logger.warning(f"Error during graceful disconnect: {e}, forcing close")
                try:
                    self.connection.close()
                    self.logger.info("FTP connection forcefully closed")
                except Exception as e:
                    self.logger.error(f"Error forcing connection close: {e}")
            
            self.connection = None
            self.logger.debug("FTP connection object cleared")
        else:
            self.logger.debug("No active FTP connection to disconnect")
    
    def list_csv_files(self) -> List[str]:
        """List all CSV files on the FTP server"""
        self.logger.info("Starting to list CSV files on FTP server")
        
        if not self.connection:
            self.logger.error("No active FTP connection available")
            return []
        
        try:
            self.logger.debug("Executing LIST command on FTP server")
            file_list = []
            self.connection.retrlines('LIST', file_list.append)
            self.logger.debug(f"Received {len(file_list)} file entries from server")
            
            csv_files = []
            for i, line in enumerate(file_list):
                self.logger.debug(f"Processing file entry {i+1}: {line}")
                
                # Parse FTP LIST output (format may vary by server)
                parts = line.split()
                if len(parts) >= 9 and parts[-1].endswith('.csv'):
                    filename = parts[-1]
                    self.logger.debug(f"Found CSV file: {filename}")
                    
                    # Look for date pattern DD_MM_YYYY.csv or DD_MM_YYYY_outside.csv
                    if re.match(r'\d{2}_\d{2}_\d{4}\.csv', filename) or re.match(r'\d{2}_\d{2}_\d{4}_outside\.csv', filename):
                        csv_files.append(filename)
                        self.logger.debug(f"CSV file matches date pattern: {filename}")
                    else:
                        self.logger.debug(f"CSV file does not match date pattern: {filename}")
                else:
                    self.logger.debug(f"File entry ignored (not CSV or invalid format): {line}")
            
            sorted_files = sorted(csv_files)
            self.logger.info(f"Found {len(sorted_files)} valid CSV files with date pattern")
            self.logger.debug(f"CSV files found: {sorted_files}")
            
            return sorted_files
            
        except ftplib.error_perm as e:
            self.logger.error(f"Permission error listing files: {e}")
            return []
        except ftplib.error_temp as e:
            self.logger.error(f"Temporary error listing files: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error listing files: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def download_file(self, filename: str) -> Optional[str]:
        """Download a file and return its content as string"""
        self.logger.info(f"Starting download of file: {filename}")
        
        if not self.connection:
            self.logger.error("No active FTP connection available for download")
            return None
        
        try:
            self.logger.debug(f"Creating binary buffer for file: {filename}")
            file_content = io.BytesIO()
            
            self.logger.debug(f"Executing RETR command for: {filename}")
            self.connection.retrbinary(f'RETR {filename}', file_content.write)
            
            file_size = file_content.tell()
            self.logger.debug(f"Downloaded {file_size} bytes from {filename}")
            
            self.logger.debug(f"Decoding content from {filename} as UTF-8")
            content = file_content.getvalue().decode('utf-8')
            
            lines_count = len(content.split('\n'))
            self.logger.info(f"Successfully downloaded {filename}: {file_size} bytes, {lines_count} lines")
            self.logger.debug(f"First 100 characters of {filename}: {content[:100]}")
            
            return content
            
        except ftplib.error_perm as e:
            self.logger.error(f"Permission error downloading {filename}: {e}")
            return None
        except ftplib.error_temp as e:
            self.logger.error(f"Temporary error downloading {filename}: {e}")
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"UTF-8 decode error for {filename}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {filename}: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return None


class FTPDownloadThread(QThread):
    """Thread for downloading FTP data without blocking UI"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    download_complete = pyqtSignal(dict, dict, list)
    download_error = pyqtSignal(str)
    
    def __init__(self, host, username, password, directory):
        super().__init__()
        self.logger = logging.getLogger('FTPDownloadThread')
        self.logger.debug("FTPDownloadThread initialized")
        
        self.host = host
        self.username = username
        self.password = password
        self.directory = directory
        
        self.logger.debug(f"Thread configured - Host: {host}, Username: {username}, Directory: '{directory}'")
    
    def run(self):
        """Run the download process in a separate thread"""
        self.logger.info("Starting FTP download thread")
        ftp_manager = FTPDataManager()
        
        try:
            self.logger.debug("Emitting connection status update")
            self.status_updated.emit("Connecting to FTP server...")
            
            self.logger.info("Initiating FTP connection from thread")
            # Connect to FTP
            success = ftp_manager.connect(self.host, self.username, self.password, self.directory)
            
            if not success:
                error_msg = "Failed to connect to FTP server"
                self.logger.error(error_msg)
                self.download_error.emit(error_msg)
                return
            
            self.logger.info("FTP connection successful, proceeding to file listing")
            self.status_updated.emit("Listing CSV files...")
            
            # Get list of CSV files
            csv_files = ftp_manager.list_csv_files()
            self.logger.debug(f"Retrieved file list: {csv_files}")
            
            if not csv_files:
                error_msg = "No CSV files found on the server"
                self.logger.warning(error_msg)
                self.download_error.emit(error_msg)
                return
            
            self.logger.info(f"Found {len(csv_files)} CSV files to download")
            self.status_updated.emit(f"Found {len(csv_files)} files. Downloading...")
            
            # Download all files
            data_cache = {}
            outdoor_data_cache = {}
            available_dates = []
            
            for i, filename in enumerate(csv_files):
                progress = int((i / len(csv_files)) * 100)
                self.logger.debug(f"Download progress: {progress}% ({i+1}/{len(csv_files)})")
                self.progress_updated.emit(progress)
                self.status_updated.emit(f"Downloading {filename}...")
                
                self.logger.info(f"Downloading file {i+1}/{len(csv_files)}: {filename}")
                content = ftp_manager.download_file(filename)
                
                if content:
                    self.logger.debug(f"Successfully downloaded {filename}, processing date")
                    
                    # Check if it's an outdoor file
                    is_outdoor = filename.endswith('_outside.csv')
                    
                    # Parse date from filename
                    if is_outdoor:
                        date_match = re.match(r'(\d{2})_(\d{2})_(\d{4})_outside\.csv', filename)
                    else:
                        date_match = re.match(r'(\d{2})_(\d{2})_(\d{4})\.csv', filename)
                    
                    if date_match:
                        day, month, year = date_match.groups()
                        date_str = f"{day}/{month}/{year}"
                        
                        if is_outdoor:
                            outdoor_data_cache[date_str] = content
                            self.logger.debug(f"Outdoor file {filename} mapped to date: {date_str}")
                            self.logger.debug(f"Outdoor content preview: {content[:150]}")
                        else:
                            data_cache[date_str] = content
                            self.logger.debug(f"Indoor file {filename} mapped to date: {date_str}")
                        
                        # Add to available dates if not already present
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                    else:
                        self.logger.warning(f"File {filename} does not match expected date pattern")
                else:
                    self.logger.error(f"Failed to download content for {filename}")
            
            self.logger.info("Disconnecting from FTP server")
            # Disconnect from FTP
            ftp_manager.disconnect()
            
            self.logger.debug(f"Sorting {len(available_dates)} dates")
            # Sort dates
            available_dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
            self.logger.debug(f"Sorted dates: {available_dates}")
            
            # Summary logging
            indoor_count = len(data_cache)
            outdoor_count = len(outdoor_data_cache)
            self.logger.info(f"Download summary: {indoor_count} indoor files, {outdoor_count} outdoor files")
            self.logger.debug(f"Indoor dates: {list(data_cache.keys())}")
            self.logger.debug(f"Outdoor dates: {list(outdoor_data_cache.keys())}")
            
            self.logger.info(f"Download process completed successfully: {len(available_dates)} unique dates")
            self.progress_updated.emit(100)
            self.status_updated.emit(f"Successfully downloaded {indoor_count + outdoor_count} files ({indoor_count} indoor, {outdoor_count} outdoor)")
            self.download_complete.emit(data_cache, outdoor_data_cache, available_dates)
            
        except Exception as e:
            error_msg = f"Error during download: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            self.download_error.emit(error_msg)
        finally:
            self.logger.debug("Ensuring FTP connection is closed in finally block")
            ftp_manager.disconnect()
            self.logger.info("FTP download thread completed")
