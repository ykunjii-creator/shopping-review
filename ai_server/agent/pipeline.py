"""검증 통합 파이프라인 (tech-spec §4.3, PRD §4.10.4) — 배치판.

흐름: analyze_batch(1회) → rule_based(로컬, fail시 judge skip) → judge_batch(1회) → final_status.
콘솔에 단계 로그 출력 (데모 하이라이트, PRD §8).
"""
from __future__ import annotations

from agent.core import analyze_batch
from agent.judge import judge_batch
from agent.validators import downgrade_to_unclassified, rule_based_validate


def _log(review_id: str, msg: str) -> None:
    print(f"[{review_id}] {msg}", flush=True)


def analyze_and_verify_batch(reviews: list[dict]) -> list[dict]:
    """리뷰 N건: 배치 분석 1회 + rule-based(로컬) + judge 배치 1회. 입력 순서 유지."""
    if not reviews:
        return []

    _log("batch", f"Main Agent 배치 분석 중... ({len(reviews)}건)")
    analyses = analyze_batch(reviews)

    final: list[dict | None] = [None] * len(reviews)
    pending: list[tuple[int, dict, dict, dict]] = []  # (idx, review, result, rule_check)

    # ① Rule-based (로컬, 호출 없음)
    for idx, (review, result) in enumerate(zip(reviews, analyses)):
        rid = review.get("review_id", "?")
        rule_check = rule_based_validate(result)
        if not rule_check["passed"]:
            _log(rid, f"Rule-based: FAIL {rule_check['failed_rules']} → 미분류 (Judge skip)")
            result = downgrade_to_unclassified(result, "rule_based_failed")
            result["verification"] = {
                "rule_based": rule_check,
                "judge_evaluation": None,
                "final_status": "rule_based_failed",
            }
            final[idx] = result
        else:
            _log(rid, "Rule-based: PASS")
            pending.append((idx, review, result, rule_check))

    # ② Judge (rule 통과분 전체를 1회 호출)
    judgments: dict[str, dict] = {}
    if pending:
        _log("batch", f"Judge 배치 평가 중... ({len(pending)}건)")
        judgments = judge_batch(
            [p[1] for p in pending],
            [p[2] for p in pending],
        )

    for idx, review, result, rule_check in pending:
        rid = review.get("review_id", "?")
        judge_result = judgments.get(rid)
        if judge_result is None or not judge_result["passed"]:
            score = judge_result["score"] if judge_result else "N/A"
            _log(rid, f"Judge: {score}/10 → FAIL → 미분류 (사람 확인)")
            result = downgrade_to_unclassified(result, "judge_score_low")
            result["verification"] = {
                "rule_based": rule_check,
                "judge_evaluation": judge_result,
                "final_status": "judge_failed",
            }
        else:
            _log(rid, f"Judge: {judge_result['score']}/10 → PASS → verified")
            result["verification"] = {
                "rule_based": rule_check,
                "judge_evaluation": judge_result,
                "final_status": "verified",
            }
        final[idx] = result

    return [r for r in final if r is not None]


def analyze_and_verify(review: dict) -> dict:
    """단일 리뷰 처리 — 배치판의 얇은 래퍼 (하위호환·테스트용)."""
    return analyze_and_verify_batch([review])[0]
