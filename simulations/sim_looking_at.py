import json
import math

ANGLE_THRESHOLD = 15

'''
x -> left (-x) | right (+x)
y -> lower (-y) | higher (+y)
z -> backward (-z) | forward (+z)

Heading is always described in a clockwise manner from heading_floor to heading_ceiling
If the heading_floor and heading_ceiling match, then assume that the object can be viewed from any angle

Answer key for simple_room.json

Pitch:|Heading:|Desc:
------+--------+---------
0     |0       |Computer
0     |-45     |Pillow
0     |90      |Plant
45    |90      |Hat
'''

with open('../environment/simple_room.json', 'r') as f:
    objs = json.load(f)

def can_view(heading_floor, heading_ceiling, angle):
    
    # If object is viewable from all angles, floor == ceiling
    if heading_ceiling == heading_floor:
        return True
    elif heading_ceiling < heading_floor:
        heading_ceiling += 360
        angle = (angle + 360) % 360
    if angle >= heading_floor and angle <= heading_ceiling:
        return True
    else:
        return False

# Returns the angle between 2 vectors on a plane parallel to both
def get_parallel_angle_diff(v1, v2):

    cross_product = [v1[1] * v2[2] - v1[2] * v2[1],
                     v1[2] * v2[0] - v1[0] * v2[2],
                     v1[0] * v2[1] - v1[1] * v2[0]]
    mag_cross_product = (cross_product[0]**2 + cross_product[1]**2 + cross_product[2]**2)**.5
    
    if mag_cross_product == 0:
        return 0
    
    unit_cross_product = [cross_product[i]/mag_cross_product for i in range(3)]
    v1_proj = [v1[i] - (v1[0] * unit_cross_product[0] + v1[1] * unit_cross_product[1] + v1[2] * unit_cross_product[2]) * unit_cross_product[i] for i in range(3)]
    v2_proj = [v2[i] - (v2[0] * unit_cross_product[0] + v2[1] * unit_cross_product[1] + v2[2] * unit_cross_product[2]) * unit_cross_product[i] for i in range(3)]
    
    dot_product = v1_proj[0]*v2_proj[0] + v1_proj[1]*v2_proj[1] + v1_proj[2]*v2_proj[2]
    mag_v1_proj = (v1_proj[0]**2 + v1_proj[1]**2 + v1_proj[2]**2)**.5
    mag_v2_proj = (v2_proj[0]**2 + v2_proj[1]**2 + v2_proj[2]**2)**.5
    angle = math.acos(dot_product / (mag_v1_proj * mag_v2_proj))

    return math.degrees(angle)

def looking_at(observation, objs):

    user_heading = math.radians(observation['heading'])
    user_pitch = math.radians(observation['pitch'])

    # User location is assumed to be 0, altitude, 0)
    user_loc_x = 0 # observation['x']
    user_loc_y = observation['altitude'] # observation['y']
    user_loc_z = 0 # observation['z']

    x = math.sin(user_heading) * math.cos(user_pitch)
    y = math.sin(user_pitch)
    z = math.cos(user_heading) * math.cos(user_pitch)
    mag_uv = (x**2 + y**2 + z**2)**.5
    view_uv = [x / mag_uv, y / mag_uv, z / mag_uv]

    # Note: mag_objv is also the distance between the user and object
    possible_objs = []
    for obj in objs:
        delta_x = obj['x'] - user_loc_x
        delta_y = obj['y'] - user_loc_y
        delta_z = obj['z'] - user_loc_z
        mag_objv = (delta_x**2 + delta_y**2 + delta_z**2)**.5
        obj_uv = [delta_x / mag_objv, delta_y / mag_objv, delta_z / mag_objv]
        delta_angle = get_parallel_angle_diff(view_uv, obj_uv)
        if delta_angle <= ANGLE_THRESHOLD and can_view(obj['heading_floor'], obj['heading_ceiling'], user_heading + 180):
            possible_objs.append(obj['desc'])
        
    return possible_objs

# Assume the user is at (0, altitude, 0)
# Hardcoded observations we recieve at some timestamp t
observation = {
    # 'x': 0,
    # 'z': 0,
    'pitch': 0, 
    'heading': -70,
    'altitude': 1 # 'y': _
}

def main():
    
    print(looking_at(observation, objs))

if __name__ == "__main__":
    main()
    