"""Local API for the T2I safety evaluation workbench.

The service indexes artifacts already written by ``demo`` and validates an
experiment configuration. It never exposes API keys or starts a provider call.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIPELINE_ROOT = PROJECT_ROOT.parent / "demo"
PIPELINE_ROOT = Path(os.getenv("T2I_PIPELINE_ROOT", DEFAULT_PIPELINE_ROOT)).expanduser()
OUTPUT_ROOT = PIPELINE_ROOT / "outputs"
QUOTA_SNAPSHOT = Path(os.getenv("T2I_QUOTA_SNAPSHOT", PROJECT_ROOT / "data" / "quota_snapshot.json")).expanduser()
PIPELINE_ENV = PIPELINE_ROOT / ".env"

app = FastAPI(title="T2I Safety Eval", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173", "http://localhost:4173",
        "http://127.0.0.1:5173", "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


T2I_MODELS = [
    {"id": "kolors-local", "name": "Kolors / 本地 SD", "channel": "本地部署", "mode": "实验目标"},
    {"id": "zhipu-free", "name": "Zhipu Image", "channel": "免费单图验证", "mode": "低成本验证"},
    {"id": "external-adapter", "name": "外部 Adapter", "channel": "需在正式 worker 配置", "mode": "仅配置"},
]
JUDGE_MODELS = [
    {"id": "gemma-4-12b-it", "name": "Gemma 4 12B", "channel": "内部部署"},
    {"id": "deepseek-chat", "name": "DeepSeek Chat", "channel": "DeepSeek 官方"},
    {"id": "qwen-plus", "name": "Qwen Plus", "channel": "阿里云百炼官方"},
    {"id": "gpt-5.4", "name": "GPT-5.4", "channel": "APIDock，额度受限"},
    {"id": "sonnet", "name": "Claude Sonnet", "channel": "APIDock，额度受限"},
]
PROVIDERS = [
    {
        "id": "apidock", "name": "APIDock", "env": "APIDOCK_API_KEY",
        "base_url": "https://apidock.ai/v1", "models": ["gpt-5.4", "Claude Sonnet"],
        "quota_mode": "manual_snapshot", "quota_note": "请从 APIDock 控制台同步余额。",
    },
    {
        "id": "deepseek", "name": "DeepSeek 官方", "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com", "models": ["deepseek-chat"],
        "quota_mode": "console_usage", "quota_note": "余额与按 Key 用量由 DeepSeek Billing/Usage 页面提供。",
    },
    {
        "id": "dashscope", "name": "Qwen / 阿里云百炼官方", "env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-plus"],
        "quota_mode": "console_usage", "quota_note": "用量由百炼模型监控与阿里云账单侧同步。",
    },
]


class PreviewRequest(BaseModel):
    """A configuration contract, deliberately incapable of spending money."""

    dataset_id: str = Field(min_length=1, max_length=500)
    t2i_model: Literal["kolors-local", "zhipu-free", "external-adapter"]
    judges: list[Literal["gemma-4-12b-it", "deepseek-chat", "qwen-plus", "gpt-5.4", "sonnet"]] = Field(min_length=1, max_length=2)
    sample_ratio: Literal[1, 10, 25, 50, 100] = 10
    images_per_prompt: int = Field(default=1, ge=1, le=1)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def local_env_values() -> dict[str, str]:
    """Read only the sibling pipeline's local environment file, never expose values."""
    values: dict[str, str] = {}
    try:
        for raw_line in PIPELINE_ENV.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def provider_inventory() -> list[dict]:
    """Return safe provider metadata. API keys remain in process memory only."""
    local_values = local_env_values()
    providers = []
    for provider in PROVIDERS:
        configured = bool(os.getenv(provider["env"]) or local_values.get(provider["env"]))
        providers.append(
            {
                "id": provider["id"],
                "name": provider["name"],
                "base_url": provider["base_url"],
                "models": provider["models"],
                "configured": configured,
                "status": "已配置" if configured else "缺少密钥",
                "quota_mode": provider["quota_mode"],
                "quota_note": provider["quota_note"],
            }
        )
    return providers


def iter_jsonl(path: Path):
    """Yield valid JSON objects only; experimental artifacts may contain partial lines."""
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    yield value
    except OSError:
        return


def artifact_id(path: Path) -> str:
    return path.relative_to(OUTPUT_ROOT).as_posix()


def dataset_inventory() -> list[dict]:
    """Discover generation artifacts without treating judge output as a dataset."""
    if not OUTPUT_ROOT.exists():
        return []
    candidates = sorted(
        (path for path in OUTPUT_ROOT.rglob("*.jsonl") if path.name in {"generated.jsonl", "gen.jsonl"}),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    datasets = []
    for path in candidates:
        categories: Counter[str] = Counter()
        sources: Counter[str] = Counter()
        count = 0
        for record in iter_jsonl(path):
            count += 1
            category = str(record.get("subcategory") or record.get("gpt_cat") or record.get("category") or "未标注")
            categories[category] += 1
            source = str(record.get("source") or "未知来源")
            sources[source] += 1
        if not count:
            continue
        stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).astimezone()
        datasets.append(
            {
                "id": artifact_id(path),
                "name": path.parent.name,
                "path": artifact_id(path),
                "count": count,
                "categories": dict(categories.most_common()),
                "sources": list(sources),
                "updated_at": stamp.strftime("%m-%d %H:%M"),
            }
        )
    return datasets


def validation_summaries() -> list[dict]:
    """Read prior text-label validation summaries as evidence, not as T2I ASR."""
    if not OUTPUT_ROOT.exists():
        return []
    summaries = []
    for path in sorted(OUTPUT_ROOT.rglob("summary.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        payload = read_json(path)
        judges = payload.get("judges")
        if not isinstance(judges, dict):
            continue
        for judge, record in judges.items():
            if not isinstance(record, dict):
                continue
            total = record.get("total", 0)
            matched = record.get("matched", 0)
            if not total:
                continue
            stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).astimezone()
            summaries.append(
                {
                    "id": f"{path.parent.name}:{judge}",
                    "dataset": path.parent.name,
                    "model": str(judge),
                    "status": "completed",
                    "progress": 100,
                    "match_rate": round(float(matched) / float(total), 4),
                    "matched": matched,
                    "total": total,
                    "created_at": stamp.strftime("%m-%d %H:%M"),
                }
            )
    return summaries


def find_dataset(dataset_id: str) -> dict | None:
    return next((item for item in dataset_inventory() if item["id"] == dataset_id), None)


def latest_metrics() -> tuple[dict, Path | None]:
    if not OUTPUT_ROOT.exists():
        return {}, None
    candidates = sorted(OUTPUT_ROOT.rglob("metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {}, None
    return read_json(candidates[0]), candidates[0]


def percent(value: object) -> int:
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


def category_asr(metrics: dict) -> list[dict]:
    colors = ["#3d7cf1", "#8972df", "#24b7aa", "#efac45", "#e5667e"]
    values = metrics.get("by_subcategory") or metrics.get("by_category") or {}
    if not isinstance(values, dict):
        return []
    result = []
    for index, (name, record) in enumerate(values.items()):
        if not isinstance(record, dict):
            continue
        result.append({"name": name, "value": percent(record.get("asr")), "color": colors[index % len(colors)]})
    return result


def recent_runs(limit: int = 5) -> list[dict]:
    return validation_summaries()[:limit]


def quota_cards() -> list[dict]:
    snapshot = read_json(QUOTA_SNAPSHOT)
    records = snapshot.get("quotas", []) if isinstance(snapshot, dict) else []
    if isinstance(records, list) and records:
        return [record for record in records if isinstance(record, dict)]
    configured = {provider["id"]: provider["configured"] for provider in provider_inventory()}
    return [
        {"name": "APIDock", "vendor": "GPT-5.4 · Sonnet", "remaining": "待同步" if configured["apidock"] else "未配置", "percent": 0, "tone": "watch" if configured["apidock"] else "low", "provider": "apidock"},
        {"name": "DeepSeek 官方", "vendor": "deepseek-chat", "remaining": "账单侧同步" if configured["deepseek"] else "未配置", "percent": 0, "tone": "watch" if configured["deepseek"] else "low", "provider": "deepseek"},
        {"name": "Qwen 官方", "vendor": "qwen-plus · 百炼", "remaining": "账单侧同步" if configured["dashscope"] else "未配置", "percent": 0, "tone": "watch" if configured["dashscope"] else "low", "provider": "dashscope"},
    ]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "pipeline_root": str(PIPELINE_ROOT), "outputs_found": OUTPUT_ROOT.exists()}


@app.get("/api/dashboard")
def dashboard() -> dict:
    metrics, source = latest_metrics()
    datasets = dataset_inventory()
    coverage: Counter[str] = Counter()
    for dataset in datasets:
        coverage.update(dataset["categories"])
    validations = validation_summaries()
    latest_validation = validations[0] if validations else None
    return {
        "asr": metrics.get("asr_risk_ratio", 0),
        "generated": metrics.get("success", 0),
        "refusal_rate": metrics.get("refusal_rate", 0),
        "dataset_count": len(datasets),
        "sample_count": sum(item["count"] for item in datasets),
        "latest_validation_rate": latest_validation.get("match_rate", 0) if latest_validation else 0,
        "queued": 0,
        "category_asr": category_asr(metrics),
        "category_coverage": [{"name": name, "value": value} for name, value in coverage.most_common()],
        "datasets": datasets,
        "runs": recent_runs(),
        "quotas": quota_cards(),
        "metrics_source": str(source) if source else None,
    }


@app.get("/api/runs")
def runs() -> list[dict]:
    return recent_runs()


@app.get("/api/datasets")
def datasets() -> list[dict]:
    return dataset_inventory()


@app.get("/api/config/options")
def config_options() -> dict:
    return {"t2i_models": T2I_MODELS, "judge_models": JUDGE_MODELS, "sample_ratios": [1, 10, 25, 50, 100]}


@app.get("/api/providers")
def providers() -> dict:
    """Expose configuration state and quota source, never a secret or fake balance."""
    return {"providers": provider_inventory(), "quotas": quota_cards(), "updated_at": datetime.now().astimezone().strftime("%m-%d %H:%M")}


@app.post("/api/runs/preview")
def preview_run(request: PreviewRequest) -> dict:
    """Validate a local run sheet without executing it."""
    dataset = find_dataset(request.dataset_id)
    if dataset is None:
        return {"accepted": False, "message": "数据集不存在或不属于本地 demo 输出目录。"}
    selected = max(1, round(dataset["count"] * request.sample_ratio / 100))
    return {
        "accepted": True,
        "mode": "preflight_only",
        "message": "已生成本地运行单。此接口不会启动模型调用或读取密钥。",
        "selection": {
            **request.model_dump(),
            "dataset_name": dataset["name"],
            "dataset_count": dataset["count"],
            "selected_prompts": selected,
            "estimated_images": selected * request.images_per_prompt,
        },
    }
