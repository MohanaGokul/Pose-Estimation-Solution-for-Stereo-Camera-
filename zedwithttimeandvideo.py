import sys
import numpy as np
import cv2
import pyzed.sl as sl
import time
import ogl_viewer.viewer as gl
import cv_viewer.tracking_viewer as cv_viewer

# Variable to enable/disable the batch option in Object Detection module
USE_BATCHING = False
with open("zed_data.txt", "w") as data_file:
    data_file.write("ZED Object Detection Data\n")

if __name__ == "__main__":
    print("Running object detection ... Press 'Esc' to quit")
    zed = sl.Camera()
    
    # Create a InitParameters object and set configuration parameters
    init_params = sl.InitParameters()
    init_params.coordinate_units = sl.UNIT.METER
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP  
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.depth_maximum_distance = 20
    is_playback = False

    # If applicable, use the SVO given as parameter
    # Otherwise use ZED live stream
    if len(sys.argv) == 2:
        filepath = sys.argv[1]
        print("Using SVO file: {0}".format(filepath))
        init_params.svo_real_time_mode = True
        init_params.set_from_svo_file(filepath)
        is_playback = True

    status = zed.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit()

    # Enable positional tracking module
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    zed.enable_positional_tracking(positional_tracking_parameters)

    # Enable object detection module
    obj_param = sl.ObjectDetectionParameters()
    obj_param.instance_module_id = 0
    obj_param.detection_model = sl.OBJECT_DETECTION_MODEL.MULTI_CLASS_BOX_FAST
    obj_param.enable_tracking = True
    zed.enable_object_detection(obj_param)

    body_param = sl.BodyTrackingParameters()
    body_param.enable_tracking = True
    body_param.enable_body_fitting = False
    body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST 
    body_param.body_format = sl.BODY_FORMAT.BODY_18
    body_param.instance_module_id = 1
    zed.enable_body_tracking(body_param)

    camera_infos = zed.get_camera_information()
    viewer = gl.GLViewer()
    point_cloud_res = sl.Resolution(min(camera_infos.camera_configuration.resolution.width, 720), min(camera_infos.camera_configuration.resolution.height, 404)) 
    point_cloud_render = sl.Mat()
    viewer.init(camera_infos.camera_model, point_cloud_res, obj_param.enable_tracking)
    
    obj_runtime_param = sl.ObjectDetectionRuntimeParameters()
    detection_confidence = 60
    obj_runtime_param.detection_confidence_threshold = detection_confidence
    obj_runtime_param.object_class_filter = [sl.OBJECT_CLASS.PERSON]
    obj_runtime_param.object_class_detection_confidence_threshold = {sl.OBJECT_CLASS.PERSON: detection_confidence}

    runtime_params = sl.RuntimeParameters()
    runtime_params.confidence_threshold = 50

    point_cloud = sl.Mat(point_cloud_res.width, point_cloud_res.height, sl.MAT_TYPE.F32_C4, sl.MEM.CPU)
    objects = sl.Objects()

    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    body_runtime_param.detection_confidence_threshold = 40
    bodies = sl.Bodies()

    image_left = sl.Mat()
    image_right = sl.Mat()  # Added for right camera feed

    display_resolution = sl.Resolution(min(camera_infos.camera_configuration.resolution.width, 1280), min(camera_infos.camera_configuration.resolution.height, 720))
    image_scale = [display_resolution.width / camera_infos.camera_configuration.resolution.width
                 , display_resolution.height / camera_infos.camera_configuration.resolution.height]
    image_left_ocv = np.full((display_resolution.height, display_resolution.width, 4), [245, 239, 239,255], np.uint8)
    image_right_ocv = np.full((display_resolution.height, display_resolution.width, 4), [245, 239, 239,255], np.uint8)  # Added for right camera feed

    cam_w_pose = sl.Pose()
    cam_c_pose = sl.Pose()

    quit_app = False
    
    # Open the file for writing object positions
    with open("zed_data.txt", "a") as data_file:
        
        # Retrieve camera frame rate from the ZED configuration
        fps = camera_infos.camera_configuration.fps  # Use the ZED camera's frame rate
        
        # Set a lower frame rate for saving video to slow it down
        save_fps = 10  # Saving at 10 FPS for slower playback

        # Set up video writers for left and right images
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer_left = cv2.VideoWriter('raw_video_left.avi', fourcc, save_fps, (display_resolution.width, display_resolution.height))
        video_writer_right = cv2.VideoWriter('raw_video_right.avi', fourcc, save_fps, (display_resolution.width, display_resolution.height))

        while viewer.is_available() and not quit_app:
            start_time = time.time()  # Start time of frame capture

            if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Retrieve objects
                returned_state = zed.retrieve_objects(objects, obj_runtime_param, obj_param.instance_module_id)
                returned_state2 = zed.retrieve_bodies(bodies, body_runtime_param, body_param.instance_module_id)
                current_time = time.strftime("%Y %m %d %H %M %S")

                # Retrieve images
                zed.retrieve_image(image_left, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
                zed.retrieve_image(image_right, sl.VIEW.RIGHT, sl.MEM.CPU, display_resolution)  # Retrieve right image

                image_render_left = image_left.get_data()            
                image_render_right = image_right.get_data()  # Get right image data
                
                np.copyto(image_left_ocv, image_render_left)
                np.copyto(image_right_ocv, image_render_right)

                # Write frames to video files
                video_writer_left.write(cv2.cvtColor(image_left_ocv, cv2.COLOR_BGRA2BGR))
                video_writer_right.write(cv2.cvtColor(image_right_ocv, cv2.COLOR_BGRA2BGR))

                if returned_state == sl.ERROR_CODE.SUCCESS and objects.is_new:
                    # Retrieve point cloud
                    zed.retrieve_measure(point_cloud, sl.MEASURE.XYZRGBA, sl.MEM.CPU, point_cloud_res)
                    point_cloud.copy_to(point_cloud_render)
                    zed.get_position(cam_w_pose, sl.REFERENCE_FRAME.WORLD)

                    # Append detected object positions to file
                    for obj in objects.object_list:
                        position = obj.position  # 3D position of the object
                        data_file.write(f"{current_time}, Object ID: {obj.id}, Position: {position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f}\n")

                    # 3D rendering
                    viewer.updateData(point_cloud_render, objects)

                    # 2D rendering
                    cv_viewer.render_2D(image_left_ocv, image_scale, objects, obj_param.enable_tracking)

                if returned_state2 == sl.ERROR_CODE.SUCCESS and bodies.is_new:
                    cv_viewer.render_2D_SK(image_left_ocv, image_scale, bodies.body_list, obj_param.enable_tracking, sl.BODY_FORMAT.BODY_18)

                cv2.imshow("ZED | Body tracking and Object detection", image_left_ocv)
                cv2.waitKey(10)

            # Introduce additional delay to slow down frame processing further
            time.sleep(0.1)  # 100 ms delay to slow down the speed

            if is_playback and (zed.get_svo_position() == zed.get_svo_number_of_frames()-1):
                print("End of SVO")
                quit_app = True

        # Release video writers after processing
        video_writer_left.release()
        video_writer_right.release()

    cv2.destroyAllWindows()
    viewer.exit()
    image_left.free(sl.MEM.CPU)
    image_right.free(sl.MEM.CPU)  # Free right image memory
    point_cloud.free(sl.MEM.CPU)
    point_cloud_render.free(sl.MEM.CPU)

    zed.disable_object_detection()
    zed.disable_positional_tracking()

    zed.close()

