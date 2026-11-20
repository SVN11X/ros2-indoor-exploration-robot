/*********************************************************************
 * ROSArduinoBridge
 *
 * A set of simple serial commands to control a differential drive
 * robot and receive back sensor and odometry data.
 *
 * Default configuration assumes use of an Arduino Nano/Uno 
 * (ATmega328P architecture) with L298 Motor Driver and 
 * direct quadrature encoder connections.
 *
 * Created for the Pi Robot Project: http://www.pirobot.org
 * Authors: Patrick Goebel, James Nugen
 * Software License Agreement (BSD License)
 *********************************************************************/

/* ==============================================
   ROBOT PHYSICAL CONSTANTS (ADJUST THESE!)
   ============================================== */
// Wheel diameter in METERS (e.g., 0.067 for 6.7cm) 
#define WHEEL_DIAMETER 0.067 

// Total encoder ticks per wheel revolution (including gearbox) 
// Example: If the motor is 1:48 and the encoder gives 12 ticks: 48 * 12 = 576.
// If using quadrature mode (4x), ensure you multiply by 4.
#define ENC_TICKS_PER_REV 1980 

// Pre-calculated conversion factor to save CPU cycles 
// Formula: (Ticks/Rev) / (Pi * Diameter * PID_RATE)
// Used to convert m/s to Ticks/Frame [cite: 40]
float MPS_TO_TICKS_FACTOR = 0.0;

#define USE_BASE      // Enable the base controller code
//#undef USE_BASE     // Disable the base controller code

/* Define the motor controller and encoder library you are using */
#ifdef USE_BASE
   /* Encoders directly attached to Arduino board pins */
   #define ARDUINO_ENC_COUNTER

   /* L298 Bridge Motor driver */
   #define L298_MOTOR_DRIVER
#endif

/* Serial port baud rate */
#define BAUDRATE     57600

/* Maximum PWM signal value */
#define MAX_PWM        255

#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

/* Include serial command definitions */
#include "commands.h"

#ifdef USE_BASE
  /* Motor driver function definitions */
  #include "motor_driver.h"

  /* Encoder driver function definitions */
  #include "encoder_driver.h"

  /* PID parameters and functions */
  #include "diff_controller.h"

  /* Run the PID loop at 30 Hz */
  #define PID_RATE           30

  /* Convert the rate into a millisecond interval */
  const int PID_INTERVAL = 1000 / PID_RATE;

  /* Track the timestamp for the next PID calculation */
  unsigned long nextPID = PID_INTERVAL;

  /* Auto-stop safety: halt robot if no command received for X ms */
  #define AUTO_STOP_INTERVAL 2000
  long lastMotorCommand = AUTO_STOP_INTERVAL;
#endif

/* Variable initialization */

// Variables to help parse serial commands
int arg = 0;
int index = 0;

// Variable to hold an input character
char chr;

// Variable to hold the current single-character command
char cmd;

// Character arrays to hold arguments
char argv1[16];
char argv2[16];

// The arguments converted to numeric types
long arg1;
long arg2;

/* Clear the current command parameters */
void resetCommand() {
  cmd = NULL;
  memset(argv1, 0, sizeof(argv1));
  memset(argv2, 0, sizeof(argv2));
  arg1 = 0;
  arg2 = 0;
  arg = 0;
  index = 0;
}

/* Parse and execute the received serial command */
int runCommand() {
  int i = 0;
  char *p = argv1;
  char *str;
  float pid_args[4];
  arg1 = atof(argv1);
  arg2 = atof(argv2);
  
  switch(cmd) {
  case GET_BAUDRATE:
    Serial.println(BAUDRATE);
    break;
  case ANALOG_READ:
    Serial.println(analogRead(arg1));
    break;
  case DIGITAL_READ:
    Serial.println(digitalRead(arg1));
    break;
  case ANALOG_WRITE:
    analogWrite(arg1, arg2);
    Serial.println("OK"); 
    break;
  case DIGITAL_WRITE:
    if (arg2 == 0) digitalWrite(arg1, LOW);
    else if (arg2 == 1) digitalWrite(arg1, HIGH);
    Serial.println("OK"); 
    break;
  case PIN_MODE:
    if (arg2 == 0) pinMode(arg1, INPUT);
    else if (arg2 == 1) pinMode(arg1, OUTPUT);
    Serial.println("OK");
    break;
    
#ifdef USE_BASE
  case READ_ENCODERS:
    Serial.print(readEncoder(LEFT));
    Serial.print(" ");
    Serial.println(readEncoder(RIGHT));
    break;
   case RESET_ENCODERS:
    resetEncoders();
    resetPID();
    Serial.println("OK");
    break;
  case MOTOR_SPEEDS:
    /* Reset the auto stop timer */
    lastMotorCommand = millis();
    if (arg1 == 0 && arg2 == 0) {
      setMotorSpeeds(0, 0);
      resetPID();
      moving = 0;
    }
    else moving = 1;
    leftPID.TargetTicksPerFrame = arg1;
    rightPID.TargetTicksPerFrame = arg2;
    Serial.println("OK"); 
    break;
  case MOTOR_RAW_PWM:
    /* Set direct PWM speeds, bypassing the PID loop */
    lastMotorCommand = millis();
    resetPID();
    moving = 0; 
    setMotorSpeeds(arg1, arg2);
    Serial.println("OK"); 
    break;
  case UPDATE_PID:
    /* Update Kp, Kd, Ki, Ko for both wheels using the same values */
    while ((str = strtok_r(p, ":", &p)) != '\0') {
       pid_args[i] = atof(str);
       i++; 
    }
    leftPID.Kp = pid_args[0];
    leftPID.Kd = pid_args[1];
    leftPID.Ki = pid_args[2];
    leftPID.Ko = pid_args[3];

    rightPID.Kp = pid_args[0];
    rightPID.Kd = pid_args[1];
    rightPID.Ki = pid_args[2];
    rightPID.Ko = pid_args[3];
    
    Serial.println("OK");
    break;
  case READ_VEL_MPS:  // Command 'j': Report current velocity in m/s to PC 
    /* NOTE: We use 'PrevInput' which stores the exact ticks measured
       during the last PID control cycle (1/30 sec) to provide a stable reading. */
    float v_left_read;
    float v_right_read;
    
    // Formula: Ticks_per_Frame / MPS_TO_TICKS_FACTOR = m/s 
    if (MPS_TO_TICKS_FACTOR > 0.001) { // Prevent division by zero 
        v_left_read = (float)leftPID.PrevInput / MPS_TO_TICKS_FACTOR;
        v_right_read = (float)rightPID.PrevInput / MPS_TO_TICKS_FACTOR;
    } else {
        v_left_read = 0.0;
        v_right_read = 0.0;
    }

    Serial.print(v_left_read);
    Serial.print(" ");
    Serial.println(v_right_read);
    break;
  case SET_VEL_MPS:   // Command 'k': Receive velocity setpoints in m/s from PC
    lastMotorCommand = millis();
    // Parse target velocities as floats
    float v_left_set = atof(argv1);
    float v_right_set = atof(argv2);

    if (v_left_set == 0.0 && v_right_set == 0.0) {
      setMotorSpeeds(0, 0);
      resetPID();
      moving = 0;
    }
    else {
      moving = 1;
      // Convert Meters/Second -> Ticks/Frame for the PID target 
      leftPID.TargetTicksPerFrame = v_left_set * MPS_TO_TICKS_FACTOR;
      rightPID.TargetTicksPerFrame = v_right_set * MPS_TO_TICKS_FACTOR;
    }
    Serial.println("OK"); 
    break;

  case READ_PIDS: // Command 'n': Return current PID constants for feedback 
    Serial.print(leftPID.Kp); Serial.print(" ");
    Serial.print(leftPID.Kd); Serial.print(" ");
    Serial.print(leftPID.Ki); Serial.print(" ");
    Serial.print(leftPID.Ko); Serial.print(" "); // Left Wheel 
    
    Serial.print(rightPID.Kp); Serial.print(" ");
    Serial.print(rightPID.Kd); Serial.print(" ");
    Serial.print(rightPID.Ki); Serial.print(" ");
    Serial.println(rightPID.Ko); // Right Wheel
    break;

  case UPDATE_PID_LR: // Command 'z': Update Left/Right PIDs independently
    // Format: z KpL:KdL:KiL:KoL:KpR:KdR:KiR:KoR
    i = 0;
    float pid_args_lr[8]; // Parse 8 distinct values 
    while ((str = strtok_r(p, ":", &p)) != '\0') {
       pid_args_lr[i] = atof(str);
       i++;
    }
    
    // Assign Left Wheel PID [cite: 85, 86]
    leftPID.Kp = pid_args_lr[0];
    leftPID.Kd = pid_args_lr[1];
    leftPID.Ki = pid_args_lr[2];
    leftPID.Ko = pid_args_lr[3];

    // Assign Right Wheel PID [cite: 86, 87]
    rightPID.Kp = pid_args_lr[4];
    rightPID.Kd = pid_args_lr[5];
    rightPID.Ki = pid_args_lr[6];
    rightPID.Ko = pid_args_lr[7];
    
    Serial.println("OK");
    break;
#endif
  default:
    Serial.println("Invalid Command");
    break;
  }
}

/* Setup routine: hardware initialization [cite: 88] */
void setup() {
  Serial.begin(BAUDRATE);

#ifdef USE_BASE
  #ifdef ARDUINO_ENC_COUNTER
    // Set encoder pins as inputs using Data Direction Registers [cite: 89, 90]
    DDRD &= ~(1<<LEFT_ENC_PIN_A);
    DDRD &= ~(1<<LEFT_ENC_PIN_B);
    DDRC &= ~(1<<RIGHT_ENC_PIN_A);
    DDRC &= ~(1<<RIGHT_ENC_PIN_B);
    
    // Enable internal pull-up resistors [cite: 90, 91]
    PORTD |= (1<<LEFT_ENC_PIN_A);
    PORTD |= (1<<LEFT_ENC_PIN_B);
    PORTC |= (1<<RIGHT_ENC_PIN_A);
    PORTC |= (1<<RIGHT_ENC_PIN_B);
    
    // Configure Pin Change Interrupt Masks for the ATmega328P [cite: 91, 92]
    PCMSK2 |= (1 << LEFT_ENC_PIN_A)|(1 << LEFT_ENC_PIN_B); // PCINT2
    PCMSK1 |= (1 << RIGHT_ENC_PIN_A)|(1 << RIGHT_ENC_PIN_B); // PCINT1
    
    // Enable PCINT1 and PCINT2 interrupts [cite: 93, 94]
    PCICR |= (1 << PCIE1) | (1 << PCIE2);
  #endif

  initMotorController();
  resetPID();

  /* Calculate how many encoder ticks correspond to 1 m/s */
  /* Formula: (Ticks/Rev) / (Wheel_Circumference * PID_Hz) */
  MPS_TO_TICKS_FACTOR = (float)ENC_TICKS_PER_REV / (PI * WHEEL_DIAMETER * PID_RATE);
#endif
}

/* Main execution loop [cite: 95] */
void loop() {
  while (Serial.available() > 0) {
    chr = Serial.read();

    // Terminate command string on Carriage Return [cite: 98]
    if (chr == 13) {
      if (arg == 1) argv1[index] = NULL;
      else if (arg == 2) argv2[index] = NULL;
      runCommand();
      resetCommand();
    }
    // Delimit command parts using spaces [cite: 100]
    else if (chr == ' ') {
      if (arg == 0) arg = 1;
      else if (arg == 1)  {
        argv1[index] = NULL;
        arg = 2;
        index = 0;
      }
      continue;
    }
    else {
      if (arg == 0) {
        cmd = chr; // First character is always the command letter
      }
      else if (arg == 1) {
        argv1[index] = chr; // First argument string
        index++;
      }
      else if (arg == 2) {
        argv2[index] = chr; // Second argument string
        index++;
      }
    }
  }
  
#ifdef USE_BASE
  /* Trigger PID update at the specified target interval [cite: 106] */
  if (millis() > nextPID) {
    updatePID();
    nextPID += PID_INTERVAL;
  }
  
  /* Check for safety auto-stop condition [cite: 107] */
  if ((millis() - lastMotorCommand) > AUTO_STOP_INTERVAL) {
    setMotorSpeeds(0, 0);
    moving = 0;
  }
#endif
}