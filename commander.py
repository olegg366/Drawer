import cv2

import pyautogui as pg
from time import time
from multiprocessing import Process, Queue

from utilites import map_coords

from gesture_recognizer import GestureRecognizer
from interface import App, canvas_h, canvas_w
from listener import Listener


pg.FAILSAFE = False


class Commander:
    def __init__(self, frames_queue: Queue, commands_queue: Queue):
        self.frames_queue = frames_queue
        self.commands_queue = commands_queue
        
        self.flag_drawing = False
        self.flag_end = False
        self.flag_drawing_line = False
        self.last_showed_end_time = -1
        self.gestures_in_row = {
            'clean': 0,
            'end': 0,
            'drag': 0
        }
        
    def draw(self, gestures: list, x: int, y: int):
        delta = 50
        x = 640 - x
        
        xm = map_coords(x, 0, 1920, -delta / 2, 1920 + delta / 2)
        ym = map_coords(y, 0, 1080, -delta / 2, 1080 + delta / 2)
        
        xc = map_coords(x, 0, 1920, -100, canvas_w + 200)
        yc = map_coords(x, 0, 1080, -100, canvas_h + 200)
        if 'Click' in gestures and self.flag_drawing:   
            if not self.flag_drawing_line:         
                self.flag_drawing_line = True
                self.commands_queue.put(('set_start', [(xc, yc)]))
                pg.moveTo(xm, ym, 0.0, _pause=False)
                pg.click()
            else: 
                self.commands_queue.put(('draw_line', [(xc, yc)]))
        elif 'Pointing_Up' in gestures or ('Click' in gestures and not self.flag_drawing):
            self.commands_queue.put(('end_line', None))
            self.flag_drawing_line = False
            pg.moveTo(xm, ym, 0.0, _pause=False)
        elif self.flag_drawing and gestures.count('Open_Palm') == 2:
            self.flag_drawing_line = False
            self.commands_queue.put(('delete', None))
        else:
            self.flag_drawing_line = False
            if 'Thumb_Up' in gestures and time() - self.last_showed_end_time > 5: 
                if not self.flag_drawing:
                    self.flag_drawing = True
                    self.last_showed_end_time = time()
                    self.commands_queue.put(('remove_instructions', None))
                    self.commands_queue.put(('remove_img', None))
                    self.commands_queue.put(('change_status', None))
                else:
                    self.flag_end = True
                    self.last_showed_end_time = time()
                    self.flag_drawing = False
                    self.commands_queue.put(('chamge_status', None))
        
    def loop(self):
        while True:
            if self.frames_queue.empty():
                continue
            
            recognition_results = self.frames_queue.get()
            
            if recognition_results.landmarks is None:
                continue
            
            fx, fy = recognition_results.landmarks[0, 8, :2]
            fx *= recognition_results.image.shape[1]
            fy *= recognition_results.image.shape[0]
            self.draw(recognition_results.gestures, fx, fy)
            
            if self.flag_end:
                text_ru, text_en = self.listener.listen()
                print(text_ru, text_en)
                self.flag_end = False
                self.commands_queue.put(('chamge_status', None))
            
        
    def start(self):
        thread = Process(target=self.loop, daemon=True)
        thread.start()
        
if __name__ == '__main__':
    frames_queue = Queue(-1)
    commands_queue = Queue(-1)
    
    gesture_recognizer = GestureRecognizer(frames_queue)
    app = App()
    com = Commander(frames_queue, commands_queue)
    
    gesture_recognizer.start_loop()
    com.start()
    app.mainloop(frames_queue, commands_queue)
        