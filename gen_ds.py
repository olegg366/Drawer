import mediapipe as mp
from utilities import draw_landmarks_on_image, get_landmarks
import numpy as np
import cv2
import matplotlib.pyplot as plt

# Инициализация захвата видео с камеры (индекс 2)
video_capture = cv2.VideoCapture(0)

# Путь к модели для детекции руки
model_path = 'mlmodels/hand_landmarker.task'

# Классы и опции Mediapipe для детекции руки
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Настройка опций для детекции руки
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path, delegate=BaseOptions.Delegate.CPU),
    running_mode=VisionRunningMode.IMAGE
)

# Инициализация списков для хранения результатов и расстояний
results = []
distances = []
max_length = 25

try:
    # Создание детектора руки на основе опций
    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            # Чтение кадра из видеозахвата
            ret, frame = video_capture.read()
            print(frame.shape)
            if not ret:
                print('Конец видеопотока')
                break

            # Преобразование кадра в формат RGB для Mediapipe
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Детекция руки на кадре
            detection_result = landmarker.detect(mp_image)

            # Отрисовка меток на кадре
            frame_with_landmarks = draw_landmarks_on_image(frame, detection_result)
            cv2.imshow('Метки руки', frame_with_landmarks)

            # Если метки руки обнаружены, вычисляем отношение расстояний
            if detection_result.hand_landmarks:
                landmarks = get_landmarks(detection_result)[0]
                landmarks[:, 0] *= frame.shape[1]
                landmarks[:, 1] *= frame.shape[0]
                
                results.append(landmarks)

            # Ожидание нажатия клавиши (1 мс) и проверка нажатия клавиши 'q' для выхода
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
except KeyboardInterrupt:
    pass

# Освобождение видеозахвата
video_capture.release()

filename = input('Enter filename: ')
np.save(filename, results)