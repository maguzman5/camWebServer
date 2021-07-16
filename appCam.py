#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  	appCam.py
#  	based on tutorial ==> https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# 	PiCam Local Web Server with Flask


from flask import Flask, render_template, Response, request

# Raspberry Pi camera module (requires picamera package)
from camera_pi import Camera
import serial
import time

app = Flask(__name__)
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
ser.flush()

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


def gen():
    """Video streaming generator function."""
    global cam
    while True:
        frame = cam.get_frame()
        #print(cam.line)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
@app.route('/receiver', methods = ['POST'])
def worker():
    global cam
    # read json + reply
    if request.method == "POST":
        data = request.form.to_dict(flat=False)
        data = [i for i in data.values()]
        print(data[0])
        string = ",".join(data[0])
        string += '\n'
        cam.ruta = string
        cam.enable = True
        cam.dormir()
        #cam.dormir()
        ser.write(bytes(string, 'utf-8'))
        line = ser.readline().decode('utf-8').rstrip()
        print(line)
        cam.despertar()
        return string


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    global cam
    cam = Camera()
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port =80, debug=True, threaded=True)
