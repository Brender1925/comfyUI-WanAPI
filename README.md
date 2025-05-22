# 通义 API 视频生成节点 for ComfyUI

这是一个用于ComfyUI的自定义节点，基于阿里云 DashScope 通义万相模型的图生视频功能，支持将图像上传至 OSS，并生成视频返回到 ComfyUI 前端中。

## 📦 功能特点

- 支持模型选择：`wanx2.1-i2v-turbo` 与 `wanx2.1-i2v-plus`
- 视频格式返回为 `VIDEO` 类型，可直接用于保存节点或后续处理
- 支持自定义提示词、分辨率、时长、随机种子等参数
- 支持环境变量注入阿里云 API Key

## 🧪 安装方法

设置 DASHSCOPE_API_KEY 环境变量
文件放入你的 `ComfyUI/custom_nodes` 目录中，并安装依赖.

