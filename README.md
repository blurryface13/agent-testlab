# Agent TestLab

面向 Agent 与多模态模型的本地自动化测试工作台。项目把传统接口测试、异步任务验证、性能压测和 Agent 输出评测放在同一套测试目录中，结果以运行批次、断言明细和失败证据的形式留存。

当前工作台基于原有 T2I Safety 控制台演进，保留文生图安全数据集、生成和多裁判分析能力，并补充面向科研 Agent / Coding Agent 的测试对象、pytest 运行器、接口链路、Jenkins 计划和 LLM-as-Judge 评测入口。真实模型调用与压测仍需要显式确认，默认使用 Mock，不会因为打开页面而产生费用。

仓库：[blurryface13/agent-testlab](https://github.com/blurryface13/agent-testlab)（公开仓库）。本地目录暂沿用 `t2i-safety-eval`，避免影响现有运行路径。

## 能力概览

- **测试目录**：按单元、接口、集成、性能和 Agent 评测组织测试场景，区分 T2I、科研 Agent 与本地 Agent Runtime。
- **自动化执行**：以 pytest＋Requests 为主，pytest-asyncio 验证异步通信、任务取消和重连；预留 Postman/Newman、JMeter 与 Jenkins 的标准化执行入口。
- **Agent 评测**：通过结构化 Trace 检查意图路由、工具调用、任务状态和输出质量，支持四维 LLM-as-Judge、版本回归与 BadCase 归档。
- **运行可观测**：记录每次运行的目标版本、环境、耗时、通过/失败/错误/跳过状态和可脱敏产物；Monitor 指标与质量评分分开统计。
- **本地部署**：提供 Docker Compose 配置，可在 Windows＋Docker Desktop 或个人 PC 上先以 Mock 模式启动；真实 T2I/VLM 服务按环境配置接入。

## 快速开始

### 本地开发

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

另开终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

打开 <http://127.0.0.1:4173>。没有相邻 `demo` 或模型密钥时，工作台仍可浏览测试目录并运行 Mock 测试。

### Docker Desktop

```bash
docker compose up --build
```

打开 <http://127.0.0.1:4173>。默认不挂载个人密钥、不连接外部模型；如需接入本地服务，在部署机通过未提交的 `.env` 或 compose 环境变量配置，并先阅读[部署说明](docs/DEPLOYMENT.md)。

## 文档

- [开发规格与实施顺序](spec.md)
- [科研 Agent Monitor 与端到端评测](docs/AGENT_EVALUATION_PLAN.md)
- [测试场景、工具与 CI 方案](docs/TEST_CATALOG.md)
- [测试工作台设计](DESIGN.md)
- [部署与环境配置](docs/DEPLOYMENT.md)
- [开发记录](docs/DEVELOPMENT_LOG.md)

## 目录

- `frontend/`：React/Vite 控制台
- `backend/`：FastAPI API、测试目录、运行器和 T2I 适配
- `tests/`：工作台自身的无模型契约测试
- `docs/`：产品、测试、部署和实现记录

## 安全与数据边界

项目不保存 API Key。服务端只从本机环境变量或显式配置文件读取密钥，前端只显示通道状态；测试运行器只接受注册的用例和目标，不接受任意 Shell 命令或任意 URL。个人实验输出、模型权重、`.env`、真实提示词数据和运行产物均不纳入仓库。

本仓库沿用原 T2I 项目的开发记录和部分适配代码；引用外部项目时保留来源与许可证说明，具体复用边界见 `spec.md`。
