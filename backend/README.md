# Backend

```bash
cd backend
/Users/dora/miniconda3/envs/dora/bin/python3 -m uvicorn app.main:app --reload --port 8010
```

- `GET /api/dashboard`：读取已有评测产物，供控制台展示。
- `GET /api/datasets`：索引 `demo/outputs` 中已有的生成数据集，不修改其内容。
- `GET /api/config/options`：返回本地工作台允许配置的被测模型、裁判和采样比例。
- `GET /api/providers`：返回 APIDock、DeepSeek 官方和阿里云百炼 Qwen 官方通道的安全配置状态，不返回 API Key。
- `POST /api/runs/preview`：验证运行单并计算采样量，固定每条提示词 `1` 张图；不执行模型调用、不读取密钥、不写入 demo。

服务会从相邻 `demo/.env` 读取下列变量是否存在，并把其用于后续正式 worker 路由；密钥不会发送给前端或写入日志：

- `APIDOCK_API_KEY`：`https://apidock.ai/v1`，GPT-5.4 / Claude Sonnet。
- `DEEPSEEK_API_KEY`：`https://api.deepseek.com`，`deepseek-chat`。
- `DASHSCOPE_API_KEY`：`https://dashscope.aliyuncs.com/compatible-mode/v1`，`qwen-plus`。

可在 `data/quota_snapshot.json` 放置本机额度快照（不纳入 Git）。API Key 不应写入该文件：

```json
{
  "quotas": [
    {"name":"APIDock","vendor":"GPT-5.4 · Sonnet","remaining":"$3.19","percent":16,"tone":"low"},
    {"name":"DeepSeek 官方","vendor":"deepseek-chat","remaining":"账单侧同步","percent":0,"tone":"watch"},
    {"name":"Qwen 官方","vendor":"qwen-plus · 百炼","remaining":"账单侧同步","percent":0,"tone":"watch"}
  ]
}
```

DeepSeek 与百炼的余额/用量以各自 Billing、Usage 或模型监控页面为准；这里将本地快照与实时运行记录分开，避免显示不可验证的“实时余额”。
