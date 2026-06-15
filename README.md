# AIGC T2I Studio

> ComfyUI 文生图工作流平台 —— 角色生成、服化道模板、数据集筛选、场景训练一站式工具。

---

## 功能概览

- **角色生成**：内置 4 套角色预设（幺幺琳、老者、老者2.0、青年），支持 Z-Image / Flux 双模型
- **服化道模板**：9 套服装 + 8 套妆容 + 14 种道具，一键组合
- **工作流卡片**：可视化 ComfyUI 工作流管理，支持锁定/解锁
- **数据集筛选**：独立微服务（端口 8888），图文质量评分、去重、导出
- **Prompt 构建器**：结构化提示词引擎，自动拼装正面/负面词
- **场景训练素材**：场景 LoRA 训练素材管理

---

## 前提条件

| 依赖 | 说明 |
|------|------|
| Python 3.8+ | 安装时勾选 "Add Python to PATH" |
| ComfyUI | 需自行部署，默认地址 `192.168.1.88:8188` |
| Qwen 服务 | 可选，默认地址 `192.168.1.222:8000` |

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Lzl-3/AIGC-T2I-Studio.git
cd AIGC-T2I-Studio

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
copy .env.example .env
# 用记事本编辑 .env，填写 QWEN_API_KEY 和 ComfyUI 地址

# 4. 启动主应用（端口 8000）
python -m uvicorn app:app --host 127.0.0.1 --port 8000

# 5. 另开终端启动数据集筛选器（端口 8888）
python filter_server.py
```

浏览器访问：
- 主应用：http://127.0.0.1:8000
- 筛选器：http://127.0.0.1:8888

---

## 配置说明（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `COMFYUI_BASE_URL` | ComfyUI 服务地址 | `http://192.168.1.88:8188` |
| `OUTPUT_DIR` | 图片输出目录 | `./output` |
| `DB_PATH` | 数据库文件路径 | `./data/tasks.db` |
| `MAX_CONCURRENT_TASKS` | 最大并发生成数 | `1` |
| `POLL_TIMEOUT` | 单张超时（秒） | `600` |
| `QWEN_BASE_URL` | Qwen 服务地址 | `http://192.168.1.222:8000/v1` |
| `QWEN_API_KEY` | Qwen API 密钥 | 需自行填写 |
| `QWEN_MODEL` | Qwen 模型名称 | `qwen-dev` |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + ComfyUI 连接状态 |
| GET | `/api/models` | ComfyUI 可用模型列表 |
| GET | `/api/character-presets` | 角色预设列表 |
| POST | `/api/generate?card_id=` | 提交生成任务 |
| POST | `/api/upload` | 上传图片 |
| GET | `/api/tasks` | 任务列表 |
| DELETE | `/api/tasks/{id}` | 取消任务 |
| GET | `/api/output` | 浏览生成图片 |
| DELETE | `/api/output/delete` | 删除图片 |
| GET/POST | `/api/cards` | 工作流卡片列表/创建 |
| PUT/DELETE | `/api/cards/{id}` | 更新/删除卡片 |
| POST | `/api/cards/{id}/lock` | 锁定卡片 |
| POST | `/api/cards/{id}/unlock` | 解锁卡片 |

---

## 项目结构

```
AIGC-T2I-Studio/
├── app.py                  # 主应用入口
├── filter_server.py        # 数据集筛选微服务
├── requirements.txt        # Python 依赖
├── .env.example            # 配置模板
├── config/                 # 配置文件
├── src/                    # 后端源码（29 个模块）
│   ├── comfyui_client.py   # ComfyUI API 客户端
│   ├── workflow_engine.py  # 工作流引擎
│   ├── prompt_builder.py   # Prompt 构建器
│   ├── task_manager.py     # 任务队列管理
│   └── ...                 # 其他模块
├── static/                 # 前端（暗色金融终端主题）
│   ├── index.html          # 主页面
│   ├── dataset_filter.html # 数据集筛选页
│   ├── prompt-studio.html  # Prompt 工作室
│   └── js/                 # 前端 JS 模块（12 个）
├── workflows/              # ComfyUI 工作流模板（28 个）
│   ├── cards/              # 工作流卡片
│   └── confyui/            # 基础工作流
├── characters/             # 角色预设
└── data/                   # 运行时数据
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 端口被占用 | 关闭占用 8000/8888 的程序 |
| 依赖安装失败 | `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 连不上 ComfyUI | 检查 `.env` 中 `COMFYUI_BASE_URL` 是否正确 |
| Qwen 不可用 | 不影响主功能，Prompt 构建会自动降级 |
| 生成无反应 | 检查 `MAX_CONCURRENT_TASKS` 是否 > 0 |

---

## 技术栈

- **后端**：FastAPI + Pydantic + aiosqlite + httpx
- **前端**：原生 JavaScript（模块化）+ 暗色终端主题
- **AI 引擎**：ComfyUI API + Qwen vLLM
