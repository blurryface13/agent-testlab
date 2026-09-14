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
