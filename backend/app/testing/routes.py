"""FastAPI endpoints for the controlled testing workbench."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .catalog import TARGETS, TOOLS, list_catalog
from .runner import badcases, cancel, compute_preview_hash, events, get_run, list_runs, preview, start
from .observability import metrics_text, redis_status

router = APIRouter(prefix="/api/testing", tags=["testing workbench"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSETS = {
    "postman": PROJECT_ROOT / "collections" / "agent-testlab-smoke.postman_collection.json",
    "postman-environment": PROJECT_ROOT / "collections" / "local.postman_environment.json",
    "jmeter": PROJECT_ROOT / "performance" / "control-plane.jmx",
    "jenkins": PROJECT_ROOT / "Jenkinsfile",
}


class PreviewRequest(BaseModel):
    target: str = Field(min_length=1, max_length=80)
    case_ids: list[str] = Field(min_length=1, max_length=30)
    tool: str = Field(min_length=1, max_length=40)
    mode: Literal["mock", "local"] = "mock"
    fault_mode: Literal["none", "timeout", "tool_error", "contract"] = "none"


class StartRequest(PreviewRequest):
    preview_hash: str | None = Field(default=None, max_length=128)


@router.get("/catalog")
def catalog(target: str | None = None, level: str | None = None, tool: str | None = None):
    return {"cases": list_catalog(target=target, level=level, tool=tool), "targets": TARGETS, "tools": TOOLS}


@router.get("/targets")
def targets():
    return {"targets": TARGETS}


@router.get("/tools")
def tools():
    return {"tools": TOOLS}


@router.get("/assets/{asset_key}")
def asset(asset_key: str):
    path = ASSETS.get(asset_key)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="工具资产不存在")
    return FileResponse(path, filename=path.name)


@router.post("/runs/preview")
def run_preview(request: PreviewRequest):
    result = preview(**request.model_dump())
    if result["accepted"]:
        result["preview_hash"] = compute_preview_hash(result)
    return result


@router.post("/runs")
def create_run(request: StartRequest):
    result = start(**request.model_dump())
    if not result["accepted"]:
        return result
    return result


@router.get("/runs")
def runs(limit: int = Query(default=50, ge=1, le=200)):
    return {"runs": list_runs(limit)}


@router.get("/runs/{run_id}")
def run(run_id: str):
    found = get_run(run_id)
    if not found:
        raise HTTPException(status_code=404, detail="测试运行不存在")
    return found


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, after: int = Query(default=0, ge=0)):
    found = events(run_id, after)
    if found is None:
        raise HTTPException(status_code=404, detail="测试运行不存在")
    return {"events": found, "after": after, "next": found[-1]["sequence"] if found else after}


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    found = cancel(run_id)
    if not found:
        raise HTTPException(status_code=404, detail="测试运行不存在")
    return found


@router.get("/badcases")
def list_badcases(limit: int = Query(default=50, ge=1, le=200)):
    return {"badcases": badcases(limit)}


@router.get("/health")
def testing_health():
    return {"status": "ok", "storage": "json", "redis": redis_status(), "metrics": "prometheus"}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(metrics_text(), media_type="text/plain; version=0.0.4")
