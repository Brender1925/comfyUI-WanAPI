# GitHub 项目介绍：上传并生成视频

## 项目概述

本项目是基于 [comfyUI-WanAPI](https://github.com/Brender1925/comfyUI-WanAPI) 的增强版本，在原功能基础上增加了多项实用功能。核心功能仍然是利用阿里云通义千问API实现图像到视频的生成。

## 新增功能

1. **步骤提示增强**：
   - 在视频生成过程中增加了详细的步骤提示
   - 每个关键步骤都有明确的进度反馈
2. **时间显示功能**：
   - 实时显示各步骤耗时
   - 总耗时统计功能
3. **API-KEY 直接填写**：
   - 在ComfyUI界面中直接输入API-KEY
   - 无需修改代码或设置环境变量
4. **用户体验优化**：
   - 更友好的错误提示
   - 生成状态可视化

## 源仓库说明

本项目基于 [comfyUI-WanAPI](https://github.com/Brender1925/comfyUI-WanAPI) 进行二次开发，主要保留了原项目的核心功能：

- 图像上传至阿里云OSS
- 通过DashScope API生成视频
- 视频下载和处理功能

## 功能特点

1. **图像上传**：支持将用户上传的图像保存为临时文件，并上传至阿里云 OSS。
2. **视频生成**：通过 DashScope API，根据用户提供的提示词和参数生成视频。
3. **视频下载**：生成的视频可以直接下载到本地。
4. **视频处理**：将下载的视频处理为 ComfyUI 格式，方便后续使用。
5. **性能监控**：记录每个步骤的耗时，方便用户了解整个流程的效率。

## 安装方法

### 作为ComfyUI自定义节点安装

```bash
# 进入ComfyUI自定义节点目录
cd ComfyUI/custom_nodes

# 克隆本仓库
git clone https://github.com/msola-ht/ComfyUI-Wan-API.git

# 安装依赖
pip install -r requirements.txt
```

完成后重启ComfyUI，新节点将出现在节点选择菜单中。

## 使用说明

### 1. 注册阿里云并获取 API 密钥

1. 打开 [通义千问控制台](https://bailian.console.aliyun.com/#/home)
2. 点击右上角"新用户开通即享每个模型100万免费Tokens"的"立即开通"
3. 注册或者登陆阿里云账号
4. 获取API Key
   - 前往"我的API-KEY"页面，单击"创建我的API-KEY"
   - 在已创建的API Key操作列，单击"查看"，获取API KEY
   - ![API KEY获取示例](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/0240945471/p943033.png)
   - 具体参考 [API密钥管理页面](https://bailian.console.aliyun.com/?spm=5176.29619931.J__Z58Z6CX7MY__Ll8p1ZOR.1.64e9521cEc4QyE&tab=api#/api)

### 2. 配置 API 密钥

在使用前，需要配置 DashScope API 密钥。可以通过以下两种方式提供：
- 在代码中直接输入 API 密钥。
- 设置环境变量 `DASHSCOPE_API_KEY`。

### 3. 调用方法

使用 `UploadAndGenerateVideo` 类的 `upload_and_generate` 方法，传入以下参数：
- `image`: 输入图像（格式为 IMAGE）。
- `api_key`: DashScope API 密钥（字符串）。
- `model_name`: 选择模型（可选值：`wanx2.1-i2v-turbo`, `wanx2.1-i2v-plus`）。
- `prompt`: 提示词（字符串）。
- `resolution`: 视频分辨率（可选值：`480P`, `720P`）。
- `duration`: 视频时长（整数，范围：3-5秒）。
- `prompt_extend`: 是否扩展提示（布尔值）。
- `seed`: 随机种子（整数）。

## 联系方式

如有任何问题或建议，请通过 GitHub 联系我们。感谢您的关注与支持！
