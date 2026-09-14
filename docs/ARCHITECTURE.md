# Agent TestLab 首版架构

```text
React dashboard  ── HTTP ──>  Nginx ──> FastAPI
                                              │
             ┌────────────────────────────────┼────────────────────────┐
             │                                │                        │
        T2I 业务 API                 Testing Catalog/Runner        Observability
             │                                │                        │
       既有 JSONL 产物              JSON 事实源 + 可选 Redis       Prometheus
                                              │
                           注册用例 → 预览 hash → 受控执行 → 事件/BadCase
```

后端不持久化 API Key，运行时从本机环境变量或本地配置读取。验证任务默认限制为一条样本、一张图，且仅允许显式选择的低成本通道。

测试 runner 与 T2I pipeline 解耦：浏览器只能选择 Catalog 中的目标、工具和 case，不能传入命令、脚本路径或任意 URL。Mock 模式默认不触发模型；本地 pytest 也只允许仓库内登记的合同测试。Redis 只做运行快照和事件镜像，JSON 结果可在 Redis 不可用时独立恢复。
