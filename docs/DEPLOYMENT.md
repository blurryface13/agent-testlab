# Agent TestLab 部署说明

更新时间：2026-09-15 · Codex（GPT-5）

这份配置面向 Windows + Docker Desktop，也适合个人 4060 主机先在本地运行。Asteria Research Agent 是本轮主测试对象；控制台默认使用 Mock，不会自动提交研究任务、不需要 GPU。真实 Asteria API 可以继续在本机、内网服务器或另一台机器上运行，通过受控环境配置接入。

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

## 3. Asteria 主测试对象

TestLab 不复制 Asteria 源码、不写 Asteria 业务数据库。两种接入方式分别对应两类测试：

| 模式 | 配置 | 用途 | 是否需要模型密钥 |
| --- | --- | --- | --- |
| 本地合同 | `ASTERIA_PROJECT_ROOT`、可选 `ASTERIA_PYTHON` | 在 Asteria checkout 中运行固定 pytest 合同测试 | 否，不启动研究任务 |
| 只读 API | `ASTERIA_BASE_URL`，默认 `http://127.0.0.1:8018` | Requests、Postman 检查 OpenAPI 与 Agent Discovery | 否，不访问受保护写接口 |

在 TestLab 根目录复制 `backend/.env.example` 为本地配置并按机器修改。Windows 示例：

```powershell
$env:ASTERIA_PROJECT_ROOT = 'D:\work\asteria-agent'
$env:ASTERIA_PYTHON = 'D:\miniconda\envs\asteria\python.exe'
$env:ASTERIA_BASE_URL = 'http://127.0.0.1:8018'
```

Asteria 的 API 若运行在另一台内网机器，只填固定的 `ASTERIA_BASE_URL`；不要把 token 写进 Collection、JMeter 文件或前端。当前无密钥冒烟不覆盖需要登录的 `/api/evaluation/*` 业务调用；需要认证时由后续独立的受控环境注入。

## 4. 4060 与内网模型

第一阶段不要求 Docker 使用 4060：TestLab 负责控制、执行和记录，Asteria 可以是本机 API、内网部署或 Mock。这样不会把测试控制面和科研模型权重绑死在同一个容器里。

若要继续使用现有 T2I pipeline（兼容目标）：

1. 把 pipeline 放在部署机的项目目录或明确的共享路径中；
2. 在未提交的 `.env` 中设置 `T2I_PIPELINE_ROOT`；
3. 按实际路径为 `api` 增加只读 volume 映射；
4. 先用 `/api/testing/runs/preview` 检查目标、用例、工具和费用，再从页面显式启动；
5. 真实模型调用和 JMeter 压测不要在 `docker compose up` 时隐式触发。

不要把 API Key 写进 Dockerfile、镜像层、前端代码或 Git。真实凭据只通过部署机的环境变量/未提交配置注入。

## 5. 内网服务器

内网服务器更适合作为被测模型或评测服务，不建议直接暴露 TestLab 控制台。可采用：

- 个人 PC：运行 TestLab、Mock 回归、报告与前端；
- 内网服务器：运行 Asteria、vLLM 或其他被测服务，通过固定地址提供受控接口；
- AutoDL：仅在需要临时 GPU 实验时启动，完成后停止并回收资源。

若 PC 无法访问内网地址，页面应显示 `blocked`/不可达，不自动切换到另一个目标冒充通过。压测由与被测服务网络相邻的机器发起，避免把 PC 到内网的网络延迟误当成服务性能。

## 6. 健康检查与故障排查

- 前端打不开：`docker compose logs frontend`，确认 4173 端口未被占用；
- API 不健康：`docker compose logs api`，确认 requirements 安装完成；
- Redis 不可用：检查 `docker compose ps redis`。这不会让 JSON 运行记录丢失；
- 运行结果消失：确认 `testlab-data` 卷仍在，未执行 `down -v`；
- Asteria API 冒烟失败：先检查 `ASTERIA_BASE_URL`、8018 端口和 OpenAPI，再区分网络不可达、服务路由未部署与测试断言失败；
- Asteria 合同测试未启动：检查 `ASTERIA_PROJECT_ROOT` 是否包含 `backend/` 和 `tests/test_testlab_contract.py`，以及 `ASTERIA_PYTHON` 是否安装项目依赖；
- Windows 上构建慢：把仓库放在 Docker Desktop 文件共享性能较好的位置，避免把 `node_modules`、模型权重或输出目录纳入构建上下文。

## 7. 当前明确边界

本配置已经提供可用的完整控制面、Asteria 目标目录、Mock 执行、注册 pytest/Requests 执行、运行事件、取消、BadCase、Redis 镜像和 Prometheus 指标；Jenkins、Postman/Newman 和 JMeter 以注册资产/导出适配为边界，未在容器启动时伪造外部工具已经连接。真实科研 Agent 的 Monitor/Judge 仍通过 Asteria 的受控评测接口接入，不把 TestLab 的 Mock 分数当作科研效果。
