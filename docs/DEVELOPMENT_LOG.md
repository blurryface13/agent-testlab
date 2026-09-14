# 开发节点

## 2026-09-15：Agent TestLab 范围与测试方案

作者：Codex（GPT-5）。本轮范围：设计文档与仓库名称，不做完整功能开发。

### 已做

- 阅读 T2I 工作区说明、产品文档、架构与前后端入口，核对现有未提交改动，全部保留。
- 阅读 EchoMind evaluator、PerformanceMonitor 与路由统计代码，明确源码复用目标、必要修正和许可核对要求。
- 查看 Test-Automation-Framework README、依赖及目录，记录 revision `ea626f26d201d321fdc6886727ffc37b2778e45d`。
- 新增 spec.md、DESIGN.md、两组科研端到端指令、历史 BadCase、测试场景目录与 CI/性能口径。
- GitHub 从 `blurryface13/t2i-safety-eval` 更名为 `blurryface13/agent-testlab`，通过 GitHub API 确认仍为 private；本地 origin 更新为新 URL。未更改可见性、分支、目录和服务名。
- README 增加新名称和开发文档入口；PRODUCT.md 补充测试工作台定位。未修改 package 名称和运行服务，避免命名调整影响启动。

### 没有做

- 没有新增或执行付费 Agent/T2I 测评，没有取得本轮新 BadCase 或性能成绩。
- 没有部署 Jenkins、Postman/Newman、JMeter 或 Docker 环境，没有改造 Asteria worker。
- 没有重启现有服务，没有修改公司仓库或 demo，没有提交/推送用户现有未提交代码。
- 两组测试指令属于设计，不把 EchoMind 的五组客服样例计为本项目测试数。

### 交接

按 spec 的 P0 开始。执行代码复用前核对许可证和来源；先隔离配置与数据，再落地一个 Mock 业务链和一个只读 API 冒烟。Asteria 侧按 AGENT_EVALUATION_PLAN 接入当前 Coordinator，而不是旧工作流 adapter。

GitHub 重命名只改变远端名称。初次交接时文档尚未提交；用户随后明确要求阶段收尾必须成功 commit，本次将上述设计文档与下列补充一同纳入文档提交，不推送。旧的历史交接文档保留原名称作为时间快照，不全局替换。

### 追加：预算授权与提交要求

- 用户授权本次真实模型测试累计 20 元人民币，由执行者分配；研究、Judge 和重试合计计费。本次仍只更新文档，新增真实调用费用为 0 元。
- spec 补充阶段成功 commit 的验收要求：排除证书链/签名等可修复故障、重试并核验提交，不绕过安全校验；区分 commit 与 push，交接提供真实哈希。
- 仅提交本轮七份 TestLab 文档；Asteria 上一轮 spec 接入计划单独提交。现有前后端代码与测试文件保持未提交，不重启服务。

## 2026-09-15：Agent TestLab 控制面与 Asteria 评测合同实现

作者：Codex（GPT-5）。本节点按用户要求从“设计”进入完整首版工作台实现；真实付费模型、真实 JMeter 压测和外部 Jenkins 连接仍未隐式启动。

### 已实现

- 在 `backend/app/testing/` 增加目标/工具/用例 Catalog、预检与配置 hash、受控 runner、JSON 持久化、事件增量读取、取消和 BadCase 候选。Runner 不接受浏览器传入任意命令、脚本路径或 URL；本地 pytest 只指向登记的合同测试。
- 前端接入测试工作台、运行记录、BadCase 和工具说明页面。页面真实调用 `/api/testing/catalog`、`/runs/preview`、`/runs`、`/events`、`/badcases`，选择故障注入时能展示失败分类和证据。
- 增加可选 Redis 快照/Stream 镜像与 Prometheus 指标。JSON 文件保持事实源，Redis 断开时降级不丢结果。
- 增加无密钥 Postman Collection/environment、控制面 JMeter JMX、Jenkins 冒烟流水线、后端/前端 Dockerfile、Compose、Nginx SPA 代理和 Windows 部署文档。
- 在 Asteria 增加 EchoMind 风格的严格 Judge 合同、Judge 结果持久化和 observation-only Monitor 聚合；不改 Coordinator 主流程，不用样本不足的统计反向影响路由。

### 验证记录

- `PYTHONPATH=backend python3 -m unittest backend.tests.test_testing_workbench -v`：4 项通过，覆盖 Catalog、目标/工具不匹配拒绝、预检 hash、Mock 故障和 BadCase。
- Python compileall、Postman JSON、JMeter XML 解析和 `git diff --check` 通过。
- 前端 `npm run build` 已在接入工作台后通过；在本轮 Docker 资产补齐后需再执行一次构建复核。
- 现有 `backend/tests/test_t2i_company_contract.py` 仍因宿主 Python 缺少 Pillow 无法启动；Docker requirements 已补 Pillow，不能把该宿主环境阻塞误记成业务失败，也不修改用户已有合同测试。
- Asteria 侧代码已完成语法检查；当前机器没有可用 Asteria Python 依赖环境，未虚报其 pytest 通过。接入逻辑以独立纯函数合同和现有 Pydantic 版本为目标，部署时需用项目锁定环境复测。

### 已知边界与下一步

- 当前 TestLab 的 Mock 是真实控制面流程，不是科研 Agent 效果成绩；`agent-eval` live/rescore 还需要把 Asteria 的认证 API、Trace/Artifact 权限和 Judge provider 配置接入。
- Postman/JMeter/Jenkins 资产已能导入/执行，但网页暂不直接操控桌面 Postman，JMeter 需在与目标服务相邻的机器运行，Jenkins 需配置凭据和节点。
- 任务记录当前以本地 JSON 为事实源，后续小范围多人使用前再迁移 TestLab 元数据至独立 PostgreSQL schema，并补用户所有权和 artifact 下载授权。

### 追加：真实页面验收（2026-09-15）

- 作者：Codex（GPT-5）。在保持本地 FastAPI/前端服务运行的前提下，使用浏览器真实操作测试工作台：选择 T2I Safety、pytest、Mock 与两个注册用例，完成“预览执行→确认开始→实时轮询→结果展示”。页面显示 2/2 通过，并在「测试运行」中恢复同一持久化运行记录。
- 在同一工作台打开「BadCase」与「测试工具」页面，确认故障注入产生的候选记录可见，Postman/JMeter/Jenkins 资产状态分别呈现为可导出/计划中，工具下载入口可见；没有把 Mock 结果冒充真实模型效果。
- 收紧本地 pytest 边界：只允许 T2I Safety 的单个登记合同用例，Asteria/QuinClaude 仍需各自 adapter，不会误跑 T2I 合同并伪装成其他目标通过。

### 追加：注册 pytest 真实执行复验（2026-09-15）

- 作者：Codex（GPT-5）。第一次从页面启动“本地注册执行”时发现真实 `pytest_error`：runner 子进程继承了工作目录，但没有补充 `backend` 源码路径，导致页面执行与终端直接执行的环境不一致。
- 修复 runner 的受控子进程环境拼装，保留原有 `PYTHONPATH` 并追加固定的 `backend` 目录；不开放前端传入任意环境变量、脚本路径或命令。
- 重启一次后端加载修复（前端未关闭），再次从页面完成“预览→确认→执行”，`U-T01` 显示“注册的 pytest 合同测试通过”，运行结果为 1/1 通过、约 275 ms。该次修复前的失败运行仍作为历史记录和候选 BadCase 保留，便于追溯。
