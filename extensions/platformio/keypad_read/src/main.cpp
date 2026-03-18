#include <Arduino.h>

const int BUZZER_PIN = 6;
const int allPins[] = {0, 1, 2, 3, 4, 5, 7}; 
const int numPins = 7;

unsigned long lastDebounceTime = 0;
const int debounceDelay = 250; 

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < numPins; i++) {
    pinMode(allPins[i], INPUT_PULLUP);
  }
}

void loop() {
  // Only scan if we aren't in the middle of a "hit" lockout
  if (millis() - lastDebounceTime < debounceDelay) return;

  for (int s = 0; s < numPins; s++) {
    int strobe = allPins[s];

    pinMode(strobe, OUTPUT);
    digitalWrite(strobe, LOW);
    delayMicroseconds(100); // Slightly longer for stability

    for (int i = 0; i < numPins; i++) {
      int target = allPins[i];
      if (target == strobe) continue;

      if (digitalRead(target) == LOW) {
        // WE FOUND ONE!
        Serial.print("SINK:");
        Serial.print(strobe);
        Serial.print(" READ:");
        Serial.println(target);

        //tone(BUZZER_PIN, 2000, 50);
        lastDebounceTime = millis();
        
        pinMode(strobe, INPUT_PULLUP);
        return; // Jump out of the whole loop to reset the lockout
      }
    }
    pinMode(strobe, INPUT_PULLUP);
  }
}