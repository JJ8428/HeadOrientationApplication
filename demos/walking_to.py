import json
import math
import serial

import sys
sys.path.append('../')

from simulations.sim_walking_to_v2 import walking_to

DIST_SIMILARITY_THRESHOLD = .9

with open('../environment/complex_room.json', 'r') as f:
    objs = json.load(f)

while True:
    # Get data from board
    ser = serial.Serial('/dev/ttyACM0', 9600)
    nano_raw_output = ser.readline()
    ser.close()

    # Convert data into format program is designed for
    nano_output = nano_raw_output.decode().strip()
    try:
        data = json.loads(nano_output)
    except:
        print('Error parsing JSON')
        continue

    # TODO

