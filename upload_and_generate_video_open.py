import os
import requests
import tempfile
import time
from pathlib import Path
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope  # 导入dashscope模块以便直接设置api_key

import numpy as np
import torch
import cv2
from PIL import Image
from fractions import Fraction

from comfy_api.input_impl import VideoFromComponents
from comfy_api.util import VideoComponents

class UploadAndGenerateVideo:
    def __init__(self):
        self.total_start_time = None  # 记录总开始时间
        self.step_start_time = None   # 记录步骤开始时间

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "输入DASHSCOPE_API_KEY或使用环境变量"
                }),
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

    def _start_timer(self):
        """开始计时"""
        self.step_start_time = time.time()

    def _end_timer(self):
        """结束计时并返回耗时(秒)"""
        if self.step_start_time is None:
            return 0.0
        return round(time.time() - self.step_start_time, 2)

    def save_image_temp(self, image_data):
        self._start_timer()
        print("⏳ 正在将输入图像保存为临时文件...")
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
        elapsed = self._end_timer()
        print(f"✅ 图像已保存到临时文件: {temp_file.name} [耗时: {elapsed}s]")
        return temp_file.name

    def get_upload_policy(self, api_key, model_name):
        self._start_timer()
        print("⏳ 正在从阿里云获取上传策略...")
        url = "https://dashscope.aliyuncs.com/api/v1/uploads"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        params = {"action": "getPolicy", "model": model_name}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"❌ 获取上传策略失败: {response.text}")
        elapsed = self._end_timer()
        print(f"✅ 上传策略获取成功 [耗时: {elapsed}s]")
        return response.json()['data']

    def upload_file_to_oss(self, policy_data, file_path):
        self._start_timer()
        print(f"⏳ 正在上传文件到OSS: {file_path}")
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
                raise Exception(f"❌ 上传文件失败: {response.text}")
        oss_url = f"oss://{key}"
        elapsed = self._end_timer()
        print(f"✅ 文件上传成功，OSS地址: {oss_url} [耗时: {elapsed}s]")
        return oss_url

    def generate(self, img_url, prompt, model_name, resolution, duration, prompt_extend, seed, api_key):
        self._start_timer()
        print("⏳ 正在生成视频...")
        print(f"📝 使用提示词: {prompt}")
        print(f"⚙️ 参数: 模型={model_name}, 分辨率={resolution}, 时长={duration}秒, 扩展提示={prompt_extend}, 种子={seed}")
        
        # 直接设置dashscope的API密钥
        dashscope.api_key = api_key
        
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
            video_url = response.output.video_url
            elapsed = self._end_timer()
            print(f"✅ 视频生成成功，下载地址: {video_url} [耗时: {elapsed}s]")
            return video_url
        else:
            raise Exception(f"❌ 视频生成失败: {response.status_code} - {response.message}")

    def download_video(self, url):
        self._start_timer()
        print(f"⏳ 正在从 {url} 下载视频...")
        response = requests.get(url)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            with open(temp_file.name, 'wb') as f:
                f.write(response.content)
            elapsed = self._end_timer()
            print(f"✅ 视频下载完成，保存到: {temp_file.name} [耗时: {elapsed}s]")
            return temp_file.name
        else:
            raise Exception("❌ 下载视频失败")

    def upload_and_generate(self, image, api_key, model_name, prompt, resolution, duration, prompt_extend, seed):
        self.total_start_time = time.time()
        print("="*50)
        print("🚀 开始上传并生成视频流程")
        print("="*50)
        
        # 获取API密钥，优先使用用户输入的，如果为空则尝试从环境变量获取
        if not api_key:
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
            if api_key:
                print("ℹ️ 使用环境变量中的DASHSCOPE_API_KEY")
            else:
                raise Exception("❌ 请提供DASHSCOPE_API_KEY，可以在节点参数中输入或设置环境变量")
        else:
            print("ℹ️ 使用用户输入的API密钥")
            
        # 直接设置dashscope的API密钥
        dashscope.api_key = api_key

        try:
            # 1. 保存输入图像为临时文件
            temp_image_path = self.save_image_temp(image)
            
            # 2. 获取上传策略并上传图像到OSS
            policy = self.get_upload_policy(api_key, model_name)
            img_url = self.upload_file_to_oss(policy, temp_image_path)
            
            # 3. 生成视频
            video_url = self.generate(img_url, prompt, model_name, resolution, duration, prompt_extend, seed, api_key)
            
            # 4. 下载生成的视频
            video_path = self.download_video(video_url)
            
            # 5. 处理视频为ComfyUI格式
            self._start_timer()
            print("⏳ 正在处理视频帧...")
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("❌ 无法打开生成的视频文件。")
            
            frames = []
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 8.0
                print(f"⚠️ 无法获取视频FPS，使用默认值: {fps}")
            
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                tensor = torch.from_numpy(frame_rgb).unsqueeze(0)
                frames.append(tensor)
            cap.release()
            
            elapsed = self._end_timer()
            print(f"✅ 已读取 {frame_count} 帧视频，FPS: {fps} [耗时: {elapsed}s]")
            
            if not frames:
                raise Exception("❌ 未读取到视频帧。")
            
            stacked = torch.cat(frames, dim=0)
            video_obj = VideoFromComponents(VideoComponents(images=stacked, frame_rate=Fraction(round(fps))))
            
            total_elapsed = round(time.time() - self.total_start_time, 2)
            print("="*50)
            print(f"🎉 视频生成流程完成! [总耗时: {total_elapsed}s]")
            print("="*50)
            
            return (video_obj,)
            
        except Exception as e:
            total_elapsed = round(time.time() - self.total_start_time, 2)
            print(f"❌ 发生错误: {str(e)} [已耗时: {total_elapsed}s]")
            raise


NODE_CLASS_MAPPINGS = {
    "UploadAndGenerateVideo": UploadAndGenerateVideo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UploadAndGenerateVideo": "上传并生成视频"
}
