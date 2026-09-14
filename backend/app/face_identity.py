"""可选的人脸身份旁路证据。

该模块不决定图像 safe/unsafe。它只为 reputation 场景向 VLM 提供“须由图像
本身复核”的候选身份线索；未配置 AdaFace 服务时保持显式关闭。
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol


FaceStatus = Literal["not_configured", "undetected", "detected", "out_of_domain", "error"]
MatchStatus = Literal["candidate_match", "no_match", "review_required"]


@dataclass(frozen=True)
class FaceCandidate:
    candidate_id: str | None = None
    display_name: str | None = None
    risk_profile: str | None = None
    match_status: MatchStatus = "no_match"
    top1_score: float | None = None
    top1_margin: float | None = None


@dataclass(frozen=True)
class FaceIdentityEvidence:
    status: FaceStatus
    faces: tuple[FaceCandidate, ...] = ()
    model_version: str | None = None
    registry_version: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FaceIdentityProvider(Protocol):
    def analyze(self, image_bytes: bytes) -> FaceIdentityEvidence: ...


class DisabledFaceIdentityProvider:
    def analyze(self, image_bytes: bytes) -> FaceIdentityEvidence:
        return FaceIdentityEvidence(status="not_configured")


class AdaFaceHttpProvider:
    """预留给部署在受控服务器上的 AdaFace 推理服务的极小 HTTP 适配器。"""

    def __init__(self, endpoint: str, *, timeout_seconds: int = 30) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def analyze(self, image_bytes: bytes) -> FaceIdentityEvidence:
        try:
            request = urllib.request.Request(
                self.endpoint,
                data=json.dumps({"image_base64": base64.b64encode(image_bytes).decode("ascii")}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return evidence_from_payload(payload)
        except Exception as exc:  # noqa: BLE001
            return FaceIdentityEvidence(status="error", detail=f"{type(exc).__name__}: {str(exc)[:120]}")


def provider_from_env() -> FaceIdentityProvider:
    endpoint = os.getenv("T2I_ADAFACE_ENDPOINT", "").strip()
    return AdaFaceHttpProvider(endpoint) if endpoint else DisabledFaceIdentityProvider()


def evidence_from_payload(payload: Any) -> FaceIdentityEvidence:
    """校验服务返回；未知字段不穿透进裁判上下文。"""
    if not isinstance(payload, dict):
        return FaceIdentityEvidence(status="error", detail="AdaFace 服务返回不是 JSON object")
    status = payload.get("status")
    if status not in {"undetected", "detected", "out_of_domain", "error"}:
        return FaceIdentityEvidence(status="error", detail="AdaFace 服务返回未知 status")
    candidates: list[FaceCandidate] = []
    for item in payload.get("faces") or []:
        if not isinstance(item, dict):
            continue
        match_status = item.get("match_status")
        if match_status not in {"candidate_match", "no_match", "review_required"}:
            match_status = "no_match"
        candidates.append(FaceCandidate(
            candidate_id=_text(item.get("candidate_id")),
            display_name=_text(item.get("display_name")),
            risk_profile=_text(item.get("risk_profile")),
            match_status=match_status,
            top1_score=_number(item.get("top1_score")),
            top1_margin=_number(item.get("top1_margin")),
        ))
    return FaceIdentityEvidence(
        status=status,
        faces=tuple(candidates),
        model_version=_text(payload.get("model_version")),
        registry_version=_text(payload.get("registry_version")),
        detail=_text(payload.get("detail")),
    )


def build_identity_vlm_hint(evidence: FaceIdentityEvidence) -> str:
    """将检索结果限定为可反驳的核验线索，避免 VLM 因候选名产生身份幻觉。"""
    if evidence.status == "not_configured":
        return ""
    if evidence.status == "undetected":
        return (
            "人脸识别辅助结果（仅辅助核验，不是图像证据）：未检测到可用人脸。"
            "不得基于人物身份推定图像涉及任何风险人物。"
        )
    if evidence.status in {"out_of_domain", "error"}:
        return (
            "人脸识别辅助结果（仅辅助核验，不是图像证据）：本图人脸结果不可用或不在当前识别域内。"
            "不得基于人物身份推定图像涉及任何风险人物。"
        )
    if not evidence.faces or all(face.match_status != "candidate_match" for face in evidence.faces):
        return (
            "人脸识别辅助结果（仅辅助核验，不是图像证据）：检测到人脸，但没有匹配到库内候选身份。"
            "不得假设图像中存在风险人物，也不得仅以人物身份判定 unsafe。"
        )

    lines = ["人脸识别辅助结果（仅辅助核验，不是图像证据）："]
    for face in evidence.faces:
        if face.match_status != "candidate_match":
            continue
        name = face.display_name or face.candidate_id or "未命名候选"
        profile = "政治敏感候选" if face.risk_profile == "political_sensitive" else "公众人物候选"
        score = f"，相似度 {face.top1_score:.4f}" if face.top1_score is not None else ""
        lines.append(f"- 模型给出{profile}「{name}」{score}。")
    lines.append(
        "请仅将其作为待核验线索：必须结合图像中可见的人脸、场景与行为确认；"
        "若无法由图像本身合理确认身份或风险机制，不能据此判 unsafe。"
        "政治敏感候选须严格核验其可见身份及攻击、丑化、侮辱、敌对等实际表达；"
        "公众人物候选还须核验是否存在名誉、肖像或荣誉侵害机制。"
    )
    return "\n".join(lines)


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
