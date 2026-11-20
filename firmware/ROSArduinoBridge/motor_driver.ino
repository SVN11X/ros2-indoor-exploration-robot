/***************************************************************
   Motor driver definitions
   
   Add a "#elif defined" block to this file to include support
   for a particular motor driver.  Then add the appropriate
   #define near the top of the main ROSArduinoBridge.ino file.
   
   *************************************************************/

/***************************************************************
   Motor driver definitions for L298
*************************************************************/

#ifdef USE_BASE
  
  // Verificamos que esté definido el driver correcto (opcional, pero buena práctica)
  #ifdef L298_MOTOR_DRIVER
    void initMotorController() {
      pinMode(RIGHT_MOTOR_ENABLE, OUTPUT);
      pinMode(LEFT_MOTOR_ENABLE, OUTPUT);
      pinMode(RIGHT_MOTOR_FORWARD, OUTPUT);
      pinMode(RIGHT_MOTOR_BACKWARD, OUTPUT);
      pinMode(LEFT_MOTOR_FORWARD, OUTPUT);
      pinMode(LEFT_MOTOR_BACKWARD, OUTPUT);

      digitalWrite(RIGHT_MOTOR_ENABLE, HIGH);
      digitalWrite(LEFT_MOTOR_ENABLE, HIGH);
    }
    
    void setMotorSpeed(int i, int spd) {
      unsigned char reverse = 0;
    
      if (spd < 0)
      {
        spd = -spd;
        reverse = 1;
      }
      if (spd > 255)
        spd = 255;
      
      if (i == LEFT) { 
        if      (reverse == 0) { analogWrite(LEFT_MOTOR_FORWARD, spd); analogWrite(LEFT_MOTOR_BACKWARD, 0); }
        else if (reverse == 1) { analogWrite(LEFT_MOTOR_BACKWARD, spd); analogWrite(LEFT_MOTOR_FORWARD, 0); }
      }
      else {
        if      (reverse == 0) { analogWrite(RIGHT_MOTOR_FORWARD, spd); analogWrite(RIGHT_MOTOR_BACKWARD, 0); }
        else if (reverse == 1) { analogWrite(RIGHT_MOTOR_BACKWARD, spd); analogWrite(RIGHT_MOTOR_FORWARD, 0); }
      }
    }
    
    void setMotorSpeeds(int leftSpeed, int rightSpeed) {
      setMotorSpeed(LEFT, leftSpeed);
      setMotorSpeed(RIGHT, rightSpeed);
    }

  #endif // Fin de L298_MOTOR_DRIVER

#endif // Fin de USE_BASE