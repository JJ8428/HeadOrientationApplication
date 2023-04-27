from jekel_sphereFit import sphereFit
import json
import matplotlib.pyplot as plt
from pynput import keyboard
import serial

'''
    This script calculated the hard iron magnetic offsets of the board
    Each board has a different hard iron magnetic offset, so this is almost required to run
    Simply run the script in a terminal and slowly move the board to cover almost all orientations

    Your goal should be to paint enough data on the 2D plot to have a red, blue, and green circle or 
    atleast enough data for a circle completion algorithm to draw the circle accurately

    The offsets will be stored in data/hard_mag_offset_xyz.csv
    Make sure to update the appropriate variables in the arduino code

    It is imperative to recalibrate in every new environment you are in for the best results
'''

# Set record_data to True if you want to record a fresh set of data (Will take 3-4 minutes)
# Set record_data to False if you want to use data from previous recording session
record_data = True

fig, ax = plt.subplots()

data_type = 'mag'

data_x = []
data_y = []
data_z = []

if record_data:
    def on_press(key):
        if key == keyboard.Key.space:
            return False

    print('Gathering data...')
    print('Press SPACE when to stop collecting data...')
    print()
    ser = serial.Serial('/dev/ttyACM0', 9600)
    plt.ioff()
    with keyboard.Listener(on_press = on_press) as listener:
        while listener.running:
            nano_raw_output = ser.readline()
            nano_output = nano_raw_output.decode().strip()
            print(nano_output)
            data = json.loads(nano_output)
            x = float(data[data_type + '_x'])
            y = float(data[data_type + '_y'])
            z = float(data[data_type + '_z'])
            data_x.append(x)
            data_y.append(y)
            data_z.append(z)
            ax.plot(x, y, 'ro')
            ax.plot(y, z, 'bo')
            ax.plot(z, x, 'go')
            plt.pause(.05)

    print('Saving raw data...')
    w = open(f'../data/calibration/raw_{data_type}_xyz.csv', 'w')
    for a in range(len(data_x)):
        to_write = f'{data_x[a]},{data_y[a]},{data_z[a]}'
        if a + 1 != len(data_x):
            to_write += '\n'
        w.write(to_write)
    w.close()
else:
    print('Reading pre-recorded raw data...')
    r = open(f'../data/calibration/raw_{data_type}_xyz.csv')
    for line in r.readlines():
        data = line.strip().split(',')
        data_x.append(float(data[0]))
        data_y.append(float(data[1]))
        data_z.append(float(data[2]))
    
print('Calculating best fitting sphere...')
r, cx, cy, cz = sphereFit(data_x, data_y, data_z)
cx = cx[0]
cy = cy[0]
cz = cz[0]

print(f'Radius: {r}, Hard {data_type} Offset: x:{cx}, y: {cy}, z: {cz}')

print('Saving offsets...')
w = open(f'../data/calibration/hard_{data_type}_offset_xyz.csv', 'w')
w.write(f'{r},{cx},{cy},{cz}')
w.close()

'''
print('Correcting data...')
correctX = [val - cx for val in data_x]
correctY = [val - cy for val in data_y]
correctZ = [val - cz for val in data_z]

print('Plotting corrected data...')
if record_data:
    plt.clf()
ax.plot(correctX, correctY, 'ro')
ax.plot(correctY, correctZ, 'bo')
ax.plot(correctZ, correctX, 'go')
plt.axis('square')
plt.show()
'''