#include <Arduino.h>
#include "HX711.h"

const int LOADCELL_SCK_PIN = 3;
const int LOADCELL_DOUT_PIN = 2;

const long LOADCELL_OFFSET = 0;
const long LOADCELL_DIVIDER = 0;

HX711 scale;

void setup() {
  Serial.begin(115200);
  while(!Serial);

  Serial.println("Remove all weight from the scale.");
  delay(2000);
  scale.set_scale();
  scale.tare();
  Serial.println("Tare complete. Place a known weight on the scale.");
}

void loop() {
  if (scale.is_ready()) {
    long reading = scale.get_units(10);
    Serial.print("Raw Value: ");
    Serial.println(reading);
  } else {
    Serial.println("HX711 not found.");
  }
  delay(1000);
}