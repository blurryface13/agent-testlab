"""裁判批量任务执行器（独立进程，由 main.py 以 subprocess 启动）。

逐样本 × 逐裁判判定，增量写 out_dir/judgements.jsonl；可断点续跑（已判的跳过）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t2i_client import judge_image, load_env  # noqa: E402


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


def main() -> int:
    parser = argparse.ArgumentParser(description="批量裁判执行器")
    parser.add_argument("--img-dir", required=True, type=Path, help="imgs/ 目录")
    parser.add_argument("--samples", required=True, type=Path, help="样本索引（samples.jsonl，含 id/subcategory/category/prompt）")
    parser.add_argument("--judges", nargs="+", required=True)
    parser.add_argument("--out", required=True, type=Path, help="输出目录（写 judgements.jsonl + meta.json）")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    env = load_env()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "judgements.jsonl"

    index: dict[str, dict] = {}
    for row in iter_jsonl(args.samples):
        if row.get("id"):
            index.setdefault(str(row["id"]), row)

    images = sorted(args.img_dir.glob("*.png"))[: args.limit]
    # 断点续跑：已有判定则跳过
    done_ids: set[str] = set()
    for row in iter_jsonl(result_path):
        done_ids.add(str(row.get("id")))

    with result_path.open("a", encoding="utf-8") as stream:
        for i, image in enumerate(images, start=1):
            sample_id = image.stem
            if sample_id in done_ids:
                continue
            source = index.get(sample_id, {})
            rec = {
                "id": sample_id,
                "subcategory": str(source.get("subcategory", "")),
                "category": str(source.get("category", "")),
                "prompt": str(source.get("prompt", "")),
                "judges": {},
            }
            for judge_id in args.judges:
                try:
                    image_bytes = image.read_bytes()
                except OSError:
                    rec["judges"][judge_id] = {"unsafe": None, "reason": "", "error": "图像读取失败"}
                    continue
                unsafe, error, reason = judge_image(
                    rec["prompt"], rec["category"], rec["subcategory"], image_bytes, judge_id, env,
                )
                rec["judges"][judge_id] = {"unsafe": unsafe, "reason": reason, "error": error}
                print(f"  [{sample_id}] {judge_id}: unsafe={unsafe} err={str(error or '')[:40]}", flush=True)
            stream.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stream.flush()
            if i % 5 == 0:
                print(f"进度 {i}/{len(images)}", flush=True)
    (out_dir / "meta.json").write_text(
        json.dumps({"judges": args.judges, "img_dir": str(args.img_dir), "total": len(images)}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"完成: {len(images)} 条", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
