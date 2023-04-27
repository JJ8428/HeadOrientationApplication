import json
from keras.callbacks import EarlyStopping
from keras.layers import Input, Conv2D, Flatten, Dense, Dropout, LSTM
from keras.models import Sequential
import os
import pandas as pd
from tensorflow import expand_dims, stack

FOLDER_PATH = '../data/recorded_data/'
WINDOW_SIZE = 60

# Load data into dataframe
filenames = os.listdir(FOLDER_PATH)
df_list = []
for f in filenames:
    this_df = pd.read_csv(FOLDER_PATH + f)
    df_list.append(this_df)

# Get list of objects as labels
with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)
obj_cols = []
for obj in objs:
    obj_cols.append(obj['desc'])
obj_cols.append('Nothing')

# Separate data into training and testing 
train_data = []
val_data = df_list[-2]
test_data = df_list[-1]
for a in range(len(df_list) - 2):
    train_data.append(df_list[a])

# Build the model
model = Sequential()
model.add(LSTM(256, return_sequences = True))
model.add(LSTM(256, return_sequences = True))
model.add(LSTM(256, return_sequences = True))
model.add(Dense(256, activation = 'relu'))
model.add(Dropout(0.2))
model.add(Dense(256, activation = 'relu'))
model.add(Dropout(0.2))
model.add(Dense(256, activation = 'relu'))
model.add(Dropout(0.2))
model.add(Dense(len(obj_cols), activation = 'softmax'))

# Compile the model (Experiment with custom loss function)
model.compile(loss = 'categorical_crossentropy', optimizer = 'adam', metrics = ['accuracy'])

# Early stop criteria
early_stop = EarlyStopping(monitor='val_loss', patience=10, verbose=1)

# Make data into snap shots and split input and output
val_ss_X = []
val_ss_Y = []
test_ss_X = []
test_ss_Y = []
for a in range(0, len(val_data) - WINDOW_SIZE):
    X = val_data.drop(columns = obj_cols).iloc[a:a + WINDOW_SIZE]
    Y = val_data[obj_cols].iloc[a + WINDOW_SIZE]
    val_ss_X.append(expand_dims(X, axis = -1))
    val_ss_Y.append(Y)
for a in range(0, len(test_data) - WINDOW_SIZE):
    X = test_data.drop(columns = obj_cols).iloc[a:a + WINDOW_SIZE]
    Y = test_data[obj_cols].iloc[a + WINDOW_SIZE]
    test_ss_X.append(expand_dims(X, axis = -1))
    test_ss_Y.append(Y)
val_ss_X = stack(val_ss_X)
val_ss_Y = stack(val_ss_Y)
test_ss_X = stack(test_ss_X)
test_ss_Y = stack(test_ss_Y)

import numpy as np

# Train the data for every XY batch we modify
for ds in train_data:
    train_ss_X = []
    train_ss_Y = []
    for a in range(0, len(ds) - WINDOW_SIZE):
        X = ds.drop(columns = obj_cols).iloc[a:a + WINDOW_SIZE].values
        Y = ds[obj_cols].iloc[a + WINDOW_SIZE].values
        train_ss_X.append(expand_dims(X, axis = -1))
        train_ss_Y.append(Y)
    train_ss_X = stack(train_ss_X)
    train_ss_Y = stack(train_ss_Y)

    print(np.squeeze(train_ss_X).shape)

    import sys
    sys.exit()

    model.fit(train_ss_X, train_ss_Y, validation_data=(val_ss_X, val_ss_Y), epochs = 50, batch_size = 50, callbacks=[early_stop])
    model.reset_states()

# Evaluate the model on the test data
loss, acc = model.evaluate(test_ss_X, test_ss_Y, batch_size=100)
print('Test loss:', loss)
print('Test acc:', acc)

# Save the model
model.save('../data/models/LSTM_ss_looking_at.h5')