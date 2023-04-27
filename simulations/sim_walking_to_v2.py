import json
import math
from sim_walking_to_v1 import ANGLE_THRESHOLD, signal_source, observations
from sim_walking_to_v1 import can_view, get_parallel_angle_diff, circle_coords, get_slope, line_circle_intersection  

with open('../environment/complex_room.json', 'r') as f:
    objs = json.load(f)

'''
    Returns a dictionary tell what object the user is walking towards and
    from position is the user walking to the object based on 2 concurrent observations.

    This can be can combined with dead-reckoning BUT this needs more testing to verify 
    the accuracy and determine what conditions can contribute to errors or inaccuracies.

    This should only be called when the user IS walking. 
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
    # possible_objects = []
    tmp_possible_locations = {}
    possible_locations = {}
    objs_iter = objs.copy()
    for c1 in circle_obs1:
        '''
            Estimate with location c1 with a circle drawn with an adjusted radius at observation2.
            We will call this point c2. The way we calculate c2 uses the heading at observation1, 
            so c1 and c2 will already be lined up.
        '''
        c2 = line_circle_intersection(c1[0], c1[1], get_slope(observation1['heading']),
            signal_source['x'], signal_source['z'], adjusted_radius, observation2['heading'])
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
            if can_view(objs_iter[a - rewind]['heading_floor'], objs_iter[a - rewind]['heading_ceiling'], 
                observation2['heading'] + 180):
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
                        # possible_objects.append(objs_iter[a - rewind]['desc'])
                        possible_traversed_dist = math.sqrt((c2[0] - c1[0])**2 + (c2[1] - c1[1])**2)
                        if objs_iter[a - rewind]['desc'] in tmp_possible_locations:
                            tmp_possible_locations[objs_iter[a - rewind]['desc']] = (
                                (
                                    tmp_possible_locations[objs_iter[a - rewind]['desc']][0][0] + c2[0],
                                    tmp_possible_locations[objs_iter[a - rewind]['desc']][0][1] + observation2['altitude'],
                                    tmp_possible_locations[objs_iter[a - rewind]['desc']][0][2] + c2[1],
                                ),
                                tmp_possible_locations[objs_iter[a - rewind]['desc']][1] + possible_traversed_dist,
                                tmp_possible_locations[objs_iter[a - rewind]['desc']][2] + 1
                            )
                        else:
                            tmp_possible_locations[objs_iter[a - rewind]['desc']] = (
                                (
                                    c2[0], 
                                    observation2['altitude'], 
                                    c2[1],
                                ),
                                possible_traversed_dist, 
                                1
                            )
                        # del objs_iter[a - rewind]
                        # rewind += 1
    
    for obj in tmp_possible_locations:
        possible_locations[obj] = {
            'x': tmp_possible_locations[obj][0][0] / tmp_possible_locations[obj][2],
            'y': tmp_possible_locations[obj][0][1] / tmp_possible_locations[obj][2],
            'z': tmp_possible_locations[obj][0][2] / tmp_possible_locations[obj][2],
            'possible_traversed_dist': tmp_possible_locations[obj][1] / tmp_possible_locations[obj][2]
        }
        
    # return set(possible_objects), possible_locations
    return possible_locations

def main():
    
    '''
        To adapt this to a demo, we need to check for the following:
        - Has the user been predicted walking towards the object numerous iterations in a row?
        - Has the user walked towards that object for a certain amount of time (certain # of observations)
        - Is the distance traversed between between each of the observations similar?

        Somethings to be aware about...
        - If the environment is symmetric to the anchor along some plane in a 3d space, it is possible to trick the simulation
            - This is why a list is being returned
            - This can be solved by placing the anchor in a locations that does not allow for symmetry along any plane in a 3d space
            - It's unlikely objects are placed in a symmetrical manner out
    '''
    print(walking_to(signal_source, observations[0], observations[1], objs))

if __name__ == "__main__":
    main()
    