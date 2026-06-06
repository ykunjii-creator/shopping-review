"""FastAPI 진입점 (PRD §4.3).

GET /health, POST /analyze-reviews (배치 → 검증 → 종합분석 → JSON).
"""
from __future__ import annotations

import time
import traceback
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from config import MAIN_MODEL, JUDGE_MODEL, SERVER_PORT
from agent.aggregator import aggregate_analysis
from agent.core import _unclassified
from agent.pipeline import analyze_and_verify_batch

app = FastAPI(title="리뷰 결함 분석 AI 서버", version="2.0")


class ReviewIn(BaseModel):
    review_id: str
    text: str
    rating: Optional[int] = None
    review_date: Optional[str] = None

    @field_validator("rating", mode="before")
    @classmethod
    def _coerce_rating(cls, v):
        # RPA의 DataTable은 별점을 문자열("5")이나 빈 값("")로 보냄.
        # 빈/비숫자는 None으로 흡수해 한 건 때문에 배치 전체가 422로 죽는 것을 막는다.
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                return int(float(v))
            except ValueError:
                return None
        return v


class AnalyzeRequest(BaseModel):
    batch_id: str
    reviews: list[ReviewIn]


class AnalyzeResponse(BaseModel):
    batch_id: str
    processed_count: int
    defect_count: int
    results: list[dict]
    summary_analysis: dict
    execution_time_ms: int = Field(..., description="처리 소요 시간(ms)")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "main_model": MAIN_MODEL, "judge_model": JUDGE_MODEL}


@app.post("/analyze-reviews", response_model=AnalyzeResponse)
def analyze_reviews(req: AnalyzeRequest) -> AnalyzeResponse:
    start = time.perf_counter()
    print(f"\n=== 배치 {req.batch_id} 수신: {len(req.reviews)}건 ===", flush=True)

    reviews = [r.model_dump() for r in req.reviews]
    try:
        results = analyze_and_verify_batch(reviews)
    except Exception as e:  # 배치 분석/검증 자체 실패 → 전건 미분류, 응답은 계속 (PRD §6)
        traceback.print_exc()
        results = []
        for review in reviews:
            res = _unclassified(review, f"처리 오류: {e}")
            res["verification"] = {
                "rule_based": None, "judge_evaluation": None, "final_status": "error",
            }
            results.append(res)

    defect_count = sum(1 for r in results if r.get("category") == "제품결함")
    summary = aggregate_analysis(results)
    elapsed = int((time.perf_counter() - start) * 1000)
    print(f"=== 배치 {req.batch_id} 완료: defect={defect_count}, {elapsed}ms ===\n", flush=True)

    return AnalyzeResponse(
        batch_id=req.batch_id,
        processed_count=len(results),
        defect_count=defect_count,
        results=results,
        summary_analysis=summary,
        execution_time_ms=elapsed,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
