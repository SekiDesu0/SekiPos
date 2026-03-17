#include <Arduino.h>

const int SCLK_PIN = 1;
const int DOUT_PIN = 2;

long tareOffset = 0;
float calibrationFactor = 74.17; //1.0 by default, callibrated by placing 796 weight and callibrating
float smoothedWeight = 0.0;
float alpha = 0.15; // Adjustment: 0.05 (very smooth/slow) to 0.3 (jumpy/fast)

long readSD10809() {
    long data = 0;
    
    // Wait for DRDY to go LOW 
    uint32_t timeout = millis();
    while (digitalRead(DOUT_PIN) == HIGH) {
        if (millis() - timeout > 100) return -1; // 20Hz rate is 50ms 
    }

    // Read 24-bit ADC result [cite: 158, 160]
    for (int i = 0; i < 24; i++) {
        digitalWrite(SCLK_PIN, HIGH);
        delayMicroseconds(1); 
        data = (data << 1) | digitalRead(DOUT_PIN);
        digitalWrite(SCLK_PIN, LOW);
        delayMicroseconds(1);
    }

    // Send 3 extra pulses (Total 27) to keep Channel A at 128x Gain [cite: 152, 161]
    for (int i = 0; i < 3; i++) {
        digitalWrite(SCLK_PIN, HIGH);
        delayMicroseconds(1);
        digitalWrite(SCLK_PIN, LOW);
        delayMicroseconds(1);
    }

    // Handle 24-bit Two's Complement sign extension [cite: 108]
    if (data & 0x800000) data |= 0xFF000000;
    
    return data;
}

long getAverageReading(int samples) {
    long sum = 0;
    int count = 0;
    while (count < samples) {
        long val = readSD10809();
        if (val != -1) {
            sum += val;
            count++;
        }
    }
    return sum / samples;
}

void tare() {
    Serial.println("Taring... keep scale still.");
    tareOffset = getAverageReading(20);
    Serial.print("New Offset: ");
    Serial.println(tareOffset);
}

void calibrate(float knownWeightGrams) {
    long currentRaw = getAverageReading(20);
    calibrationFactor = (float)(currentRaw - tareOffset) / knownWeightGrams;
    Serial.print("Calibration Factor set to: ");
    Serial.println(calibrationFactor);
}

void setup() {
    Serial.begin(115200);
    pinMode(SCLK_PIN, OUTPUT);
    pinMode(DOUT_PIN, INPUT);
    
    // Give the chip time to stabilize (2 cycles for SD10809) [cite: 142]
    delay(500); 
    tare();
}

void loop() {
    long raw = readSD10809();
    
    if (raw != -1) {
        // 1. Calculate current instantaneous weight
        float currentWeight = (raw - tareOffset) / calibrationFactor;

        // 2. Apply EMA Filter
        smoothedWeight = (alpha * currentWeight) + (1.0 - alpha) * smoothedWeight;

        // 3. Optional: "Auto-Zero" or Snap-to-Zero
        // If the weight is within 0.05g of zero, just show 0.00
        float displayWeight = smoothedWeight;
        if (abs(displayWeight) < 0.05) {
            displayWeight = 0.00;
        }

        Serial.print("Weight: ");
        Serial.print(displayWeight, 2);
        Serial.println(" g");
    }

    // Example trigger for calibration via Serial
    if (Serial.available()) {
        char c = Serial.read();
        if (c == 't') {
          tare();
        }
        if (c == 'c') {
          calibrate(796);
        }
    }
}