import requests
import numpy as np
import base64
import io
from imageio import imread
import matplotlib.pyplot as plt

# Создаем массив NumPy
image = imread('images/scribble.png')

# Сериализуем массив в байты
buffer = io.BytesIO()
np.save(buffer, image)
buffer.seek(0)

# Кодируем байты в base64
array_base64 = base64.b64encode(buffer.read()).decode('utf-8')

# Отправляем массив на сервер
response = requests.post(
    'https://qtf4vqzx-5000.euw.devtunnels.ms/generator',
    json={
        'image': array_base64,
        'prompt': 'pineapple'
    }
)
print(response)
data = response.json()
array_data = base64.b64decode(data['generated'])
        
image = np.load(io.BytesIO(array_data), allow_pickle=True)

plt.imshow(image)
plt.show()