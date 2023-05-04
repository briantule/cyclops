from threading import Thread
import os, queue
import shutil
import cv2
import ffmpeg
import subprocess

import time
from print_handler import print_handler

import warnings
warnings.filterwarnings('ignore')

# Testing Lib
#from imutils.video import FPS

class Threaded_Video_Writing():
    def __init__(self, fps):
        self.powering_off = False

        # Temporary location where clips are stored -> Clear it
        self.temp_dir = '/home/capstone/Documents/temp/video/'
        self.clear_tmp()

        # Create video capture object
        self.capture = cv2.VideoCapture(-1, cv2.CAP_V4L2)
        (self.status, self.frame) = self.capture.read()

        # Set resolution
        self.frame_width = 640
        self.frame_height = 480
        # self.frame_width = 1280
        # self.frame_height = 720
        # self.frame_width = 1920
        # self.frame_height = 1080
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

        # Setting Capture Parameters
        self.video_ext = ".mp4"
        self.fps = fps
        self.capture.set(cv2.CAP_PROP_FPS, self.fps)
        self.codec = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # Exposure Settings
        # self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1) # Set exposure to manual mode
        # self.capture.set(cv2.CAP_PROP_EXPOSURE, self.fps) # exposure time = 1 / desired fps

        # Output Video Parameters
        self.output_num = 0
        self.output_video = cv2.VideoWriter(self.temp_dir + str(self.output_num) + self.video_ext, self.codec, self.fps, (self.frame_width, self.frame_height))

        # Start the thread to read frames from the video stream
        Thread(target=self.grab_frame, args=()).start()

    def clear_tmp(self):
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))

    def grab_frame(self):
        # retieve the next frame from the camera
        while self.powering_off == False:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()

    def write_frame(self):
        # Save obtained frame into video output file
        if self.status:
            self.output_video.write(self.frame)

    def refresh(self):
        self.output_video.release()
        self.output_num = (self.output_num+1)%2
        self.output_video = cv2.VideoWriter(self.temp_dir + str(self.output_num) + self.video_ext, self.codec, self.fps, (self.frame_width, self.frame_height))
    
    def log_video(self, directory):
        # release the current result video -> this allows it to be accessed
        self.output_video.release()
        output_directory = directory.get()
        output_file_name = '/video_' + time.strftime('%Y-%m-%d_%H-%M-%S') + self.video_ext
        # store videos names in txt file to be concatenated using ffmpeg demux
        f = open(self.temp_dir + "concat_list.txt", "w")
        num_files = 0
        self.output_num = (self.output_num+1)%2
        if os.path.isfile(self.temp_dir + str(self.output_num) + self.video_ext):
                f.write("file '" + self.temp_dir + str(self.output_num) + self.video_ext + "'\n")
                num_files += 1
        self.output_num = (self.output_num+1)%2
        if os.path.isfile(self.temp_dir + str(self.output_num) + self.video_ext):
                f.write("file '" + self.temp_dir + str(self.output_num) + self.video_ext + "'\n")
                num_files += 1
        f.close()
        try:
            if num_files > 1:
                # concatanate files & rename the output
                (
                    ffmpeg
                    .input(self.temp_dir + "concat_list.txt", format='concat', safe=0)
                    .output(output_directory + output_file_name, loglevel="quiet", c='copy')
                    .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                )
            else:
                shutil.move(self.temp_dir + str(self.output_num) + self.video_ext, output_directory + output_file_name)
        except Exception as e:
            print(e)
            print_handler("Thread - Camera", "An error occured while concatenating or saving the output video at: " + output_directory + output_file_name)
        else:
            print_handler("Thread - Camera", "Saved last 60 seconds of data to: " + output_directory + output_file_name)
        
        # Clean Up
        self.clear_tmp() # clear the tmp dir so old clips are not re-used 
        self.output_num = 0
        self.output_video = cv2.VideoWriter(self.temp_dir + str(self.output_num) + self.video_ext, self.codec, self.fps, (self.frame_width, self.frame_height))

    def close(self):
        self.powering_off = True
        time.sleep(.1) # if getting segmentation fault -> increase wait time
        self.capture.release()
        self.output_video.release()
        cv2.destroyAllWindows()
        self.clear_tmp()