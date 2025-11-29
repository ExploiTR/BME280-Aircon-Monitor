#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>

// Platform-specific includes
#ifdef ESP32
#include <WiFi.h>
#include <esp_wifi.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#endif

#include <time.h>
#include "FTPClient.h"

// WiFi Status Return Codes
enum WiFiStatus {
    WIFI_SUCCESS,
    WIFI_AUTH_FAILED,
    WIFI_NO_AP_FOUND,
    WIFI_GENERIC_FAILURE
};

class NetworkManager {
public:
    NetworkManager(const char* ssid, const char* password);
    
    WiFiStatus connectToWiFi(unsigned long timeout = 10000);
    bool syncTime(const char* ntpServer, long gmtOffset, int daylightOffset);
    bool uploadDataToFTP(FTPClient& ftpClient, const char* basePath, 
                        const char* filename, const String& csvData, bool createHeader);
    void disconnect();
    
    String getCurrentTimeString();
    String getCurrentDateString();
    
private:
    const char* ssid;
    const char* password;
    
    WiFiStatus checkWiFiFailureReason();
};

#endif // NETWORK_MANAGER_H
