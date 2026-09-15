# 测试场景、工具与 CI 计划

2026-09-15 · Codex（GPT-5）。Asteria 为本轮主测试对象；未执行的外部工具和真实模型场景仍明确标注。

## 1. 技术栈与职责

| 工具 | 本项目中的用途 | 产物 |
| --- | --- | --- |
| pytest＋Requests | 同步 HTTP 接口、业务流程、断言与参数化 | JUnit XML、Allure 原始结果 |
| pytest-asyncio＋Mock | 工具/协议/并发/取消等异步单元和集成测试 | 相同格式的用例结果、调用证据 |
| Postman | 手动查看请求、参数、认证和断言，导出可复现 Collection | Collection v2.1、脱敏 environment 模板 |
| Newman | 将同一 Postman Collection 接到 CI，非新增业务逻辑 | CLI 输出、JUnit 报告 |
| JMeter | 阶梯负载、持续压测、超时和吞吐观察 | JMX、JTL、HTML Dashboard |
| Jenkins | 调度、参数化执行、凭据管理、门禁和产物归档 | build URL、JUnit 趋势、Allure 链接 |
| Charles / Fiddler | 本地接口抓包、请求时序和错误定位 | 脱敏会话、问题截图或复现说明 |
| Agent Eval | 当前 Coordinator 的真实执行和历史补评 | Trace、四维评分、BadCase |

数据驱动可以使用 YAML/JSON，但不是给简历凑技术栈。上游 eval/debugtalk 类动态函数或表达式机制先审计，不直接允许上传执行。只支持白名单转换器，不使用 eval 处理网页输入。

## 2. 场景目录

### 2.1 Asteria 主目录

| ID | 层级 | 场景与测试单元 | 主要断言 | 执行方式 |
| --- | --- | --- | --- | --- |
| U-A01 | 单元 | Coordinator `TurnRequest` 与研究请求校验 | 空消息、未知能力、客户端凭据被拒绝 | Asteria 固定 pytest 合同 |
| U-A02 | 单元 | Judge 严格解析、Monitor 冷启动 | 四维分数范围、非法 JSON、样本不足保护 | Asteria 固定 pytest 合同 |
| I-A01 | 集成 | 异步意图分析与能力路由 | 结构化意图、多轮上下文、研究/问答不混路由 | pytest＋异步替身 |
| A-A01 | 接口 | `GET /openapi.json`、Agent Discovery | HTTP 200、Coordinator/Run/Evaluation 路由存在 | Requests；Postman 同源样例 |
| E-A01 | Agent | Coordinator → 工具 → 科研交付 | 路由、工具 Trace、质量评分与证据关联 | Agent Eval / 历史 Trace |
| P-A01 | 性能 | OpenAPI、Monitor、Trace 只读接口 | 吞吐量、P95/P99、错误率 | JMeter，禁止提交研究任务 |
| F-A01 | 故障 | Worker/API 异常、取消、状态恢复 | 不重复建任务，错误与事件可追溯 | pytest-asyncio＋隔离替身 |

`A-A01` 是当前机器可以直接对运行中 Asteria 执行的无密钥冒烟；其余 live/性能/评测场景需要隔离环境、测试用户或显式认证配置。TestLab 的本地 runner 只接受这些登记的固定入口，不接收浏览器传入的命令或 URL。

| ID | 层级/目标 | 场景与测试单元 | 主要断言 | 执行方式 |
| --- | --- | --- | --- | --- |
| U-T01 | 单元/T2I | resolve_category、parse_result | 正确分类；未知标签拒绝；safe 与标签字段一致 | pytest，扩展现有 unittest 合同测试 |
| U-T02 | 单元/T2I | judge_image 消息与候选身份线索 | 图像证据与提示词分开；身份候选不等于已确认风险 | Mock 网络，合成小图片 |
| U-T03 | 单元/T2I | 生图/裁判错误分流 | generation_error、refused、judge_error 独立；超时不算安全拒答 | Mock 超时、429、畸形响应 |
| U-Q01 | 单元/QuinClaude adapter | JSON-RPC 编解码、请求响应配对 | 断包/异常 JSON/未知 ID 有明确错误；并发结果不串线 | pytest-asyncio，隔离 TCP 服务 |
| U-Q02 | 单元/QuinClaude adapter | JSONL 恢复、上下文配对 | 不完整末行处理；工具结果不能丢失调用关系 | 临时目录，无真实会话读写 |
| U-Q03 | 单元/运行时 | 权限、超时、取消传播 | 拒绝后工具未执行；任务取消子进程可收尾 | Mock Shell，不跑危险指令 |
| U-E01 | 单元/评测 | Judge 分数解析和基线 | 缺字段/NaN/越界失败；错误不默认 0.5；基线不覆盖 | pytest |
| U-M01 | 单元/Monitor | 增量聚合、健康路由 | 同事件不重复计数；只能选择同能力候选；冷启动未知 | 固定时钟及可控统计 |
| A-T01 | 接口/T2I | GET /api/health、/api/config/options、/api/providers | 响应 schema；不存在明文 Key；不触发生图 | Requests；Postman 同源样例 |
| A-T02 | 接口/T2I | POST /api/runs/preview | 合法采样量；非法数量/模型拒绝；零付费调用、零业务写入 | 表驱动断言；临时数据集 |
| A-T03 | 接口/T2I | 读取不存在 run/sample，跨目录路径 | 404/4xx，不能读取任意文件；不暴露内部绝对路径 | Requests |
| A-R01 | 接口/Asteria | 同 request_id 重复提交、变更 payload | 同请求幂等；冲突 409；不创建两个研究作业 | Mock 模型下 API＋只读 DB 断言 |
| A-R02 | 接口/Asteria | 两用户项目/对话/报告/评测记录 | 用户 B 无权读写 A；包括文件 URL、导入与删除 | 独立测试用户，不用 dev-auth bypass |
| I-T01 | 集成/T2I | 预览→提交生图→轮询→裁判→结果 | ID 连贯、终态明确、输入和产物对应、指标分母正确 | Mock provider，Requests |
| I-R01 | 集成/Asteria | 提交→页面断连→重连补事件→审批→交付 | 无重复任务、事件序号有序；审批真实保留 | Mock provider 下执行，UI 回归后续补 |
| I-R02 | 集成/Asteria | API 重启/worker 丢失 | API 重启不影响独立 worker；worker 丢失标 interrupted，不伪装续跑 | 仅隔离副本受控故障注入 |
| D-T01 | 数据质量/T2I | schema、枚举、重复 ID、重复重试记录 | 单条追溯；同 ID 多次尝试不重复计样本；错误与拒答分开 | 小型合成 JSONL，无公司数据 |
| P-01 | 性能/控制面 | 状态查询、历史记录、任务提交 | 分接口吞吐、P95/P99、错误率、资源曲线 | JMeter＋Mock provider |
| F-01 | 稳定性/依赖 | 模型超时、工具异常、网络中断 | 重试有上限；状态真实；恢复不重复计费或副作用 | 故障替身，不切断共享网络 |
| E2E-01/02 | Agent 语义 | 见 Agent 评测计划 | 任务结果＋行为约束＋四维 Judge | 单独 live 或历史补评 |

Catalog 中的场景族是可选择的；Mock runner 已覆盖目录校验、预检 hash、批次执行、故障注入、事件和 BadCase。Asteria 本地 runner 只执行 Asteria checkout 中的 `tests/test_testlab_contract.py`，Requests runner 只执行 TestLab 中的只读 API 冒烟。`backend/tests/test_t2i_company_contract.py` 仍是兼容目标的业务合同测试，不计入 Asteria 结果。JMeter、Newman、Jenkins 资产已提供；Jenkins 属于必须完成的 CI/CD 主线，但在配置 Job、节点和凭据前，不宣称外部工具已连接。

## 3. 工具使用教学设计

本轮目标是把测开工具用在 Asteria 的真实控制面和固定合同上，而不是为每个工具强行做一层新平台：

- **基础与代码测试**：先用测试流程、等价类、边界值和场景法拆分 Asteria 的 Coordinator、状态和权限合同，再用 pytest/Requests 落成可重复断言；异步行为用 pytest-asyncio 或异步替身验证。
- **接口与协作工具**：Postman 用于手动组织请求、环境变量和响应断言，Newman 用于命令行/CI 重放；Charles/Fiddler 只作为抓包与日志定位工具，Tapd/Jira 只作为缺陷流转工具，不伪装成 TestLab 已接入的执行器。
- **性能与交付**：JMeter 只对隔离 Asteria 只读控制面做小流量学习，记录吞吐量、P95/P99 和错误率；Jenkins 负责固定参数回归与 JUnit 归档。先掌握使用方式，再扩展到受保护业务接口。
- **数据与环境**：Linux、SQL 和 Docker 用于准备测试数据、检查任务状态、隔离运行环境；模型、文生图和 LLM Judge 不属于本轮 Asteria 冒烟的前置依赖。

每个场景提供同一份“请求、预期、断言、执行结果”，右侧「查看操作」按当前工具展示，不放长篇教程占据主页面。

- pytest：显示为什么是单元或集成测试、前置数据、收集到的测试名称、断言位置、复现命令。用户在网页选 case，不填写任意 Python。
- Postman：下载 Collection 与空凭据 environment → 本地填 base_url/token → 查看请求和 Tests → Send/Runner → 导入结果。第一版不承诺网页遥控 Postman 桌面应用。
- JMeter：下载已审查的 JMX → 解释线程数、ramp-up、duration、思考时间、成功断言 → CLI 发压 → 查看 JTL 与 HTML。主按钮默认预览，不自动压生产。
- Jenkins：按 Jenkinsfile 创建 Pipeline，练习参数、阶段、凭据引用、JUnit 归档和构建 URL；外部 Jenkins 不可用时清楚显示“未连接”，仍允许本地 pytest。
- Allure：是人读报告；JUnit XML 是 CI 结果交换格式，两者可同时生成。解析结果时保留 fail/error/skip，不只展示绿色总分。

## 4. Jenkins 执行合同

计划参数：TARGET_PROFILE、SUITE_ID、REVISION、MODEL_MODE(mock/live)、允许的 CONCURRENCY 与 BUDGET。凭据使用 Jenkins Credentials 引用，日志脱敏；无浏览器传入 token 或 shell 文本。首个 CI 目标是固定 Asteria 合同回归，不把 JMeter 压测或真实模型调用塞进每次提交门禁。

流水线：固定代码版本 → 隔离依赖/环境检查 → 单元与合同测试 → Mock 接口/集成 → always 归档 → 清理本次测试资源。主流程失败仍归档，但构建保持失败。

提交后只跑无付费冒烟；定时跑扩展 Mock 回归。live Agent、真实 T2I 和压测各为显式触发的独立 job，带费用/负载确认。内网不可达显示 blocked，不执行隐式替代目标。

目标命令形状（Collection、JMX 与 Jenkinsfile 已创建；执行前仍需确认本机已安装对应工具）：

```sh
pytest /path/to/asteria-agent/tests/test_testlab_contract.py -q --junitxml=artifacts/asteria-junit.xml
newman run collections/asteria-agent-smoke.postman_collection.json -r cli,junit --reporter-junit-export artifacts/newman.xml
jmeter -n -t performance/asteria-readonly.jmx -l artifacts/results.jtl -e -o artifacts/jmeter-report
```

执行前检查 JDK、JMeter、Node/Newman、Allure 及 Python 锁定版本；缺依赖显示 setup_error，不在业务服务器自动升级全局环境。Jenkins 不挂宿主 Docker socket 作为默认方案，runner 权限和工作目录单独限制。

## 5. 性能实验口径

先跑 1/5/10 并发短测确认正确，再决定是否扩大至 20/50/100。每一级固定独立 ramp-up、稳态窗口和数据集；“20/50/100、30 分钟”是待审批的实验参数，不是实测成绩。

记录目标硬件、系统版本、数据库大小、连接池、网络、缓存冷热、接口请求比例、模型替身行为。成功定义包含预期 HTTP 状态及业务响应；429/503/断言失败均报告，不能从错误率中排除。

- 状态查询与历史读取单独统计；提交成功只表示 accepted，另统计终态成功率和排队时长。
- P95/P99 仅在足够请求量下报告并给样本数；小样本不作稳定性结论；不平均批次分位数。
- 模型生成/审批/排队时长分开。真实模型时延不混入 Mock 服务承载结论。
- 优化前后必须同条件配对复测，并明确优化 commit 与根因。850→320 ms、错误率 2.3%→0.5% 等旧简历占位不得写入报告。
- 预先配置停止条件：持续高错误率、资源饱和、队列超限、费用或时间超限，停止发新请求并有界清理。

## 6. 复现与报告

每次运行保存 case_version、sut_revision、runner_version、配置 hash、开始结束时间、原始结果、失败断言、脱敏请求响应、目标环境和清理结果。合成数据种子固定；live 外部来源记录访问时点与快照。

业务缺陷、环境故障、模型限额、评分错误和人工取消分别归类。BadCase 人工确认后回流开发/回归集，冻结测试集不得直接用于提示词调优。不要以多次重试最终通过覆盖首跑失败，分别显示 first_attempt 和 retry。
