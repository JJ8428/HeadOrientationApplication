import json
import math
import pandas as pd
from pynput import keyboard
import serial

import sys
sys.path.append('../')

from demos.looking_at_console import millis, SCORE_THRESHOLD, DECAY_RATE, ACCELERATED_DECAY_RATE, DECAY_SCORE_FLOOR
from simulations.sim_looking_at import looking_at

SAVE_PATH = '../data/recorded_data/looking_at_session_7.csv'

# Load the environment
with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)

# Columns to add into dataframe
df_cols = ['roll', 'pitch', 'heading', 'in_motion', 'is_rotating']

# Variables we used to calculate score gain/decay
# Also add columns for one hot encoding
obj_score = {}
for obj in objs:
    df_cols.append(obj['desc'])
    obj_score[obj['desc']] = {
        'score': 0,
        'decay_score': 0,
        'penalty': 0
    }
df_cols.append('Nothing')

# Higher order function to insert within score_focus
def declare_focus_func(obj_desc):

    print(obj_desc)

def on_press(key):
    
    if key == keyboard.Key.space:
        return False

# Declare dataframe to write the data into
df = pd.DataFrame(columns=df_cols)

prev_t = millis()

print('Gathering data...')
print('Press SPACE when to stop collecting data...')
print()
with keyboard.Listener(on_press = on_press) as listener:
    while listener.running:
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
            'roll': data['cf_roll'],
            'pitch': data['cf_pitch'], 
            'heading': data['cf_heading'],
            'in_motion': data['in_motion'],
            'is_rotating': data['is_rotating'],
            'altitude': 1
        }

        # Pass into algorithm to detect what objects we are possibly looking at
        focus_objs = looking_at(observation, objs)

        # Milliseconds between observation
        delta_t = millis() - prev_t
        prev_t = millis()

        # Declare list as row we will append to dataframe
        row = [observation['roll'], 
            observation['pitch'],
            observation['heading'],
            observation['in_motion'],
            observation['is_rotating']
        ]

        '''
            Determine what obj the user is looking that satisifies our score threshold.
            Once an obj meets the thresholds, we do whatever we have to do with out declared
            obj.
        '''
        print("----------")
        focused_obj = []
        obj_descs = obj_score.keys()
        if focus_objs == []:
            for obj in obj_descs:
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
                    # If the score reaches a threshold, it is likely we are looking at an object
                    if obj_score[obj]['score'] >= SCORE_THRESHOLD:
                        obj_score[obj]['penalty'] = 0
                        '''
                            obj user is looking at will be DECLARED HERE
                        '''
                        focused_obj.append(obj)
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

            '''
                Append encoding to row list. Technically it is possible that multiple objects can be returned,
                but the environment we will be testing in has the objects well spaced, so it is impossible for
                multiple 1's to be in a row. Therefore, this is essentially one hot encoding
            '''
            nothing = '1'
            for obj in obj_descs:
                if obj in focused_obj:
                    row.append('1')
                    nothing = '0'
                else:
                    row.append('0')
            row.append(nothing)

            # Append to dataframe
            df.loc[len(df)] = row

df.to_csv(SAVE_PATH, index = False)
print(f'Created dataset of {len(df)} data points')
print(f'Saving to {SAVE_PATH}')