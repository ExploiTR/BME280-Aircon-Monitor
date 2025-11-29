#ifndef LED_MANAGER_H
#define LED_MANAGER_H

#include <Arduino.h>

// LED Pattern Definitions
enum LedPattern {
    STARTUP,              // 3 Quick Blinks (System Alive)
    WIFI_CONNECTING,      // Fast continuous blinking (100ms)
    WIFI_CONNECTED,       // Solid ON for 2 seconds
    WIFI_AUTH_FAIL,       // 5 Fast Blinks + 1 Long (Wrong Credentials/Corrupt Flash)
    WIFI_NO_AP,           // 2 Long Blinks (Timeout)
    SENSOR_FAILURE,       // 3 Long Blinks
    FTP_FAILURE,          // 4 Short Blinks
    SLEEP_ENTRY           // 1 Long Fade/Blink (Goodbye)
};

class LedManager {
public:
    LedManager(int pin = LED_BUILTIN);
    void init();
    void signal(LedPattern pattern);
    
private:
    int ledPin;
    void blink(int times, int onDuration, int offDuration);
    void blinkSequence(int fastBlinks, int longBlinks, int fastDuration, int longDuration);
    void solidOn(int duration);
};

#endif // LED_MANAGER_H
