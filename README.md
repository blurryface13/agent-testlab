# Agent TestLab

面向 Agent 与文生图服务的自动化测试及效果评测工作台。

当前已具备 T2I 数据集、实验、裁判结果和模型额度管理；pytest、Postman、JMeter、Jenkins 测试入口与科研 Agent 评测集成处于设计阶段，尚未完成部署。

仓库：[blurryface13/agent-testlab](https://github.com/blurryface13/agent-testlab)。本地目录暂沿用 `t2i-safety-eval`，避免影响现有运行路径。

## 开发文档

- [开发规格与实施顺序](spec.md)
- [科研 Agent Monitor 与端到端评测](docs/AGENT_EVALUATION_PLAN.md)
- [测试场景、工具与 CI 方案](docs/TEST_CATALOG.md)
- [测试工作台设计](DESIGN.md)
- [开发记录](docs/DEVELOPMENT_LOG.md)

## 结构

- `frontend/`：React 控制台
- `backend/`：FastAPI，本地读取 pipeline 结果、管理配置与任务
- `docs/`：产品与工程说明

项目不保存 API Key；服务端仅从本机环境变量读取。
