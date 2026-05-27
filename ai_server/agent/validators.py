"""Rule-based 검증 — 검증수단 ① (tech-spec §4.2, PRD §4.10.1).

모든 결과에 무조건 적용. 8개 check + 환각 휴리스틱.
실패 시 downgrade_to_unclassified로 강등. 모순(긍정+high)도 강등으로 단순화 (implement.md 결정).
"""
from __future__ import annotations

import re

from config import CATEGORIES, UNCLASSIFIED
from agent.tools import DEPT_MAP

# 환각 휴리스틱에서 무시할 조사/접미 (명사 추출 단순화용)
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def _hallucination_ok(summary: str, original_text: str) -> bool:
    """summary 핵심 명사(2글자+) 중 일부가 원문에 등장하는지 휴리스틱 검사.

    목적은 '완전 날조'(원문과 무관한 단어로만 구성된 요약) 차단.
    LLM이 원문 어휘를 정규화/요약하는 것은 정상이므로, 토큰이 하나라도
    원문에 부분일치하면 통과로 본다. 0건일 때만 환각으로 간주.
    원문/후보가 없으면 통과.
    """
    if not original_text:
        return True
    src = original_text
    cand = [t for t in _tokens(summary) if len(t) >= 2]
    if not cand:
        return True
    # 부분일치: summary 토큰이 원문에 substring으로 있거나, 앞 2글자(어간)가 겹치면 hit
    src_stems = {t[:2] for t in _tokens(src) if len(t) >= 2}
    hits = sum(1 for t in cand if t in src or t[:2] in src_stems)
    return hits >= 1


def rule_based_validate(result: dict) -> dict:
    """규칙 기반 검증. (tech-spec §4.2)"""
    category = result.get("category", "")
    urgency = result.get("urgency", "")
    summary = result.get("summary", "") or ""
    confidence = result.get("confidence", -1)
    email = result.get("department_email", "") or ""
    department = result.get("department", "")

    expected_dept = DEPT_MAP.get(category, {}).get("department")

    checks = {
        "summary_length_ok": len(summary) <= 30,
        "confidence_in_range": isinstance(confidence, (int, float))
        and 0.0 <= confidence <= 1.0,
        "category_valid": category in CATEGORIES,
        "urgency_valid": urgency in ["high", "medium", "low"],
        "email_format_ok": "@" in email,
        "no_positive_high_urgency": not (category == "긍정" and urgency == "high"),
        "defect_urgency_ok": not (category == "제품결함" and urgency == "low"),
        "department_matches": department == expected_dept,
        "no_hallucination": _hallucination_ok(summary, result.get("original_text", "")),
    }

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_rules": [k for k, v in checks.items() if not v],
    }


def downgrade_to_unclassified(result: dict, reason: str) -> dict:
    """결과를 미분류로 강등 (PRD §6). 원본 필드는 유지."""
    entry = DEPT_MAP[UNCLASSIFIED]
    result = dict(result)
    result.update({
        "category": UNCLASSIFIED,
        "department": entry["department"],
        "department_email": entry["department_email"],
        "urgency": "low",
        "needs_human_review": True,
        "downgrade_reason": reason,
    })
    return result
