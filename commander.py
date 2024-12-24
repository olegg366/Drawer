import sys
import signal
import pyautogui as pg
from time import time, sleep
from multiprocessing import Process, Queue, Value

from utilites import map_coords

from gesture_recognizer import GestureRecognizer
from interface import App

import speech_recognition as sr
from googletrans import Translator


pg.FAILSAFE = False


class Commander:
    def __init__(
        self, 
        frames_queue: Queue, 
        commands_queue: Queue, 
        canvas_w, canvas_h, 
        shiftx, shifty,
        flag_recognition, flag_recognition_result
    ):
        self.frames_queue = frames_queue
        self.commands_queue = commands_queue
        
        self.flag_recognition = flag_recognition
        self.flag_recognition_result = flag_recognition_result
        
        self.flag_drawing = False
        self.flag_end = False
        self.flag_drawing_line = False
        self.last_showed_end_time = -1
        self.gestures_in_row = {
            'clean': 0,
            'end': 0,
            'drag': 0
        }
        
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        
        self.shiftx = shiftx
        self.shifty = shifty
        
    def listen(self):
        recognizer = sr.Recognizer()
        translator = Translator()
        while not self.flag_recognition_result.value:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                self.commands_queue.put(('print_text', ('Говорите...', )))
                audio = recognizer.listen(source, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language='ru-RU')
            text_en = translator.translate(text, src='ru', dest='en').text
            self.commands_queue.put(('print_text', (f'Вы сказали: {text}?', )))
            self.commands_queue.put(('check_recognition', None))
            while not self.flag_recognition.value:
                sleep(1)
                continue
        return text, text_en
        
    def draw(self, gestures: list, x: int, y: int, image_size: tuple):
        delta = 50
        w, h = pg.size()
        imgw, imgh = image_size
        x = imgh - x
        
        xm = map_coords(x, 0, imgh, 0, w + delta / 2)
        ym = map_coords(y, 0, imgw, 0, h + delta / 2)
        
        xc = map_coords(x, 0, imgh, -self.shiftx.value, self.canvas_w.value)
        yc = map_coords(y, 0, imgw, -self.shifty.value, self.canvas_h.value)
        if 'Click' in gestures and self.flag_drawing: 
            pg.moveTo(xm, ym, 0.0, _pause=False)  
            if not self.flag_drawing_line:         
                self.flag_drawing_line = True
                self.commands_queue.put(('set_start', [(xc, yc)]))
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
                    self.commands_queue.put(('change_status', None))
        
    def loop(self):
        while not self.terminate_flag:
            if self.frames_queue.empty():
                continue
            
            recognition_results = self.frames_queue.get()
            
            if recognition_results.landmarks is None:
                continue
            
            fx, fy = recognition_results.landmarks[0, 8, :2]
            fx *= recognition_results.image.shape[1]
            fy *= recognition_results.image.shape[0]
            self.draw(recognition_results.gestures, fx, fy, recognition_results.image.shape[:2])
            
            if self.flag_end:
                text_ru, text_en = self.listen()
                print(text_ru, text_en)
                self.flag_end = False
                
    
    def terminate(self):
        self.terminate_flag = True
        if self.process.is_alive():
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join()
        
    def start(self):
        self.terminate_flag = False
        self.process = Process(target=self.loop, daemon=True)
        self.process.start()
        
    def join(self):
        self.process.join()
        
if __name__ == '__main__':
    canvas_w = Value('i', 0)
    canvas_h = Value('i', 0)
    
    shiftx = Value('i', 0)
    shifty = Value('i', 0)
    
    flag_recognition = Value('i', 0)
    flag_recognition_result = Value('i', 0)
    
    frames_queue = Queue(-1)
    commands_queue = Queue(-1)
    
    gesture_recognizer = GestureRecognizer(frames_queue)
    app = App()
    com = Commander(frames_queue, commands_queue, canvas_w, canvas_h, shiftx, shifty, flag_recognition, flag_recognition_result)

    
    gesture_recognizer.start_loop()
    com.start()
    
    def cleanup(signum, frame):
        print("Cleaning up resources...")
        com.terminate()
        app.running = False
        gesture_recognizer.terminate()
        frames_queue.close()
        commands_queue.close()
        frames_queue.join_thread()
        commands_queue.join_thread()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        app.mainloop(frames_queue, commands_queue, canvas_w, canvas_h, shiftx, shifty, flag_recognition, flag_recognition_result)
    except KeyboardInterrupt:
        cleanup(None, None)
    gesture_recognizer.join()
    com.join()
        