"""검증 통합 파이프라인 (tech-spec §4.3, PRD §4.10.4).

흐름: analyze_review → rule_based (fail시 judge skip) → judge → final_status.
콘솔에 단계 로그 출력 (데모 하이라이트, PRD §8).
"""
from __future__ import annotations

from agent.core import analyze_review
from agent.judge import judge_evaluate
from agent.validators import downgrade_to_unclassified, rule_based_validate


def _log(review_id: str, msg: str) -> None:
    print(f"[{review_id}] {msg}", flush=True)


def analyze_and_verify(review: dict) -> dict:
    """단일 리뷰: 분석 + 2단 검증. 검증 메타를 result['verification']에 부착."""
    rid = review.get("review_id", "?")
    _log(rid, "Main Agent 분석 중...")
    result = analyze_review(review)
    _log(rid, f"분석 완료: {result['category']} (conf {result.get('confidence')})")

    # ① Rule-based
    rule_check = rule_based_validate(result)
    if not rule_check["passed"]:
        _log(rid, f"Rule-based: FAIL {rule_check['failed_rules']} → 미분류 (Judge skip)")
        result = downgrade_to_unclassified(result, "rule_based_failed")
        result["verification"] = {
            "rule_based": rule_check,
            "judge_evaluation": None,
            "final_status": "rule_based_failed",
        }
        return result
    _log(rid, "Rule-based: PASS")

    # ② Judge
    judge_result = judge_evaluate(review, result)
    if not judge_result["passed"]:
        _log(rid, f"Judge: {judge_result['score']}/10 → FAIL → 미분류 (사람 확인)")
        result = downgrade_to_unclassified(result, "judge_score_low")
        result["verification"] = {
            "rule_based": rule_check,
            "judge_evaluation": judge_result,
            "final_status": "judge_failed",
        }
        return result
    _log(rid, f"Judge: {judge_result['score']}/10 → PASS → verified")

    result["verification"] = {
        "rule_based": rule_check,
        "judge_evaluation": judge_result,
        "final_status": "verified",
    }
    return result
