#include <Wire.h>
#define _MOTOR_A 0
#define _MOTOR_B 1
#define _SHORT_BRAKE 0
#define _CCW  1
#define _CW   2
#define _STOP 3
#define _STANDBY 4

void init_channel(uint8_t address, uint32_t freq) {
  Wire.begin();
  Wire.beginTransmission(address);
  Wire.write(((byte)(freq >> 16)) & (byte)0x0f);
  Wire.write((byte)(freq >> 16));
  Wire.write((byte)(freq >> 8));
  Wire.write((byte)freq);
  Wire.endTransmission();
  delay(100);
}

void set_motor(uint8_t address, uint8_t motor, uint8_t dir, uint8_t spd) {
  Wire.beginTransmission(address);
  Wire.write(motor | (byte)0x10);
  Wire.write(dir);
  uint16_t _pwm_val = spd * 100;
  _pwm_val = constrain(_pwm_val, 0, 10000);
  Wire.write((byte)(_pwm_val >> 8));
  Wire.write((byte)_pwm_val);
  Wire.endTransmission();     // stop transmitting
}

void setup() {
  Wire.begin();
  init_channel(0x30, 1000);
  init_channel(0x2F, 1000);
}

void loop() {
  for (int i = 50; i <=100; i++) {
    set_motor(0x30, _MOTOR_A, _CW, i);
    set_motor(0x30, _MOTOR_B, _CW, i);
    set_motor(0x2F, _MOTOR_A, _CW, i);
    set_motor(0x2F, _MOTOR_B, _CW, i);
    delay(50);
  }
  
  set_motor(0x30, _MOTOR_A, _STOP, 0);
  set_motor(0x30, _MOTOR_B, _STOP, 0);
  set_motor(0x2F, _MOTOR_A, _STOP, 0);
  set_motor(0x2F, _MOTOR_B, _STOP, 0);
  delay(1000);
  
    for (int i = 50; i <=100; i++) {
    set_motor(0x30, _MOTOR_A, _CCW, i);
    set_motor(0x30, _MOTOR_B, _CCW, i);
    set_motor(0x2F, _MOTOR_A, _CCW, i);
    set_motor(0x2F, _MOTOR_B, _CCW, i);
    delay(50);
  }
  set_motor(0x30, _MOTOR_A, _STOP, 0);
  set_motor(0x30, _MOTOR_B, _STOP, 0);
  set_motor(0x2F, _MOTOR_A, _STOP, 0);
  set_motor(0x2F, _MOTOR_B, _STOP, 0);
  delay(1000);
}
