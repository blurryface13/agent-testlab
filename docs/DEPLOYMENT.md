# Agent TestLab 部署说明

更新时间：2026-09-15 · Codex（GPT-5）

这份配置面向 Windows + Docker Desktop，也适合个人 4060 主机先在本地运行。控制台默认使用 Mock 测试，不会自动调用外部模型、不需要 GPU；真实 T2I/VLM 服务可以继续放在内网服务器或另一台机器上，通过受控环境配置接入。

## 1. 推荐拓扑

```text
浏览器 :4173
    │
    ▼
Nginx 前端 ── /api ──► FastAPI TestLab :8010 ──► JSON 文件卷（事实源）
                                  │
                                  ├─► Redis（可选加速、事件镜像）
                                  └─► pytest / 受控适配器
```

Redis 不是唯一数据库。即使 Redis 不可用，运行记录仍写入 `testlab-data` 卷；Prometheus 指标在依赖存在时由 `/api/testing/metrics` 提供。

## 2. Windows Docker Desktop

在 PowerShell 中进入项目根目录，执行：

```powershell
docker compose build
docker compose up -d
```

然后打开 <http://127.0.0.1:4173>。确认状态：

```powershell
docker compose ps
curl http://127.0.0.1:8010/api/testing/health
```

停止服务但保留数据：

```powershell
docker compose stop
```

重新启动：

```powershell
docker compose start
```

只有在明确需要清理所有本地运行记录时才执行 `docker compose down -v`；这会删除 Docker 卷中的 TestLab 结果和 Redis 镜像数据。

## 3. 4060 与内网模型

第一阶段不要求 Docker 使用 4060：TestLab 负责控制、执行和记录，模型可以是 Mock、内网 vLLM，或另一台服务器的受控 API。这样不会把测试控制面和模型权重绑死在同一个容器里。

若要接入现有 T2I pipeline：

1. 把 pipeline 放在部署机的项目目录或明确的共享路径中；
2. 在未提交的 `.env` 中设置 `T2I_PIPELINE_ROOT`；
3. 按实际路径为 `api` 增加只读 volume 映射；
4. 先用 `/api/testing/runs/preview` 检查目标、用例、工具和费用，再从页面显式启动；
5. 真实模型调用和 JMeter 压测不要在 `docker compose up` 时隐式触发。

不要把 API Key 写进 Dockerfile、镜像层、前端代码或 Git。真实凭据只通过部署机的环境变量/未提交配置注入。

## 4. 内网服务器

内网服务器更适合作为被测模型或评测服务，不建议直接暴露 TestLab 控制台。可采用：

- 个人 PC：运行 TestLab、Mock 回归、报告与前端；
- 内网服务器：运行 vLLM/T2I/VLM，通过固定地址提供受控接口；
- AutoDL：仅在需要临时 GPU 实验时启动，完成后停止并回收资源。

若 PC 无法访问内网地址，页面应显示 `blocked`/不可达，不自动切换到另一个目标冒充通过。压测由与被测服务网络相邻的机器发起，避免把 PC 到内网的网络延迟误当成服务性能。

## 5. 健康检查与故障排查

- 前端打不开：`docker compose logs frontend`，确认 4173 端口未被占用；
- API 不健康：`docker compose logs api`，确认 requirements 安装完成；
- Redis 不可用：检查 `docker compose ps redis`。这不会让 JSON 运行记录丢失；
- 运行结果消失：确认 `testlab-data` 卷仍在，未执行 `down -v`；
- 真实 T2I 失败：先检查 pipeline 路径、模型服务网络和凭据，再区分 provider error、judge error 与测试断言失败；
- Windows 上构建慢：把仓库放在 Docker Desktop 文件共享性能较好的位置，避免把 `node_modules`、模型权重或输出目录纳入构建上下文。

## 6. 当前明确边界

本配置已经提供可用的完整控制面、目录、Mock 执行、运行事件、取消、BadCase、Redis 镜像和 Prometheus 指标；Jenkins、Postman/Newman 和 JMeter 仍以注册工具/导出适配为边界，未在容器启动时伪造外部工具已经连接。真实科研 Agent 的 Monitor/Judge 仍应通过 Asteria 的受控评测接口接入，不把 TestLab 的 Mock 分数当作科研效果。
