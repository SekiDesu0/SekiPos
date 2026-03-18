#include <Arduino.h>

const int BUZZER_PIN = 6;
const int pins[] = {0, 1, 2, 3, 4, 5, 7};
const int numPins = 7;

struct KeyMap {
  int strobe;
  int target;
  char key;
};

// Your discovered mapping
KeyMap keypad[] = {{7, 1, '1'}, {7, 2, '2'}, {3, 7, '3'}, {5, 0, 'C'},
                   {7, 0, 'T'}, {4, 1, 'm'}, {1, 2, 'Y'}, {5, 3, '6'},
                   {1, 0, '+'}, {2, 0, 'Z'}, {1, 5, '7'}, {5, 2, 'U'},
                   {2, 5, '8'}, {3, 5, '9'}, {2, 4, 'M'}, {3, 1, '4'},
                   {0, 2, '5'}, {3, 4, 'P'}, {4, 0, '$'}, {0, 4, 'L'}};

void setup() {
  Serial.begin(115200);
  for (int p : pins) {
    pinMode(p, INPUT_PULLUP);
  }
  // Keep buzzer pin high-impedance so it doesn't sink the matrix
  pinMode(BUZZER_PIN, INPUT_PULLUP);
}

void playBeep() {
  analogWrite(BUZZER_PIN, 10); 
  
  delay(50); // Beep duration
  
  analogWrite(BUZZER_PIN, 0); // Turn it off
  pinMode(BUZZER_PIN, INPUT_PULLUP); // Reset to input for the matrix
}

char getKeyPressed() {
  for (int s = 0; s < numPins; s++) {
    int strobe = pins[s];

    pinMode(strobe, OUTPUT);
    digitalWrite(strobe, LOW);
    delayMicroseconds(50);

    for (int i = 0; i < numPins; i++) {
      int target = pins[i];
      if (target == strobe)
        continue;

      if (digitalRead(target) == LOW) {
        for (int k = 0; k < 20; k++) {
          if (keypad[k].strobe == strobe && keypad[k].target == target) {

            // Visual and Audio feedback
            Serial.print("Pressed: ");
            Serial.println(keypad[k].key);
            playBeep();

            while (digitalRead(target) == LOW)
              ; // Wait for release
            pinMode(strobe, INPUT_PULLUP);
            return keypad[k].key;
          }
        }
      }
    }
    pinMode(strobe, INPUT_PULLUP);
  }
  return '\0';
}

void loop() {
  getKeyPressed();
  delay(10);
}
