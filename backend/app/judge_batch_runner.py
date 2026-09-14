"""裁判批量任务执行器（独立进程，由 main.py 以 subprocess 启动）。

逐样本 × 逐裁判判定，增量写 out_dir/judgements.jsonl；可断点续跑（已判的跳过）。
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t2i_client import judge_image, load_env  # noqa: E402

DEMO_EVAL_DIR = Path(os.getenv("T2I_DEMO_EVAL_DIR", "/Users/dora/Downloads/GEN/demo/dataset_eval"))
sys.path.insert(0, str(DEMO_EVAL_DIR))
from category_definitions import GB_OF_V6  # noqa: E402


def iter_jsonl(path: Path):
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


def is_completed_judgement(record: dict, judge_id: str) -> bool:
    """只有得到有效布尔结论的裁判才算完成，可为同一图补跑其他/失败裁判。"""
    result = (record.get("judges") or {}).get(judge_id)
    return isinstance(result, dict) and isinstance(result.get("unsafe"), bool) and not result.get("error")


def main() -> int:
    parser = argparse.ArgumentParser(description="批量裁判执行器")
    parser.add_argument("--img-dir", required=True, type=Path, help="imgs/ 目录")
    parser.add_argument("--samples", required=True, type=Path, help="样本索引（samples.jsonl，含 id/subcategory/category/prompt）")
    parser.add_argument("--judges", nargs="+", required=True)
    parser.add_argument("--out", required=True, type=Path, help="输出目录（写 judgements.jsonl + meta.json）")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--task-name", default="", help="前端历史列表显示名称")
    parser.add_argument("--source-model", default="", help="被测生图模型名称")
    args = parser.parse_args()

    env = load_env()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "judgements.jsonl"
    # 任务一启动即可出现在前端历史列表；结束时再以最终 total 覆盖确认。
    meta_path = out_dir / "meta.json"
    try:
        initial_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        initial_meta = {}
    initial_meta.update({"judges": args.judges, "img_dir": str(args.img_dir), "total": args.limit})
    if args.task_name:
        initial_meta["task_name"] = args.task_name
    if args.source_model:
        initial_meta["source_model"] = args.source_model
    meta_path.write_text(json.dumps(initial_meta, ensure_ascii=False), encoding="utf-8")
    # 同一结果目录只允许一个 worker 写入。flock 在进程退出时自动释放，
    # 既防止并发启动写出重复样本，也不会留下无法恢复的 stale lock。
    lock_stream = (out_dir / ".runner.lock").open("a", encoding="utf-8")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"已有裁判任务正在写入：{out_dir}", file=sys.stderr)
        return 2

    index: dict[str, dict] = {}
    for row in iter_jsonl(args.samples):
        if row.get("id"):
            index.setdefault(str(row["id"]), row)

    images = sorted(args.img_dir.glob("*.png"))[: args.limit]
    # 断点续跑按“样本 × 裁判”而非仅样本 id 判断：已有 Gemma 结果时，
    # 仍允许向同一任务补跑 GPT；此前网络失败的 None 结果也可重试。
    existing_by_id: dict[str, dict] = {}
    for row in iter_jsonl(result_path):
        sample_id = str(row.get("id", ""))
        if not sample_id:
            continue
        existing = existing_by_id.get(sample_id)
        if existing is None:
            existing_by_id[sample_id] = row
            continue
        # 兼容历史 append 记录：不同轮次的裁判结果合并，而非以最后一行覆盖。
        existing.setdefault("judges", {}).update(row.get("judges") or {})

    with result_path.open("a", encoding="utf-8") as stream:
        for i, image in enumerate(images, start=1):
            sample_id = image.stem
            source = index.get(sample_id, {})
            subcategory = str(source.get("subcategory", ""))
            # 优先保留数据集已配置的大类/criteria；只有历史数据缺失时才按小类兼容补齐。
            category = str(source.get("category", "")).strip() or GB_OF_V6.get(subcategory, "")
            previous = existing_by_id.get(sample_id, {})
            rec = {
                "id": sample_id,
                "subcategory": subcategory,
                "category": category,
                "prompt": str(source.get("prompt", "")),
                "judges": dict(previous.get("judges") or {}),
            }
            if all(is_completed_judgement(rec, judge_id) for judge_id in args.judges):
                continue
            image_bytes = None
            for judge_id in args.judges:
                if is_completed_judgement(rec, judge_id):
                    continue
                try:
                    image_bytes = image_bytes or image.read_bytes()
                except OSError:
                    rec["judges"][judge_id] = {"unsafe": None, "reason": "", "error": "图像读取失败"}
                    continue
                unsafe, error, reason, risk_category, risk_subcategories, face_evidence = judge_image(
                    rec["prompt"], rec["category"], rec["subcategory"], image_bytes, judge_id, env,
                    domain=source.get("domain"),
                )
                rec["judges"][judge_id] = {
                    "unsafe": unsafe,
                    "reason": reason,
                    "risk_category": risk_category,
                    "risk_subcategories": risk_subcategories,
                    "face_evidence": face_evidence,
                    "error": error,
                }
                print(f"  [{sample_id}] {judge_id}: unsafe={unsafe} err={str(error or '')[:40]}", flush=True)
            stream.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stream.flush()
            existing_by_id[sample_id] = rec
            if i % 5 == 0:
                print(f"进度 {i}/{len(images)}", flush=True)
    # 保留由前端创建任务时写入的可读名称；手动实验也可通过参数写入名称。
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        meta = {}
    meta.update({"judges": args.judges, "img_dir": str(args.img_dir), "total": len(images)})
    if args.task_name:
        meta["task_name"] = args.task_name
    if args.source_model:
        meta["source_model"] = args.source_model
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"完成: {len(images)} 条", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
