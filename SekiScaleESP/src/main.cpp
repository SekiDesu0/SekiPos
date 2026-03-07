#include <Arduino.h>

const int triggerPin = D2;
bool lastState = HIGH;

void setup() {
    Serial.begin(115200);
    randomSeed(analogRead(0)); 
    
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(triggerPin, INPUT_PULLUP);

    // Flash LED to signal boot
    digitalWrite(LED_BUILTIN, LOW);
    delay(500);
    digitalWrite(LED_BUILTIN, HIGH);
}

void loop() {
    bool currentState = digitalRead(triggerPin);

    // Detect when D4 touches GND (Falling Edge)
    if (currentState == LOW && lastState == HIGH) {
        int randomWeight = random(100, 5000); 
        
        // Output formatted for easy parsing
        Serial.print("WEIGHT:");
        Serial.println(randomWeight);

        // Visual feedback
        digitalWrite(LED_BUILTIN, LOW);
        delay(100);
        digitalWrite(LED_BUILTIN, HIGH);
        
        delay(250); // Debounce
    }

    lastState = currentState;
}