# AIGC T2I Studio

> ComfyUI 文生图工作流平台 —— 角色生成、服化道模板、数据集筛选、场景训练一站式工具。

---

## 功能概览

- **角色生成**：内置角色预设，支持 Z-Image / Flux 双模型
- **服化道模板**：服装 + 妆容 + 道具，一键组合
- **工作流卡片**：可视化 ComfyUI 工作流管理
- **数据集筛选**：独立微服务（端口 8888），图文质量评分、去重
- **Prompt 构建器**：结构化提示词引擎
- **场景训练素材**：LoRA 训练素材管理

---

## 快速开始（无需装 Python）

### 方式一：一键脚本

```
1. 双击 setup.bat  → 自动检测并安装 Python + 依赖
2. 编辑 .env       → 用记事本打开，填写 ComfyUI 地址和 API 密钥
3. 双击 run.bat    → 自动启动两个服务
```

> 如果 `setup.bat` 提示未找到 Python，浏览器会自动打开 Python 官网，安装后重试。

### 方式二：手动安装

```bash
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 填写配置
python -m uvicorn app:app --host 127.0.0.1 --port 8000
python filter_server.py          # 另开终端
```

---

## 访问地址

| 服务 | 端口 | 地址 |
|------|------|------|
| 主应用 | 8000 | http://127.0.0.1:8000 |
| 数据集筛选器 | 8888 | http://127.0.0.1:8888 |

---

## 配置说明（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `COMFYUI_BASE_URL` | ComfyUI 服务地址 | `http://192.168.1.88:8188` |
| `MAX_CONCURRENT_TASKS` | 最大并发生成数 | `1` |
| `POLL_TIMEOUT` | 单张超时（秒） | `600` |
| `QWEN_BASE_URL` | Qwen 服务地址（可选） | `http://192.168.1.222:8000/v1` |
| `QWEN_API_KEY` | Qwen API 密钥（可选） | 需自行填写 |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 可用模型列表 |
| GET | `/api/character-presets` | 角色预设 |
| POST | `/api/generate` | 提交生成任务 |
| POST | `/api/upload` | 上传图片 |
| GET | `/api/tasks` | 任务列表 |
| GET/POST | `/api/cards` | 工作流卡片管理 |

---

## 项目结构

```
├── app.py / filter_server.py   # 入口
├── setup.bat / run.bat          # 一键安装/启动
├── src/                         # 后端 29 个模块
├── static/                      # 前端（暗色主题）
├── workflows/                   # ComfyUI 工作流模板
├── characters/                  # 角色预设
└── data/                        # 运行时数据
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 未装 Python | 双击 `setup.bat`，脚本会自动引导安装 |
| 依赖安装慢 | 已配置清华镜像源 |
| 端口被占用 | 关闭占用 8000/8888 的程序 |
| 连不上 ComfyUI | 检查 `.env` 中地址是否正确 |
| Qwen 不可用 | 不影响主功能，Prompt 构建自动降级 |
