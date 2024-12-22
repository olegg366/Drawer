import cv2

import pyautogui as pg
from queue import Queue
from time import time
from threading import Thread

from utilites import map_coords, draw_landmarks_on_image

from gesture_recognizer import GestureRecognizer
from interface import App
from listener import Listener


pg.FAILSAFE = False


class Commander:
    def __init__(self, app: App, recognizer: GestureRecognizer, frames_queue: Queue):
        self.app = app
        self.frames_queue = frames_queue
        self.gesture_recognizer = recognizer
        
        self.flag_drawing = False
        self.flag_end = False
        self.last_showed_end_time = -1
        self.gestures_in_row = {
            'clean': 0,
            'end': 0,
            'drag': 0
        }
        
        self.listener = Listener(self.app)
        
    def draw(self, gestures: list, x: int, y: int):
        delta = 300
        x = 640 - x
        
        xm = map_coords(x, 0, 640, -delta / 2, 1920 + delta / 2)
        ym = map_coords(y, 0, 480, -delta / 2, 1080 + delta / 2)
        
        xc = map_coords(x, 0, 640, self.app.left_corner_x, self.app.left_corner_x + self.app.canvas_w)
        yc = map_coords(y, 0, 480, self.app.left_corner_y, self.app.left_corner_y + self.app.canvas_h)
        print(self.app.left_corner_x, self.app.left_corner_y, self.app.canvas_w, self.app.canvas_h)
        if 'Click' in gestures and self.flag_drawing:   
            if self.app.line_id is None:         
                self.app.set_start((xc, yc))
                pg.moveTo(xm, ym, 0.0, _pause=False)
                print('moved')
                pg.click()
            else: 
                self.app.draw_line((xc, yc))
        elif 'Pointing_Up' in gestures or ('Click' in gestures and not self.flag_drawing):
            self.app.end_line()
            pg.moveTo(xm, ym, 0.0, _pause=False)
            print('moved')
        elif self.flag_drawing and gestures.count('Open_Palm') == 2:
            self.app.delete()
        else:
            if 'Thumb_Up' in gestures and time() - self.last_showed_end_time > 5: 
                if not self.flag_drawing:
                    self.flag_drawing = True
                    self.last_showed_end_time = time()
                    self.app.remove_instructions()
                    self.app.remove_img()
                    self.app.now_clr = "green"
                else:
                    self.flag_end = True
                    self.last_showed_end_time = time()
                    self.flag_drawing = False
                    self.app.now_clr = "yellow"
        
    def loop(self):
        while True:
            if self.frames_queue.empty():
                continue
            
            recognition_results = self.frames_queue.get()
            
            app.camera_image = draw_landmarks_on_image(recognition_results.image, recognition_results.detection)
            
            if recognition_results.landmarks is None:
                continue
            
            # fx, fy = recognition_results.landmarks[0, 8, :2]
            # fx *= recognition_results.image.shape[1]
            # fy *= recognition_results.image.shape[0]
            # self.draw(recognition_results.gestures, fx, fy)
            
            # if self.flag_end:
            #     text_ru, text_en = self.listener.listen()
            #     print(text_ru, text_en)
            #     self.flag_end = False
            #     self.app.now_clr = "red"
            
        
    def start(self):
        self.gesture_recognizer.start_loop()
        thread = Thread(target=self.loop, daemon=True)
        thread.start()
        
if __name__ == '__main__':
    frames_queue = Queue()
    
    video = cv2.VideoCapture(0)
    
    gesture_recognizer = GestureRecognizer(video, frames_queue)
    app = App()
    com = Commander(app, gesture_recognizer, frames_queue)
    
    gesture_recognizer.start_loop()
    com.start()
    app.mainloop()
        