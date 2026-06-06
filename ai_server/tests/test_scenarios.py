"""시나리오 테스트 — 5개 케이스 (역설/별점5+결함/단순불만/긍정/모순).

실제 OpenAI 호출 대신 analyze_batch / judge_batch를 mock하여
검증 파이프라인(validators + 강등 + final_status) 로직을 키 없이 검증.
실호출 E2E는 A12(키 확보 후).
"""
import pytest

from agent import pipeline
from agent.aggregator import aggregate_analysis

QUALITY_EMAIL = "a01039261344@gmail.com"


def _result(review_id, category, summary, department, urgency, confidence, text):
    return {
        "review_id": review_id,
        "category": category,
        "summary": summary,
        "department": department,
        "department_email": QUALITY_EMAIL,
        "urgency": urgency,
        "confidence": confidence,
        "reasoning": "테스트",
        "self_check_notes": "재검토 완료",
        "external_evidence": "",
        "original_text": text,
        "original_rating": None,
        "review_date": "2026-05-25",
    }


# review_id → (mock 분석결과, mock judge 점수)
SCENARIOS = {
    # 1. 역설: 별점 높지만 결함 텍스트 → 텍스트 우선
    "R_PARADOX": (
        _result("R_PARADOX", "제품결함", "액정 파손", "품질관리팀", "high", 0.93,
                "별점은 주지만 액정 파손 되어 왔네요"),
        9,
    ),
    # 2. 별점5 + 명확한 결함
    "R_DEFECT5": (
        _result("R_DEFECT5", "제품결함", "전원 작동 불량", "품질관리팀", "high", 0.9,
                "별 다섯개 주는데 전원 작동 불량 있어요"),
        8,
    ),
    # 3. 단순불만
    "R_MINOR": (
        _result("R_MINOR", "단순불만", "색상 취향 차이", "고객지원팀", "low", 0.8,
                "색상이 제 취향이 아니에요"),
        9,
    ),
    # 4. 긍정
    "R_POS": (
        _result("R_POS", "긍정", "재구매 의사 만족", "마케팅팀", "low", 0.95,
                "정말 만족스러워서 재구매 의사 있어요"),
        10,
    ),
    # 5. 모순: 긍정 + high urgency → rule fail → 강등
    "R_CONTRA": (
        _result("R_CONTRA", "긍정", "만족스러운 제품", "마케팅팀", "high", 0.85,
                "만족스러운 제품이에요"),
        9,
    ),
}


@pytest.fixture
def patched(monkeypatch):
    def fake_analyze_batch(reviews):
        return [SCENARIOS[r["review_id"]][0] for r in reviews]

    def fake_judge_batch(reviews, results):
        out = {}
        for r in reviews:
            score = SCENARIOS[r["review_id"]][1]
            out[r["review_id"]] = {"score": score, "passed": score >= 7, "reasoning": "mock"}
        return out

    monkeypatch.setattr(pipeline, "analyze_batch", fake_analyze_batch)
    monkeypatch.setattr(pipeline, "judge_batch", fake_judge_batch)


def _review(rid, text):
    return {"review_id": rid, "text": text, "rating": 5, "review_date": "2026-05-25"}


def test_paradox_verified(patched):
    out = pipeline.analyze_and_verify(_review("R_PARADOX", "별점은 주지만 액정 파손"))
    assert out["category"] == "제품결함"
    assert out["verification"]["final_status"] == "verified"


def test_defect5_verified(patched):
    out = pipeline.analyze_and_verify(_review("R_DEFECT5", "전원 작동 불량"))
    assert out["verification"]["final_status"] == "verified"


def test_minor_verified(patched):
    out = pipeline.analyze_and_verify(_review("R_MINOR", "색상 취향"))
    assert out["category"] == "단순불만"
    assert out["verification"]["final_status"] == "verified"


def test_positive_verified(patched):
    out = pipeline.analyze_and_verify(_review("R_POS", "재구매 의사"))
    assert out["category"] == "긍정"
    assert out["verification"]["final_status"] == "verified"


def test_contradiction_downgraded(patched):
    out = pipeline.analyze_and_verify(_review("R_CONTRA", "만족스러운 제품"))
    # 긍정+high → rule fail → 미분류 강등, judge skip
    assert out["category"] == "미분류"
    assert out["verification"]["final_status"] == "rule_based_failed"
    assert "no_positive_high_urgency" in out["verification"]["rule_based"]["failed_rules"]
    assert out["verification"]["judge_evaluation"] is None


def test_batch_order_and_status(patched):
    reviews = [
        _review("R_PARADOX", "액정 파손"),
        _review("R_CONTRA", "만족"),
        _review("R_POS", "재구매"),
    ]
    out = pipeline.analyze_and_verify_batch(reviews)
    # 입력 순서 유지
    assert [r["review_id"] for r in out] == ["R_PARADOX", "R_CONTRA", "R_POS"]
    # R_CONTRA(긍정+high)는 rule fail → judge skip, 나머지는 verified
    statuses = {r["review_id"]: r["verification"]["final_status"] for r in out}
    assert statuses["R_PARADOX"] == "verified"
    assert statuses["R_CONTRA"] == "rule_based_failed"
    assert statuses["R_POS"] == "verified"


def test_aggregate(patched):
    reviews = [
        _review("R_PARADOX", "액정 파손"),
        _review("R_DEFECT5", "전원 불량"),
        _review("R_MINOR", "색상"),
        _review("R_POS", "만족"),
        _review("R_CONTRA", "만족"),
    ]
    results = pipeline.analyze_and_verify_batch(reviews)
    summary = aggregate_analysis(results)

    assert summary["category_distribution"].get("제품결함") == 2
    assert summary["category_distribution"].get("미분류") == 1
    assert 0.0 <= summary["verification_pass_rate"] <= 1.0
    assert "average_confidence" in summary
    assert isinstance(summary["key_findings"], list)
