#include "NetworkManager.h"

NetworkManager::NetworkManager(const char* ssid, const char* password) 
    : ssid(ssid), password(password) {}

WiFiStatus NetworkManager::connectToWiFi(unsigned long timeout) {
    Serial.printf("Connecting to WiFi: %s\n", ssid);
    
    // CRITICAL: Disable WiFi persistence to prevent flash corruption
    WiFi.persistent(false);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < timeout) {
        delay(500);
        Serial.print(".");
        yield();
        ESP.wdtFeed();
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.printf("WiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
        return WIFI_SUCCESS;
    } else {
        Serial.println("\nWiFi connection failed!");
        return checkWiFiFailureReason();
    }
}

WiFiStatus NetworkManager::checkWiFiFailureReason() {
    wl_status_t status = WiFi.status();
    
    switch (status) {
        case WL_NO_SSID_AVAIL:
            Serial.println("Reason: No AP found (SSID not available)");
            return WIFI_NO_AP_FOUND;
            
        case WL_CONNECT_FAILED:
            Serial.println("Reason: Connection failed (likely wrong password)");
            return WIFI_AUTH_FAILED;
            
        case WL_WRONG_PASSWORD:
            Serial.println("Reason: Wrong password");
            return WIFI_AUTH_FAILED;
            
        case WL_DISCONNECTED:
            Serial.println("Reason: Disconnected (timeout or signal lost)");
            return WIFI_GENERIC_FAILURE;
            
        default:
            Serial.printf("Reason: Unknown (status code: %d)\n", status);
            return WIFI_GENERIC_FAILURE;
    }
}

bool NetworkManager::syncTime(const char* ntpServer, long gmtOffset, int daylightOffset) {
    Serial.println("Syncing time with NTP server...");
    
    int ntpAttempts = 0;
    const int maxNtpAttempts = 3;
    
    while (ntpAttempts < maxNtpAttempts) {
        ntpAttempts++;
        Serial.printf("NTP attempt %d of %d\n", ntpAttempts, maxNtpAttempts);
        
        configTime(gmtOffset, daylightOffset, ntpServer);
        
        // Wait for time to be set
        int retries = 0;
        while (time(nullptr) < 100000 && retries < 10) {
            delay(1000);
            retries++;
            Serial.print(".");
            yield();
            ESP.wdtFeed();
        }
        
        if (time(nullptr) > 100000) {
            // Check if we got a valid year (not 1970)
            time_t now = time(nullptr);
            struct tm* timeinfo = localtime(&now);
            int currentYear = timeinfo->tm_year + 1900;
            
            if (currentYear > 1970) {
                Serial.println("\nTime synchronized successfully!");
                return true;
            } else {
                Serial.printf("\nNTP returned invalid year (%d), retrying...\n", currentYear);
                delay(2000);
            }
        } else {
            Serial.println("\nNTP sync timeout, retrying...");
            delay(2000);
        }
    }
    
    Serial.println("Time sync failed after all attempts!");
    return false;
}

bool NetworkManager::uploadDataToFTP(FTPClient& ftpClient, const char* basePath, 
                                     const char* filename, const String& csvData, bool createHeader) {
    Serial.println("Starting FTP upload process...");
    Serial.printf("Target file: %s\n", filename);
    Serial.printf("New data to add: %s", csvData.c_str());
    
    return ftpClient.uploadData(basePath, filename, csvData, createHeader);
}

void NetworkManager::disconnect() {
    Serial.println("Disconnecting and powering down WiFi...");
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    
    #ifdef ESP32
    esp_wifi_stop();
    #endif
    
    Serial.println("WiFi disconnected and powered down");
}

String NetworkManager::getCurrentTimeString() {
    time_t now = time(nullptr);
    struct tm* timeinfo = localtime(&now);
    
    char timeStr[20];
    strftime(timeStr, sizeof(timeStr), "%d/%m/%Y %H:%M", timeinfo);
    return String(timeStr);
}

String NetworkManager::getCurrentDateString() {
    time_t now = time(nullptr);
    struct tm* timeinfo = localtime(&now);
    
    char dateStr[20];
    strftime(dateStr, sizeof(dateStr), "%d_%m_%Y", timeinfo);
    return String(dateStr);
}
