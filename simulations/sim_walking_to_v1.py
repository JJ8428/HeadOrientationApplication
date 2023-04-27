import json
import math
from sim_looking_at import can_view, get_parallel_angle_diff

ANGLE_THRESHOLD = 7.5

signal_source = {
    'x': 0,
    'y': 2,
    'z': 0,
}

# Hardcoded observations we recieve at time stamps [0]:t-1, [1]:t
# Set of observations that have the user walking towards the Thermostat object
observations = [
    {
        'distance': 16.01,
        'pitch': 0,
        'heading': -90,
        'altitude': 2
    },
    {
        'distance': 13.46,
        'pitch': 0,
        'heading': -90,
        'altitude': 2
    }
]

'''
# Set of observations that don't have the user walking any where
observations = [
    {
        'distance': 21.21,
        'pitch': 0,
        'heading': 90,
        'altitude': 2
    },
    {
        'distance': 13.46,
        'pitch': 0,
        'heading': -90,
        'altitude': 2
    }
]
'''

'''
# Hardcoded objects in a given environment
objs = [
    {
        "desc": "Window_1",
        "x": 5,
        "y": 2,
        "z": 25,
        "range": 20,
        "heading_floor": 120,
        "heading_ceiling": -150
    },
    {
        "desc": "Window_2",
        "x": 25,
        "y": 2,
        "z": 25,
        "range": 20,
        "heading_floor": 135,
        "heading_ceiling": -150
    },
    {
        "desc": "Clock",
        "x": 32.5,
        "y": 4,
        "z": 15,
        "range": 20,
        "heading_floor": 180,
        "heading_ceiling": 0
    },
    {
        "desc": "Poster",
        "x": 20,
        "y": 2,
        "z": 4,
        "range": 20,
        "heading_floor": -120,
        "heading_ceiling": 0
    },
    {
        "desc": "Thermostat",
        "x": 0,
        "y": 2,
        "z": 12.5,
        "range": 20,
        "heading_floor": 0,
        "heading_ceiling": 180
    }
]
'''

with open('../environment/complex_room.json', 'r') as f:
    objs = json.load(f)

# Generate coordinates of a circle with variability based on size
def circle_coords(radius, signal_source, resolution = 15):

    coords = []
    '''
    On smaller circles, less points where the space between 2 points is not to large.
    To make the program computationally cheap, choosing the number of points based on 
    '''
    dynamic_resolution = int(radius * resolution)
    interval = 0
    for _ in range(dynamic_resolution):
        interval += (2 * math.pi / dynamic_resolution)
        coords.append([
            (math.cos(interval) * radius) + signal_source['x'], (math.sin(interval) * radius) + signal_source['z']
        ])
    return coords

# Get the slope angle in the range (-180, 180] where 0 is vertical
def get_slope(angle):

    return math.tan(math.radians(90 - angle))

'''
    Returns a point of intersection between a line defined 
    by a point (line_x, line_y) and a slope m, and a circle 
    defined at the center (circle_x, circle_y) with a radius r
'''
def line_circle_intersection(px, py, m, cx, cy, r, heading):

    px -= cx
    py -= cy

    a = 1 + m**2
    b = 2 * ((py * m) - (px * m**2))
    c = (px**2 * m**2) + py**2 - (2 * px * py * m) - r**2

    discriminant = b**2 - (4 * a * c)
    
    # No intersection
    if discriminant < 0:
        return None
    # 1 intersection
    elif discriminant == 0:
        x = -b / (2 * a)
        y = (m * (x - px)) + py
        return (x + cx, y + cy)
    # 2 intersections
    else:
        x1 = (-b + math.sqrt(discriminant)) / (2 * a)
        y1 = (m * (x1 - px)) + py
        x2 = (-b - math.sqrt(discriminant)) / (2 * a)
        y2 = (m * (x2 - px)) + py

        # Compare angle among both points to see what our true point is
        dist1 = math.sqrt((x1 - px)**2 + (y1 - py)**2)
        dist2 = math.sqrt((x2 - px)**2 + (y2 - py)**2)
        if (dist1 < dist2):
            return (x1 + cx, y1 + cy)
        else:
            return (x2 + cx, y2 + cy)

'''
    Return a list of objects the user can be walking to based on
    2 concurrent observations.

    We need to make sure this is only called when the user IS walking. 
'''
def walking_to(signal_source, observation1, observation2, objs):

    # Determine if we are walking in a straightline from observation1 to observation2
    angle_diff = abs(observation1['heading'] - observation2['heading'])
    if angle_diff > 180: 
        angle_diff = 360 - angle_diff
    if angle_diff > ANGLE_THRESHOLD:
        return []
    
    # Calculate possible positions of where we are at observation1
    delta_y = observation1['altitude'] - signal_source['y']
    adjusted_radius = math.sqrt(observation1['distance']**2 - delta_y**2)
    circle_obs1 = circle_coords(adjusted_radius, signal_source)

    # Calculate possible paths based on observation1 and observation2
    delta_y = observation2['altitude'] - signal_source['y']
    adjusted_radius = math.sqrt(observation2['distance']**2 - delta_y**2)
    possible_objects = []
    objs_iter = objs.copy()
    for c1 in circle_obs1:
        '''
            Estimate with location c1 with a circle drawn with an adjusted radius at observation2.
            We will call this point c2. The way we calculate c2 uses the heading at observation1, 
            so c1 and c2 will already be lined up.
        '''
        c2 = line_circle_intersection(c1[0], c1[1], get_slope(observation1['heading']), signal_source['x'], signal_source['z'], adjusted_radius, observation2['heading'])
        '''
            Calculate the vector from location c2 to the object.
            If that vector lines up with the user's POV (pitch and heading), we can assume that
            the user is walking towards that object. 
        '''
        if c2 == None: 
            continue
        # Create a unit vector to capture the user's POV
        theta_x = math.sin(math.radians(observation2['heading'])) * math.cos(math.radians(observation2['pitch']))
        theta_y = math.sin(math.radians(observation2['pitch']))
        theta_z = math.cos(math.radians(observation2['heading'])) * math.cos(math.radians(observation2['pitch']))
        mag_uv = math.sqrt(theta_x**2 + theta_y**2 + theta_z**2)
        view_uv = [theta_x / mag_uv, theta_y / mag_uv, theta_z / mag_uv]

        rewind = 0
        for a in range(0, len(objs_iter)):
            # First check if our heading even allows for us to look at the object
            if can_view(objs_iter[a - rewind]['heading_floor'], objs_iter[a - rewind]['heading_ceiling'], observation2['heading'] + 180):
                # Create a unit vector to capture the angle of location c2 to the object
                delta_x = objs_iter[a - rewind]['x'] - c2[0]
                delta_y = objs_iter[a - rewind]['y'] - observation2['altitude']
                delta_z = objs_iter[a - rewind]['z'] - c2[1]
                # This is also the distance from the user at location c2 and the object
                mag_objv = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
                # Check if we are in range of the object
                if mag_objv <= objs_iter[a - rewind]['range']:
                    obj_uv = [delta_x / mag_objv, delta_y / mag_objv, delta_z / mag_objv]
                    delta_angle = get_parallel_angle_diff(view_uv, obj_uv)
                    # Check if difference between the 2 vectors is under a certain threshold
                    if delta_angle <= ANGLE_THRESHOLD:
                        possible_objects.append(objs_iter[a - rewind]['desc'])
                        del objs_iter[a - rewind]
                        rewind += 1
    
    return possible_objects

def main():
    
    print(walking_to(signal_source, observations[0], observations[1], objs))

if __name__ == "__main__":
    main()
    