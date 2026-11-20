from threading import Thread
import serial
import time
import sys
import numpy as np

class serialArduino:
     def __init__(self, port, baud=57600, sizeData=1):
          self.port = port
          self.baud = baud
          self.sizeData = sizeData 

          self.isReceiving = False
          self.isRun     = True
          self.thread    = None
          
          self.rawData = [0.0] * self.sizeData
          print('Trying to connect to: ' + str(self.port))
          try:
               self.serialConnection = serial.Serial(self.port, self.baud, timeout=1)
               print('Connected to ' + str(self.port))
          except Exception as e:
               print(f"ERROR REAL: {e}")
               sys.exit("Failed to connect with " + str(self.port))
               
     def readSerialStart(self):
          if self.thread == None:
               self.thread = Thread(target=self.backgroundThread)
               self.thread.start()
               print("Starting background thread...")
               time.sleep(0.1) 
               self.isReceiving = True
               print("Thread started (Async mode)")
                    
     def backgroundThread(self):
          time.sleep(1.0)
          self.serialConnection.flushInput()
          while (self.isRun):
               try:
                    if self.serialConnection.in_waiting > 0:
                         line = self.serialConnection.readline().decode('utf-8').strip()
                         try:
                              parts = line.split() 
                              if len(parts) >= self.sizeData and is_number(parts[0]):
                                   for k in range(self.sizeData):
                                        self.rawData[k] = float(parts[k])
                                   self.isReceiving = True
                              else:
                                   # Mensajes de texto (debug)
                                   # print(f"[Arduino]: {line}") 
                                   pass
                         except ValueError:
                              pass
               except Exception as e:
                    print("Error reading serial: ", e)
                    if "Access is denied" in str(e) or "PermissionError" in str(e):
                         print("CRITICAL: Conexión perdida. Cerrando hilo.")
                         self.isRun = False
                         break
               
     def sendData(self, dataToSend, cmd='v'):
          # Construimos el string. 
          # CAMBIO: Usamos {val} directamente para permitir floats (0.5), no int(val).
          stringData = f"{cmd}"
          for val in dataToSend:
               stringData += f" {val}" 
          
          stringData += '\r'
          self.serialConnection.write(stringData.encode())     
               
     def close(self):
          self.isRun = False
          if self.thread is not None:
               self.thread.join()
          self.serialConnection.close()
          print('Disconnected...')

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False