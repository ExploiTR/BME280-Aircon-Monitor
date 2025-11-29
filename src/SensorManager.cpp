#include "SensorManager.h"

// Sensor Configuration Constants
const uint8_t BME280_ADDR_PRIMARY = 0x76;
const uint8_t BME280_ADDR_SECONDARY = 0x77;
const uint32_t I2C_CLOCK = 100000;
const unsigned long WARMUP_TIME = 2000;

#ifdef USE_BME280
const Adafruit_BME280::sensor_mode SENSOR_MODE = Adafruit_BME280::MODE_NORMAL;
const Adafruit_BME280::sensor_sampling TEMP_OVERSAMPLING = Adafruit_BME280::SAMPLING_X2;
const Adafruit_BME280::sensor_sampling PRESSURE_OVERSAMPLING = Adafruit_BME280::SAMPLING_X16;
const Adafruit_BME280::sensor_sampling HUMIDITY_OVERSAMPLING = Adafruit_BME280::SAMPLING_X1;
const Adafruit_BME280::sensor_filter FILTER_SETTING = Adafruit_BME280::FILTER_X16;
const Adafruit_BME280::standby_duration STANDBY_TIME = Adafruit_BME280::STANDBY_MS_500;
#else
const Adafruit_BMP280::sensor_mode SENSOR_MODE = Adafruit_BMP280::MODE_NORMAL;
const Adafruit_BMP280::sensor_sampling TEMP_OVERSAMPLING = Adafruit_BMP280::SAMPLING_X2;
const Adafruit_BMP280::sensor_sampling PRESSURE_OVERSAMPLING = Adafruit_BMP280::SAMPLING_X16;
const Adafruit_BMP280::sensor_filter FILTER_SETTING = Adafruit_BMP280::FILTER_X16;
const Adafruit_BMP280::standby_duration STANDBY_TIME = Adafruit_BMP280::STANDBY_MS_500;
#endif

SensorManager::SensorManager(int sda, int scl) 
    : sdaPin(sda), sclPin(scl), tempSum(0), pressureSum(0), humiditySum(0), sampleCount(0) {}

bool SensorManager::init() {
    #ifdef USE_BME280
    Serial.println("Initializing BME280 sensor...");
    #else
    Serial.println("Initializing BMP280 sensor...");
    #endif
    
    // Initialize I2C with custom pins
    Wire.begin(sdaPin, sclPin);
    Wire.setClock(I2C_CLOCK);
    
    // Give sensor time to stabilize
    delay(500);
    Serial.println("Allowing sensor to stabilize...");
    
    // Try to initialize sensor with multiple attempts
    const int maxAttempts = 3;
    bool sensorFound = false;
    
    for (int attempt = 1; attempt <= maxAttempts && !sensorFound; attempt++) {
        Serial.printf("Attempt %d/%d: Trying sensor init at primary address 0x%02X\n", 
                     attempt, maxAttempts, BME280_ADDR_PRIMARY);
        
        #ifdef USE_BME280
        sensorFound = bme.begin(BME280_ADDR_PRIMARY, &Wire);
        #else
        sensorFound = bmp.begin(BME280_ADDR_PRIMARY);
        #endif
        
        if (sensorFound) {
            Serial.printf("Sensor found at address 0x%02X on attempt %d!\n", BME280_ADDR_PRIMARY, attempt);
            break;
        }
        
        // Try alternative address
        Serial.printf("Attempt %d/%d: Trying sensor init at secondary address 0x%02X\n", 
                     attempt, maxAttempts, BME280_ADDR_SECONDARY);
        
        #ifdef USE_BME280
        sensorFound = bme.begin(BME280_ADDR_SECONDARY, &Wire);
        #else
        sensorFound = bmp.begin(BME280_ADDR_SECONDARY);
        #endif
        
        if (sensorFound) {
            Serial.printf("Sensor found at address 0x%02X on attempt %d!\n", BME280_ADDR_SECONDARY, attempt);
            break;
        }
        
        if (attempt < maxAttempts) {
            Serial.printf("Attempt %d failed, retrying in 1 second...\n", attempt);
            delay(1000);
        }
    }
    
    if (!sensorFound) {
        Serial.printf("Could not initialize sensor after %d attempts!\n", maxAttempts);
        Serial.println("Running I2C scan for debugging...");
        scanI2CDevices();
        return false;
    }
    
    // Configure sensor settings
    #ifdef USE_BME280
    bme.setSampling(SENSOR_MODE, TEMP_OVERSAMPLING, PRESSURE_OVERSAMPLING, 
                    HUMIDITY_OVERSAMPLING, FILTER_SETTING, STANDBY_TIME);
    #else
    bmp.setSampling(SENSOR_MODE, TEMP_OVERSAMPLING, PRESSURE_OVERSAMPLING, 
                    FILTER_SETTING, STANDBY_TIME);
    #endif
    
    // Allow sensor to warm up with watchdog-friendly delay
    unsigned long startWarmup = millis();
    while (millis() - startWarmup < WARMUP_TIME) {
        yield();
        ESP.wdtFeed();
        delay(100);
    }
    
    // Test reading
    Serial.println("Testing sensor readings...");
    
    #ifdef USE_BME280
    float testTemp = bme.readTemperature();
    float testPressure = bme.readPressure() / 100.0F;
    #else
    float testTemp = bmp.readTemperature();
    float testPressure = bmp.readPressure() / 100.0F;
    #endif
    
    if (isnan(testTemp) || isnan(testPressure)) {
        Serial.println("Sensor readings are invalid - sensor may not be working properly!");
        return false;
    }
    
    Serial.printf("Test readings: %.1f°C, %.1fhPa\n", testTemp, testPressure);
    
    #ifdef USE_BME280
    Serial.println("BME280 initialized successfully!");
    #else
    Serial.println("BMP280 initialized successfully!");
    #endif
    
    return true;
}

void SensorManager::collectReadings(int numReadings, unsigned long interval) {
    Serial.printf("Collecting %d sensor readings...\n", numReadings);
    
    tempSum = 0;
    pressureSum = 0;
    humiditySum = 0;
    sampleCount = 0;
    
    for (int i = 0; i < numReadings; i++) {
        #ifdef USE_BME280
        float temperature = bme.readTemperature();
        float pressure = bme.readPressure() / 100.0F;
        float humidity = bme.readHumidity();
        #else
        float temperature = bmp.readTemperature();
        float pressure = bmp.readPressure() / 100.0F;
        float humidity = 0.0;
        #endif
        
        bool tempValid = !isnan(temperature);
        bool pressureValid = !isnan(pressure);
        
        #ifdef USE_BME280
        bool humidityValid = !isnan(humidity);
        #else
        bool humidityValid = true;
        #endif
        
        if (tempValid && pressureValid && humidityValid) {
            tempSum += temperature;
            pressureSum += pressure;
            
            #ifdef USE_BME280
            humiditySum += humidity;
            Serial.printf("Reading %d: %.1f°C, %.1fhPa, %.1f%%\n", 
                         i+1, temperature, pressure, humidity);
            #else
            Serial.printf("Reading %d: %.1f°C, %.1fhPa (BMP280 - no humidity)\n", 
                         i+1, temperature, pressure);
            #endif
            
            sampleCount++;
        } else {
            Serial.printf("Reading %d: Invalid data\n", i+1);
        }
        
        // Use yield-friendly delay
        if (i < numReadings - 1) {
            unsigned long startDelay = millis();
            while (millis() - startDelay < interval) {
                yield();
                ESP.wdtFeed();
                delay(100);
            }
        }
    }
    
    Serial.printf("Collected %d valid readings out of %d attempts\n", sampleCount, numReadings);
}

float SensorManager::getAverageTemperature() const {
    return sampleCount > 0 ? tempSum / sampleCount : 0.0;
}

float SensorManager::getAveragePressure() const {
    return sampleCount > 0 ? pressureSum / sampleCount : 0.0;
}

float SensorManager::getAverageHumidity() const {
    return sampleCount > 0 ? humiditySum / sampleCount : 0.0;
}

int SensorManager::getSampleCount() const {
    return sampleCount;
}

void SensorManager::scanI2CDevices() {
    Serial.println("\n=== I2C Device Scanner ===");
    Serial.printf("Scanning I2C bus (SDA:%d, SCL:%d)...\n", sdaPin, sclPin);
    
    byte error, address;
    int nDevices = 0;
    
    for(address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        error = Wire.endTransmission();
        
        if (error == 0) {
            Serial.printf("I2C device found at address 0x%02X", address);
            if (address == 0x76 || address == 0x77) {
                Serial.print(" <- This could be BME280/BMP280!");
            }
            Serial.println();
            nDevices++;
        }
        else if (error == 4) {
            Serial.printf("Unknown error at address 0x%02X\n", address);
        }
    }
    
    if (nDevices == 0) {
        Serial.println("No I2C devices found!");
        Serial.println("\nTroubleshooting tips:");
        Serial.println("1. Check wiring:");
        Serial.println("   BMP280 VCC -> 3.3V (NOT 5V!)");
        Serial.println("   BMP280 GND -> GND");
        Serial.printf("   BMP280 SDA -> D6 (GPIO%d)\n", sdaPin);
        Serial.printf("   BMP280 SCL -> D5 (GPIO%d)\n", sclPin);
        Serial.println("2. Ensure sensor has power (LED should be on if present)");
        Serial.println("3. Check if you have BME280 instead of BMP280");
        Serial.println("4. Try different I2C pins if wiring is correct");
    } else {
        Serial.printf("Found %d I2C device(s)\n", nDevices);
    }
    Serial.println("========================\n");
}
