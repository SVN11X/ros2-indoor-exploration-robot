/* *************************************************************
   Encoder driver function definitions - by James Nugen
   ************************************************************ */
   
   
#ifdef ARDUINO_ENC_COUNTER
  //below can be changed, but should be PORTD pins; 
  //otherwise additional changes in the code are required
  #define LEFT_ENC_PIN_A PD3  //pin 3 amarillo
  #define LEFT_ENC_PIN_B PD2  //pin 2 verde
  
  //below can be changed, but should be PORTC pins
  #define RIGHT_ENC_PIN_A PC4  //pin A4 amarillo
  #define RIGHT_ENC_PIN_B PC5   //pin A5 verde
#endif
   
long readEncoder(int i);
void resetEncoder(int i);
void resetEncoders();

