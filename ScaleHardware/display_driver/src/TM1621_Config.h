#ifndef TM1621_CONFIG_H
#define TM1621_CONFIG_H

#include <Arduino.h>

const uint8_t digitMap[] = {
  0b11111100, // 0
  0b00000110, // 1 
  0b01011011, // 2
  0b01001111, // 3
  0b01100110, // 4
  0b01101101, // 5
  0b01111101, // 6
  0b00000111, // 7
  0b01111111, // 8
  0b01101111  // 9
};

const int arrows[] = {283,363,183,203};    //tare,?,?,Zero
const int battery[] = {63,83,103};         //LOW / MED / FULL

// Following your pattern: {A, B, C, D, E, F, G}
const int row1_d1[] = {300, 301, 302, 313, 312, 310, 311}; // Addresses 30 & 31
const int row1_d2[] = {280, 281, 282, 293, 292, 290, 291}; // Addresses 28 & 29
const int row1_d3[] = {260, 261, 262, 273, 272, 270, 271}; // Addresses 26 & 27
const int row1_d4[] = {240, 241, 242, 253, 252, 250, 251}; // Addresses 24 & 25
const int row1_d5[] = {220, 221, 222, 233, 232, 230, 231}; // Addresses 22 & 23
const int row1_decimal[] = {263,232,223}; //XX.X.X.X

const int row2_d1[] = {200, 201, 202, 213, 212, 210, 211}; // Addresses 20 & 21
const int row2_d2[] = {180, 181, 182, 193, 192, 190, 191}; // Addresses 18 & 19
const int row2_d3[] = {160, 161, 162, 173, 172, 170, 171}; // Addresses 16 & 17
const int row2_d4[] = {140, 141, 142, 153, 152, 150, 151}; // Addresses 14 & 15
const int row2_d5[] = {120, 121, 122, 133, 132, 130, 131}; // Addresses 12 & 13
const int row2_decimal[] = {163,143,123}; //XX.X.X.X

const int row3_d1[] = {100, 101, 102, 113, 112, 110, 111}; // Addresses 10 & 11
const int row3_d2[] = {80, 81, 82, 93, 92, 90, 91};        // Addresses 8 & 9
const int row3_d3[] = {60, 61, 62, 73, 72, 70, 71};        // Addresses 6 & 7
const int row3_d4[] = {40, 41, 42, 53, 52, 50, 51};        // Addresses 4 & 5
const int row3_d5[] = {20, 21, 22, 33, 32, 30, 31};        // Addresses 2 & 3
const int row3_d6[] = {0, 1, 2, 13, 12, 10, 11};           // Addresses 0 & 1
const int row3_decimal[] = {43,23,3};     //XX.X.X.X

const int* digitsRow1[] = {row1_d1, row1_d2, row1_d3, row1_d4, row1_d5};
const int* digitsRow2[] = {row2_d1, row2_d2, row2_d3, row2_d4, row2_d5};
const int* digitsRow3[] = {row3_d1, row3_d2, row3_d3, row3_d4, row3_d5, row3_d6};

const int* decimals[] = {row1_decimal, row2_decimal, row3_decimal};
#endif