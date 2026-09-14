"""A small, explicit catalog of executable test scenarios.

The catalog is intentionally data driven. The browser can select a case, but
it cannot submit an arbitrary command, script path, URL, or provider.
"""
from __future__ import annotations

from copy import deepcopy

TARGETS = [
    {
        "id": "t2i-safety",
        "name": "T2I Safety",
        "description": "文生图生成、图像裁判与数据质量链路",
        "status": "local",
        "default_mode": "mock",
    },
    {
        "id": "asteria-agent",
        "name": "Asteria Research Agent",
        "description": "科研 Agent 的 Coordinator、任务执行与评测链路",
        "status": "adapter_pending",
        "default_mode": "mock",
    },
    {
        "id": "quinclaude-runtime",
        "name": "QuinClaude Runtime",
        "description": "本地 Agent Runtime 的异步通信、权限和上下文管理",
        "status": "adapter_pending",
        "default_mode": "mock",
    },
]

TOOLS = [
    {
        "id": "pytest",
        "name": "pytest",
        "kind": "unit",
        "status": "ready",
        "description": "源码单元测试与断言回归",
        "guide": ["准备隔离测试数据", "执行注册的 pytest 用例", "查看 JUnit/Allure 结果与失败日志"],
    },
    {
        "id": "pytest-asyncio",
        "name": "pytest-asyncio",
        "kind": "integration",
        "status": "ready",
        "description": "异步任务、事件和取消行为验证",
        "guide": ["启动 Mock provider", "执行异步场景集", "检查事件顺序、超时和取消传播"],
    },
    {
        "id": "requests",
        "name": "Requests",
        "kind": "api",
        "status": "ready",
        "description": "HTTP 接口请求、参数提取与响应断言",
        "guide": ["选择目标环境", "执行受控接口用例", "按状态码、JSON 和数据库状态交叉断言"],
    },
    {
        "id": "postman",
        "name": "Postman / Newman",
        "kind": "api",
        "status": "export",
        "description": "接口调试、Collection 导出与 CI 执行",
        "guide": ["下载无密钥 Collection", "在 Postman 配置本地环境", "用 Newman 导出机器可读结果"],
        "asset": "postman",
    },
    {
        "id": "jmeter",
        "name": "JMeter",
        "kind": "performance",
        "status": "export",
        "description": "控制面接口的阶梯负载与持续压测",
        "guide": ["先使用 Mock provider", "逐级增加并发并观察错误率", "查看 P95/P99、吞吐量和资源曲线"],
        "asset": "jmeter",
    },
    {
        "id": "jenkins",
        "name": "Jenkins",
        "kind": "ci",
        "status": "planned",
        "description": "提交后冒烟、定时回归与报告归档",
        "guide": ["选择已登记的 Job", "使用固定参数触发构建", "归档 JUnit/Allure 与脱敏日志"],
        "asset": "jenkins",
    },
    {
        "id": "agent-eval",
        "name": "AgentEval / LLM-as-Judge",
        "kind": "agent",
        "status": "adapter",
        "description": "结构化 Trace、行为检查和四维质量评分",
        "guide": ["先运行 Coordinator 或导入历史 Trace", "检查工具与状态断言", "查看相关性、准确性、完整性和帮助性"],
    },
]

CASES = [
    {
        "id": "U-T01",
        "name": "安全评测输入合同",
        "target": "t2i-safety",
        "level": "unit",
        "tools": ["pytest"],
        "scope": "数据与参数",
        "precondition": "合成样本，不调用模型",
        "assertions": ["必需字段完整", "风险类别属于冻结集合", "无效输入被拒绝"],
        "description": "检查数据集行、类别和裁判请求的输入合同。",
    },
    {
        "id": "U-T02",
        "name": "图像裁判消息与身份线索",
        "target": "t2i-safety",
        "level": "unit",
        "tools": ["pytest"],
        "scope": "裁判消息",
        "precondition": "Mock VLM 与合成图片",
        "assertions": ["image 在 text 前发送", "候选身份不自动等于风险", "输出标签受体系约束"],
        "description": "验证图像证据、提示词上下文和身份候选线索的边界。",
    },
    {
        "id": "A-T01",
        "name": "服务健康与配置脱敏",
        "target": "t2i-safety",
        "level": "api",
        "tools": ["requests", "postman"],
        "scope": "GET /api/health、/api/providers",
        "precondition": "本地服务已启动",
        "assertions": ["HTTP 200", "不返回 API Key", "provider 状态可读"],
        "description": "只读检查服务、通道和敏感配置展示。",
    },
    {
        "id": "A-T02",
        "name": "运行预览零副作用",
        "target": "t2i-safety",
        "level": "api",
        "tools": ["requests", "postman"],
        "scope": "POST /api/testing/runs/preview",
        "precondition": "Mock 模式与注册用例",
        "assertions": ["返回预览摘要", "不启动模型", "不写入业务产物"],
        "description": "确认用户明确开始前，预览只做配置和权限校验。",
    },
    {
        "id": "I-T01",
        "name": "T2I 生成到裁判链路",
        "target": "t2i-safety",
        "level": "integration",
        "tools": ["pytest-asyncio", "requests"],
        "scope": "数据集 → 生图 → 裁判 → 结果",
        "precondition": "Mock generation provider 与 Mock VLM",
        "assertions": ["样本 ID 连贯", "generation_error 与 judge_error 分离", "结果分母正确"],
        "description": "以替身服务验证完整 T2I 测评链路。",
    },
    {
        "id": "I-R01",
        "name": "任务断连与恢复",
        "target": "quinclaude-runtime",
        "level": "integration",
        "tools": ["pytest-asyncio"],
        "scope": "JSON-RPC + EventBus",
        "precondition": "隔离 Runtime mock",
        "assertions": ["断连不丢后台任务", "事件序号可续传", "取消可传播"],
        "description": "验证前端离开后任务、事件和重连状态的一致性。",
    },
    {
        "id": "I-R02",
        "name": "科研任务状态一致性",
        "target": "asteria-agent",
        "level": "integration",
        "tools": ["pytest-asyncio", "agent-eval"],
        "scope": "Coordinator → Run → Event → Artifact",
        "precondition": "Mock Coordinator adapter",
        "assertions": ["重复提交幂等", "人工等待不算工具失败", "报告和事件可追溯"],
        "description": "检查科研任务的持久运行状态和评测边界。",
    },
    {
        "id": "E-R01",
        "name": "科研 Agent 行为回归",
        "target": "asteria-agent",
        "level": "agent",
        "tools": ["agent-eval"],
        "scope": "意图、工具、状态和交付",
        "precondition": "两组固定评测指令或历史 Trace",
        "assertions": ["路由正确", "工具选择有依据", "四维质量均分可追溯"],
        "description": "调用真实 Coordinator 或历史 Trace，形成 Agent 行为回归记录。",
    },
    {
        "id": "P-T01",
        "name": "控制面阶梯负载",
        "target": "t2i-safety",
        "level": "performance",
        "tools": ["jmeter"],
        "scope": "提交、状态、历史接口",
        "precondition": "Mock provider，独立测试数据",
        "assertions": ["吞吐量可记录", "P95/P99 可记录", "错误按接口分类"],
        "description": "不调用真实模型，验证控制面接口在阶梯负载下的行为。",
    },
    {
        "id": "F-R01",
        "name": "模型超时与工具异常恢复",
        "target": "asteria-agent",
        "level": "fault",
        "tools": ["pytest-asyncio", "agent-eval"],
        "scope": "超时、异常、重试和取消",
        "precondition": "故障注入 provider",
        "assertions": ["错误分类准确", "不重复创建任务", "恢复后状态可继续读取"],
        "description": "用受控故障替身验证 Agent 的异常兜底。",
    },
]


def _tool_index() -> dict[str, dict]:
    return {item["id"]: item for item in TOOLS}


def list_catalog(*, target: str | None = None, level: str | None = None, tool: str | None = None) -> list[dict]:
    tools = _tool_index()
    items = []
    for case in CASES:
        if target and case["target"] != target:
            continue
        if level and case["level"] != level:
            continue
        if tool and tool not in case["tools"]:
            continue
        item = deepcopy(case)
        item["tool_details"] = [tools[name] for name in case["tools"] if name in tools]
        items.append(item)
    return items


def get_case(case_id: str) -> dict | None:
    for case in CASES:
        if case["id"] == case_id:
            item = deepcopy(case)
            item["tool_details"] = [_tool_index()[name] for name in case["tools"]]
            return item
    return None
