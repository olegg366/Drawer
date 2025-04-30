import cv2
import numpy as np
from time import sleep

from utilites import dist, draw_landmarks_on_image

from keras.models import load_model

import mediapipe as mp
from multiprocessing import Process, Queue

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions  
VisionRunningMode = mp.tasks.vision.RunningMode

classes_mapper = {
    0 : 'Open_Palm',
    1 : 'Pointing_Up',
    2 : 'Thumb_Up',
    3 : 'Thumb_Down'
}

class RecognitionResult:
    def __init__(
        self,
        shape: tuple[int],
        gestures: list[str],
        landmarks: np.ndarray
    ):
        self.shape = shape
        self.gestures = gestures
        self.landmarks = landmarks
        

class GestureRecognizer:
    def __init__(
        self,
        frames_queue: Queue,
        recognitions_queue: Queue,
        landmarker_path: str = 'src/mlmodels/hand_landmarker.task', 
        recognizer_path: str = "src/mlmodels/static.keras",
        running_mode: str = "VIDEO"
    ):
        self.frames_queue = frames_queue
        self.recognitions_queue = recognitions_queue
        
        self.running_mode = running_mode
        
        self.recognizer_path = recognizer_path
        self.landmarker_path = landmarker_path
        
    def start_loop(self):
        self.terminate_flag = False
        self.process = Process(target=self.loop, daemon=True)
        self.process.start()
    
    def join(self):
        self.process.join()
    
    def terminate(self):
        self.terminate_flag = True
        if self.process.is_alive():
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join()
        
    def get_landmarks(self, detection_result):
        hand_landmarks_list = detection_result.hand_landmarks
        res = []

        for idx in range(len(hand_landmarks_list)):
            hand_landmarks = hand_landmarks_list[idx]
            res.append([[l.x, l.y, l.z] for l in hand_landmarks])
        return np.array(res, dtype='float32')
    
    def is_click(self, landmarks):
        for i in range(len(landmarks)):
            is_clisk = dist(landmarks[i, 4], landmarks[i, 8]) / dist(landmarks[i, 0], landmarks[i, 8]) <= 0.2
            if is_clisk:
                return True
        return False
        
    def loop(self):
        self.video = cv2.VideoCapture(0)
        timestamp = 0
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.landmarker_path),
            num_hands=2,
            running_mode=getattr(VisionRunningMode, self.running_mode)
        )
        
        self.landmarker = HandLandmarker.create_from_options(options)
        self.recognizer = load_model(self.recognizer_path)
        while not self.terminate_flag:
            flag, img = self.video.read()
            
            if not flag:
                print("Can't read image")
                continue
            
            timestamp += 1
            
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            mediapipe_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
            detection = self.landmarker.detect_for_video(mediapipe_image, timestamp)
            
            if detection.hand_landmarks:
                landmarks = self.get_landmarks(detection)      
                if self.is_click(landmarks):
                    gestures = ['Click']                  
                else:
                    recognitions = self.recognizer.predict(landmarks, verbose=False)
                    gestures = [
                        classes_mapper[recognition]
                        for recognition in np.argmax(recognitions, axis=-1)
                    ]
                
                self.recognitions_queue.put(RecognitionResult(
                    img.shape,
                    gestures,
                    landmarks
                ))
                self.frames_queue.put(draw_landmarks_on_image(img, detection))
            else:
                sleep(0.02)
                self.recognitions_queue.put(RecognitionResult(
                    img.shape,
                    None, 
                    None
                ))
                self.frames_queue.put(img)
            