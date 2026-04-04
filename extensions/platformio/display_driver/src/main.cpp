#include <Arduino.h>
#include "TM1621_Config.h"

#define LCD_DATA 29
#define LCD_WR   28
#define LCD_CS   27

// Tracking variables
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
  writeBits(0x04, 3);   // Binary 100 [cite: 432]
  writeBits(cmd, 8);    // Command [cite: 413, 534]
  writeBits(0, 1);      // X bit [cite: 416]
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

void setup() {
  pinMode(LCD_DATA, OUTPUT);
  pinMode(LCD_WR, OUTPUT);
  pinMode(LCD_CS, OUTPUT);
  digitalWrite(LCD_CS, HIGH); // Initialize serial interface [cite: 443]
  
  sendCmd(0x01); // SYS EN [cite: 534]
  sendCmd(0x29); // BIAS 1/3, 4 COM [cite: 420, 544]
  sendCmd(0x03); // LCD ON [cite: 534]

  updateDisplay();
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

int counter1 = 0;
int counter2 = 0;
int counter3 = 0;

void loop() {
  printToRow(1, counter1);
  printToRow(2, counter2);
  printToRow(3, counter3);

  counter1 = (counter1 + 1) % 1000;
  counter2 = (counter2 + 2) % 1000;
  counter3 = (counter3 + 3) % 1000;
  delay(100);
}

// void loop() {
//   writeAddr(0, 0x00);
//   writeAddr(1, 0x00);
//   writeAddr(2, 0x00);
//   writeAddr(3, 0x00);

//   displayDigit(row1_d1, counter);

//   Serial.println(counter);

//   counter++;
//   if (counter > 9) {
//     counter = 0;
//   }

//   delay(1000); 
// }

// void loop() {
//   if (Serial.available() > 0) {
//     char input = Serial.read();
    
//     // Ignore newline/carriage return characters
//     if (input == '\n' || input == '\r') return;

//     if (input == 'n' || input == 'N') {
//       currentBit++;
//       if (currentBit > 3) {
//         currentBit = 0;
//         currentAddr++;
//       }
//       if (currentAddr > 31) currentAddr = 0;
//       updateDisplay();
//     } 
//     else if (input == 'p' || input == 'P') {
//       currentBit--;
//       if (currentBit < 0) {
//         currentBit = 3;
//         currentAddr--;
//       }
//       if (currentAddr < 0) currentAddr = 31;
//       updateDisplay();
//     }
//   }
// }