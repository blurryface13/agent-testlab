"""Controlled local runner for Agent TestLab.

The first implementation makes the test workflow real without making the
browser a remote shell. Mock execution is deterministic and persisted to a
separate directory. A later adapter can replace one registered executor while
the run/result contract remains unchanged.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import TARGETS, TOOLS, get_case
from .observability import mirror_snapshot, record_case, record_run

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.getenv("TESTLAB_DATA_ROOT", str(PROJECT_ROOT / "data" / "testlab"))).expanduser()
RUN_ROOT = DATA_ROOT / "runs"
RUN_ROOT.mkdir(parents=True, exist_ok=True)

RUNS: dict[str, dict[str, Any]] = {}
LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_path(run_id: str) -> Path:
    if not all(char.isalnum() or char in "-_" for char in run_id):
        raise ValueError("invalid run id")
    return RUN_ROOT / run_id / "run.json"


def _write(run: dict[str, Any]) -> None:
    directory = RUN_ROOT / run["id"]
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "run.json.tmp"
    durable = {key: value for key, value in run.items() if key != "cancel_event"}
    temporary.write_text(json.dumps(durable, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(directory / "run.json")
    mirror_snapshot(run)


def _load(run_id: str) -> dict[str, Any] | None:
    with LOCK:
        if run_id in RUNS:
            return RUNS[run_id]
        path = _run_path(run_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict):
            return None
        value["cancel_event"] = threading.Event()
        RUNS[run_id] = value
        return value


def _event(run: dict[str, Any], kind: str, message: str, **extra: Any) -> None:
    run["sequence"] += 1
    run["events"].append({
        "sequence": run["sequence"], "at": now_iso(), "kind": kind,
        "message": message, **extra,
    })


def _public(run: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in run.items() if key not in {"cancel_event"}}
    result["progress"] = round((run["completed_cases"] / run["total_cases"]) * 100) if run["total_cases"] else 0
    result["summary"] = {
        "passed": sum(item["status"] == "passed" for item in run["results"]),
        "failed": sum(item["status"] == "failed" for item in run["results"]),
        "error": sum(item["status"] == "error" for item in run["results"]),
        "skipped": sum(item["status"] == "skipped" for item in run["results"]),
    }
    return result


def preview(*, target: str, case_ids: list[str], tool: str, mode: str, fault_mode: str) -> dict[str, Any]:
    if target not in {item["id"] for item in TARGETS}:
        return {"accepted": False, "message": "测试对象未登记，不能执行。"}
    if tool not in {item["id"] for item in TOOLS}:
        return {"accepted": False, "message": "执行工具未登记，不能执行。"}
    if mode == "local" and tool != "pytest":
        return {"accepted": False, "message": "本地执行模式目前只开放注册的 pytest 入口。"}
    normalized_case_ids = list(dict.fromkeys(case_ids))
    if mode == "local" and (target != "t2i-safety" or len(normalized_case_ids) != 1):
        return {"accepted": False, "message": "本地 pytest 目前只开放 T2I Safety 的单个注册合同用例。"}
    cases = [get_case(case_id) for case_id in normalized_case_ids]
    missing = [case_id for case_id, case in zip(normalized_case_ids, cases) if case is None]
    selected = [case for case in cases if case is not None]
    incompatible = [case["id"] for case in selected if tool not in case["tools"]]
    if missing:
        return {"accepted": False, "message": f"未注册用例：{', '.join(missing)}"}
    if not selected:
        return {"accepted": False, "message": "至少选择一个测试用例。"}
    if incompatible:
        return {"accepted": False, "message": f"工具 {tool} 不适用于：{', '.join(incompatible)}"}
    wrong_target = [case["id"] for case in selected if case["target"] != target]
    if wrong_target:
        return {"accepted": False, "message": f"用例与测试对象不匹配：{', '.join(wrong_target)}"}
    if mode not in {"mock", "local"}:
        return {"accepted": False, "message": "执行模式只支持 mock 或 local。"}
    if fault_mode not in {"none", "timeout", "tool_error", "contract"}:
        return {"accepted": False, "message": "未知故障注入类型。"}
    paid = mode == "local" and any(case["level"] == "agent" for case in selected)
    return {
        "accepted": True,
        "mode": "preflight_only",
        "message": "预览已通过。此阶段不执行测试、不调用模型。",
        "selection": {
            "target": target,
            "tool": tool,
            "mode": mode,
            "fault_mode": fault_mode,
            "case_ids": [case["id"] for case in selected],
            "case_count": len(selected),
            "estimated_seconds": max(1, len(selected)),
            "cost_mode": "可能产生模型费用，需显式确认" if paid else "无模型调用",
            "output_dir": str(RUN_ROOT),
        },
    }


def compute_preview_hash(result: dict[str, Any]) -> str:
    encoded = json.dumps(result["selection"], sort_keys=True, ensure_ascii=False).encode()
    import hashlib
    return hashlib.sha256(encoded).hexdigest()[:16]


def start(*, target: str, case_ids: list[str], tool: str, mode: str, fault_mode: str, preview_hash: str | None = None) -> dict[str, Any]:
    checked = preview(target=target, case_ids=case_ids, tool=tool, mode=mode, fault_mode=fault_mode)
    if not checked["accepted"]:
        return checked
    if not preview_hash or preview_hash != compute_preview_hash(checked):
        return {"accepted": False, "message": "预览已失效，请重新生成执行预览。"}
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run = {
        "id": run_id, "target": target, "tool": tool, "mode": mode,
        "fault_mode": fault_mode, "status": "queued", "created_at": now_iso(),
        "started_at": None, "finished_at": None, "preview_hash": preview_hash,
        "case_ids": checked["selection"]["case_ids"], "total_cases": checked["selection"]["case_count"],
        "completed_cases": 0, "results": [], "events": [], "sequence": 0,
        "cancel_event": threading.Event(), "runner_version": "testlab-mock-1",
    }
    with LOCK:
        RUNS[run_id] = run
        _event(run, "queued", "运行已创建，等待受控 runner。")
        _write(run)
    thread = threading.Thread(target=_execute, args=(run,), name=f"testlab-{run_id}", daemon=True)
    thread.start()
    return {"accepted": True, "message": "测试任务已启动。", "run": _public(run)}


def _execute(run: dict[str, Any]) -> None:
    started_clock = time.monotonic()
    with LOCK:
        run["status"] = "running"
        run["started_at"] = now_iso()
        _event(run, "started", f"使用 {run['tool']} 执行 {run['mode']} 测试。")
        _write(run)
    if run["mode"] == "local" and run["tool"] == "pytest":
        _execute_registered_pytest(run)
        return
    for index, case_id in enumerate(run["case_ids"]):
        if run["cancel_event"].is_set():
            with LOCK:
                _event(run, "cancelled", "用户取消了后续用例。")
                run["status"] = "cancelled"
                run["finished_at"] = now_iso()
                _write(run)
            return
        time.sleep(0.08)
        status = "passed"
        error_type = None
        message = "断言通过"
        if run["fault_mode"] != "none" and index == min(1, len(run["case_ids"]) - 1):
            status = "failed"
            error_type = run["fault_mode"]
            message = {
                "timeout": "模拟 provider 超时，任务状态保持可读",
                "tool_error": "模拟工具返回异常，未进入无效重试",
                "contract": "模拟响应字段缺失，契约断言拒绝",
            }[run["fault_mode"]]
        with LOCK:
            run["results"].append({
                "case_id": case_id, "status": status, "error_type": error_type,
                "message": message, "duration_ms": 80, "assertions": get_case(case_id)["assertions"],
                "evidence": {"mode": run["mode"], "runner": run["runner_version"]},
            })
            run["completed_cases"] += 1
            record_case(run["target"], run["tool"], status)
            _event(run, "case_completed", f"{case_id}：{message}", case_id=case_id, status=status)
            _write(run)
    with LOCK:
        run["status"] = "completed"
        run["finished_at"] = now_iso()
        _event(run, "completed", "全部注册用例执行完毕。")
        record_run(run["target"], run["tool"], run["status"], time.monotonic() - started_clock)
        _write(run)


def _execute_registered_pytest(run: dict[str, Any]) -> None:
    """Run only the checked-in contract test file, never a browser-supplied path."""
    command = [sys.executable, "-m", "pytest", "backend/tests/test_t2i_company_contract.py", "-q"]
    started = time.monotonic()
    try:
        environment = os.environ.copy()
        backend_path = str(PROJECT_ROOT / "backend")
        current_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, [backend_path, current_pythonpath]))
        completed = subprocess.run(
            command, cwd=str(PROJECT_ROOT), env=environment,
            capture_output=True, text=True, timeout=120,
        )
        output = (completed.stdout + "\n" + completed.stderr).strip()[-3000:]
        status = "passed" if completed.returncode == 0 else "failed"
        error_type = None if status == "passed" else "pytest_error"
        message = "注册的 pytest 合同测试通过" if status == "passed" else "pytest 执行失败或依赖未准备"
    except (OSError, subprocess.TimeoutExpired) as exc:
        output = str(exc)
        status, error_type, message = "error", "runner_error", "pytest runner 无法完成"
    with LOCK:
        run["results"].append({
            "case_id": run["case_ids"][0], "status": status, "error_type": error_type,
            "message": message, "duration_ms": round((time.monotonic() - started) * 1000),
            "assertions": get_case(run["case_ids"][0])["assertions"], "evidence": {"output": output},
        })
        run["completed_cases"] = run["total_cases"]
        _event(run, "case_completed", message, case_id=run["case_ids"][0], status=status)
        run["status"] = "completed" if status == "passed" else "failed"
        run["finished_at"] = now_iso()
        record_case(run["target"], run["tool"], status)
        record_run(run["target"], run["tool"], run["status"], time.monotonic() - started)
        _event(run, run["status"], "pytest 注册执行结束。")
        _write(run)


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(RUN_ROOT.glob("*/run.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        loaded = _load(path.parent.name)
        if loaded:
            entries.append(_public(loaded))
        if len(entries) >= limit:
            break
    return entries


def get_run(run_id: str) -> dict[str, Any] | None:
    run = _load(run_id)
    return _public(run) if run else None


def cancel(run_id: str) -> dict[str, Any] | None:
    run = _load(run_id)
    if not run:
        return None
    with LOCK:
        if run["status"] in {"completed", "failed", "cancelled"}:
            return _public(run)
        run["cancel_event"].set()
        _event(run, "cancel_requested", "已请求取消，等待当前用例结束。")
        _write(run)
    return _public(run)


def events(run_id: str, after: int = 0) -> list[dict[str, Any]] | None:
    run = _load(run_id)
    if not run:
        return None
    return [item for item in run["events"] if item["sequence"] > after]


def badcases(limit: int = 50) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for run in list_runs(200):
        for item in run.get("results", []):
            if item.get("status") not in {"failed", "error"}:
                continue
            result.append({
                "id": f"{run['id']}:{item['case_id']}", "run_id": run["id"], "case_id": item["case_id"],
                "target": run["target"], "tool": run["tool"], "status": "candidate",
                "failure_type": item.get("error_type") or "assertion_failed",
                "summary": item.get("message", ""), "evidence": item.get("evidence", {}),
                "created_at": run["finished_at"] or run["created_at"],
            })
            if len(result) >= limit:
                return result
    return result
