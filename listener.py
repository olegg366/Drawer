from interface import App

import speech_recognition as sr
from googletrans import Translator

class Listener:
    def __init__(self, app: App):
        self.flag_recognition = False
        self.recognizer = sr.Recognizer()
        self.translator = Translator()
        
        self.app = app
        
    def listen(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.app.print_text('Говорите...')
            audio = self.recognizer.listen(source, phrase_time_limit=5)
        text = self.recognizer.recognize_google(audio, language='ru-RU')
        text_en = self.translator.translate(text, src='ru', dest='en').text
        return text, text_en