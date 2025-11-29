#include "LedManager.h"

LedManager::LedManager(int pin) : ledPin(pin) {}

void LedManager::init() {
    pinMode(ledPin, OUTPUT);
    digitalWrite(ledPin, LOW);
}

void LedManager::blink(int times, int onDuration, int offDuration) {
    for (int i = 0; i < times; i++) {
        digitalWrite(ledPin, HIGH);
        delay(onDuration);
        digitalWrite(ledPin, LOW);
        if (i < times - 1) { // Don't delay after last blink
            delay(offDuration);
        }
    }
}

void LedManager::blinkSequence(int fastBlinks, int longBlinks, int fastDuration, int longDuration) {
    // Fast blinks
    for (int i = 0; i < fastBlinks; i++) {
        digitalWrite(ledPin, HIGH);
        delay(fastDuration);
        digitalWrite(ledPin, LOW);
        delay(fastDuration);
    }
    
    // Pause between sequences
    delay(300);
    
    // Long blinks
    for (int i = 0; i < longBlinks; i++) {
        digitalWrite(ledPin, HIGH);
        delay(longDuration);
        digitalWrite(ledPin, LOW);
        if (i < longBlinks - 1) {
            delay(300);
        }
    }
}

void LedManager::solidOn(int duration) {
    digitalWrite(ledPin, HIGH);
    delay(duration);
    digitalWrite(ledPin, LOW);
}

void LedManager::signal(LedPattern pattern) {
    switch (pattern) {
        case STARTUP:
            // 3 Quick Blinks (System Alive)
            blink(3, 150, 150);
            delay(500);
            break;
            
        case WIFI_CONNECTING:
            // Fast continuous blinking (100ms) - run for ~2 seconds
            blink(10, 100, 100);
            break;
            
        case WIFI_CONNECTED:
            // Solid ON for 2 seconds
            solidOn(2000);
            delay(500);
            break;
            
        case WIFI_AUTH_FAIL:
            // 5 Fast Blinks + 1 Long (Wrong Credentials/Corrupt Flash)
            blinkSequence(5, 1, 100, 800);
            delay(500);
            break;
            
        case WIFI_NO_AP:
            // 2 Long Blinks (Timeout)
            blink(2, 800, 300);
            delay(500);
            break;
            
        case SENSOR_FAILURE:
            // 3 Long Blinks
            blink(3, 800, 300);
            delay(500);
            break;
            
        case FTP_FAILURE:
            // 4 Short Blinks
            blink(4, 200, 200);
            delay(500);
            break;
            
        case SLEEP_ENTRY:
            // 1 Long Fade/Blink (Goodbye)
            digitalWrite(ledPin, HIGH);
            delay(1000);
            digitalWrite(ledPin, LOW);
            delay(200);
            break;
    }
}
