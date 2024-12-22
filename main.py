import cv2
import pyautogui as pg
import numpy as np

import mediapipe as mp
from keras.models import load_model

from PIL import Image
from skimage.transform import resize

from utilites import draw_landmarks_on_image, draw, get_landmarks, dist
from interface import App

from google_speech import recognize

from time import sleep

pg.FAILSAFE = False

print('Setting up widget...')
app = App()
print('Successfully set up widget.')

if __name__ == '__main__':
    #камера
    vid = cv2.VideoCapture(0)

    #модель распознавания жестов
    print('Loading gesture recognizer...')
    model = load_model('mlmodels/static.h5')
    print('Succesfully loaded gesture recognizer.')

    #разметка руки
    print('Setting up hand landmarker...')
    model_path = 'mlmodels/hand_landmarker.task'
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        num_hands=2,
        running_mode=VisionRunningMode.VIDEO)
    print('Succesfully set up hand landmarker.')

    #время последних жестов
    t = {
        'paint' : -1,
        'clean' : -1,
        'start' : -1
    }

    #классы жестов
    classes = {
        0 : 'Open_Palm',
        1 : 'Pointing_Up',
        2 : 'Thumb_Up'
    }
    
    # счетчик жестов подряд
    cnt = {
        'clean': 0,
        'end': 0,
        'drag': 0
    }
    
    last_cords = []

    #индикатор того, рисуем мы или нет 
    flag = False
    end = False
    flag_checking = False
    timestamp = 0
    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            res, img = vid.read()

            if not res: 
                print(0)
                continue
            
            detection = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), timestamp)
            if detection.hand_landmarks:
                lmks = get_landmarks(detection)
                x, y = lmks[0, 8, :2]
                x *= img.shape[1]
                y *= img.shape[0]
                last_cords.append([x, y])
                if len(last_cords) > 20:
                    last_cords.pop(0)
                if len(last_cords) < 6:
                    timestamp += 1
                    continue
                if dist(lmks[0, 4], lmks[0, 8]) / dist(lmks[0, 0], lmks[0, 8]) <= 0.2:
                    gts = ['Click']
                else:
                    pred = model.predict(lmks[:, :, :2])
                    gts = [classes[x] for x in np.argmax(pred, axis=-1)]
                if flag_checking:
                    _, t, cnt, __ = draw(gts, t, cnt, True, last_cords, end, app)
                    if not app.flag_answer:
                        img = draw_landmarks_on_image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), detection)
                        app.update((resize(img, (img.shape[0] // 2, img.shape[1] // 2)) * 255).astype('uint8'))
                        cv2.waitKey(1)
                        timestamp += 1
                        continue
                    else:
                        flag_checking = False
                else:
                    flagn, t, cnt, end = draw(gts, t, cnt, flag, last_cords, end, app)
                if flagn != flag and not end:
                    app.change_status()
                flag = flagn
                if end or app.flag_generate:
                    if not app.flag_answer:
                        scribble = app.image
                        scribble.save('images/scribble.png')
                        prompt = ''
                        while not prompt:
                            try:
                                prompt, rus = recognize(app)
                            except ValueError:
                                app.print_text("Распознавание не удалось. Попробуйте ещё раз.")
                                sleep(3)
                                
                        app.print_text('Вы сказали: ' + rus + '?')
                        app.check_recognition()
                        flag_checking = 1
                        app.update()
                    else:
                        app.flag_answer = 0
                        flag_checking = 0
                        
                        if not app.flag_recognition:
                            timestamp += 1
                            app.update()
                            continue
                        app.print_text('Генерация по запросу: ' + rus)
                        app.change_status()
                        app.setup_progressbar()
                        
                        # здесь будет генерация 
                        # ...
                        
                        app.flag_generate = 0
                        
                        app.print_text('')
                        app.delete()
                        app.fr_progressbar.pack_forget()
                        
                        gen = Image.open('images/good_morning.png')
                        
                        app.display(gen)
                        
                        app.change_status()                   
                        
                        sleep(10)
                        
                        flag = False
                        flagn = False
                        end = False
                        app.flag_answer = 0
                        
                        cnt = {
                            'clean': 0,
                            'end': 0,
                            'drag': 0
                        }
                        t = {
                            'paint' : 0,
                            'clean' : 0,
                            'start' : 0
                        }
            img = draw_landmarks_on_image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), detection)
            app.update((resize(img, (img.shape[0] // 2, img.shape[1] // 2)) * 255).astype('uint8'))
            cv2.waitKey(1)
            timestamp += 1

    vid.release()
