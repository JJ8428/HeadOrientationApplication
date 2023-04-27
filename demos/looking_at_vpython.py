import json
import math
import serial
import time
from vpython import *

import sys
sys.path.append('../')

from simulations.sim_looking_at import looking_at

SCORE_THRESHOLD = 1500 # Milliseconds
DECAY_RATE = .025
ACCELERATED_DECAY_RATE = .125
DECAY_SCORE_FLOOR = 100

BIAS_X = 0
BIAS_Y = 1
BIAS_Z = 0

# Load the environment
with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)

# Variables we used to calculate score gain/decay
obj_score = {}
obj_sphere = {}
obj_dist = {}
for obj in objs:
    obj_score[obj['desc']] = {
        'score': 0,
        'penalty': 0
    }
    obj_sphere[obj['desc']] = sphere(pos = vector(obj['x'], obj['y'], -obj['z']), color = vector(5, 3, 1), radius = 0.2, opacity = 0.5, shininess = 1, emissive = False)
    obj_dist[obj['desc']] = math.sqrt((obj['x'] - BIAS_X)**2 + (obj['y'] - BIAS_Y)**2 + (obj['z'] - BIAS_Z)**2)

# Returns milliseconds passed
def millis():

    return round(time.time() * 1000)

def main():

    # Arrow object represents the direction the user is looking at
    pov = arrow(pos = vector(0, 1, 0), axis = vector(0, 0, -1), shaftwidth = 0.1, round = True)

    # Alter the camera
    scene.camera.pos = vector(2 + BIAS_X, 2 + BIAS_Y, 2 + BIAS_Z)
    scene.camera.axis = vector(-1, -1, -1)

    # Draw the X, Y, Z axes
    curve(pos=[vector(0 + BIAS_X, 0 + BIAS_Y, 0 + BIAS_Z), vector(1 + BIAS_X, 0 + BIAS_Y, 0 + BIAS_Z)], shaftwidth = 0, color = color.red)
    curve(pos=[vector(0 + BIAS_X, 0 + BIAS_Y, 0 + BIAS_Z), vector(0 + BIAS_X, 1 + BIAS_Y, 0 + BIAS_Z)], shaftwidth = 0, color = color.green)
    curve(pos=[vector(0 + BIAS_X, 0 + BIAS_Y, 0 + BIAS_Z), vector(0 + BIAS_X, 0 + BIAS_Y, -1 + BIAS_Z)], shaftwidth = 0, color = color.blue)

    prev_t = millis()

    while True:
        # Get data from board
        ser = serial.Serial('/dev/ttyACM0', 9600)
        nano_raw_output = ser.readline()
        ser.close()
        nano_output = nano_raw_output.decode().strip()
        try:
            data = json.loads(nano_output)
        except:
            print('Error parsing JSON')
            continue
        observation = {
            'pitch': data['cf_pitch'], 
            'heading': data['cf_heading'],
            'altitude': 1
        }

        # Pass into algorithm to detect what objects we are possibly looking at
        focus_objs = looking_at(observation, objs)

        # Milliseconds between observation
        delta_t = millis() - prev_t
        prev_t = millis()

        print("----------")

        '''
            Determine what obj the user is looking that satisifies our score threshold
            Once an obj meets the thresholds, we call the higher order function declare_focus_func
        '''
        obj_descs = obj_score.keys()
        if focus_objs == []:
            pov_magnitude = .5
            for obj in obj_descs:
                # Make all spheres normal color
                obj_sphere[obj].color = vector(5, 3, 1)
                # Decay score only if not 0
                if (obj_score[obj]['score'] != 0):
                    obj_score[obj]['penalty'] += 1
                    # Decay at normal rate if we are not looking at anything
                    decay_score = int(obj_score[obj]['score'] * math.exp(-DECAY_RATE *  obj_score[obj]['penalty']))
                    # If score decays for enough time, reset score and penalty
                    if decay_score <= DECAY_SCORE_FLOOR:
                        obj_score[obj]['score'] = 0
                        obj_score[obj]['penalty'] = 0
        else:
            for obj in obj_descs:
                if obj in focus_objs:
                    # Make magnitude of user POV's vector adjust distance to object
                    pov_magnitude = obj_dist[obj]
                    # Make all focus_objs' spheres highlight color
                    obj_sphere[obj].color = vector(255, 55, 200)
                    # If the score reaches a threshold, it is likely we are looking at an object
                    if obj_score[obj]['score'] >= SCORE_THRESHOLD:
                        obj_score[obj]['penalty'] = 0
                        '''
                            obj user is looking at will be DECLARED HERE with a higher order function
                        '''
                        print(obj)
                    else: 
                        if obj_score[obj]['penalty'] == 0:
                            '''
                                If user's gaze fixes on obj with a penalty of 0 (has not been looked for atleast some time),
                                scale with the score starting from 0
                            '''
                            obj_score[obj]['score'] += delta_t
                        else:
                            '''
                                If user's gaze looked at obj, looked elsewhere, then returned to object, leading to a penalty != 0,
                                either due to overshoot or delayed calibration of the board, scale the score starting from the
                                decayed score
                            '''
                            decay_score = int(obj_score[obj]['score'] * math.exp(-DECAY_RATE *  obj_score[obj]['penalty']))
                            obj_score[obj]['score'] = decay_score + delta_t
                        # Reset penalty
                        obj_score[obj]['penalty'] = 0
                else:
                    # Decay score only if not 0
                    if (obj_score[obj]['score'] != 0):
                        obj_score[obj]['penalty'] += 1
                        # Decay at normal rate if we are not looking at anything
                        decay_score = int(obj_score[obj]['score'] * math.exp(-ACCELERATED_DECAY_RATE *  obj_score[obj]['penalty']))
                        # If score decays for enough time, reset score and penalty
                        if decay_score <= DECAY_SCORE_FLOOR:
                            obj_score[obj]['score'] = 0
                            obj_score[obj]['penalty'] = 0

        # Calculate vector to get user's POV vector from the observation and update arrow vector
        user_heading = math.radians(observation['heading'])
        user_pitch = math.radians(observation['pitch'])
        pov_x = math.sin(user_heading) * math.cos(user_pitch) * pov_magnitude
        pov_y = math.sin(user_pitch) * pov_magnitude
        pov_z = math.cos(user_heading) * math.cos(user_pitch) * pov_magnitude
        pov.axis = vector(pov_x, pov_y, -pov_z)
        
if __name__ == '__main__':
    main()