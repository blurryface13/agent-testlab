# Backend

```bash
cd backend
/Users/dora/miniconda3/envs/dora/bin/python3 -m uvicorn app.main:app --reload --port 8010
```

- `GET /api/dashboard`：读取已有评测产物，供控制台展示。
- `POST /api/runs/preview`：仅验证低成本预览参数，强制 `1` 条样本、`1` 张图，不执行模型调用。

可在 `data/quota_snapshot.json` 放置本机额度快照（不纳入 Git）：

```json
{"quotas":[{"name":"APIDock","vendor":"GPT-5.4 · Sonnet","remaining":"$3.19","percent":16,"tone":"low"}]}
```
