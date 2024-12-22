import cv2
import numpy as np
from queue import Queue

from utilites import dist

from keras.models import load_model

import mediapipe as mp
from threading import Thread

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions  
VisionRunningMode = mp.tasks.vision.RunningMode

classes_mapper = {
    0 : 'Open_Palm',
    1 : 'Pointing_Up',
    2 : 'Thumb_Up'
}

class RecognitionResult:
    def __init__(
        self,
        image: np.ndarray,
        gestures: list[str],
        landmarks: np.ndarray,
        detection
    ):
        self.image = image
        self.gestures = gestures
        self.landmarks = landmarks
        self.detection = detection
        

class GestureRecognizer:
    def __init__(
        self, 
        video: cv2.VideoCapture, 
        queue: Queue,
        landmarker_path: str = 'mlmodels/hand_landmarker.task', 
        recognizer_path: str = "mlmodels/static.h5",
        running_mode: str = "VIDEO"
    ):
        self.video = video
        self.queue = queue
        
        if running_mode == "VIDEO":
            running_mode = VisionRunningMode.VIDEO
        else:
            running_mode = VisionRunningMode.IMAGE

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=landmarker_path),
            num_hands=2,
            running_mode=running_mode
        )
        
        self.landmarker = HandLandmarker.create_from_options(options)
        self.recognizer = load_model(recognizer_path)
        
    def start_loop(self):
        thread = Thread(target=self.loop, daemon=True)
        thread.start()
        
    def get_landmarks(self, detection_result):
        hand_landmarks_list = detection_result.hand_landmarks
        res = []

        for idx in range(len(hand_landmarks_list)):
            hand_landmarks = hand_landmarks_list[idx]
            res.append([[l.x, l.y, l.z] for l in hand_landmarks])
        return np.array(res, dtype='float32')
    
    def is_click(self, landmarks):
        return dist(landmarks[0, 4], landmarks[0, 8]) / dist(landmarks[0, 0], landmarks[0, 8]) <= 0.2
        
    def loop(self):
        timestamp = 0
        while True:
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
                    recognitions = self.recognizer.predict(landmarks[:, :, :2], verbose=False)
                    gestures = [
                        classes_mapper[recognition]
                        for recognition in np.argmax(recognitions, axis=-1)
                    ]
                
                self.queue.put(RecognitionResult(
                    img,
                    gestures,
                    landmarks,
                    detection
                ))
            else:
                self.queue.put(RecognitionResult(
                    img,
                    None, 
                    None,
                    detection
                ))
            