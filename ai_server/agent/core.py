"""Agent 메인 루프 — OpenAI Responses API + function calling.

tech-spec §3.1. Anthropic Messages 루프를 Responses API로 변환:
  system= → instructions= / messages → input(resp.output 누적) /
  tool_use → function_call / tool_result → function_call_output /
  stop_reason 분기 → output item type 순회.
"""
from __future__ import annotations

import json

from config import MAIN_MODEL, MAX_ITERATIONS, UNCLASSIFIED, get_client
from agent.prompts import SYSTEM_PROMPT, build_analysis_input
from agent.tools import DEPT_MAP, execute_tool, get_tools


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


def analyze_review(review: dict) -> dict:
    """단일 리뷰 분석. Agent가 web_search/self_check를 자율 결정."""
    client = get_client()
    input_list: list = [{"role": "user", "content": build_analysis_input(review)}]
    tools = get_tools()

    for _ in range(MAX_ITERATIONS):
        resp = client.responses.create(
            model=MAIN_MODEL,
            instructions=SYSTEM_PROMPT,
            tools=tools,
            input=input_list,
            reasoning={"effort": "low"},
        )
        # assistant turn 통째로 누적
        input_list += resp.output

        final = None
        for item in resp.output:
            if getattr(item, "type", None) != "function_call":
                continue  # web_search(hosted)·reasoning·message 등은 자동 처리
            args = json.loads(item.arguments)
            out = execute_tool(item.name, args)
            input_list.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": out,
            })
            if item.name == "submit_analysis":
                final = args

        if final is not None:
            return {**final, **_original_fields(review)}

    return _unclassified(review, "MAX_ITERATIONS 초과")
