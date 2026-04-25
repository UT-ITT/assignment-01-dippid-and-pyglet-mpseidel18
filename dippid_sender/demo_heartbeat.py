import time
from DIPPID import SensorUDP

# use UPD (via WiFi) for communication
PORT = 5700
sensor = SensorUDP(PORT)

def handle_tick(_):
    # called for every packet because tick always changes.
    print(sensor.get_value('button_state'))
    print(sensor.get_value('accel_x'))
    print(sensor.get_value('accel_y'))
    print(sensor.get_value('accel_z'))
# register the callback for the tick capability, which is sent with every packet
sensor.register_callback('tick', handle_tick)

while True:
    time.sleep(10)



