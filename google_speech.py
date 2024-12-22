import speech_recognition as sr
from googletrans import Translator
    
def recognize(app):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Say something!")
        app.print_text('Говорите...')
        app.update()
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=5)
    try:
        print('listened, recognizing')
        app.print_text("Аудио распознается...")
        text = r.recognize_google(audio, language='ru-RU')
        print('recognized, translating...')
        if not text:
            return ''
        translator = Translator()
        text_en = translator.translate(text, src='ru', dest='en').text
        return text_en, text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return ''
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return ''