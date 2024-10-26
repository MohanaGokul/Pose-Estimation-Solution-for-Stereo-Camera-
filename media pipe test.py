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
import pyzed.sl as sl
import ogl_viewer.viewer as gl
import cv_viewer.tracking_viewer as cv_viewer

USE_BATCHING = False

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
if piazza.valid() == False:
    print("Error loading piazza.osgb")

# Load the avatar
avatar = viz.addAvatar('vcc_female.cfg')
if avatar.valid() == False:
    print("Error loading avatar")

# Set avatar initial position and orientation
avatar.setPosition([0, 0, 0])  # Initial position of avatar
avatar.setEuler([0, 0, 0])     # Initial orientation of avatar

idle_animation = avatar.state(1)  # Assumes state 1 is idle
walk_animation = avatar.state(2)  # Assumes state 2 is walking

avatar.state(1)

move_threshold = 0.0001
move_duration = 0.1
yaw = 0
# Function to calculate the angles (yaw, pitch, roll)
def calculate_pose_angles(landmarks):
    global yaw
    yaw1 = yaw
    # Get landmarks for shoulders and hips
    left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
    left_hip = landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP]

    # Calculate shoulder roll and yaw
    shoulder_width = right_shoulder.x - left_shoulder.x
    shoulder_slope = left_shoulder.y - right_shoulder.y
    shoulder_roll = math.degrees(math.atan2(shoulder_slope, shoulder_width))

    shoulder_yaw = math.degrees(math.atan2(shoulder_width, 1))

    # Calculate hip roll and yaw
    hip_width = right_hip.x - left_hip.x
    hip_slope = left_hip.y - right_hip.y
    hip_roll = math.degrees(math.atan2(hip_slope, hip_width))

    hip_yaw = math.degrees(math.atan2(hip_width, 1))

    # Combine roll and yaw from shoulders and hips with weights
    roll = 0.6 * shoulder_roll + 0.4 * hip_roll
    yaw = 0.6 * shoulder_yaw + 0.4 * hip_yaw
    if yaw+60 > yaw1:
        yaw = yaw1

    # Calculate pitch using average shoulder and hip heights
    shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
    hip_height = (left_hip.y + right_hip.y) / 2
    pitch = math.degrees(math.atan2(shoulder_height - hip_height, 1))

    return roll, 0, yaw

# Function to capture pose using OpenCV and Mediapipe
def capture_pose():
    # Start video capture
    global previous_position
    cap = cv2.VideoCapture(1)

    # Open file to log pose angles
    with open("test_run.txt", "w") as f:
        f.write("yaw,pitch,roll\n")
        
        # Setup Mediapipe pose detection
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
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

                    # Update the avatar's orientation in the virtual environment
                    avatar.clearActions()
                    avatar.runAction(vizact.parallel(
                        vizact.spinTo(euler=orientation, time=0.1, interpolate=None)
                    ))
                    
                    # Get current timestamp and log the pose angles to the file
                    f.write(f"{yaw},{pitch},{roll}\n")
                
                # Display the video feed with pose landmarks
                cv2.imshow('Mediapipe Feed', image)

                # Exit the loop if 'q' is pressed
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

# Start the video capture in a separate thread
thread = threading.Thread(target=capture_pose)
thread.start()

# Start Vizard environment
viz.go()
