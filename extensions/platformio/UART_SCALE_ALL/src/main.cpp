#include <Arduino.h>
#include "TM1621_Config.h"
#include <Keypad.h>

#define SCLK_SDI0819 1
#define DOUT_SDI0819 2
#define LCD_DATA 3
#define LCD_WR 4
#define LCD_CS 5
#define BUZZER_PIN 6
#define BACKLIGHT_PIN 7

int currentAddr = 0;
int currentBit = 0;

void writeBits(uint32_t data, uint8_t count) {
  for (int8_t i = count - 1; i >= 0; i--) {
    digitalWrite(LCD_WR, LOW);
    digitalWrite(LCD_DATA, (data >> i) & 0x01);
    digitalWrite(LCD_WR, HIGH);
  }
}

void sendCmd(uint8_t cmd) {
  digitalWrite(LCD_CS, LOW);
  writeBits(0x04, 3); // Binary 100 [cite: 432]
  writeBits(cmd, 8);  // Command [cite: 413, 534]
  writeBits(0, 1);    // X bit [cite: 416]
  digitalWrite(LCD_CS, HIGH);
}

void writeAddr(uint8_t addr, uint8_t data) {
  digitalWrite(LCD_CS, LOW);
  uint16_t header = (0x05 << 6) | (addr & 0x3F); // Mode 101 [cite: 475]
  writeBits(header, 9);
  writeBits(data & 0x0F, 4); // 4 bits of data [cite: 475]
  digitalWrite(LCD_CS, HIGH);
}

void updateDisplay() {
  // Clear all segments first
  for (int i = 0; i < 32; i++) {
    writeAddr(i, 0x00);
  }
  // Light up only the current bit
  writeAddr(currentAddr, (1 << currentBit));

  Serial.print(">>> CURRENT - Address: ");
  Serial.print(currentAddr);
  Serial.print(" | Bit (COM): ");
  Serial.println(currentBit);
  Serial.println("Enter 'n' for Next, 'p' for Prev:");
}

uint8_t shadowRAM[32] = {0}; 

void writeMappedSegment(int aab, bool state) {
  int addr = aab / 10;
  int bit = aab % 10;
  
  if (state) shadowRAM[addr] |= (1 << bit);
  else shadowRAM[addr] &= ~(1 << bit);

  writeAddr(addr, shadowRAM[addr]);
}

void displayDigit(const int segments[], int number) {
  uint8_t bits = digitMap[number % 10];
  for (int i = 0; i < 7; i++) {
    // We check Bit 0, then Bit 1, etc.
    // This maps i=0 to Segment A, i=1 to Segment B...
    bool state = (bits >> i) & 0x01; 
    writeMappedSegment(segments[i], state);
  }
}

void printToRow(int row, long value, int decimalPos = 0) {
  const int** currentRow;
  int numDigits;
  
  // Select row configuration
  switch(row) {
    case 1: currentRow = digitsRow1; numDigits = 5; break;
    case 2: currentRow = digitsRow2; numDigits = 5; break;
    case 3: currentRow = digitsRow3; numDigits = 6; break;
    default: return;
  }

  // Display the number right-aligned
  long tempValue = value;
  for (int i = numDigits - 1; i >= 0; i--) {
    if (tempValue > 0 || i == numDigits - 1) { // Show at least one digit
      displayDigit(currentRow[i], tempValue % 10);
      tempValue /= 10;
    } else {
      // Clear leading zeros (all segments off)
      for (int s = 0; s < 7; s++) writeMappedSegment(currentRow[i][s], false);
    }
  }

  // Handle Decimal Points (if applicable for that row)
  if (decimalPos > 0 && decimalPos <= 3) {
    writeMappedSegment(decimals[row-1][decimalPos-1], true);
  }
}

void setupDisplay() {
  pinMode(LCD_DATA, OUTPUT);
  pinMode(LCD_WR, OUTPUT);
  pinMode(LCD_CS, OUTPUT);
  digitalWrite(LCD_CS, HIGH); // Initialize serial interface [cite: 443]

  sendCmd(0x01); // SYS EN [cite: 534]
  sendCmd(0x29); // BIAS 1/3, 4 COM [cite: 420, 544]
  sendCmd(0x03); // LCD ON [cite: 534]

  updateDisplay();
}

const byte ROWS = 4;
const byte COLS = 5;

char keys[ROWS][COLS] = {{'1', '2', '3', 'C', 'T'},
                         {'4', '5', '6', 'A', 'Z'},
                         {'7', '8', '9', 'X', 'Y'},
                         {'0', '.', 'S', 'M', 'L'}};

byte rowPins[ROWS] = {8,9, 10, 11};
byte colPins[COLS] = {12,13,14,15,16};

Keypad kpd = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

void playBeep() {
  analogWrite(BUZZER_PIN, 10);
  delay(50);
  analogWrite(BUZZER_PIN, 0);
}

long tareOffset = 0;
float calibrationFactor =
    74.17; // 1.0 by default, callibrated by placing 796 weight and callibrating

long readSD10809() {
  long data = 0;

  // Wait for DRDY to go LOW
  uint32_t timeout = millis();
  while (digitalRead(DOUT_SDI0819) == HIGH) {
    if (millis() - timeout > 100)
      return -1; // 20Hz rate is 50ms
  }

  // Read 24-bit ADC result [cite: 158, 160]
  for (int i = 0; i < 24; i++) {
    digitalWrite(SCLK_SDI0819, HIGH);
    delayMicroseconds(1);
    data = (data << 1) | digitalRead(DOUT_SDI0819);
    digitalWrite(SCLK_SDI0819, LOW);
    delayMicroseconds(1);
  }

  // Send 3 extra pulses (Total 27) to keep Channel A at 128x Gain [cite: 152,
  // 161]
  for (int i = 0; i < 3; i++) {
    digitalWrite(SCLK_SDI0819, HIGH);
    delayMicroseconds(1);
    digitalWrite(SCLK_SDI0819, LOW);
    delayMicroseconds(1);
  }

  // Handle 24-bit Two's Complement sign extension [cite: 108]
  if (data & 0x800000)
    data |= 0xFF000000;

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

void setupADC() {
  pinMode(SCLK_SDI0819, OUTPUT);
  pinMode(DOUT_SDI0819, INPUT);

  // Give the chip time to stabilize (2 cycles for SD10809) [cite: 142]
  delay(500);
  tare();
}

void setup() {
  Serial.begin(115200);
  setupDisplay();
  setupADC();
}

void loop() {
  long raw = readSD10809();

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

  if (raw != -1) {
    float displayWeight = (raw - tareOffset) / calibrationFactor;

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