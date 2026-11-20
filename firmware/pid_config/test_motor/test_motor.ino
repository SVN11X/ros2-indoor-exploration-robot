/*
  TEST DE MOTORES - L298N + ARDUINO NANO
  Basado en tu diagrama de conexión corregido.
*/

// --- DEFINICIÓN DE PINES (Según tu diagrama) ---

// Motor DERECHO (Superior)
const int R_IN1 = 9;   // Dirección A
const int R_IN2 = 5;   // Dirección B
const int R_ENA = 12;  // Enable (Velocidad/ON-OFF) - Cable Verde

// Motor IZQUIERDO (Inferior)
const int L_IN3 = 6;  // Dirección A
const int L_IN4 = 10;   // Dirección B
const int L_ENB = 13;   // Enable (Velocidad/ON-OFF) - Cable Azul (CORREGIDO)

void setup() {
  Serial.begin(9600);
  Serial.println("--- INICIANDO TEST DE HARDWARE ---");
  Serial.println("Si los motores no se mueven, revisa baterias y el interruptor.");

  // Configurar todos los pines como SALIDA
  pinMode(R_IN1, OUTPUT);
  pinMode(R_IN2, OUTPUT);
  pinMode(R_ENA, OUTPUT);

  pinMode(L_IN3, OUTPUT);
  pinMode(L_IN4, OUTPUT);
  pinMode(L_ENB, OUTPUT);
}

void loop() {
  // 1. ADELANTE (Máxima Potencia)
  Serial.println("Moviendo: ADELANTE");
  moverAdelante();
  delay(2000); // Mantener 2 segundos

  // 2. PARAR
  Serial.println("Moviendo: STOP");
  pararMotores();
  delay(1000); // Esperar 1 segundo

  // // 3. ATRÁS (Máxima Potencia)
  Serial.println("Moviendo: ATRAS");
  moverAtras();
  delay(2000); // Mantener 2 segundos

  // // 4. PARAR
  Serial.println("Moviendo: STOP");
  pararMotores();
  delay(2000); // Esperar 2 segundos antes de repetir
  
}

// --- FUNCIONES AUXILIARES ---

void moverAdelante() {
  // Activar Enables (Quitar el freno de mano)
  digitalWrite(R_ENA, HIGH); 
  digitalWrite(L_ENB, HIGH);

  // Motor Derecho Adelante
  digitalWrite(R_IN1, HIGH);
  digitalWrite(R_IN2, LOW);

  // Motor Izquierdo Adelante
  digitalWrite(L_IN3, HIGH);
  digitalWrite(L_IN4, LOW);
}

void moverAtras() {
  // Activar Enables
  digitalWrite(R_ENA, HIGH); 
  digitalWrite(L_ENB, HIGH);

  // Motor Derecho Atrás (Invertimos HIGH/LOW)
  digitalWrite(R_IN1, LOW);
  digitalWrite(R_IN2, HIGH);

  // Motor Izquierdo Atrás (Invertimos HIGH/LOW)
  digitalWrite(L_IN3, LOW);
  digitalWrite(L_IN4, HIGH);
}

void pararMotores() {
  // Desactivar Enables (Apagar motor)
  digitalWrite(R_ENA, LOW);
  digitalWrite(L_ENB, LOW);
  
  // Por seguridad, ponemos todo en LOW
  digitalWrite(R_IN1, LOW);
  digitalWrite(R_IN2, LOW);
  digitalWrite(L_IN3, LOW);
  digitalWrite(L_IN4, LOW);
}