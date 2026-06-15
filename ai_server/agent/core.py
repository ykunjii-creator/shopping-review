"""배치 분석 — OpenAI Responses API + structured output.

리뷰 N건을 1회 호출로 분석해 analyses 배열로 받는다(tech-spec §3.1의 단건 agentic
루프를 효율화). 부서/메일은 모델이 아니라 Python이 DEPT_MAP으로 결정적으로 채운다.
web_search·function tool은 미사용(검증 2단계와 무관한 분석 보조 기능 제거).
"""
from __future__ import annotations

import json

from config import CATEGORIES, MAIN_MODEL, UNCLASSIFIED, get_client
from agent.prompts import BATCH_SYSTEM_PROMPT, build_batch_analysis_input
from agent.tools import DEPT_MAP

# 배치 분석 structured output (strict json_schema, analyses 배열)
_ANALYSIS_BATCH_FORMAT = {
    "format": {
        "type": "json_schema",
        "name": "batch_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "analyses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "review_id": {"type": "string"},
                            "category": {"type": "string", "enum": CATEGORIES},
                            "summary": {"type": "string"},
                            "urgency": {"type": "string", "enum": ["high", "medium", "low"]},
                            "confidence": {"type": "number"},
                            "reasoning": {"type": "string"},
                            "self_check_notes": {"type": "string"},
                            "external_evidence": {"type": "string"},
                        },
                        "required": [
                            "review_id", "category", "summary", "urgency",
                            "confidence", "reasoning", "self_check_notes", "external_evidence",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["analyses"],
            "additionalProperties": False,
        },
    }
}


def _with_department(analysis: dict, review: dict) -> dict:
    """모델 출력(부서 제외)에 카테고리별 부서/메일을 결정적으로 주입 + 원본필드 부착."""
    entry = DEPT_MAP.get(analysis.get("category"), DEPT_MAP[UNCLASSIFIED])
    return {
        **analysis,
        "department": entry["department"],
        "department_email": entry["department_email"],
        **_original_fields(review),
    }


def _original_fields(review: dict) -> dict:
    """응답에 항상 실어야 하는 원본 필드 (PRD §4.3)."""
    return {
        "original_text": review.get("text", ""),
        "original_rating": review.get("rating"),
        "review_date": review.get("review_date"),
    }


def _unclassified(review: dict, reason: str) -> dict:
    """미분류 결과 생성 (PRD §4.4, §6)."""
    entry = DEPT_MAP[UNCLASSIFIED]
    return {
        "review_id": review.get("review_id", ""),
        "category": UNCLASSIFIED,
        "summary": reason[:30],
        "department": entry["department"],
        "department_email": entry["department_email"],
        "urgency": "low",
        "confidence": 0.0,
        "reasoning": f"미분류 처리: {reason}",
        "self_check_notes": "",
        "external_evidence": "",
        **_original_fields(review),
    }


def analyze_batch(reviews: list[dict]) -> list[dict]:
    if not reviews:
        return []
    client = get_client()
    prompt = BATCH_SYSTEM_PROMPT + "\n\n" + build_batch_analysis_input(reviews) + "\n\n반드시 JSON만 출력하고, ```json 같은 마크다운 없이 순수 JSON만 반환하라."
    resp = client.models.generate_content(
        model=MAIN_MODEL,
        contents=prompt,
    )
    raw = resp.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        analyses = parsed
    else:
        analyses = parsed.get("analyses", [])
    by_id = {a.get("review_id"): a for a in analyses}

    out: list[dict] = []
    for review in reviews:
        a = by_id.get(review.get("review_id"))
        if a is None:
            out.append(_unclassified(review, "분석 누락"))
        else:
            out.append(_with_department(a, review))
    return out