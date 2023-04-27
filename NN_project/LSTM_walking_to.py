import json
from keras.callbacks import EarlyStopping
import keras.backend as K
from keras.layers import Dense, Dropout, LSTM
from keras.models import Sequential
import tensorflow as tf
import os
import pandas as pd

FOLDER_PATH = '../data/recorded_data/'

# Load data into dataframe
filenames = os.listdir(FOLDER_PATH)
sum_df = pd.DataFrame()
df_list = []
for f in filenames:
    this_df = pd.read_csv(FOLDER_PATH + f)
    # this_df['roll'] = deg2rad(this_df['roll'])
    # this_df['pitch'] = deg2rad(this_df['pitch'])
    # this_df['heading'] = deg2rad(this_df['heading'])
    df_list.append(this_df)
    sum_df = sum_df.append(this_df)

# Get list of objects as labels
with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)
obj_cols = []
for obj in objs:
    obj_cols.append(obj['desc'])
obj_cols.append('Nothing')

'''
EXPERIMENTAL COLUMN SWAP
What if instead of booleans as to whether the board is in motion or is rotating, we feed how long it has been in neither state?

We coded our hard truth with 1.5 seconds, since our board returns data at 20 Hz, 30 => 1.5 seconds until positive
LSTM can try to learn positive means we are looking at something
'''
'''
score1 = -30
score2 = -30
for a in range(len(df_list)):
    no_motion_score = []
    no_rotation_score = []
    for b in range(len(df_list[a])):
        if df_list[a].iloc[b]['in_motion'] == 0:
            if(score1 < 0):
                score1 += 1
        else:
            score1 = -30
        if df_list[a].iloc[b]['is_rotating'] == 0:
            if(score2 < 0):
                score2 += 1
        else:
                score2 = -30
        no_motion_score.append(score1)
        no_rotation_score.append(score2)
    df_list[a]['in_motion'] = no_motion_score
    df_list[a] = df_list[a].rename(columns={'in_motion': 'no_motion_score'})
    df_list[a]['is_rotating'] = no_rotation_score
    df_list[a] = df_list[a].rename(columns={'is_rotating': 'no_rotation_score'})
'''

# Look at the number of occurences for each class (w/ one hot encoding in mind)
'''
for col in obj_cols:
    print(sum_df[col].value_counts())
'''

# Make sure data is clean
'''
error_rows = 0

def one_hot_encoding_error(row):

    global error_rows

    sum = 0
    for cols in obj_cols:
        sum += row[cols]
    if sum != 1:
        print(f'{sum} != 0')
        error_rows += 1

sum_df.apply(lambda row: one_hot_encoding_error(row), axis = 1)
print(error_rows)
'''

# Separate data into training and testing 
train_data = []
val_data = df_list[-2]
test_data = df_list[-1]
for a in range(len(df_list) - 2):
    train_data.append(df_list[a])

# Separate data into input and output
train_X = []
train_Y = []
for df in train_data:
    train_X.append(df.drop(columns = obj_cols).values)
    train_Y.append(df[obj_cols].values)
val_X = val_data.drop(columns = obj_cols).values
val_Y = val_data[obj_cols].values
test_X = test_data.drop(columns = obj_cols).values
test_Y = test_data[obj_cols].values

# Build the model
model = Sequential()
model.add(LSTM(32, return_sequences = True))
model.add(Dropout(0.2))
model.add(LSTM(64, return_sequences = True))
model.add(Dropout(0.2))
model.add(LSTM(32))
model.add(Dropout(0.2))
model.add(Dense(32, activation = 'relu'))
model.add(Dropout(0.2))
model.add(Dense(32, activation = 'relu'))
model.add(Dropout(0.2))
model.add(Dense(len(obj_cols), activation = 'softmax'))

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

# Compile the model (Experiment with custom loss function)
model.compile(loss = 'categorical_crossentropy', optimizer = 'adam', metrics = ['accuracy'])
# model.compile(loss = custom_loss, optimizer = 'adam', metrics = ['accuracy'], run_eagerly=True)

# Early stop criteria
early_stop = EarlyStopping(monitor='val_loss', patience=5, verbose=1)

# Train the model
for a in range(len(train_X)):
    model.fit(train_X[a].reshape(-1, 1, 5), train_Y[a], validation_data=(val_X.reshape(-1, 1, 5), val_Y), epochs = 20, batch_size = 100, callbacks=[early_stop])
    model.reset_states()

# Evaluate the model on the test data
loss, acc = model.evaluate(test_X.reshape(-1, 1, 5), test_Y, batch_size=1000)
print('Test loss:', loss)
print('Test acc:', acc)

# Save the model
model.save('../data/models/LSTM_looking_at.h5')