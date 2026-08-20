from flask import Flask, jsonify, request
import torch
import tomesd
from DeepCache import DeepCacheSDHelper
from diffusers import StableDiffusionControlNetPipeline, UniPCMultistepScheduler, ControlNetModel
from skimage.util import invert
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

controlnet = ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-scribble", 
                                             torch_dtype=torch.float32)
pipe = StableDiffusionControlNetPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", 
                                                        controlnet=controlnet,
                                                        safety_checker=None, 
                                                        use_safetensors=True,
                                                        torch_dtype=torch.float32).to('cuda')
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)

helper = DeepCacheSDHelper(pipe=pipe)
helper.set_params(
    cache_interval=5,
    cache_branch_id=0,
)
helper.enable()


tomesd.apply_patch(pipe, ratio=0.5)
pipe.enable_xformers_memory_efficient_attention()

pipe.unet.to(memory_format=torch.channels_last)
pipe.vae.to(memory_format=torch.channels_last)

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/generator', methods=['POST'])
def generate():
    data = request.json
    if 'prompt' not in data.keys():
        return jsonify({'Error': 'Please provide prompt for the model'}), 400
    if 'image' not in data.keys():
        return jsonify({'Error': 'Please provide base image for the model'}), 400
    
    if 'negative_prompt' in data.keys():
        negative_prompt = data['negative_prompt']
    else:
        negative_prompt = ''
        
    prompt = data['prompt']
    array_data = base64.b64decode(data['image'])
    image = np.load(io.BytesIO(array_data), allow_pickle=True)
    
    img = invert(image)[..., :3]
    img[img != 255] = 0
    img[img == 255] = 1
    
    with torch.inference_mode():
        gen = pipe(prompt, [img.astype('float')], num_inference_steps=50, height=512, width=512, negative_prompt=negative_prompt, num_images_per_prompt=3, output_type='np').images
    gen = np.stack(gen)

    buffer = io.BytesIO()
    np.save(buffer, gen)
    buffer.seek(0)
    array_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return jsonify({'generated': array_base64}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)