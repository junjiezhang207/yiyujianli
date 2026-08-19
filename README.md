# 一语简历

一句话输入，AI 帮你生成可编辑、可导出的专业简历。

![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

## 项目介绍

**一语简历** 是一个面向中文求职场景的 AI 简历生成与优化系统，覆盖从内容生成、结构化编辑到高质量 PDF 导出的完整流程。用户可以通过自然语言生成简历，也可以手动编辑字段、导入 PDF/图片简历，并通过 AI 助手进行诊断、润色和局部修改。

## 核心能力

| 能力 | 说明 |
|:--|:--|
| AI 一键生成 | 根据一句话描述或原始文本，生成结构化简历 |
| 对话式修改 | 支持整份优化、局部修改、润色、扩写、缩写等操作 |
| 智能导入解析 | 支持 PDF / 图片简历导入，并转换为结构化数据 |
| 简历诊断 | 对简历内容完整度、表达质量和岗位匹配度进行分析 |
| 可视化编辑 | 左侧字段编辑，右侧 PDF 预览，支持实时渲染 |
| 模板与排版 | 支持模板选择、排版配置和简历版本管理 |
| PDF 导出 | 基于 LaTeX / XeLaTeX 渲染专业 PDF |

## 页面截图

| 编辑工作区 | AI 助手 |
|:--:|:--:|
| ![编辑工作区](assets/readme/workspace-editor.png) | ![AI 助手](assets/readme/ai-assistant.png) |

| 我的简历 |
|:--:|
| ![我的简历](assets/readme/resume-library.png) |

## 技术栈

| 层级 | 技术 |
|:--|:--|
| 前端 | React 18、TypeScript、Vite、React Router、Tailwind CSS、PDF.js、TipTap、SSE |
| 后端 | FastAPI、Python、Pydantic、SQLAlchemy、SQLite / PostgreSQL |
| Agent | LangChain 1.x、LangGraph、Tool / Skill 调用、短期记忆、意图路由 |
| AI 模型 | DeepSeek、Qwen / DashScope、智谱 GLM、OpenAI 兼容接口 |
| 简历数据 | Resume JSON Schema、字段归一化、路径级 patch、before / after diff |
| PDF 渲染 | LaTeX、XeLaTeX、PDF 流式渲染、PDF / 图片导入 OCR |
| 认证服务 | Next.js、Better Auth |

## 本地部署

### 1. 环境要求

- Python 3.12+
- Node.js 20+，因为 `web` 认证服务使用 Next.js 16
- XeLaTeX，PDF 导出必需
- 中文字体，Linux 环境建议安装 Noto CJK

### 2. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install

# 认证服务依赖
cd ../web
npm install
```

### 3. 后端环境变量

复制后端环境变量模板：

```bash
cp .env.example .env
```

常用配置：

```ini
# DeepSeek / Qwen 走 DashScope 兼容接口
DASHSCOPE_API_KEY=

# RuoLi 中转，可选
RUOLI_API_KEY=

# 智谱 OCR / 视觉识别
ZHIPU_API_KEY=

# 豆包模型，可选
DOUBAO_API_KEY=

# OpenAI 兼容模型，可选
OPENAI_API_KEY=

# JWT 签名密钥，本地开发可填随机字符串
JWT_SECRET_KEY=change-me-to-a-random-string

# 可选：启用 LangChain 1.x Agent Runtime
AGENT_RUNTIME=langchain_v1
```

### 4. 前端环境变量

```bash
cp frontend/.env.example frontend/.env.local
```

关键配置：

```ini
VITE_API_BASE_URL_LOCAL=http://127.0.0.1:9000
VITE_AUTH_WEB_URL=http://localhost:3000
VITE_AGENT_ENABLED=false
VITE_AGENT_ASKING_MODE_ENABLED=false
```

### 5. 认证服务环境变量

```bash
cp web/.env.example web/.env.local
```

关键配置：

```ini
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_SECRET=replace-with-openssl-rand-base64-32
BETTER_AUTH_DATABASE_URL=postgresql://resume_user:password@localhost:5432/resume_db
NEXT_PUBLIC_FASTAPI_BASE_URL=http://127.0.0.1:9000
FASTAPI_INTERNAL_BASE_URL=http://127.0.0.1:9000
FASTAPI_INTERNAL_AUTH_SECRET=replace-with-shared-internal-secret
AUTH_PROXY_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
AUTH_DEFAULT_RETURN_TO=http://localhost:5173/workspace
```

如果只做本地功能调试，可以先不接第三方 OAuth；如果需要登录注册，必须启动 `web` 服务。

### 6. 启动服务

后端：

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 9000
```

认证服务：

```bash
cd web
npm run dev
```

前端：

```bash
cd frontend
npm run dev
```

### 7. 访问地址

| 服务 | 地址 |
|:--|:--|
| 前端 | http://localhost:5173 |
| 后端 API | http://127.0.0.1:9000 |
| 后端文档 | http://127.0.0.1:9000/docs |
| 认证服务 | http://localhost:3000 |

## 开发验证

```bash
# 前端构建
cd frontend
npm run build

# 后端测试
python -m pytest backend/tests/ -q
```

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
