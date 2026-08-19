"""提示词查看器：只读调用 demo 的提示词构造入口，还原各节点 LLM 实际收到的完整提示词。

- 不改动 demo 任何代码；由 main.py 以子进程方式执行（使用 demo 的 python 环境）。
- 输出 JSON 到 stdout：{node, sample_id, subcategory, system, user, note}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEMO_EVAL_DIR = Path(os.getenv("T2I_DEMO_EVAL_DIR", "/Users/dora/Downloads/GEN/demo/dataset_eval"))
sys.path.insert(0, str(DEMO_EVAL_DIR))

from assign_label import build_assign_prompt, build_assign_system  # noqa: E402
from category_definitions import GB_OF_V6, V6_SUBCATEGORIES  # noqa: E402
from generation_planner import plan_generation  # noqa: E402
from prompt_templates import (  # noqa: E402
    GENERIC_GENERATION_SYSTEM,
    POLISH_SYSTEM,
    build_generation_request,
    build_generation_system,
    build_polish_request,
    build_polish_system,
)
from semantic import build_verify_prompt, build_verify_system  # noqa: E402
from vlm_judge_prompts import VLM_EVALUATOR_NAMES, build_vlm_judge_instruction, build_vlm_judge_system  # noqa: E402

RISK_SUBCATEGORIES = [name for name in V6_SUBCATEGORIES if name != "safe"]


def load_rows(dataset_path: Path) -> list[dict]:
    rows: list[dict] = []
    with dataset_path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def pick_sample(rows: list[dict], sample_id: str, subcategory: str = "") -> dict:
    if subcategory:
        rows = [row for row in rows if str(row.get("subcategory")) == subcategory]
    if sample_id:
        for row in rows:
            if str(row.get("id")) == str(sample_id):
                return row
        raise ValueError(f"样本 {sample_id} 不存在")
    if not rows:
        raise ValueError("数据集中没有可展示的样本")
    return rows[0]


def render(node: str, sample: dict) -> dict:
    prompt = str(sample.get("prompt", ""))
    sub = str(sample.get("subcategory") or sample.get("gb_label") or "safe")
    parent = GB_OF_V6.get(sub, sub)

    if node == "judge":
        # 裁判三输入：原始提示词 + 风险 label + 生成图像（图像由调用方附上）
        item = {"prompt": prompt, "category": parent, "subcategory": sub}
        return {"system": build_vlm_judge_system(item), "user": build_vlm_judge_instruction(item, evidence_mode="targeted"),
                "note": "发送时附加生成图像（本视图不含图像）。category 由小类映射为评估大类。"}

    if node == "generate":
        definition = V6_SUBCATEGORIES[sub]
        plan = plan_generation(sub, 1)[0]
        system = build_generation_system(
            subcategory=sub, category=parent,
            definition=definition.get("definition", ""),
            positive=definition.get("positive", []),
            negative=definition.get("negative", []),
            boundary=definition.get("boundary", ""),
        )
        user = build_generation_request(
            subcategory=sub, category=parent, plan={**plan, "count": 1},
        )
        return {"system": system, "user": user,
                "note": f"策略切面 {plan.get('id')}（plan_generation 确定性分配；context 为空时无示例注入）"}

    if node == "polish":
        definition = V6_SUBCATEGORIES[sub]
        system = build_polish_system(
            subcategory=sub, category=parent,
            definition=definition.get("definition", ""),
            positive=definition.get("positive", []),
            negative=definition.get("negative", []),
            boundary=definition.get("boundary", ""),
        )
        user = build_polish_request(prompt=prompt, subcategory=sub, category=parent, count=2)
        return {"system": system, "user": user, "note": "候选数按 2 展示；实际由任务参数决定。"}

    if node == "label":
        candidates = RISK_SUBCATEGORIES + ["BENIGN"]
        return {"system": build_assign_system(candidates),
                "user": build_assign_prompt(prompt, candidates),
                "note": "候选类别为 11 个风险小类 + BENIGN（定义已入 system）。"}

    if node == "verify":
        return {"system": build_verify_system(sample), "user": build_verify_prompt(sample),
                "note": "输入为数据集记录（含 metadata.gb_label 时附加标准标签）。"}

    raise ValueError(f"未知节点: {node}（可选 judge/generate/polish/label/verify）")


def list_categories() -> dict:
    """大类 -> 小类映射（供日志页联动选择）。"""
    groups: dict[str, list[str]] = {}
    for sub in V6_SUBCATEGORIES:
        parent = GB_OF_V6.get(sub, "BENIGN")
        groups.setdefault(parent, []).append(sub)
    return {
        "found": True,
        "categories": [
            {
                "id": parent,
                "name": VLM_EVALUATOR_NAMES.get(parent, "对照组" if parent == "BENIGN" else parent),
                "subcategories": subs,
            }
            for parent, subs in sorted(groups.items(), key=lambda item: (item[0] != "BENIGN", item[0]))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="还原各节点 LLM 完整提示词")
    parser.add_argument("--node", choices=["judge", "generate", "polish", "label", "verify"])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--sample-id", default="")
    parser.add_argument("--subcategory", default="")
    parser.add_argument("--list-categories", action="store_true")
    args = parser.parse_args()

    try:
        if args.list_categories:
            print(json.dumps(list_categories(), ensure_ascii=False))
            return 0
        if args.node is None:
            raise ValueError("--node 必填（judge/generate/polish/label/verify）")
        sample = pick_sample(load_rows(args.dataset), args.sample_id, args.subcategory)
        payload = render(args.node, sample)
        payload.update({
            "found": True,
            "node": args.node,
            "sample_id": str(sample.get("id", "")),
            "subcategory": str(sample.get("subcategory") or sample.get("gb_label") or "safe"),
            "category": str(sample.get("category", "")),
        })
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"found": False, "message": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
