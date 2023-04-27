import json
from keras.models import load_model
import os
import pandas as pd
from PIL import Image as IMG
from PIL import ImageDraw, ImageFont
from tensorflow import expand_dims, stack

LSTM_MODEL_PATH = '../data/models/LSTM_looking_at.h5'
CNN_MODEL_PATH = '../data/models/CNN_looking_at.h5'
FOLDER_PATH = '../data/recorded_data/'
CUTOFF = 60
LSTM_IMAGE_PATH = '../data/figures/LSTM_looking_at_analysis.png'
CNN_IMAGE_PATH = '../data/figures/CNN_looking_at_analysis.png'

with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)

# Custom loss function
def custom_loss(y_true, y_pred):

    # Define the weight for the class you want to double the loss for
    class_weight = 0.75
    
    # Calculate the cross entropy loss
    ce_loss = K.categorical_crossentropy(y_true, y_pred)
    
    # Create a mask to identify the class you want to double the loss for
    target_class_mask = K.cast(K.argmax(y_true) == -1, K.floatx())
    
    # Double the loss for the target class
    weighted_loss = ce_loss + class_weight * target_class_mask * ce_loss
    
    return weighted_loss

import tensorflow as tf

# Load the models
# tf.keras.utils.get_custom_objects()['custom_loss'] = custom_loss
LSTM_model = load_model(LSTM_MODEL_PATH)
CNN_model = load_model(CNN_MODEL_PATH)

# Load data into dataframe and get actual Y
filename = os.listdir(FOLDER_PATH)[-2]
data = pd.read_csv(FOLDER_PATH + filename)
obj_cols = []
for obj in objs:
    obj_cols.append(obj['desc'])
obj_cols.append('Nothing')
data_X = data.drop(columns = obj_cols).values
actual_Y = data[obj_cols].values

# Get Y hat (LSTM_pred_Y)
LSTM_pred_Y = LSTM_model.predict(data_X.reshape(-1, 1, 5))

# Convert LSTM prob. into class labels
for a in range(len(LSTM_pred_Y)):
    one_hot_class_index = 0
    max = 0.0
    for b in range(len(LSTM_pred_Y[a])):
        if max < LSTM_pred_Y[a][b]:
            max = LSTM_pred_Y[a][b]
            one_hot_class_index = b
    for c in range(len(LSTM_pred_Y[a])):
        if c == one_hot_class_index:
            LSTM_pred_Y[a][c] = 1
        else:
            LSTM_pred_Y[a][c] = 0

# Make data into snap shots and split input and output
data_ss_X = []
data_ss_Y = []
for a in range(0, len(data) - CUTOFF):
    X = data.drop(columns = obj_cols).iloc[a:a + CUTOFF].values
    Y = data[obj_cols].iloc[a + CUTOFF].values
    data_ss_X.append(expand_dims(X, axis = -1))
    data_ss_Y.append(Y)
data_ss_X = stack(data_ss_X)
data_ss_Y = stack(data_ss_Y)

# Get Y hat (CNN_pred_Y)
CNN_pred_Y = CNN_model.predict(data_ss_X)

# Convert CNN prob. into class labels
for a in range(len(CNN_pred_Y)):
    one_hot_class_index = 0
    max = 0.0
    for b in range(len(CNN_pred_Y[a])):
        if max < CNN_pred_Y[a][b]:
            max = CNN_pred_Y[a][b]
            one_hot_class_index = b
    for c in range(len(CNN_pred_Y[a])):
        if c == one_hot_class_index:
            CNN_pred_Y[a][c] = 1
        else:
            CNN_pred_Y[a][c] = 0

# Write the actual and predicted Y values down
w = open('../data/figures/actual_Y.csv', 'w')
for y in actual_Y:
    for i in y:
        w.write(str(int(i)))
        w.write(',')
    w.write('\n')
w.close()
w = open('../data/figures/LSTM_pred_Y.csv', 'w')
for y in LSTM_pred_Y:
    for i in y:
        w.write(str(int(i)))
        w.write(',')
    w.write('\n')
w.close()
w = open('../data/figures/CNN_pred_Y.csv', 'w')
for y in CNN_pred_Y:
    for i in y:
        w.write(str(int(i)))
        w.write(',')
    w.write('\n')
w.close()
            
# Calculate adjusted accuracy of LSTM model
acc = 0
for a in range(CUTOFF, len(LSTM_pred_Y)):
    match = True
    for b in range(len(LSTM_pred_Y[a])):
        if LSTM_pred_Y[a][b] - actual_Y[a][b] != 0:
            match = False
            break
    if match:
        acc += 1
acc /= (len(LSTM_pred_Y) - CUTOFF)
print(f'LSTM Adjusted Accuracy: {acc * 100} %')

# Calculate adjusted accuracy of CNN model
acc = 0
for a in range(len(CNN_pred_Y)):
    adjusted_a = a + CUTOFF
    match = True
    for b in range(len(CNN_pred_Y[a])):
        if CNN_pred_Y[a][b] - actual_Y[adjusted_a][b] != 0:
            match = False
            break
    if match:
        acc += 1
acc /= (len(CNN_pred_Y))
print(f'CNN Adjusted Accuracy: {acc * 100} %')

# Draw an image to compare LSTM_pred_Y to actual_Y
'''
Red = Actual
Blue = LSTM prediction (incorrect)
Purple = LSTM Prediction and Actual (correct)
'''
red = (255, 0, 0)
blue = (0, 0, 255)
purple = (160, 32, 240)
height = 10 * len(obj_cols)
width = 10 * (len(LSTM_pred_Y) - CUTOFF)
im = IMG.new("RGB", (width, height), (80, 80, 80))
draw = ImageDraw.Draw(im)
for a in range(CUTOFF, len(LSTM_pred_Y)):
    left = 10 * (a - CUTOFF)
    right = left + 10
    class_pred = -1
    class_actual = -1
    for b in range(len(LSTM_pred_Y[a])):
        if LSTM_pred_Y[a][b] == 1:
            class_pred = b
        if actual_Y[a][b] == 1:
            class_actual = b
        if class_pred != -1 and class_actual != -1:
            break
    if class_pred != class_actual:
        top = 10 * class_pred
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=blue, outline=blue)
        top = 10 * class_actual
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=red, outline=red)
    else:
        top = 10 * class_pred
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=purple, outline=purple)
im.save(LSTM_IMAGE_PATH)

# Draw an image to compare LSTM_pred_Y to actual_Y
'''
Red = Actual
Yellow = CNN prediction (incorrect)
Orange = CNN Prediction and Actual (correct)
'''
red = (255, 0, 0)
yellow = (255, 255, 0)
orange = (255, 165, 0)
height = 10 * len(obj_cols)
width = 10 * (len(CNN_pred_Y) - CUTOFF)
im = IMG.new("RGB", (width, height), (80, 80, 80))
draw = ImageDraw.Draw(im)
for a in range(len(CNN_pred_Y)):
    left = 10 * a
    right = left + 10
    class_pred = -1
    class_actual = -1
    for b in range(len(CNN_pred_Y[a])):
        if CNN_pred_Y[a][b] == 1:
            class_pred = b
        if actual_Y[a + CUTOFF][b] == 1:
            class_actual = b
        if class_pred != -1 and class_actual != -1:
            break
    if class_pred != class_actual:
        top = 10 * class_pred
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=yellow, outline=yellow)
        top = 10 * class_actual
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=red, outline=red)
    else:
        top = 10 * class_pred
        bottom = top + 10
        draw.rectangle((left, top, right, bottom), fill=orange, outline=orange)
im.save(CNN_IMAGE_PATH)

from sklearn.metrics import confusion_matrix
import numpy as np

# CM for CNN 
Y_pred = np.array(CNN_pred_Y)
Y_actual = np.array(actual_Y[60:])
conf_mat = confusion_matrix(np.argmax(Y_actual, axis=1), np.argmax(Y_pred, axis=1))
print(conf_mat)

# CM for LSTM 
Y_pred = np.array(LSTM_pred_Y)
Y_actual = np.array(actual_Y)
conf_mat = confusion_matrix(np.argmax(Y_actual, axis=1), np.argmax(Y_pred, axis=1))
print(conf_mat)