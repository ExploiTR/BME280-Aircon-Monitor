#include <Arduino.h>

// Platform-specific includes
#ifdef ESP32
#include <esp_bt.h>
#include <esp_wifi.h>
#include <esp_sleep.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#endif

#include "LedManager.h"
#include "SensorManager.h"
#include "NetworkManager.h"
#include "FTPClient.h"

// =============================================================================
// CONFIGURABLE PARAMETERS
// =============================================================================

// I2C Configuration
#ifndef SDA_PIN
#define SDA_PIN 21  // Default for ESP32
#endif
#ifndef SCL_PIN
#define SCL_PIN 22  // Default for ESP32
#endif

// Serial Communication
const uint32_t SERIAL_BAUD = 115200;

// Sleep and Wake Configuration
const uint64_t SLEEP_TIME_US = 5 * 60 * 1000000ULL;  // 5 minutes
const int READINGS_PER_CYCLE = 5;
const unsigned long READING_INTERVAL = 3000;

// WiFi Configuration
const char* WIFI_SSID = "AX72-IoT";
const char* WIFI_PASSWORD = "SecureIoT_Ax72";
const unsigned long WIFI_TIMEOUT = 10000;

// NTP Configuration
const char* NTP_SERVER = "time.google.com";
const long GMT_OFFSET_SEC = 5.5 * 3600;  // IST UTC+5:30
const int DAYLIGHT_OFFSET_SEC = 0;

// FTP Configuration
const char* FTP_SERVER = "192.168.0.1";
const int FTP_PORT = 21;
const char* FTP_USER = "admin";
const char* FTP_PASSWORD = "f6a3067773";
const char* FTP_BASE_PATH = "/G/USD_TPL/";

#ifndef FILENAME_SUFFIX
#define FILENAME_SUFFIX ""
#endif

// =============================================================================
// GLOBAL OBJECTS
// =============================================================================

LedManager led;
SensorManager sensor(SDA_PIN, SCL_PIN);
NetworkManager network(WIFI_SSID, WIFI_PASSWORD);
FTPClient ftpClient;

// =============================================================================
// FUNCTION DECLARATIONS
// =============================================================================

void optimizePowerConsumption();
void goToSleep();
String getCSVFilename();

// =============================================================================
// SETUP
// =============================================================================

void setup() {
    // Initialize serial communication
    Serial.begin(SERIAL_BAUD);
    delay(2000);
    
    // Initialize LED
    led.init();
    
    // Signal startup
    led.signal(STARTUP);
    
    // Check reset cause for ESP8266
    #ifdef ESP8266
    String resetReason = ESP.getResetReason();
    Serial.printf("Reset reason: %s\n", resetReason.c_str());
    
    if (resetReason.indexOf("Exception") >= 0 || resetReason.indexOf("Watchdog") >= 0) {
        Serial.println("Previous crash detected - adding safety delay");
        delay(5000);
    }
    #endif
    
    #ifdef ESP32
    Serial.println("\n=== ESP32 BME280 Environmental Logger ===");
    Serial.println("Device: ESP32 WROOM-32");
    Serial.printf("I2C Pins: SDA=%d, SCL=%d\n", SDA_PIN, SCL_PIN);
    Serial.println("Sensor: BME280 (Temp + Pressure + Humidity)");
    Serial.println("File suffix: (none) - indoor sensor");
    #elif defined(ESP8266)
    Serial.println("\n=== ESP8266 BMP280 Environmental Logger ===");
    Serial.println("Device: ESP8266 NodeMCU v2");
    Serial.printf("I2C Pins: SDA=%d (D6), SCL=%d (D5)\n", SDA_PIN, SCL_PIN);
    Serial.println("Sensor: BMP280 (Temp + Pressure only)");
    Serial.println("File suffix: _outside - outdoor sensor");
    #endif
    
    Serial.println("Wake up from sleep - starting data collection cycle");
    
    // Optimize power consumption
    optimizePowerConsumption();
    
    // Initialize sensor
    if (!sensor.init()) {
        Serial.println("Failed to initialize sensor. Going to sleep...");
        led.signal(SENSOR_FAILURE);
        goToSleep();
        return;
    }
    
    // Collect sensor readings
    sensor.collectReadings(READINGS_PER_CYCLE, READING_INTERVAL);
    
    // Show WiFi connecting pattern
    led.signal(WIFI_CONNECTING);
    
    // Connect to WiFi
    WiFiStatus wifiStatus = network.connectToWiFi(WIFI_TIMEOUT);
    
    if (wifiStatus != WIFI_SUCCESS) {
        Serial.println("WiFi connection failed. Going to sleep...");
        
        // Show appropriate LED pattern based on failure reason
        if (wifiStatus == WIFI_AUTH_FAILED) {
            led.signal(WIFI_AUTH_FAIL);
        } else if (wifiStatus == WIFI_NO_AP_FOUND) {
            led.signal(WIFI_NO_AP);
        } else {
            led.signal(WIFI_NO_AP);  // Generic failure
        }
        
        goToSleep();
        return;
    }
    
    // WiFi connected successfully
    led.signal(WIFI_CONNECTED);
    
    // Sync time
    if (!network.syncTime(NTP_SERVER, GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC)) {
        Serial.println("Time sync failed. Continuing with system time...");
    }
    
    // Calculate averages
    float avgTemp = sensor.getAverageTemperature();
    float avgPressure = sensor.getAveragePressure();
    float avgHumidity = sensor.getAverageHumidity();
    int sampleCount = sensor.getSampleCount();
    
    #ifdef USE_BME280
    Serial.printf("Data collected: %d samples\n", sampleCount);
    Serial.printf("Averages - Temp: %.1f°C, Pressure: %.1fhPa, Humidity: %.2f%%\n", 
                 avgTemp, avgPressure, avgHumidity);
    #else
    Serial.printf("Data collected: %d samples\n", sampleCount);
    Serial.printf("Averages - Temp: %.1f°C, Pressure: %.1fhPa (BMP280 - no humidity)\n", 
                 avgTemp, avgPressure);
    #endif
    
    // Prepare CSV data
    String filename = getCSVFilename();
    String currentTime = network.getCurrentTimeString();
    
    #ifdef USE_BME280
    String csvData = currentTime + "," + String(sampleCount) + "," + 
                    String(avgTemp, 1) + "," + String(avgPressure, 1) + "," + 
                    String(avgHumidity, 2) + "\r\n";
    #else
    String csvData = currentTime + "," + String(sampleCount) + "," + 
                    String(avgTemp, 1) + "," + String(avgPressure, 1) + "," + 
                    "N/A\r\n";
    #endif
    
    // Upload data to FTP
    ftpClient.setServer(FTP_SERVER, FTP_PORT);
    ftpClient.setCredentials(FTP_USER, FTP_PASSWORD);
    
    bool uploadSuccess = network.uploadDataToFTP(ftpClient, FTP_BASE_PATH, 
                                                  filename.c_str(), csvData, true);
    
    if (uploadSuccess) {
        Serial.println("Data upload successful!");
    } else {
        Serial.println("Data upload failed!");
        led.signal(FTP_FAILURE);
    }
    
    // Disconnect WiFi
    network.disconnect();
    
    // Signal sleep entry
    led.signal(SLEEP_ENTRY);
    
    // Go to sleep
    Serial.println("Going to sleep for 5 minutes...");
    goToSleep();
}

void loop() {
    // This should never be reached due to deep sleep
    Serial.println("ERROR: loop() reached unexpectedly!");
    goToSleep();
}

// =============================================================================
// FUNCTION IMPLEMENTATIONS
// =============================================================================

String getCSVFilename() {
    String filename = network.getCurrentDateString() + FILENAME_SUFFIX + ".csv";
    return filename;
}

void optimizePowerConsumption() {
    Serial.println("Optimizing power consumption...");
    
    #ifdef ESP32
    esp_bt_controller_disable();
    esp_wifi_stop();
    #elif defined(ESP8266)
    WiFi.mode(WIFI_OFF);
    #endif
    
    Serial.println("Power optimization complete");
}

void goToSleep() {
    Serial.println("Configuring deep sleep...");
    
    // Ensure WiFi is properly disabled
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    
    #ifdef ESP32
    esp_wifi_stop();
    esp_sleep_enable_timer_wakeup(SLEEP_TIME_US);
    
    Serial.println("Entering deep sleep now");
    Serial.flush();
    esp_deep_sleep_start();
    
    #elif defined(ESP8266)
    uint32_t sleep_time_seconds = SLEEP_TIME_US / 1000000;
    
    Serial.println("IMPORTANT: Ensure GPIO16 (D0) is connected to RST pin for auto-wake!");
    Serial.println("Entering deep sleep now");
    
    Serial.flush();
    delay(100);
    
    // Use WAKE_RF_DEFAULT to maintain WiFi calibration
    ESP.deepSleep(SLEEP_TIME_US, WAKE_RF_DEFAULT);
    #endif
}
