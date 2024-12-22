import mediapipe as mp
from utilites import draw_landmarks_on_image, dist, map_coords
import numpy as np
import cv2
import pyautogui as pg
from keras.models import load_model

pg.FAILSAFE = False

def get_landmarks(detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    res = []

    # Loop through the detected hands to visualize.
    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        res.append([[l.x, l.y, l.z] for l in hand_landmarks])
    return np.array(res)

vid = cv2.VideoCapture(0)

model = load_model('mlmodels/static.h5')

model_path = 'mlmodels/hand_landmarker.task'
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Create a hand landmarker instance with the image mode:
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.IMAGE)

classes = {
    0 : 'Open_Palm',
    1 : 'Pointing_Up',
    2 : 'Thumb_Up'
}

flag_drawing = False

with HandLandmarker.create_from_options(options) as landmarker:
    while True:
        res, img = vid.read()

        if not res: print(0)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        detection = landmarker.detect(mp_image)

        if detection.hand_landmarks:
            lmks = get_landmarks(detection)
            if dist(lmks[0, 4], lmks[0, 8]) / dist(lmks[0, 0], lmks[0, 8]) <= 0.2:
                gt = 'Click'
            else:
                pred = model(lmks[:, :, :2])
                print(classes[np.argmax(pred)])
                gt = classes[np.argmax(pred)]
            x, y = lmks[0, 8][:2]
            x = 640 - x * 640
            y *= 480
            print(x, y)
            x = map_coords(x, 0, 640, 0, 1920)
            y = map_coords(y, 0, 480, 0, 1080)
            if gt == 'Click':
                if flag_drawing:
                    pg.dragTo(x, y, 0.0, _pause=False)
                else:
                    pg.moveTo(x, y, 0.0, _pause=False)
                    pg.click()
                    flag_drawing = True
            elif gt == 'Pointing_Up':
                pg.moveTo(x, y, 0.0, _pause=False)
                flag_drawing = False            
 
        img = draw_landmarks_on_image(img, detection)
        cv2.imshow('img', img)

        cv2.waitKey(1)

vid.release()
