#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py
#  
#  
#  
import time
import io
import threading
import picamera
import cv2
import numpy as np
import serial

class streamThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.paused = False
        self.pause_cond = threading.Condition(threading.Lock())
        self.ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        self.ser.flush()
        self.counter = 0
        self.last_access = time.time()
        self.frame = None
        self.D = 99
        self.centro = (0, 0)
        
    def run(self):
        with picamera.PiCamera() as camera:
            with self.pause_cond:
                # camera setup
                camera.resolution = (320, 240)
                camera.hflip = True
                camera.vflip = True
                centro = (156, 132)

                # let camera warm up
                camera.start_preview()
                time.sleep(2)

                stream = io.BytesIO()
                for foo in camera.capture_continuous(stream, 'jpeg',
                                                     use_video_port=True):
                    while self.paused:
                        self.pause_cond.wait()
                    #print(cls.enable)
                    # store frame
                    stream.seek(0)
                    #Convert the picture into a numpy array
                    buff = np.frombuffer(stream.getvalue(), dtype=np.uint8)

                    #Now creates an OpenCV image
                    image = cv2.imdecode(buff, 1)
                    #gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
                    
                    if self.counter == 5:
                        laser = (image[:,:,2] == 255) # Se obtienen los pixeles más brillantes del color rojo 
                        xy_pos = np.nonzero(laser) # Posiciones de los pixeles más brillantes
                        try:
                            y_pos = int(np.median(xy_pos[0])) # Posicion en y del pixel mas brillante en la mitad del puntero
                            x_pos = int(np.median(xy_pos[1])) # Posicion en x del pixel mas brillante en la mitad del puntero
                        except ValueError:
                            x_pos = centro[0]
                            y_pos = centro[1]

                        # Se calcula distancia euclidiana con el centro
                        dist = ((x_pos - centro[0])**2 + (y_pos - centro[1])**2 )**0.5
                        #print(dist)
                        #print((x_pos, y_pos))
                        
                        loc = (x_pos, y_pos) # Tupla con los valores del centro del puntero
                        # Se calcula la tangente de \theta segun la regresion realizada 
                        tang = np.tan(0.00322*dist + 0.0175)

                        if tang > 0: # Calculo de la distancia en cm 
                            self.D =  int(4.5 / tang)
                        #cv2.circle(img, self.loc, 10, (255, 0, 0), 2) # Circulo en la imagen que señala el puntero
                        #cv2.imshow('CAM', img) # Se muestra la imagen
                        #print(f"Distancia del obstáculo: {D} cm")
                        
                        string = f"Distancia del obstáculo: {self.D} cm \n"
                        #print(self.D)
                        if self.D < 30:
                            pass
                            #print("STOP!")
                            #cv2.putText(image, f"CUIDADO!!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255, 1))
                            #self.ser.write(bytes("STOP\n", 'utf-8'))
			#self.ser.write(bytes(string, 'utf-8'))
                        #line = self.ser.readline().decode('utf-8').rstrip()
                        #print(line)
                        self.counter = 0
                    else:
                        self.counter += 1
                    
                    if self.D < 60 and self.D > 50:
                        cv2.putText(image, f"OBSTACULO CERCA", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    elif self.D < 50 and self.D > 40:
                        cv2.putText(image, f"OBSTACULO AL FRENTE!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    elif self.D < 40 and self.D > 30:
                        cv2.putText(image, f"DETENTE!!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    elif self.D < 30:
                        self.ser.write(bytes("MOVE\n", 'utf-8'))
                        cv2.putText(image, f"FRENADO EMERGENCIA", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(image, f"Distancia del obstaculo: {self.D} cm",(10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255),1)

                    ret, jpeg = cv2.imencode('.jpg', image)

                    #cls.frame = stream.read()
                    self.frame = jpeg.tobytes()

                    # reset stream for next frame
                    stream.seek(0)
                    stream.truncate()

                    # if there hasn't been any clients asking for frames in
                    # the last 10 seconds stop the thread
                    if time.time() - self.last_access > 10:
                        break
                        
                time.sleep(5)
 
    def pause(self):
        self.paused = True
        self.pause_cond.acquire()
        
    def resume(self):
        self.counter = 0
        self.paused = False
        self.pause_cond.notify()
        self.pause_cond.release()
        


class Camera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera

    def initialize(self):
        if Camera.thread is None:
            # start background frame thread
            #Camera.thread = threading.Thread(target=self._thread)
            Camera.thread = streamThread()
            Camera.thread.start()

            # wait until frames start to be available
            while Camera.thread.frame is None:
                time.sleep(0)

    def dormir(self):
        Camera.thread.pause()
        
    def despertar(self):
        Camera.thread.resume()

    def get_frame(self):
        if Camera.thread is not None:
            Camera.thread.last_access = time.time()
        self.initialize()
        return Camera.thread.frame

    @classmethod
    def _thread(cls):
        cls.thread = None
