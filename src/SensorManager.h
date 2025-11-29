#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>

#ifdef USE_BME280
#include <Adafruit_BME280.h>
#else
#include <Adafruit_BMP280.h>
#endif

class SensorManager {
public:
    SensorManager(int sdaPin, int sclPin);
    bool init();
    void collectReadings(int numReadings, unsigned long interval);
    
    float getAverageTemperature() const;
    float getAveragePressure() const;
    float getAverageHumidity() const;
    int getSampleCount() const;
    
private:
    int sdaPin;
    int sclPin;
    
    #ifdef USE_BME280
    Adafruit_BME280 bme;
    #else
    Adafruit_BMP280 bmp;
    #endif
    
    float tempSum;
    float pressureSum;
    float humiditySum;
    int sampleCount;
    
    void scanI2CDevices();
};

#endif // SENSOR_MANAGER_H
