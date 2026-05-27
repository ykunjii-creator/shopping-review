# API 스펙 (D2)

> AI 서버(Python/FastAPI) ↔ UiPath RPA 간 HTTP 계약. PRD §4.3 기준. 구현: `ai_server/main.py`.

베이스: `http://localhost:8000`

---

## GET /health

서버 상태 확인.

**응답 200**
```json
{ "status": "ok", "main_model": "gpt-5.4-mini", "judge_model": "gpt-5.4-nano" }
```

---

## POST /analyze-reviews

리뷰 배치 → 개별 분석 + 2단 검증(Rule + Judge) → 종합 분석.

### 요청 Body
```json
{
  "batch_id": "20260527_001",
  "reviews": [
    {
      "review_id": "R001",
      "text": "배송도 빠른데 화면 우측 하단에 액정이 깨져서 왔어요. 교환해주세요.",
      "rating": 2,
      "review_date": "2026-05-25"
    }
  ]
}
```

| 필드 | 타입 | 필수 | 비고 |
|---|---|---|---|
| `batch_id` | string | ✅ | 배치 식별자 (`yyyyMMdd_HHmmss` 권장) |
| `reviews[].review_id` | string | ✅ | |
| `reviews[].text` | string | ✅ | 리뷰 본문 |
| `reviews[].rating` | int\|null | ✕ | 1~5 |
| `reviews[].review_date` | string\|null | ✕ | `yyyy-MM-dd` |

### 응답 Body
```json
{
  "batch_id": "20260527_001",
  "processed_count": 20,
  "defect_count": 3,
  "results": [
    {
      "review_id": "R001",
      "category": "제품결함",
      "summary": "우측 하단 액정 파손",
      "department": "품질관리팀",
      "department_email": "a01039261344@gmail.com",
      "urgency": "high",
      "confidence": 0.95,
      "reasoning": "물리적 파손은 명확한 제품 결함이며 교환 요청 발생",
      "self_check_notes": "...",
      "external_evidence": "",
      "original_text": "배송도 빠른데...",
      "original_rating": 2,
      "review_date": "2026-05-25",
      "verification": {
        "rule_based": { "passed": true, "checks": { "...": true }, "failed_rules": [] },
        "judge_evaluation": { "score": 9, "passed": true, "reasoning": "..." },
        "final_status": "verified"
      }
    }
  ],
  "summary_analysis": {
    "category_distribution": { "제품결함": 3, "배송문제": 2, "단순불만": 5, "긍정": 9, "미분류": 1 },
    "defect_types": { "액정 파손": 2, "포장 불량": 1 },
    "urgency_distribution": { "high": 1, "medium": 4, "low": 15 },
    "average_confidence": 0.88,
    "verification_pass_rate": 0.95,
    "key_findings": ["액정 파손 2건 동일 패턴 발견 - 로트 불량 가능성"],
    "trending_keywords": ["액정", "배송", "..."]
  },
  "execution_time_ms": 12345
}
```

### `results[]` 필드 (RPA가 Master_Log 12컬럼 매핑에 사용)

| 응답 필드 | → Master_Log 컬럼 |
|---|---|
| (수신 시각) | 분석일시 |
| `review_id` | 리뷰ID |
| `original_text` | 원본텍스트 |
| `original_rating` | 별점 |
| `review_date` | 작성일 |
| `category` | 카테고리 |
| `summary` | 요약 |
| `department` | 담당부서 |
| `department_email` | 담당메일 |
| `urgency` | 긴급도 (high/medium/low) |
| `confidence` | 확신도 (0.0~1.0) |
| `reasoning` | 판단근거 |

> `self_check_notes`, `external_evidence`, `verification`은 응답엔 있으나 Master_Log 12컬럼엔 미포함(검증 메타).

### `verification.final_status` 값
| 값 | 의미 | RPA 처리 |
|---|---|---|
| `verified` | Rule+Judge 통과 | 정상 |
| `rule_based_failed` | Rule 실패 → 미분류 강등 | RED |
| `judge_failed` | Judge <7점 → 미분류 강등 | RED |
| `error` | 처리 중 예외 → 미분류 | RED |

### 카테고리 → 부서 매핑 (`data/department_map.json`)
| category | department | 긴급 메일 트리거 |
|---|---|---|
| 제품결함 | 품질관리팀 | ✅ (defect_count>0) |
| 배송문제 | 물류팀 | |
| 단순불만 | 고객지원팀 | |
| 긍정 | 마케팅팀 | |
| 미분류 | 고객지원팀(사람확인) | |

### 에러/예외 (PRD §6)
- 개별 리뷰 처리 실패 → 해당 건만 `미분류` + `verification.final_status="error"`, **배치는 계속**.
- 신규 리뷰 0건 → RPA가 AI 호출 차단(서버 호출 안 함), 정상 종료.
- AI API 에러 → 서버 내부 3회 재시도 후 해당 건만 미분류.
