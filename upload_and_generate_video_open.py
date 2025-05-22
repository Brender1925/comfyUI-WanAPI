import os
import requests
import tempfile
from pathlib import Path
from http import HTTPStatus
from dashscope import VideoSynthesis

import numpy as np
import torch
import cv2
from PIL import Image
from fractions import Fraction

from comfy_api.input_impl import VideoFromComponents
from comfy_api.util import VideoComponents

class UploadAndGenerateVideo:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model_name": (["wanx2.1-i2v-turbo", "wanx2.1-i2v-plus"],),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "请输入提示词"
                }),
                "resolution": (["480P", "720P"],),
                "duration": ("INT", {
                    "default": 5,
                    "min": 3,
                    "max": 5,
                    "step": 1
                }),
                "prompt_extend": (["true", "false"],),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 2147483647,
                    "step": 1
                }),
            }
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video_file",)
    FUNCTION = "upload_and_generate"

    CATEGORY = "通义API"

    def save_image_temp(self, image_data):
        if hasattr(image_data, "cpu"):
            image_data = image_data.cpu().numpy()
        image = image_data.squeeze()
        if image.ndim == 3 and image.shape[0] in [1, 3]:
            image = np.transpose(image, (1, 2, 0))
        if image.ndim == 2:
            image = np.stack([image] * 3, axis=-1)
        image = (image * 255).clip(0, 255).astype(np.uint8)
        image_pil = Image.fromarray(image)
        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        image_pil.save(temp_file.name, format='JPEG')
        return temp_file.name

    def get_upload_policy(self, api_key, model_name):
        url = "https://dashscope.aliyuncs.com/api/v1/uploads"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        params = {"action": "getPolicy", "model": model_name}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"获取上传策略失败: {response.text}")
        return response.json()['data']

    def upload_file_to_oss(self, policy_data, file_path):
        file_name = Path(file_path).name
        key = f"{policy_data['upload_dir']}/{file_name}"
        with open(file_path, 'rb') as file:
            files = {
                'OSSAccessKeyId': (None, policy_data['oss_access_key_id']),
                'Signature': (None, policy_data['signature']),
                'policy': (None, policy_data['policy']),
                'x-oss-object-acl': (None, policy_data['x_oss_object_acl']),
                'x-oss-forbid-overwrite': (None, policy_data['x_oss_forbid_overwrite']),
                'key': (None, key),
                'success_action_status': (None, '200'),
                'file': (file_name, file)
            }
            response = requests.post(policy_data['upload_host'], files=files)
            if response.status_code != 200:
                raise Exception(f"上传文件失败: {response.text}")
        return f"oss://{key}"

    def generate(self, img_url, prompt, model_name, resolution, duration, prompt_extend, seed):
        parameters = {
            'resolution': resolution,
            'duration': duration,
            'prompt_extend': prompt_extend == "true"
        }
        if seed > 0:
            parameters['seed'] = seed

        response = VideoSynthesis.call(
            model=model_name,
            prompt=prompt,
            img_url=img_url,
            parameters=parameters,
            headers={'X-DashScope-OssResourceResolve': 'enable'}
        )

        if response.status_code == HTTPStatus.OK:
            return response.output.video_url
        else:
            raise Exception(f"视频生成失败: {response.status_code} - {response.message}")

    def download_video(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            with open(temp_file.name, 'wb') as f:
                f.write(response.content)
            return temp_file.name
        else:
            raise Exception("下载视频失败")

    def upload_and_generate(self, image, model_name, prompt, resolution, duration, prompt_extend, seed):
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise Exception("环境变量 DASHSCOPE_API_KEY 未设置。")

        temp_image_path = self.save_image_temp(image)
        policy = self.get_upload_policy(api_key, model_name)
        img_url = self.upload_file_to_oss(policy, temp_image_path)
        video_url = self.generate(img_url, prompt, model_name, resolution, duration, prompt_extend, seed)
        video_path = self.download_video(video_url)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开生成的视频文件。")
        frames = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = 8.0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = torch.from_numpy(frame_rgb).unsqueeze(0)
            frames.append(tensor)
        cap.release()

        if not frames:
            raise Exception("未读取到视频帧。")

        stacked = torch.cat(frames, dim=0)
        video_obj = VideoFromComponents(VideoComponents(images=stacked, frame_rate=Fraction(round(fps))))
        return (video_obj,)


NODE_CLASS_MAPPINGS = {
    "UploadAndGenerateVideo": UploadAndGenerateVideo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UploadAndGenerateVideo": "上传并生成视频"
}
