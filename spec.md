# Agent TestLab 开发规格

日期：2026-09-15。作者：Codex（GPT-5）。状态：设计稿，尚未实现新增测试系统。

## 1. 目标与边界

将现有个人 T2I Safety 控制台扩展为自动化测试工作台。传统测试负责接口、状态、权限、异常和性能；Agent 评测负责意图、执行行为和交付质量。两者共用用例目录、批次记录、报告入口和 BadCase 流程，不混用通过率分母。

本轮只交付规格、界面设计、两组 Agent 测试指令、历史 BadCase 目录和仓库更名。不发起真实模型调用、不安装 Jenkins、不运行压测、不修改科研编排、不复制公司代码或私有数据。

角色边界：

- Asteria：被测科研系统，接入 EchoMind 启发的 Monitor 和独立评分服务，保留真实 Coordinator、持久化研究 worker、人工审批与技能选择。
- Agent TestLab：测试控制台，承载 pytest、Postman、JMeter、Jenkins 的任务选择与结果汇总；读取 Asteria 评测结果，不在前端再实现另一套评分。
- QuinClaude：运行时测试场景来源。通过单独 adapter 测试，不假定其代码已经成为 Asteria 的真实依赖。
- T2I：现有业务模块，也是合同、数据质量、生成及裁判流程的测试对象。
- 公司仓库与相邻 demo：不纳入本轮写入、复制、发布或压测范围。

## 2. 当前基线

| 系统 | 已核对 | 本轮不宣称已完成 |
| --- | --- | --- |
| T2I | FastAPI、React/Vite，数据集/生图/裁判入口；本地存在 unittest＋Mock 合同测试 | 通用测试 runner、Jenkins、Postman Collection、JMeter 测试计划 |
| Asteria | PostgreSQL Run/Event/审批/产物，Coordinator，规则评测及 BadCase 页面 | 当前自主入口的完整 LLM Judge、历史语义补评、Monitor 路由反馈 |
| 旧评测 adapter | basic、multi_agent、multi_agent_perspectives 工作流 | 不等于通过当前 Coordinator 的端到端测试 |
| EchoMind | Python evaluator、PerformanceMonitor、同类实例路由评分、四维 Judge | 原始代码不等于已迁入 Asteria；五组内置客服用例不计入本项目 |

T2I 工作区已有未提交代码，保持原样；当前设计与实施不能顺手暂存这些修改。QuinClaude 的历史 272 条测试也不得直接作为新系统已接入数量。

## 3. 框架复用策略

### 3.1 EchoMind

本地参考根目录：`/Users/dora/Downloads/EchoMind所有代码+详细文档+简历/EchoMind`。

| 来源 | 复用目标 | 必要适配 |
| --- | --- | --- |
| evaluation/evaluator.py | QualityScores、分类统计、Judge 调用、报告与退化比较 | 科研 rubric、真实 Coordinator adapter、历史补评、评分失败独立状态 |
| monitor/performance_monitor.py | 周期采集、告警、Prometheus 导出、健康度惩罚 | 持久事件增量聚合、科研时延口径、低样本保护 |
| agents/agent_orchestrator.py | get_stats/update_routing_penalties 合同、同类实例评分 | 不替换 Asteria 研究循环；无同能力候选时仅观测，不伪造路由优化 |

实施前生成来源清单，保存路径、SHA256、修改说明。下载包尚未确认可再分发许可证，不能把“代码在手”当作公开发布授权；源码复制提交前确认许可。许可未明时只在个人本地验证，公共实现依据接口合同独立实现，不复制受限文本。

### 3.2 Test-Automation-Framework

上游：https://github.com/youngyangyang04/Test-Automation-Framework

本轮查阅 revision：`ea626f26d201d321fdc6886727ffc37b2778e45d`。依赖与目录已核对，不代表全部模块已运行验证。

- 复用候选：`common/sendrequest.py` 请求封装、`common/assertions.py` 断言、`base/apiutil.py` 与 `base/apiutil_business.py` 用例执行结构、`conftest.py` 生命周期、`run.py` Allure/JUnit 产物方式。
- 替换业务：商品/订单/支付用例改为数据集、会话、研究任务、裁判及产物读取。
- 保持 Python＋pytest＋Requests 主栈；pytest-asyncio 只用于异步单元/集成测试。Requests 是同步客户端，不直接阻塞 FastAPI 事件循环，测试应在独立进程执行。
- Postman/Newman、JMeter 测试计划与 Jenkinsfile 属于本项目要新增的适配。上游依赖出现 Jenkins 不等于已经有可直接复用的完整流水线。
- 上游为 GPL-3.0；复制时保留许可与归属，发布前检查适用义务和依赖许可。只引入必要模块，不导入上游凭据、生成报告、缓存或无关数据库依赖。

## 4. 系统合同

目标流程：工作台预览测试单 → 明确执行 → 独立 runner/Jenkins → 结果解析 → 持久化结果 → 人工复核与回归。

### 4.1 最小实体

- TargetProfile：目标类型、允许访问的地址、代码版本、环境标识、凭据引用、是否允许付费调用。
- TestCase：case_id、version、level、target、tool、前置条件、输入、断言、清理规则、来源。
- TestRun：批次 ID、所有者、用例快照、执行器与目标版本、环境、状态、开始结束时间、预算。
- TestResult：run/case/attempt、pass/fail/error/skip、断言明细、错误分类、耗时、产物引用。
- AgentEval：research_run_id、artifact_hash、rubric_version、judge_version、score_status、四维分数与证据。
- BadCase：来源运行、预期/实际、最小复现、证据、候选/确认/拒绝/修复待回归状态。

TestLab 元数据使用独立 PostgreSQL database/schema 与凭据，不写 Asteria 业务表；报告置于独立受控目录。优先复用 PostgreSQL 实例，不新引入另一套主数据库。Redis 可作缓存，不承担唯一运行记录。实际迁移另开实施任务。

### 4.2 计划 API（均未实现）

- GET `/api/testing/catalog`：合法的类型、工具及场景组合。
- GET `/api/testing/targets`：可用目标与脱敏环境状态。
- POST `/api/testing/runs/preview`：解析用例、权限、预算与执行命令，无模型调用或写业务数据。
- POST `/api/testing/runs`：携带预览摘要、幂等键，确认启动。
- GET `/api/testing/runs/{id}` 与 `/events?after=`：状态与增量日志。
- POST `/api/testing/runs/{id}/cancel`：取消本次执行，不停止共享服务。
- GET `/api/testing/runs/{id}/artifacts/{artifact_id}`：校验所有者后下载。
- GET `/api/testing/cases/{id}/exports/{format}`：导出 Postman Collection/environment 模板或已审查 JMX，禁止包含密钥。

Runner 只接受注册的执行器、case_id 和受控参数；不接受前端任意 shell、任意脚本路径、任意 URL。子进程使用参数数组、固定目录、时限与取消清理。Jenkins job 使用白名单，凭据后端持有，回调验签且幂等。内网目标仅由对应网络内授权 runner 访问，不能搭建任意代理。

## 5. 环境与上线

先在 Mac 使用 Mock 模型及独立测试数据跑通；个人 PC 可用 Docker Compose 承载 TestLab、PostgreSQL 和 runner/Jenkins。无需公网域名或 GPU。

数据库、文件卷和测试用户与日常使用隔离。T2I 当前依赖相邻 demo 的环境及产物，第一笔实施必须取消测试对其真实目录的默认写入，不复制密钥。真实模型网络默认禁止，仅 explicit live 配置允许。

公网不是当前目标。Asteria 先处理报告文件授权、评测资产用户隔离、免登录开关与备份；不得因测试上线直接暴露 `/outputs`、数据库、Jenkins 或 `/metrics`。

JMeter 从独立机器发压；控制面接口压测使用模型替身，低并发真实模型测评另报。网络中断、费用耗尽、人工取消和裁判异常各自记录，不从总失败数剔除。

## 6. 交付顺序与完成证据

| 阶段 | 实施范围 | 完成证据 |
| --- | --- | --- |
| P0 隔离与合同 | 测试配置、临时数据目录、目标白名单、来源许可核对 | 零凭据导出、零 demo 写入、未授权目标拒绝测试 |
| P1 基础自动化 | pytest＋Requests、现有 T2I 单元测试收集、Allure、Postman 导出 | 一条 Mock 业务链＋真实只读 API 冒烟，结果可追溯 |
| P2 科研评测 | EchoMind adapter、Monitor、两组用例、历史补评 | 两组各有真实 run/trace/score；失败也完整展示，不要求造出 BadCase |
| P3 控制台 | 按 DESIGN.md 接入类型/工具/内容选择与结果详情 | 真实请求、真实日志，未实现工具明确禁用 |
| P4 CI 与性能 | Jenkins 冒烟/定时回归、Newman、JMeter | build URL、Allure、脱敏 JTL、负载与环境配置、故障复测 |

每阶段记录代码 revision、环境、命令、退出状态、产物与已知边界。无实测不填写简历提升比例；先两组不宣称五组。5% 为基线退化规则，0.75 为质量阈值，均不是已达效果。

## 7. 交付约定补充（2026-09-15）

- 用户已授权本次测试开发使用累计不超过 **20 元人民币**的真实模型调用预算，由执行者按验证价值分配，额度内无需逐次确认。该额度不是每条用例或每轮对话各 20 元，也不是必须花完；研究、Judge、失败调用和重试共同计入。
- 执行前核对模型价格及可获取的 usage，记录实际用量、估算费用和剩余额度；为在途请求预留费用。价格或用量无法核实、无法可靠约束累计开销时，先停止新增真实请求并说明情况，不把未知费用当作零。超过总预算须重新征得用户同意。
- **阶段收尾必须完成成功的本地 Git commit**，不能仅保存文件或暂存；提交前审查 diff、检查敏感信息并完成与修改范围相称的验证，只暂存本任务文件，不夹带用户已有修改。
- 遇到证书链、签名、身份配置或提交钩子故障，应定位原因并在权限范围内修复后重试，不能把这类可处理问题作为暂缓提交的理由。不得关闭 TLS 校验、绕过安全检查或擅自关闭签名来制造成功；如确需用户凭据或新权限，明确说明阻塞，不宣称已提交。
- 本地 commit 通常不依赖网络证书；须区分 commit、push 和合并。提交成功以退出状态及 `git log`/`git show` 核验为准，交接提供提交哈希与剩余改动；push/合并按用户授权单独执行，不以本地提交冒充远端同步。

## 8. 文档导航

- [两组科研用例与 Monitor](docs/AGENT_EVALUATION_PLAN.md)
- [测试目录与工具操作](docs/TEST_CATALOG.md)
- [前端设计](DESIGN.md)
- [开发节点](docs/DEVELOPMENT_LOG.md)
