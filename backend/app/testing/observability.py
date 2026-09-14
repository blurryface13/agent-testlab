"""Optional Redis event mirror and bounded Prometheus metrics.

The JSON files remain the local source of truth. Redis is an acceleration and
live-event layer when REDIS_URL is configured, so a missing Redis container
never makes a test result disappear.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from prometheus_client import Counter, Histogram, REGISTRY, generate_latest
except ImportError:  # local minimal installs can still run the workbench
    Counter = Histogram = None  # type: ignore[assignment]
    REGISTRY = None
    generate_latest = None  # type: ignore[assignment]


RUNS_TOTAL = Counter("testlab_runs_total", "TestLab runs by target, tool and status", ["target", "tool", "status"]) if Counter else None
CASES_TOTAL = Counter("testlab_cases_total", "TestLab cases by target, tool and result", ["target", "tool", "status"]) if Counter else None
RUN_DURATION = Histogram("testlab_run_duration_seconds", "TestLab run duration", ["target", "tool"]) if Histogram else None


def record_case(target: str, tool: str, status: str) -> None:
    if CASES_TOTAL:
        CASES_TOTAL.labels(target=target, tool=tool, status=status).inc()


def record_run(target: str, tool: str, status: str, duration_seconds: float) -> None:
    if RUNS_TOTAL:
        RUNS_TOTAL.labels(target=target, tool=tool, status=status).inc()
    if RUN_DURATION:
        RUN_DURATION.labels(target=target, tool=tool).observe(max(0.0, duration_seconds))


def metrics_text() -> bytes:
    return generate_latest(REGISTRY) if generate_latest and REGISTRY else b"# prometheus-client not installed\n"


def redis_client():
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        from redis import Redis
        client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.4, socket_timeout=0.4)
        client.ping()
        return client
    except Exception:
        return None


def redis_status() -> dict[str, Any]:
    configured = bool(os.getenv("REDIS_URL", "").strip())
    if not configured:
        return {"configured": False, "status": "not_configured", "note": "未配置 REDIS_URL，使用本地持久化"}
    client = redis_client()
    return {"configured": True, "status": "ready" if client else "unavailable", "note": "事件镜像可选，JSON 仍是本地事实源"}


def mirror_snapshot(run: dict[str, Any]) -> None:
    client = redis_client()
    if not client:
        return
    try:
        run_id = run["id"]
        client.setex(f"testlab:run:{run_id}", 86400, __import__("json").dumps({key: value for key, value in run.items() if key != "cancel_event"}, ensure_ascii=False, default=str))
        if run.get("events"):
            event = run["events"][-1]
            client.xadd(f"testlab:events:{run_id}", {"sequence": str(event["sequence"]), "kind": event["kind"], "message": event["message"]}, maxlen=500, approximate=True)
    except Exception:
        # Redis is explicitly best-effort; never hide a durable local result.
        return
