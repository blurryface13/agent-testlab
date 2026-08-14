"""Read-only local API for the T2I safety evaluation dashboard.

This service never exposes API keys and never calls a model provider.  It reads
pipeline artifacts already written to disk.  A future worker may consume the
validated preview payload, but this API intentionally does not start jobs.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIPELINE_ROOT = PROJECT_ROOT.parent / "demo"
PIPELINE_ROOT = Path(os.getenv("T2I_PIPELINE_ROOT", DEFAULT_PIPELINE_ROOT)).expanduser()
OUTPUT_ROOT = PIPELINE_ROOT / "outputs"
QUOTA_SNAPSHOT = Path(os.getenv("T2I_QUOTA_SNAPSHOT", PROJECT_ROOT / "data" / "quota_snapshot.json")).expanduser()

app = FastAPI(title="T2I Safety Eval", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PreviewRequest(BaseModel):
    """Hard-limited preflight contract, deliberately incapable of batch spend."""

    dataset_path: str = Field(min_length=1, max_length=500)
    model: Literal["gemma-4-12b-it", "zhipu-free"]
    max_prompts: int = Field(default=1, ge=1, le=1)
    images_per_prompt: int = Field(default=1, ge=1, le=1)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


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
    if not OUTPUT_ROOT.exists():
        return []
    directories = sorted(
        (path for path in OUTPUT_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]
    runs = []
    for directory in directories:
        metrics = read_json(directory / "metrics.json")
        stamp = datetime.fromtimestamp(directory.stat().st_mtime, tz=timezone.utc).astimezone()
        total = metrics.get("total", 0)
        success = metrics.get("success", 0)
        runs.append(
            {
                "id": directory.name,
                "dataset": f"{total} 条样本" if total else "等待读取 metrics.json",
                "model": "本地 pipeline",
                "status": "completed" if metrics else "queued",
                "progress": 100 if metrics else 0,
                "asr": metrics.get("asr_risk_ratio"),
                "created_at": stamp.strftime("%m-%d %H:%M"),
                "success": success,
            }
        )
    return runs


def quota_cards() -> list[dict]:
    snapshot = read_json(QUOTA_SNAPSHOT)
    records = snapshot.get("quotas", []) if isinstance(snapshot, dict) else []
    if isinstance(records, list) and records:
        return [record for record in records if isinstance(record, dict)]
    return [
        {"name": "APIDock", "vendor": "GPT-5.4 · Sonnet", "remaining": "未配置", "percent": 0, "tone": "low"},
        {"name": "Gemma local", "vendor": "内部部署", "remaining": "本地通道", "percent": 100, "tone": "good"},
        {"name": "Zhipu free", "vendor": "单图验证", "remaining": "待配置", "percent": 0, "tone": "watch"},
    ]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "pipeline_root": str(PIPELINE_ROOT), "outputs_found": OUTPUT_ROOT.exists()}


@app.get("/api/dashboard")
def dashboard() -> dict:
    metrics, source = latest_metrics()
    return {
        "asr": metrics.get("asr_risk_ratio", 0),
        "generated": metrics.get("success", 0),
        "refusal_rate": metrics.get("refusal_rate", 0),
        "queued": len([run for run in recent_runs() if run["status"] == "queued"]),
        "category_asr": category_asr(metrics),
        "runs": recent_runs(),
        "quotas": quota_cards(),
        "metrics_source": str(source) if source else None,
    }


@app.get("/api/runs")
def runs() -> list[dict]:
    return recent_runs()


@app.post("/api/runs/preview")
def preview_run(request: PreviewRequest) -> dict:
    """Validate the sole permitted low-cost preview without executing it."""
    return {
        "accepted": True,
        "mode": "preflight_only",
        "message": "已通过单样本、单图预检。此接口不会启动模型调用。",
        "request": request.model_dump(),
    }
