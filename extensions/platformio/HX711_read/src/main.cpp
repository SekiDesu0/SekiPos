#include <Arduino.h>
#include "HX711.h"

const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 3;

HX711 scale;

float smoothedWeight = 0.0;
float alpha = 0.3; 
float calibration_factor = 111.17; 
float known_weight = 796.0; 

// Stability Lock Variables
float lastDisplayedWeight = 0.0;
const float STABILITY_THRESHOLD = 0.5;

void calibrateScale() {
    Serial.println("--- Calibration Mode ---");
    Serial.println("1. Clear scale, type 't' to tare.");
    Serial.print("2. Place "); Serial.print(known_weight); Serial.println("g weight.");
    Serial.println("3. Type 'c' to confirm weight.");
    
    while (true) {
        if (Serial.available()) {
            char c = Serial.read();
            if (c == 't') {
                scale.tare();
                Serial.println("Tared! Place weight and type 'c'...");
            } else if (c == 'c') {
                long reading = scale.get_value(15); 
                calibration_factor = (float)reading / known_weight;
                scale.set_scale(calibration_factor);
                Serial.print("New Factor: "); Serial.println(calibration_factor);
                Serial.println("Calibration Done! Exiting mode.");
                break;
            }
        }
    }
}

void setup() {
    Serial.begin(115200);
    scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    scale.set_gain(128); 
    scale.set_scale(calibration_factor);
    scale.tare();
    Serial.println("HX711 Ready (Stable Lock Mode)");
}

void loop() {
    if (scale.is_ready()) {
        float currentReading = scale.get_units(1);
        smoothedWeight = (alpha * currentReading) + (1.0 - alpha) * smoothedWeight;

        // 1. Calculate the intended new display value
        float targetWeight = round(smoothedWeight * 2.0) / 2.0;
        if (abs(targetWeight) < 1.0) targetWeight = 0.0;

        // 2. Stability Check
        // Only update lastDisplayedWeight if the change exceeds the threshold
        if (abs(targetWeight - lastDisplayedWeight) >= STABILITY_THRESHOLD) {
            lastDisplayedWeight = targetWeight;
        }

        Serial.print("Weight: ");
        Serial.print(lastDisplayedWeight, 1);
        Serial.println(" g");
    }

    if (Serial.available()) {
        char cmd = Serial.read();
        if (cmd == 't') {
            scale.tare();
            smoothedWeight = 0; 
            lastDisplayedWeight = 0; // Force display to zero immediately
            Serial.println(">> Tared");
        } else if (cmd == 'k') {
            calibrateScale();
        }
    }

    delay(10); 
}