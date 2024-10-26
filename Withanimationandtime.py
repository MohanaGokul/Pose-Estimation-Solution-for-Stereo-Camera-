import viz
import vizconnect
import vizshape
import vizact
import vizmat
import time  # Import time module for getting the current date and time

vizshape.addAxes()

viz.go()
viz.add('piazza.osgb')
origin1 = viz.add('soccerball.ive') 
origin1.setPosition([0,0,0])
origin = [0, 0, 0]

# Load the vizconnect configuration file
vizconnect.go('vizconnect_config.py')

# Get the Vive Tracker objects (configured in VizConnect)
tracker_1 = vizconnect.getTracker('steamvr_tracker')  # Replace 'steamvr_tracker' with your tracker name
tracker_2 = vizconnect.getTracker('steamvr_tracker2')  # Replace 'steamvr_tracker_2' with the name of the second tracker

# Load an avatar
avatar = viz.addAvatar('vcc_female.cfg')
avatar.setPosition([0, 0, 0])  # Initial position of avatar
avatar.setEuler([0, 0, 0])     # Initial orientation of avatar

# Load the walking and idle animations
idle_animation = avatar.state(1)  # Assumes state 1 is idle
walk_animation = avatar.state(2)  # Assumes state 2 is walking

# Set up initial states
avatar.state(1)

# Define a threshold for detecting movement
move_threshold = 0.0001
move_duration = 0.1  # Time for transitions

# Track the previous position to detect movement
previous_position = avatar.getPosition()
initial_tracker_position = tracker_1.getPosition()
initial_tracker_2_position = tracker_2.getPosition()

# Open a file in write mode to clear contents and write headers for the first tracker
with open('vive_data.txt', 'w') as vive_data_file:
    vive_data_file.write("Timestamp, Position_X, Position_Y, Position_Z, Orientation_Yaw, Orientation_Pitch, Orientation_Roll\n")

# Open a file in write mode to clear contents and write headers for the second tracker
with open('vive_zed_data.txt', 'w') as vive_zed_data_file:
    vive_zed_data_file.write("Timestamp, Position_X, Position_Y, Position_Z, Orientation_Yaw, Orientation_Pitch, Orientation_Roll\n")

# Function to update avatar's position, orientation, and animation based on the first tracker
def update_avatar():
    global previous_position
    
    # Get the first tracker's current position and orientation
    tracker_1_position = tracker_1.getPosition()
    tracker_1_orientation = tracker_1.getEuler()

    # Get the second tracker's current position and orientation
    tracker_2_position = tracker_2.getPosition()
    tracker_2_orientation = tracker_2.getEuler()
    
    offset = vizmat.Distance(origin, tracker_1_position)
    
    relative_position = [tracker_1_position[0] - initial_tracker_position[0],
                         tracker_1_position[1] - initial_tracker_position[1],
                         tracker_1_position[2] - initial_tracker_position[2]]
                         
    relative_position_2 = [tracker_2_position[0] - initial_tracker_2_position[0],
                         tracker_2_position[1] - initial_tracker_2_position[1] ,
                         tracker_2_position[2] - initial_tracker_2_position[2]]

    # Move the avatar smoothly to the new position based on the first tracker
    avatar.clearActions()
    avatar.runAction(vizact.parallel(
        vizact.moveTo(relative_position, 
                       time=move_duration, interpolate=None),
        vizact.spinTo(euler=tracker_1_orientation, time=move_duration, interpolate=None)
    ))

    # Get the current date and time in YYYY MM DD HH MM SS format
    current_time = time.strftime("%Y %m %d %H %M %S")

    # Round relative position and tracker orientation values to 2 decimal places
    relative_position = [round(val, 2) for val in relative_position]
    tracker_1_orientation = [round(val, 2) for val in tracker_1_orientation]
    tracker_2_position = [round(val, 2) for val in relative_position_2]
    tracker_2_orientation = [round(val, 2) for val in tracker_2_orientation]

    # Append first tracker's data to the 'vive_data.txt' file
    with open('vive_data.txt', 'a') as vive_data_file:
        vive_data_file.write(f'{current_time}, {relative_position[0]}, {relative_position[1]}, {relative_position[2]}, ' +
                             f'{tracker_1_orientation[0]}, {tracker_1_orientation[1]}, {tracker_1_orientation[2]}\n')

    # Append second tracker's data to the 'vive_zed_data.txt' file
    with open('vive_zed_data.txt', 'a') as vive_zed_data_file:
        vive_zed_data_file.write(f'{current_time}, {tracker_2_position[0]}, {tracker_2_position[1]}, {tracker_2_position[2]}, ' +
                                 f'{tracker_2_orientation[0]}, {tracker_2_orientation[1]}, {tracker_2_orientation[2]}\n')
    
    # Check if the avatar is moving (compare current position with previous position)
    current_position = avatar.getPosition()
    distance_moved = vizmat.Distance(current_position, previous_position)

    # If the avatar is moving, switch to walking animation
    if distance_moved > move_threshold:
        avatar.state(2)
    else:
        avatar.state(1)

    # Update the previous position
    previous_position = current_position

# Continuously update the avatar's position, orientation, and animation
vizact.ontimer(0, update_avatar)

# Close the file when the script ends
def onExit():
    # No need to close the files here since they are opened and closed each time in append mode
    pass

viz.callback(viz.EXIT_EVENT, onExit)
