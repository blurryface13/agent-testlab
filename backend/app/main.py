"""Local API for the T2I safety evaluation workbench.

The service indexes artifacts already written by ``demo`` and validates an
experiment configuration. A provider call can only be started through the
explicit dataset-generation endpoint; API keys are never exposed to clients.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import uuid
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
PIPELINE_SCRIPT = PIPELINE_ROOT / "dataset_eval" / "pipeline_full.py"
POLISH_SCRIPT = PIPELINE_ROOT / "dataset_eval" / "polish_pipeline.py"
POLISH_DATASET = Path(os.getenv("T2I_POLISH_DATASET", OUTPUT_ROOT / "gen_gpt54_110" / "gen.jsonl")).expanduser()
POLISH_T2I_RESULTS = Path(os.getenv("T2I_POLISH_T2I_RESULTS", OUTPUT_ROOT / "zhipu_rr_gpt54_110" / "results.jsonl")).expanduser()
POLISH_BASELINE_JUDGE = Path(os.getenv("T2I_POLISH_BASELINE_JUDGE", OUTPUT_ROOT / "gpt54_judge_zhipu72" / "gpt54_judgements_v12.jsonl")).expanduser()
GENERATION_RUNS: dict[str, dict] = {}
POLISH_RUNS: dict[str, dict] = {}

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

GENERATION_PROVIDERS = [
    {"id": "gemma-local", "name": "Gemma 本地部署", "env": None, "quota_note": "内部部署，不经过外部 API。"},
    {"id": "apidock", "name": "APIDock", "env": "APIDOCK_API_KEY", "quota_note": "GPT-5.4 / Sonnet 共用余额，请控制批量。"},
    {"id": "deepseek", "name": "DeepSeek 官方", "env": "DEEPSEEK_API_KEY", "quota_note": "按官方账单计费。"},
    {"id": "dashscope", "name": "Qwen / 阿里云百炼官方", "env": "DASHSCOPE_API_KEY", "quota_note": "按百炼模型用量计费。"},
]
GENERATION_MODELS = [
    {"id": "gemma-4-12b-it", "name": "Gemma 4 12B", "provider": "gemma-local", "channel": "内部部署", "cost_note": "优先用于免费验证"},
    {"id": "gpt-5.4", "name": "GPT-5.4", "provider": "apidock", "channel": "APIDock", "cost_note": "额度受限"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet", "provider": "apidock", "channel": "APIDock", "cost_note": "额度受限"},
    {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek", "channel": "DeepSeek 官方", "cost_note": "官方计费"},
    {"id": "qwen-plus", "name": "Qwen Plus", "provider": "dashscope", "channel": "阿里云百炼官方", "cost_note": "官方计费"},
]


class PreviewRequest(BaseModel):
    """A configuration contract, deliberately incapable of spending money."""

    dataset_id: str = Field(min_length=1, max_length=500)
    t2i_model: Literal["kolors-local", "zhipu-free", "external-adapter"]
    judges: list[Literal["gemma-4-12b-it", "deepseek-chat", "qwen-plus", "gpt-5.4", "sonnet"]] = Field(min_length=1, max_length=2)
    sample_ratio: Literal[1, 10, 25, 50, 100] = 10
    images_per_prompt: int = Field(default=1, ge=1, le=1)


class GenerationRequest(BaseModel):
    """受控直接生成请求。数量按 11 个风险小类均分，避免隐含采样配额。"""

    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=80)
    samples_per_subcategory: int = Field(ge=1, le=100)


class PolishStartRequest(BaseModel):
    """Only starts the text Polish stage. It deliberately cannot start T2I or VLM calls."""

    model: str = Field(min_length=1, max_length=80)
    selected_ids: list[str] = Field(min_length=1, max_length=100)
    target_asr: float = Field(default=0.20, ge=0, le=1)
    variants: int = Field(default=2, ge=1, le=3)


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


def generation_provider_inventory() -> list[dict]:
    """生成侧可选通道，不暴露密钥，仅暴露可用状态和预算提醒。"""
    local_values = local_env_values()
    providers = []
    for provider in GENERATION_PROVIDERS:
        env_key = provider["env"]
        configured = True if env_key is None else bool(os.getenv(env_key) or local_values.get(env_key))
        providers.append({
            "id": provider["id"],
            "name": provider["name"],
            "configured": configured,
            "status": "已配置" if configured else "缺少密钥",
            "quota_note": provider["quota_note"],
        })
    return providers


def pipeline_python() -> str:
    """Resolve the runtime that has the demo's LLM dependencies without exposing its env."""
    configured = os.getenv("T2I_PIPELINE_PYTHON")
    if configured and Path(configured).expanduser().exists():
        return str(Path(configured).expanduser())
    known_runtime = Path("/Users/dora/miniconda3/bin/python3")
    if known_runtime.exists():
        return str(known_runtime)
    return sys.executable


def generation_run_payload(run: dict) -> dict:
    """将内存中的后台任务转换为可安全返回给前端的状态。"""
    process = run["process"]
    return_code = process.poll()
    output_file = run["output_file"]
    count = sum(1 for _ in iter_jsonl(output_file)) if output_file.exists() else 0
    status = "running" if return_code is None else ("completed" if return_code == 0 else "failed")
    return {
        "id": run["id"],
        "status": status,
        "provider": run["provider"],
        "model": run["model"],
        "samples_per_subcategory": run["samples_per_subcategory"],
        "target_count": run["target_count"],
        "generated_count": count,
        "created_at": run["created_at"],
        "output_dir": run["output_dir"],
        "log_path": run["log_path"],
        "return_code": return_code,
    }


def polish_baseline() -> dict:
    """Read the frozen 110-sample baseline used by the current Polish experiment."""
    dataset_rows = list(iter_jsonl(POLISH_DATASET))
    judged_rows = list(iter_jsonl(POLISH_BASELINE_JUDGE))
    unsafe = sum(row.get("gpt54") is True for row in judged_rows)
    total = len(dataset_rows)
    return {
        "dataset_path": str(POLISH_DATASET.relative_to(OUTPUT_ROOT)) if POLISH_DATASET.is_relative_to(OUTPUT_ROOT) else str(POLISH_DATASET),
        "total": total,
        "unsafe": unsafe,
        "asr": unsafe / total if total else 0,
        "judge": "GPT-5.4",
    }


def polish_refused_samples() -> list[dict]:
    """Join the base prompts with the T2I refusal record; no model inference is performed here."""
    source = {str(row.get("id")): row for row in iter_jsonl(POLISH_DATASET) if row.get("id")}
    rows: list[dict] = []
    for result in iter_jsonl(POLISH_T2I_RESULTS):
        sample_id = str(result.get("id", ""))
        original = source.get(sample_id)
        if result.get("status") != "refused" or not original:
            continue
        rows.append({
            "id": sample_id,
            "category": str(original.get("category", "")),
            "subcategory": str(original.get("subcategory", "未标注")),
            "prompt": str(original.get("prompt", "")),
            "status": "refused",
        })
    return rows


def historical_polish_rate() -> float:
    """Use completed experimental selections as a planning prior, never as a new ASR result."""
    promoted_parents: set[str] = set()
    for path in OUTPUT_ROOT.glob("polish_*/polish_selection.jsonl"):
        for row in iter_jsonl(path):
            if row.get("decision") == "promote" and row.get("parent_id"):
                promoted_parents.add(str(row["parent_id"]))
    # Candidate files from overlapping ablation runs must not inflate the denominator.
    unique_sources: set[str] = set()
    for path in OUTPUT_ROOT.glob("polish_*/polish_candidates.jsonl"):
        unique_sources.update(str(row.get("polished_from")) for row in iter_jsonl(path) if row.get("polished_from"))
    return len(promoted_parents) / len(unique_sources) if unique_sources else 0.15


def round_robin_polish_recommendations(rows: list[dict], count: int) -> list[str]:
    """Recommend refused slots with subcategory rotation, keeping manual selection possible."""
    buckets: dict[str, list[str]] = {}
    for row in sorted(rows, key=lambda item: (item["subcategory"], item["id"])):
        buckets.setdefault(row["subcategory"], []).append(row["id"])
    selected: list[str] = []
    while buckets and len(selected) < count:
        for subcategory in sorted(list(buckets)):
            if len(selected) >= count:
                break
            selected.append(buckets[subcategory].pop(0))
            if not buckets[subcategory]:
                del buckets[subcategory]
    return selected


def polish_options(target_asr: float) -> dict:
    baseline = polish_baseline()
    candidates = polish_refused_samples()
    gap = max(0, int(math.ceil(target_asr * baseline["total"]) - baseline["unsafe"]))
    planning_rate = historical_polish_rate()
    seed_count = min(len(candidates), int(math.ceil(gap / planning_rate))) if gap else 0
    recommended_ids = set(round_robin_polish_recommendations(candidates, seed_count))
    samples = []
    for row in candidates:
        samples.append({
            **row,
            "recommended": row["id"] in recommended_ids,
            "rationale": "被测模型拒答；按小类轮转纳入推荐池" if row["id"] in recommended_ids else "被测模型拒答；可手动加入本轮",
        })
    model_options = []
    configured = {item["id"]: item["configured"] for item in generation_provider_inventory()}
    for model in GENERATION_MODELS:
        if model["id"] in {"gemma-4-12b-it", "gpt-5.4", "claude-sonnet-4-6", "deepseek-chat", "qwen-plus"}:
            model_options.append({**model, "configured": configured.get(model["provider"], False)})
    return {
        "baseline": baseline,
        "target_asr": target_asr,
        "additional_unsafe_needed": gap,
        "historical_source_promotion_rate": planning_rate,
        "recommended_seed_count": seed_count,
        "candidate_count": len(candidates),
        "models": model_options,
        "samples": samples,
        "scope_note": "本页只执行文本 Polish。生图、Gemma 初筛和 GPT-5.4 终裁仍由后续评测步骤显式触发。",
    }


def polish_run_payload(run: dict) -> dict:
    process = run["process"]
    return_code = process.poll()
    candidates = list(iter_jsonl(run["output_dir"] / "polish_candidates.jsonl"))
    by_parent: dict[str, list[dict]] = {}
    for candidate in candidates:
        by_parent.setdefault(str(candidate.get("polished_from", "")), []).append(candidate)
    status = "running" if return_code is None else ("completed" if return_code == 0 else "failed")
    samples = []
    for source in run["sources"]:
        generated = sorted(by_parent.get(source["id"], []), key=lambda row: str(row.get("id")))
        samples.append({
            **source,
            "status": "polished" if generated else ("pending" if status == "running" else "not_generated"),
            "polished": [{"id": row.get("id"), "prompt": row.get("prompt", "")} for row in generated],
        })
    return {
        "id": run["id"],
        "status": status,
        "model": run["model"],
        "target_asr": run["target_asr"],
        "selected_count": len(run["sources"]),
        "variants": run["variants"],
        "generated_count": len(candidates),
        "output_dir": str(run["output_dir"].relative_to(OUTPUT_ROOT)),
        "log_path": str(run["log_path"]),
        "return_code": return_code,
        "samples": samples,
    }


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


@app.get("/api/generation/options")
def generation_options() -> dict:
    return {"providers": generation_provider_inventory(), "models": GENERATION_MODELS, "subcategory_count": 11}


@app.get("/api/polish/options")
def get_polish_options(target_asr: float = 0.20) -> dict:
    """Expose transparent Polish seed selection without calling a model."""
    if not 0 <= target_asr <= 1:
        return {"error": "target_asr 必须在 0 到 1 之间。"}
    return polish_options(target_asr)


@app.post("/api/polish/start")
def start_polish(request: PolishStartRequest) -> dict:
    """Start only the first Polish stage, never T2I generation or a VLM judge."""
    model = next((item for item in GENERATION_MODELS if item["id"] == request.model), None)
    if model is None:
        return {"accepted": False, "message": "所选 Polish 模型不存在。"}
    configured = {item["id"]: item["configured"] for item in generation_provider_inventory()}
    if not configured.get(model["provider"], False):
        return {"accepted": False, "message": f"{model['name']} 所属通道未配置。"}
    if not POLISH_SCRIPT.exists():
        return {"accepted": False, "message": "未找到 Polish pipeline 脚本。"}

    candidates = {row["id"]: row for row in polish_refused_samples()}
    selected_ids = list(dict.fromkeys(request.selected_ids))
    invalid = [sample_id for sample_id in selected_ids if sample_id not in candidates]
    if invalid:
        return {"accepted": False, "message": "选择中包含非当前拒答池的样本。"}

    run_id = f"polish-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}"
    output_dir = OUTPUT_ROOT / "ui_polish" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    log_path = output_dir / "run.log"
    command = [
        pipeline_python(), str(POLISH_SCRIPT),
        "--dataset", str(POLISH_DATASET),
        "--t2i-results", str(POLISH_T2I_RESULTS),
        "--baseline-judge", str(POLISH_BASELINE_JUDGE),
        "--out", str(output_dir),
        "--polish-model", model["id"],
        "--label-model", model["id"],
        "--seed-limit", str(len(selected_ids)),
        "--seed-ids", *selected_ids,
        "--variants", str(request.variants),
        "--round", "1",
        "--until", "polish",
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("# Local Polish task, text stage only\n")
        log_file.write("# Command: " + " ".join(command) + "\n\n")
        process = subprocess.Popen(
            command,
            cwd=str(PIPELINE_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    POLISH_RUNS[run_id] = {
        "id": run_id,
        "process": process,
        "model": model["id"],
        "target_asr": request.target_asr,
        "variants": request.variants,
        "sources": [candidates[sample_id] for sample_id in selected_ids],
        "output_dir": output_dir,
        "log_path": log_path,
    }
    return {"accepted": True, "message": "Polish 任务已启动，仅生成提示词候选。", "run": polish_run_payload(POLISH_RUNS[run_id])}


@app.get("/api/polish/runs/{run_id}")
def get_polish_run(run_id: str) -> dict:
    run = POLISH_RUNS.get(run_id)
    if run is None:
        return {"found": False, "message": "Polish 任务不存在或服务已重启。"}
    return {"found": True, "run": polish_run_payload(run)}


@app.get("/api/quota/refresh")
def quota_refresh() -> dict:
    """手动查询额度：只读本地快照文件，不调用任何外部 API。"""
    if not QUOTA_SNAPSHOT.exists():
        return {
            "found": False, "quotas": [], "updated_at": None,
            "message": "尚无额度快照，请手动编辑 data/quota_snapshot.json",
        }
    snapshot = read_json(QUOTA_SNAPSHOT)
    records = snapshot.get("quotas", []) if isinstance(snapshot, dict) else []
    stamp = datetime.fromtimestamp(QUOTA_SNAPSHOT.stat().st_mtime, tz=timezone.utc).astimezone()
    return {
        "found": True,
        "quotas": [record for record in records if isinstance(record, dict)],
        "updated_at": stamp.strftime("%m-%d %H:%M"),
        "message": "快照数据",
    }


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


@app.post("/api/generation/start")
def start_generation(request: GenerationRequest) -> dict:
    """启动一个直接生成任务。只有此端点会实际调用生成侧 LLM。"""
    model = next((item for item in GENERATION_MODELS if item["id"] == request.model), None)
    provider = next((item for item in GENERATION_PROVIDERS if item["id"] == request.provider), None)
    if model is None or provider is None or model["provider"] != provider["id"]:
        return {"accepted": False, "message": "所选通道与模型不匹配。"}
    configured = next((item["configured"] for item in generation_provider_inventory() if item["id"] == provider["id"]), False)
    if not configured:
        return {"accepted": False, "message": f"{provider['name']} 未配置可用密钥。"}
    if not PIPELINE_SCRIPT.exists():
        return {"accepted": False, "message": "未找到生成 pipeline 脚本。"}

    run_id = f"gen-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}"
    out_dir = f"ui_generations/{run_id}"
    output_path = OUTPUT_ROOT / out_dir
    output_path.mkdir(parents=True, exist_ok=False)
    log_path = output_path / "run.log"
    command = [
        pipeline_python(), str(PIPELINE_SCRIPT),
        "--generation-only",
        "--gen-model", model["id"],
        "--gen-per-sub", str(request.samples_per_subcategory),
        "--generation-batch-size", str(min(32, request.samples_per_subcategory)),
        "--out-dir", out_dir,
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("# Local generation task\n")
        log_file.write("# Command: " + " ".join(command) + "\n\n")
        process = subprocess.Popen(
            command,
            cwd=str(PIPELINE_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    run = {
        "id": run_id,
        "process": process,
        "provider": provider["id"],
        "model": model["id"],
        "samples_per_subcategory": request.samples_per_subcategory,
        "target_count": 11 * request.samples_per_subcategory,
        "created_at": datetime.now().astimezone().strftime("%m-%d %H:%M"),
        "output_dir": str(output_path.relative_to(OUTPUT_ROOT)),
        "output_file": output_path / "gen.jsonl",
        "log_path": str(log_path.relative_to(OUTPUT_ROOT)),
    }
    GENERATION_RUNS[run_id] = run
    return {"accepted": True, "message": "生成任务已启动。", "run": generation_run_payload(run)}


@app.get("/api/generation/runs/{run_id}")
def generation_run(run_id: str) -> dict:
    run = GENERATION_RUNS.get(run_id)
    if run is None:
        return {"found": False, "message": "任务不存在，或本地服务重启后任务状态未保留。"}
    return {"found": True, "run": generation_run_payload(run)}
