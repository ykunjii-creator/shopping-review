"""Rule-based 검증 단위 테스트 (API 불필요)."""
from agent.validators import (
    downgrade_to_unclassified,
    rule_based_validate,
)


def _base_result(**over) -> dict:
    r = {
        "review_id": "R001",
        "category": "제품결함",
        "summary": "우측 하단 액정 파손",
        "department": "품질관리팀",
        "department_email": "a01039261344@gmail.com",
        "urgency": "high",
        "confidence": 0.95,
        "reasoning": "물리적 파손",
        "original_text": "배송도 빠른데 우측 하단 액정 파손 되어 왔어요 교환해주세요",
    }
    r.update(over)
    return r


def test_valid_result_passes():
    out = rule_based_validate(_base_result())
    assert out["passed"], out["failed_rules"]


def test_summary_too_long_fails():
    out = rule_based_validate(_base_result(summary="가" * 31))
    assert not out["passed"]
    assert "summary_length_ok" in out["failed_rules"]


def test_confidence_out_of_range_fails():
    out = rule_based_validate(_base_result(confidence=1.5))
    assert "confidence_in_range" in out["failed_rules"]


def test_invalid_category_fails():
    out = rule_based_validate(_base_result(category="이상한카테고리"))
    assert "category_valid" in out["failed_rules"]


def test_email_format_fails():
    out = rule_based_validate(_base_result(department_email="bademail"))
    assert "email_format_ok" in out["failed_rules"]


def test_positive_high_urgency_contradiction_fails():
    out = rule_based_validate(
        _base_result(category="긍정", department="마케팅팀", urgency="high",
                     summary="정말 만족스러운 제품", original_text="정말 만족스러운 제품이에요")
    )
    assert "no_positive_high_urgency" in out["failed_rules"]


def test_defect_low_urgency_fails():
    out = rule_based_validate(_base_result(urgency="low"))
    assert "defect_urgency_ok" in out["failed_rules"]


def test_department_mismatch_fails():
    out = rule_based_validate(_base_result(department="물류팀"))
    assert "department_matches" in out["failed_rules"]


def test_hallucination_detected():
    # summary가 원문에 전혀 없는 내용
    out = rule_based_validate(
        _base_result(summary="배터리 발화 폭발 위험", original_text="색깔이 화면이랑 좀 달라요")
    )
    assert "no_hallucination" in out["failed_rules"]


def test_downgrade_to_unclassified():
    d = downgrade_to_unclassified(_base_result(), "rule_based_failed")
    assert d["category"] == "미분류"
    assert d["urgency"] == "low"
    assert d["needs_human_review"] is True
    assert d["downgrade_reason"] == "rule_based_failed"
