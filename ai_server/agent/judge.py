"""LLM-as-a-Judge — 검증수단 ② (tech-spec §3.3, PRD §4.10.2).

JUDGE_MODEL(gpt-5.4-nano, 메인과 다른 모델 → 교차검증) + structured output(json_schema strict).
score < JUDGE_PASS_THRESHOLD → fail → 미분류 강등.
"""
from __future__ import annotations

import json

from config import JUDGE_MODEL, JUDGE_PASS_THRESHOLD, get_client
from agent.prompts import JUDGE_PROMPT, build_batch_judge_input, build_judge_input

_JUDGE_FORMAT = {
    "format": {
        "type": "json_schema",
        "name": "judgment",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 10},
                "reasoning": {"type": "string"},
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False,
        },
    }
}


_JUDGE_BATCH_FORMAT = {
    "format": {
        "type": "json_schema",
        "name": "batch_judgment",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "evaluations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "review_id": {"type": "string"},
                            "score": {"type": "integer", "minimum": 1, "maximum": 10},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["review_id", "score", "reasoning"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["evaluations"],
            "additionalProperties": False,
        },
    }
}


def judge_evaluate(review: dict, result: dict) -> dict:
    """Judge LLM이 분류 결과를 1~10점 평가 (단건)."""
    client = get_client()
    resp = client.responses.create(
        model=JUDGE_MODEL,
        instructions=JUDGE_PROMPT,
        input=[{"role": "user", "content": build_judge_input(review, result)}],
        text=_JUDGE_FORMAT,
    )
    j = json.loads(resp.output_text)
    score = int(j["score"])
    return {
        "score": score,
        "passed": score >= JUDGE_PASS_THRESHOLD,
        "reasoning": j.get("reasoning", ""),
    }


def judge_batch(reviews: list[dict], results: list[dict]) -> dict[str, dict]:
    """rule 통과분 전체를 1회 호출로 평가. {review_id: {score, passed, reasoning}} 반환."""
    if not reviews:
        return {}
    client = get_client()
    resp = client.responses.create(
        model=JUDGE_MODEL,
        instructions=JUDGE_PROMPT,
        input=[{"role": "user", "content": build_batch_judge_input(reviews, results)}],
        text=_JUDGE_BATCH_FORMAT,
    )
    evals = json.loads(resp.output_text).get("evaluations", [])
    out: dict[str, dict] = {}
    for e in evals:
        score = int(e["score"])
        out[e.get("review_id")] = {
            "score": score,
            "passed": score >= JUDGE_PASS_THRESHOLD,
            "reasoning": e.get("reasoning", ""),
        }
    return out
