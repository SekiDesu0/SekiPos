#include <Arduino.h>
#include <Keypad.h>

#define BUZZER_PIN 9

const byte ROWS = 4;
const byte COLS = 5;

char keys[ROWS][COLS] = {{'1', '2','3','C','T'},
                         {'4', '5','6','A','Z'},
                         {'7', '8','9','X','Y'},
                         {'0', '.','S','M','L'}};

byte rowPins[ROWS] = {0,1,2,3};
byte colPins[COLS] = {4,5,6,7,8};

Keypad kpd = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

unsigned long loopCount = 0;
unsigned long startTime;

void playBeep() {
  analogWrite(BUZZER_PIN, 10);
  delay(50);
  analogWrite(BUZZER_PIN, 0);
}

void setup() {
  Serial.begin(115200);
  startTime = millis();
}

void loop() {
  loopCount++;
  if ((millis() - startTime) > 5000) {
    Serial.print("Average loops per second = ");
    Serial.println(loopCount / 5);
    startTime = millis();
    loopCount = 0;
  }

  if (kpd.getKeys()) {
    for (int i = 0; i < LIST_MAX; i++) {
      if (kpd.key[i].stateChanged) {
        String msg = "";
        switch (kpd.key[i].kstate) {
        case PRESSED:
          msg = " PRESSED.";
          playBeep();
          break;
        case HOLD:
          msg = " HOLD.";
          break;
        case RELEASED:
          msg = " RELEASED.";
          break;
        case IDLE:
          msg = " IDLE.";
          break;
        }

        if (msg != "") {
          Serial.print("Key ");
          Serial.print(kpd.key[i].kchar);
          Serial.println(msg);
        }
      }
    }
  }
}