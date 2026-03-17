#include <Arduino.h>

const int SCLK_PIN = 18;
const int DOUT_PIN = 19;
const int TARE_BUTTON_PIN = 4;

long offset = 0;
float scaleFactor = 1.0; // Update this after your calibration test

void setup() {
  Serial.begin(115200);
  
  pinMode(SCLK_PIN, OUTPUT);
  pinMode(DOUT_PIN, INPUT);
  pinMode(TARE_BUTTON_PIN, INPUT_PULLUP);
  
  digitalWrite(SCLK_PIN, LOW);

  Serial.println("Initializing SD10819 ADC...");
  delay(500); // Wait for chip stabilization
  calibrateZero();
}

long readADC() {
  // 1. Wait for DRDY to go LOW
  // Timeout added to prevent infinite loop if ADC is disconnected
  unsigned long startWait = millis();
  while (digitalRead(DOUT_PIN) == HIGH) {
    if (millis() - startWait > 500) return 0; 
  }

  long value = 0;

  // 2. Read 24 bits of data
  for (int i = 0; i < 24; i++) {
    digitalWrite(SCLK_PIN, HIGH);
    delayMicroseconds(1); // pulse width t3 > 100ns
    value = (value << 1) | digitalRead(DOUT_PIN);
    digitalWrite(SCLK_PIN, LOW);
    delayMicroseconds(1);
  }

  // 3. Configuration Pulses: 27 pulses = Channel A, 128x Gain
  for (int i = 0; i < 3; i++) {
    digitalWrite(SCLK_PIN, HIGH);
    delayMicroseconds(1);
    digitalWrite(SCLK_PIN, LOW);
    delayMicroseconds(1);
  }

  // Handle 24-bit two's complement
  if (value & 0x800000) {
    value |= 0xFF000000;
  }
  return value;
}

void calibrateZero() {
  Serial.println("Taring... stay still.");
  long sum = 0;
  for(int i = 0; i < 20; i++) {
    sum += readADC();
    delay(10);
  }
  offset = sum / 20;
  Serial.print("New Offset: ");
  Serial.println(offset);
}

void loop() {
  // Check Tare Button
  if (digitalRead(TARE_BUTTON_PIN) == LOW) {
    calibrateZero();
    while(digitalRead(TARE_BUTTON_PIN) == LOW); // Wait for release
  }

  // Read and Filter
  long raw = readADC();
  float weight = (float)(raw - offset) * scaleFactor;

  // Serial Output for Debugging / Plotting
  Serial.print("Raw:");
  Serial.print(raw);
  Serial.print("\tWeight:");
  Serial.print(weight, 2);
  Serial.println("g");

  delay(100); // 10Hz sampling rate
}