"""배치 종합 분석 (tech-spec §4b, PRD §4.11).

분포 / defect_types(LLM 클러스터) / avg_conf / pass_rate / key_findings(규칙) / trending.
"""
from __future__ import annotations

import json
import re
from collections import Counter

from config import MAIN_MODEL, get_client
from agent.prompts import build_defect_cluster_input

_VERIFIED = "verified"
_DEFECT_FORMAT = {
    "format": {
        "type": "json_schema",
        "name": "defect_clusters",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "defect_types": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                }
            },
            "required": ["defect_types"],
            "additionalProperties": False,
        },
    }
}


def _llm_cluster_defects(summaries: list[str]) -> dict:
    """제품결함 summary들을 결함유형별 빈도로 클러스터 (gpt-5.4-mini 재호출).

    LLM 불가/실패 시 summary 원문 빈도로 폴백.
    """
    if not summaries:
        return {}
    try:
        client = get_client()
        resp = client.responses.create(
            model=MAIN_MODEL,
            input=[{"role": "user", "content": build_defect_cluster_input(summaries)}],
            text=_DEFECT_FORMAT,
            reasoning={"effort": "low"},
        )
        return json.loads(resp.output_text).get("defect_types", {})
    except Exception:
        return dict(Counter(summaries))


_KW_RE = re.compile(r"[가-힣]{2,}")
_STOP = {"제품", "배송", "리뷰", "구매", "사용", "정도", "조금", "생각", "그냥"}


def _extract_keywords(results: list[dict], top: int = 5) -> list[str]:
    c: Counter = Counter()
    for r in results:
        for tok in _KW_RE.findall(r.get("summary", "") or ""):
            if tok not in _STOP:
                c[tok] += 1
    return [w for w, _ in c.most_common(top)]


def _generate_key_findings(results: list[dict], defect_types: dict) -> list[str]:
    """PRD §4.11.3 규칙."""
    findings: list[str] = []
    n = len(results) or 1

    for defect, count in defect_types.items():
        if count >= 3:
            findings.append(f"{defect} {count}건 동일 패턴 발견 - 로트 불량 가능성")

    defect_count = sum(1 for r in results if r.get("category") == "제품결함")
    defect_rate = defect_count / n
    if defect_rate > 0.15:
        findings.append(f"전체 결함률 {defect_rate:.0%}로 평균(10%) 대비 높음")

    failed = sum(
        1 for r in results
        if r.get("verification", {}).get("final_status") != _VERIFIED
    )
    if failed >= 3:
        findings.append(f"검증 실패 {failed}건 - 사람 재확인 필요")

    return findings


def aggregate_analysis(results: list[dict]) -> dict:
    """배치 전체 종합 분석."""
    n = len(results) or 1
    defect_summaries = [
        r["summary"] for r in results
        if r.get("category") == "제품결함" and r.get("summary")
    ]
    defect_types = _llm_cluster_defects(defect_summaries)

    verified = sum(
        1 for r in results
        if r.get("verification", {}).get("final_status") == _VERIFIED
    )
    confs = [r["confidence"] for r in results if isinstance(r.get("confidence"), (int, float))]

    return {
        "category_distribution": dict(Counter(r.get("category") for r in results)),
        "defect_types": defect_types,
        "urgency_distribution": dict(Counter(r.get("urgency") for r in results)),
        "average_confidence": round(sum(confs) / len(confs), 3) if confs else 0.0,
        "verification_pass_rate": round(verified / n, 3),
        "key_findings": _generate_key_findings(results, defect_types),
        "trending_keywords": _extract_keywords(results),
    }
