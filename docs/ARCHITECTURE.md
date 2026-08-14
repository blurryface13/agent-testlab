# 首版架构

```text
React dashboard  ── HTTP ──>  FastAPI
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
                 数据集索引     实验结果      pipeline 启动器
                     │            │            │
                 JSONL       metrics.json   demo/server_eval.py
```

后端不持久化 API Key，运行时从本机环境变量或本地配置读取。验证任务默认限制为一条样本、一张图，且仅允许显式选择的低成本通道。
