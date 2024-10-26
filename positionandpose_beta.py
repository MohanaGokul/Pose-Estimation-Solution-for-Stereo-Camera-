import sys
import viz
import vizconnect
import vizshape
import vizact
import vizmat
import threading
import cv2
import mediapipe as mp
import numpy as np
import time
import math
import statistics

# Mediapipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Initialize Vizard environment
viz.setMultiSample(4)  # Anti-aliasing for better visuals
viz.fov(60)            # Set the field of view
viz.clearcolor(viz.SKYBLUE)  # Set a background color
vizshape.addAxes()  # Add coordinate axes to the environment

# Load the virtual scene
piazza = viz.add('piazza.osgb')
if not piazza.valid():
    print("Error loading piazza.osgb")

# Load the avatar
avatar = viz.addAvatar('vcc_female.cfg')
if not avatar.valid():
    print("Error loading avatar")

# Set avatar initial position and orientation
avatar.setPosition([0, 0, 0])  # Initial position of avatar
avatar.setEuler([0, 0, 0])     # Initial orientation of avatar

# Event to signal exit
exit_flag = threading.Event()

yaw = 0
yaw1 = 0
yaw2 = 0

# Function to calculate the angles (yaw, pitch, roll)
def calculate_pose_angles(landmarks):
    global yaw,yaw1,yaw2
    yaw1 = yaw
    yaw2 = yaw1
    yaw3 = yaw2
    print(yaw1,yaw2,yaw3)
    mean_yaw = (yaw1+yaw2+yaw3)/3
    sd_yaw = ((((yaw1-mean_yaw)**2)+((yaw2-mean_yaw)**2)+((yaw3-mean_yaw)**2))/3)
    #sd_yaw = statistics.stdev([yaw1,yaw2,yaw3])
    print(sd_yaw)
    left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
    left_hip = landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP]

    shoulder_width = right_shoulder.x - left_shoulder.x
    shoulder_slope = left_shoulder.y - right_shoulder.y
    shoulder_roll = math.degrees(math.atan2(shoulder_slope, shoulder_width))
    shoulder_yaw = math.degrees(math.atan2(shoulder_width, 1))

    hip_width = right_hip.x - left_hip.x
    hip_slope = left_hip.y - right_hip.y
    hip_roll = math.degrees(math.atan2(hip_slope, hip_width))
    hip_yaw = math.degrees(math.atan2(hip_width, 1))

    roll = 0.6 * shoulder_roll + 0.4 * hip_roll
    yaw = 0.7 * shoulder_yaw + 0.3 * hip_yaw
    if sd_yaw != 0:
        yaw = yaw1
    

    shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
    hip_height = (left_hip.y + right_hip.y) / 2
    pitch = math.degrees(math.atan2(shoulder_height - hip_height, 1))

    return roll, 0, yaw

# Function to read the next position from zed_data_modified.txt
def read_next_position(file, current_index):
    try:
        with open(file, 'r') as f:
            # Move to the current index
            for _ in range(current_index):
                f.readline()  # Skip lines until the current index
            # Read the next line
            line = f.readline().strip()
            if line:  # Check if the line is not empty
                parts = line.split(', ')
                if len(parts) == 3:
                    # Convert parts to float
                    x = float(parts[0]) * 1
                    y = float(parts[1]) * 1
                    z = -float(parts[2]) * 1
                    return (x, y, z), current_index + 1  # Return new position and next index
    except Exception as e:
        print(f"Error reading position data: {e}")
    return None, current_index

# Function to capture pose using OpenCV and Mediapipe
def capture_pose(exit_flag):
    cap = cv2.VideoCapture("raw_video_left.avi")  # Use your video file

    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Open file to log pose angles
    with open("test_run.txt", "w") as f:
        f.write("yaw,pitch,roll,x,y,z\n")

        # Setup Mediapipe pose detection
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            last_read_time = time.time()  # Initialize the time for reading positions
            position_index = 0  # Index to track the current line being read from the file

            while not exit_flag.is_set():  # Check if exit flag is set
                ret, frame = cap.read()
                
                if not ret:  # If the video has reached the end
                    print("Video ended. Restarting from the beginning.")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to the first frame
                    continue  # Skip to the next iteration to read the first frame
                
                # Convert the frame to RGB for Mediapipe processing
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = pose.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                
                # Draw pose landmarks on the frame
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
                    )

                    # Calculate yaw, pitch, and roll based on landmark positions
                    landmarks = results.pose_landmarks.landmark
                    yaw, pitch, roll = calculate_pose_angles(landmarks)
                    orientation = [yaw, pitch, roll]

                    # Check if it's time to update the position from the file
                    current_time = time.time()
                    if current_time - last_read_time >= 0.0625:  # 0.25 seconds
                        positions, position_index = read_next_position('zed_data_modified.txt', position_index)  # Get next position
                        if positions:
                            x, y, z = positions  # Unpack new position
                            print(f"Updating avatar position to: ({x}, {y}, {z})")  # Debugging line
                        else:
                            x, y, z = avatar.getPosition()  # Keep current position if no more lines
                        last_read_time = current_time  # Update the last read time

                    # Update the avatar's orientation and position in the virtual environment
                    avatar.clearActions()
                    avatar.runAction(vizact.parallel(
                        vizact.moveTo([x, y, z], time=0.1, interpolate=None),
                        vizact.spinTo(euler=orientation, time=0.1, interpolate=None)
                    ))
                    
                    # Log the pose angles and position data to the file
                    f.write(f"{yaw},{pitch},{roll},{x},{y},{z}\n")
                
                # Display the video feed with pose landmarks
                cv2.imshow('Mediapipe Feed', image)

                # Exit the loop if 'q' is pressed or exit flag is set
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

# Function to exit on ESC key press
def check_for_exit():
    if viz.key.isDown(viz.KEY_ESCAPE):  # Check if ESC is pressed
        print("ESC pressed. Closing application.")
        exit_flag.set()  # Set the exit flag to terminate the OpenCV thread
        viz.quit()  # Exit the Vizard application

# Start the video capture in a separate thread
thread = threading.Thread(target=capture_pose, args=(exit_flag,))
thread.start()

# Set the timer to check for ESC key press
vizact.ontimer(0, check_for_exit)

# Start Vizard environment
viz.go()
