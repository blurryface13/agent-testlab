# Backend

```bash
cd backend
/Users/dora/miniconda3/envs/dora/bin/python3 -m uvicorn app.main:app --reload --port 8010
```

- `GET /api/dashboard`：读取已有评测产物，供控制台展示。
- `GET /api/datasets`：索引 `demo/outputs` 中已有的生成数据集，不修改其内容。
- `GET /api/config/options`：返回本地工作台允许配置的被测模型、裁判和采样比例。
- `POST /api/runs/preview`：验证运行单并计算采样量，固定每条提示词 `1` 张图；不执行模型调用、不读取密钥、不写入 demo。

可在 `data/quota_snapshot.json` 放置本机额度快照（不纳入 Git）：

```json
{"quotas":[{"name":"APIDock","vendor":"GPT-5.4 · Sonnet","remaining":"$3.19","percent":16,"tone":"low"}]}
```
