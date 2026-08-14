# T2I Safety Eval

面向文生图安全评测的本地控制台。首版围绕现有 pipeline：管理数据集、启动和查看实验、比较 ASR，并监控模型 API 额度。

## 结构

- `frontend/`：React 控制台
- `backend/`：FastAPI，本地读取 pipeline 结果、管理配置与任务
- `docs/`：产品与工程说明

项目不保存 API Key；服务端仅从本机环境变量读取。
