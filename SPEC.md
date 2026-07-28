# 图片压缩工具 - Image Compressor

## 1. 项目概述

- **项目名称**: Image Compressor
- **类型**: 前后端分离的Web应用（Flask + 原生HTML/JS）
- **核心功能**: 拖拽/上传多张图片，批量压缩后打包下载
- **目标用户**: 需要快速压缩图片的用户

## 2. 技术栈

- **后端**: Python 3 + Flask
- **前端**: 原生 HTML5 + CSS3 + JavaScript
- **图片处理**: Pillow (PIL)
- **压缩包生成**: zipfile

## 3. 功能列表

### 上传功能
- [ ] 点击选择文件上传（支持多选）
- [ ] 拖拽上传（支持多文件）
- [ ] 显示上传进度
- [ ] 支持格式: JPG, PNG, WEBP, BMP

### 压缩功能
- [ ] 可调节压缩质量滑块 (10-100%)
- [ ] 批量压缩处理
- [ ] 实时显示压缩进度
- [ ] 显示原文件大小 vs 压缩后大小

### 下载功能
- [ ] 打包为ZIP压缩包下载
- [ ] 点击单个文件单独下载
- [ ] 显示压缩比统计

### 界面功能
- [ ] 拖拽区域视觉反馈
- [ ] 文件列表预览（缩略图、名称、大小、状态）
- [ ] 响应式设计

## 4. 视觉规范

### 配色方案
- **主色**: #4F46E5 (靛蓝色)
- **背景色**: #F8FAFC (浅灰白)
- **卡片色**: #FFFFFF
- **边框色**: #E2E8F0
- **文字色**: #1E293B
- **成功色**: #22C55E
- **警告色**: #F59E0B
- **错误色**: #EF4444

### 字体
- **主字体**: "Inter", system-ui, sans-serif
- **等宽字体**: "JetBrains Mono", monospace

### 间距系统
- 基础单位: 4px
- 卡片圆角: 12px
- 按钮圆角: 8px

## 5. 项目结构

```
/Users/zhennamener/code-project/image-compression
├── app.py                 # Flask 后端
├── compress.py            # 图片压缩逻辑
├── templates/
│   └── index.html         # 前端页面
├── static/
│   └── style.css          # 样式文件
└── uploads/               # 上传文件临时目录
```

## 6. API 设计

### POST /upload
- **功能**: 上传图片文件
- **请求**: multipart/form-data
- **响应**: JSON `{ "success": true, "file_id": "xxx", "filename": "xxx", "size": 1234 }`

### POST /compress
- **功能**: 压缩指定文件
- **请求**: JSON `{ "file_ids": ["id1", "id2"], "quality": 80 }`
- **响应**: JSON `{ "success": true, "files": [{ "id": "xxx", "original_size": 1000, "compressed_size": 500 }] }`

### GET /download/<file_id>
- **功能**: 下载单个压缩文件
- **响应**: 文件流

### GET /download-all
- **功能**: 下载所有压缩文件ZIP包
- **响应**: ZIP文件流

### DELETE /clear
- **功能**: 清理所有上传文件
- **响应**: JSON `{ "success": true }`