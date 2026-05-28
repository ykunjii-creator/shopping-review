"""RPA ↔ AI 서버 데이터 계약 테스트.

RPA의 dtReviews는 모든 컬럼이 문자열이라 rating이 "5"/"" 형태로 들어온다.
한 건의 빈/비정상 별점 때문에 배치 전체가 422로 죽지 않아야 한다.
"""
from main import AnalyzeRequest, ReviewIn


def test_rating_accepts_numeric_string():
    r = ReviewIn(review_id="R001", text="액정 깨짐", rating="5")
    assert r.rating == 5


def test_rating_empty_string_becomes_none():
    r = ReviewIn(review_id="R002", text="별점 없음", rating="")
    assert r.rating is None


def test_rating_non_numeric_becomes_none():
    r = ReviewIn(review_id="R003", text="이상한 별점", rating="N/A")
    assert r.rating is None


def test_rating_decimal_string_truncates():
    r = ReviewIn(review_id="R004", text="소수 별점", rating="4.0")
    assert r.rating == 4


def test_batch_with_mixed_ratings_validates():
    # RPA가 보내는 전형적 페이로드(문자열 별점 + 빈 별점 혼재)
    req = AnalyzeRequest(
        batch_id="20260528_001",
        reviews=[
            {"review_id": "R001", "text": "액정 깨짐", "rating": "2", "review_date": "2026-05-25"},
            {"review_id": "R002", "text": "별점 누락 케이스", "rating": "", "review_date": ""},
        ],
    )
    assert len(req.reviews) == 2
    assert req.reviews[0].rating == 2
    assert req.reviews[1].rating is None
