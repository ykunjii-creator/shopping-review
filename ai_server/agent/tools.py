"""Tool 정의 (Responses API flat 포맷) + 디스패처.

tech-spec §3.1. OpenAI Responses API는 function tool을 flat 포맷으로 받는다:
  {"type":"function","name":...,"description":...,"parameters":{...},"strict":true}
(pydantic_function_tool() 헬퍼는 Chat Completions용 nested 포맷이라 여기선 미사용.)

strict 모드 제약: 모든 property가 required 여야 하고 additionalProperties=False.
maxLength 등은 strict가 무시할 수 있어 length 검증은 validators.py가 책임 (tech-spec §3.2).
"""
from __future__ import annotations

import json

from config import CATEGORIES, DEPARTMENT_MAP_PATH, ENABLE_WEB_SEARCH

with open(DEPARTMENT_MAP_PATH, encoding="utf-8") as f:
    DEPT_MAP: dict = json.load(f)


# --- function tool 스키마 (flat / strict) ---
LOOKUP_TOOL = {
    "type": "function",
    "name": "lookup_department_mapping",
    "description": "카테고리에 해당하는 담당 부서/메일 조회.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": CATEGORIES},
        },
        "required": ["category"],
        "additionalProperties": False,
    },
}

SUBMIT_TOOL = {
    "type": "function",
    "name": "submit_analysis",
    "description": "최종 분석 결과 제출. Self-check 후 호출.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "review_id": {"type": "string"},
            "category": {"type": "string", "enum": CATEGORIES},
            "summary": {"type": "string", "description": "30자 이내, 명사 위주"},
            "department": {"type": "string"},
            "department_email": {"type": "string"},
            "urgency": {"type": "string", "enum": ["high", "medium", "low"]},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
            "self_check_notes": {"type": "string"},
            "external_evidence": {
                "type": "string",
                "description": "web_search 외부 근거 (없으면 빈 문자열)",
            },
        },
        # strict 모드: 모든 property required
        "required": [
            "review_id", "category", "summary", "department", "department_email",
            "urgency", "confidence", "reasoning", "self_check_notes", "external_evidence",
        ],
        "additionalProperties": False,
    },
}

WEB_SEARCH_TOOL = {"type": "web_search"}  # hosted tool (tech-spec §3.1)


def get_tools() -> list[dict]:
    """Agent에 넘길 tool 목록. web_search는 .env 토글."""
    tools = [LOOKUP_TOOL, SUBMIT_TOOL]
    if ENABLE_WEB_SEARCH:
        tools.append(WEB_SEARCH_TOOL)
    return tools


# --- 디스패처 ---
def lookup_department_mapping(category: str) -> dict:
    entry = DEPT_MAP.get(category)
    if entry is None:
        return {"error": f"알 수 없는 카테고리: {category}"}
    return entry


def execute_tool(name: str, args: dict) -> str:
    """function_call 실행 → JSON 문자열 반환 (function_call_output용).

    submit_analysis는 별도 처리(core.py)이므로 여기선 ack만.
    """
    if name == "lookup_department_mapping":
        return json.dumps(lookup_department_mapping(args.get("category", "")), ensure_ascii=False)
    if name == "submit_analysis":
        return json.dumps({"status": "received"}, ensure_ascii=False)
    return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
