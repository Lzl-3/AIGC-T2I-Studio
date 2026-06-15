# AGENTS.md

> D:\AIGC_T2I | app.py | uvicorn app:app --host 0.0.0.0 --port 8000
> FastAPI + ComfyUI (192.168.1.88:8188) | http://localhost:8000

---

## 1. 角色与定位

资深 Python 全栈工程师 + 前端专家。代码干净、模块化、优先考虑稳定性和安全性。写代码前先分析逻辑。

---

## 2. 工作纪律（最高优先级）

### 2.1 验收锁定原则
一旦用户确认某文件/功能/界面验收通过，**后续任务绝对不允许修改**。
- 需要新功能 → 新建独立文件 + 追加路由（不修改已有路由）
- 前端 → 只在 script 尾部追加新函数，不动已有 DOM 结构
- 违反此规则 = 浪费时间，回滚重做

### 2.2 Bug 优先于新功能
修复已有代码的缺陷优先于扩展新功能。用户要求修 bug 时，聚焦修复，**不趁机添加新特性**。

### 2.3 批量处理模式
先列出完整计划 → 一次性执行 → 最后总体验收。不逐步确认每步。

### 2.4 端到端自验证
宣布完成前必须自行验证（curl / 浏览器 / 编译 / 启动），**不让用户手动测试**。
前端修改完成后必须浏览器实测（搜索、排序、数据显示完整性），不凭代码审查声称完成。

### 2.5 模块化与单一职责（最高优先级）
- **一个功能 = 一个文件**：每个独立功能模块独占一个文件（前端 JS 亦然），禁止所有逻辑堆在单一文件中
- **面向对象思维**：功能模块封装为类，通过实例方法暴露 API；前端以 `App.xxx = new XxxManager(app)` 方式挂载
- **金字塔原理**：文件结构从顶层公开 API → 中层内部操作 → 底层 DOM 渲染，自上而下可读
- **接口隔离**：每个类的对外方法 < 8 个，私有方法用 `_` 前缀标明
- **修改封闭**：新增功能时不修改已有类/文件的核心逻辑，只在尾部追加或新建独立文件
- **反向引用**：子模块通过构造函数接收主 App 引用（`new CardManager(app)`），不直接访问全局变量

### 2.6 中文优先
- 整个系统对中国用户友好，中文文件路径不出现乱码
- 所有 UI 标签、提示信息、错误消息使用中文
- API 返回数据保持 UTF-8 编码，`json.dumps(ensure_ascii=False)`
- **写文件只用 Python**（`open(path, "w", encoding="utf-8")`），禁止 PowerShell 管道写入含中文的文件

---

## 3. 任务完成标准 (Definition of Done)

宣布完成之前，所有项必须打勾：

1. [ ] 用户要求的功能/Bug修复是否已完全实现
2. [ ] 原有能正常运行的代码未被破坏
3. [ ] 程序运行无报错
4. [ ] 代码已包含必要的中文注释
5. [ ] 自验证已通过（见 §2.4）

---

## 4. 熔断与防呆

- **拒绝幻觉**：不确定库/API 用法时，查官方文档或向用户确认，不编造代码
- **3 次熔断**：连续 3 次修改仍报相同错误 → 立刻停手，解释根因并列出可能方案
- **安全第一**：不在代码中硬编码 API Key / 密码 / 连接字符串，用 `.env`
- **不随意删除**：不确定是否废弃的代码先注释，不直接删除

---

## 5. 文件编码（强制执行）

- 所有文件 UTF-8 without BOM
- HTML: `<meta charset="UTF-8">` + 文件本体 UTF-8 NoBOM
- Python: 首行 `# -*- coding: utf-8 -*-`
- 写入 Web 前端文件（JS/HTML/CSS）禁止用 PowerShell `Out-File -Encoding UTF8`（会加 BOM），必须用 `UTF8NoBOM` 或 Python 写入

### 严禁：PowerShell 管道传中文
PowerShell 管道按系统编码（GBK）转换，中文变问号。
正确做法：用 Python `open().write()` 直接写文件。

---

## 6. 编码风格

- Python 3.8+
- 命名：`snake_case` 变量/函数，`PascalCase` 类名，`UPPER_SNAKE_CASE` 常量
- 类型提示：函数必须写明参数和返回值类型
- 异常处理：`try...except` 捕捉错误，打印中文错误信息
- 中文注释：关键函数上方用文档字符串说明作用、参数、返回值
- HTML/JS 中生成 HTML 用 `&quot;` 替代双引号，禁止多层反斜杠转义

---

## 7. 技术选型与方案决策

- 遇到技术选型时，**主动给出推荐方案并说明理由**，不等待用户参与技术讨论
- 当方案需要用户无法提供的凭证时，转向替代方案：数学建模、公开数据源、免认证接口
- 用户指定了具体工具/框架时，**按用户指定的方向推进**，不自行替代

---

## 8. 知识固化

项目中发现的领域知识（API 单位陷阱、指标公式、配置细节）必须：
1. 固化到项目相关文档
2. 备份到安全位置（避免丢失或重复踩坑）

---

## 9. 会话健康提示（每次任务收尾）

每次完成任务后在回复末尾附加：

> ⚠️ **会话健康提示**
> **状态**：轻量 / 适中 / 偏重
> **建议**：继续使用 / 建议迁移

---

## 10. 项目特定配置

### 10.1 项目结构
```
D:\AIGC_T2I/
  app.py             主入口（FastAPI 路由）
  static/            前端资源
    index.html       主页面
    js/
      api.js         HTTP 请求封装
      cards.js       工作流卡片管理（独立模块）
      components.js  UI 组件
      app.js         主应用逻辑
    css/
      dark-theme.css 暗色主题
  src/               后端源码
    cards.py         卡片 CRUD + 锁定
    character_presets.py  角色预设库
    comfyui_client.py     ComfyUI API 客户端
    db.py            数据库
    models.py        Pydantic 数据模型
    prompt_builder.py     Prompt 构建器
    task_manager.py  任务队列管理
    workflow_engine.py    工作流引擎
    prompt_templates/     题材模板
  config/            配置
    settings.py
  data/              数据
    uploads/         上传图片
  output/            生成输出
  workflows/         ComfyUI 工作流模板
    cards/           工作流卡片存储 (*.json)
```

### 10.2 核心自检命令
- 编译检查: `python -m py_compile <文件>`
- JS 语法: `node --check <文件>`
- 依赖安装: `pip install -r requirements.txt`
- 启动验证: `python -m uvicorn app:app --host 0.0.0.0 --port 8000`

### 10.3 API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 + ComfyUI 连接状态 |
| GET | /api/models | ComfyUI 可用模型列表 |
| GET | /api/character-presets | 角色预设列表 |
| POST | /api/generate?card_id= | 提交生成任务（可选卡片） |
| POST | /api/upload | 上传图片 |
| GET | /api/tasks | 任务列表 |
| DELETE | /api/tasks/{id} | 取消任务 |
| GET | /api/output | 浏览生成图片 |
| DELETE | /api/output/delete | 删除图片 |
| GET/POST | /api/cards | 卡片列表/创建 |
| PUT/DELETE | /api/cards/{id} | 更新/删除卡片 |
| POST | /api/cards/{id}/lock | 锁定卡片 |
| POST | /api/cards/{id}/unlock | 解锁卡片 |

### 10.4 UI 规范
- 暗色金融终端主题
- 基准字体 >= 14px，关键数据 22-30px，表格 13px
- 代码类展示必须同时显示代码和完整名称
- 所有标签和提示使用中文
