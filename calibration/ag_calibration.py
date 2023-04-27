import json
import matplotlib.pyplot as plt
from pynput import keyboard
import serial

'''
    When running the script ensure that the board is absolutely still and on a hard surface.
        - Orientation does not matter as long as the board is still
        - Do not let the board lay on carpet, with a fan running, or etc. 
        - Less disturbances mean better calibration results


    This script handles calculating the gryoscope and accelomter offsets
    The gyroscope offsets are stored in data/hard_gyro_offsets_xyz.csv
    The resultant acceleration will be stored in data/acc_resultant.csv

    Once these files have been generated, please go into the arduino code and update the appropriate variables
'''

data_gx = []
data_gy = []
data_gz = []
data_ax = []
data_ay = []
data_az = []

def on_press(key):
    
    if key == keyboard.Key.space:
        return False

print('Gathering data...')
print('Press SPACE when to stop collecting data...')
print()
ser = serial.Serial('/dev/ttyACM0', 9600)
with keyboard.Listener(on_press = on_press) as listener:
    while listener.running:
        nano_raw_output = ser.readline()
        nano_output = nano_raw_output.decode().strip()
        data = json.loads(nano_output)
        gx = float(data['gyro_x'])
        gy = float(data['gyro_y'])
        gz = float(data['gyro_z'])
        ax = float(data['acc_x'])
        ay = float(data['acc_y'])
        az = float(data['acc_z'])
        data_ax.append(ax)
        data_ay.append(ay)
        data_az.append(az)
        data_gx.append(gx)
        data_gy.append(gy)
        data_gz.append(gz)

print('Plotting data before calibration...')
y_axis = list(range(len(data_gx)))
plt.plot(data_gx, y_axis, 'red')
plt.plot(data_gy, y_axis, 'blue')
plt.plot(data_gz, y_axis, 'green')
plt.show()

mean_gx = sum(data_gx)/len(data_gx)
mean_gy = sum(data_gy)/len(data_gy)
mean_gz = sum(data_gz)/len(data_gz)
mean_ax = sum(data_ax)/len(data_ax)
mean_ay = sum(data_ay)/len(data_ay)
mean_az = sum(data_az)/len(data_az)

resultant_acc = (((mean_ax ** 2) + (mean_ay ** 2) + (mean_az ** 2)) ** .5) * 10

print(f'Hard Gyro Offset: x: {mean_gx}, y: {mean_gy}, z: {mean_gz}')

print(f'Average Resultant Acc: {resultant_acc} m/(sec^2)')

print('Saving offsets...')
w = open('../data/calibration/hard_gyro_offset_xyz.csv', 'w')
w.write(f'{mean_gx},{mean_gy},{mean_gz}')
w.close()

print('Saving resultant...')
w = open('../data/calibration/acc_resultant.csv', 'w')
w.write(f'{resultant_acc}')
w.close()

