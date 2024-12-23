import cv2
import numpy as np

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
    2 : 'Thumb_Up'
}

class RecognitionResult:
    def __init__(
        self,
        image: np.ndarray,
        gestures: list[str],
        landmarks: np.ndarray
    ):
        self.image = image
        self.gestures = gestures
        self.landmarks = landmarks
        

class GestureRecognizer:
    def __init__(
        self,
        queue: Queue,
        landmarker_path: str = 'mlmodels/hand_landmarker.task', 
        recognizer_path: str = "mlmodels/static.h5",
        running_mode: str = "VIDEO"
    ):
        self.queue = queue
        
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
        return dist(landmarks[0, 4], landmarks[0, 8]) / dist(landmarks[0, 0], landmarks[0, 8]) <= 0.2
        
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
                    recognitions = self.recognizer.predict(landmarks[:, :, :2], verbose=False)
                    gestures = [
                        classes_mapper[recognition]
                        for recognition in np.argmax(recognitions, axis=-1)
                    ]
                
                self.queue.put(RecognitionResult(
                    draw_landmarks_on_image(img, detection),
                    gestures,
                    landmarks
                ))
            else:
                self.queue.put(RecognitionResult(
                    img,
                    None, 
                    None
                ))
            