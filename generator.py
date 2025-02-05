import requests
import numpy as np
import base64
import io
from multiprocessing import Process, Queue

class Generator:
    def __init__(self, url: str, queue: Queue):
        self.url = url
        self.queue = queue
    
    def generate(self, image: np.ndarray, prompt: str, negative_prompt: str = ''):
        buffer = io.BytesIO()
        np.save(buffer, image)
        buffer.seek(0)

        array_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        response = requests.post(
            self.url,
            json={
                'image': array_base64,
                'prompt': prompt,
                'negative_prompt': negative_prompt
            }
        )
        data = response.json()
        array_data = base64.b64decode(data['generated'])
                
        image = np.load(io.BytesIO(array_data), allow_pickle=True)
        
        self.queue.put(image)
    
    def start_generation(self, image: np.ndarray, prompt: str, negative_prompt: str = ''):
        process = Process(target=self.generate, args=(image, prompt, negative_prompt))
        process.start()
        