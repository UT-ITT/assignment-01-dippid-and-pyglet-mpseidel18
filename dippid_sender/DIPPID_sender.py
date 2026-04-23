"""
DIPPID sender file to simulate accelerometer and button press
"""

import socket
import time
import random
import json
import math

IP = '127.0.0.1'
PORT = 5700

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
counter = 0
phase_x = 0.0
phase_y = 0.0
phase_z = 0.0

freq_x = 0.1
freq_y = 0.2
freq_z = 0.3

min_freq = 0.05
max_freq = 0.5
freq_drift = 0.01

# sends every second an increasing heartbeat number
#while True:
#    message = '{"heartbeat" : ' + str(counter) + '}'
#    print(message)#
#
#    sock.sendto(message.encode(), (IP, PORT))
#
#    counter += 1
#    time.sleep(1)
#
while True:
    # Sends random button values. Added a tick so each message can be observed.
    button_state = random.choice([True, False]) # Randomly choose between pressed (True) and non-pressed (False)
    button_label = "pressed" if button_state else "non-pressed"
    # Gently vary the phase step so the motion drifts over time instead of staying perfectly periodic.
    freq_x = max(min_freq, min(max_freq, freq_x + random.uniform(-freq_drift, freq_drift)))
    freq_y = max(min_freq, min(max_freq, freq_y + random.uniform(-freq_drift, freq_drift)))
    freq_z = max(min_freq, min(max_freq, freq_z + random.uniform(-freq_drift, freq_drift)))

    # Sends accelerometer values using sine functions with slowly changing frequencies.
    accel_x = math.sin(phase_x) * 10
    accel_y = math.sin(phase_y) * 10
    accel_z = math.sin(phase_z) * 10

    phase_x += freq_x
    phase_y += freq_y
    phase_z += freq_z
    # Create a JSON message with the button state, accelerometer values, and tick counter.
    message = json.dumps({
        "button": button_state,
        "button_state": button_label,
        "accel_x": accel_x,
        "accel_y": accel_y,
        "accel_z": accel_z,
        "tick": counter
    })
    print(message)
    sock.sendto(message.encode(), (IP, PORT))
    counter += 1
    time.sleep(1)