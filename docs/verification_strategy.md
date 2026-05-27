# 검증 전략 (D4)

> "AI 분류기"가 아니라 **"검증된 자동화 시스템"**. 3계층 검증으로 AI 결과를 신뢰 가능하게 만든다. PRD §4.10 / §9.2~9.3 / tech-spec §4.

## 전체 3계층

| 계층 | 구현 | 종류 | 실패 시 |
|---|---|---|---|
| ① AI 결과 검증 | `validators.py` (Python) | **Rule-based** | 미분류 강등 + 엑셀 RED |
| ② AI 결과 검증 | `judge.py` (Python, gpt-5.4-nano) | **LLM-as-a-Judge** | <7점 → 미분류 강등 + 로그 |
| ③ RPA 실행 검증 | `Verify_RPA_Results.xaml` (UiPath) | 파일/컬럼/건수/메일 | execution_log ERROR |

추가: **Self-check**(Agent가 submit 전 자기 결과 1회 재검토, `prompts.py`) + **External**(`ground_truth.json` 정답셋 대비 정확도, 발표용 사후 측정).

## ① Rule-based (`validators.py`)

submit된 결과를 규칙으로 검사. 하나라도 실패 → 미분류 강등(Judge skip).

| 규칙 | 내용 |
|---|---|
| `summary_length_ok` | summary 길이 제한(명사 위주 20자 내외) |
| `confidence_in_range` | 0.0~1.0 |
| `category_valid` | 4종(+미분류) enum |
| `no_contradiction` / `no_positive_high_urgency` | 모순 검사. **긍정+high urgency → 강등으로 단순화**(데모 명확성) |

## ② LLM-as-a-Judge (`judge.py`)

- 별도 모델 `gpt-5.4-nano`로 **교차 검증**(메인 `gpt-5.4-mini`와 분리 → 어필 포인트).
- 원문 vs 분류/요약/부서 매핑 적절성을 0~10점 평가.
- `JUDGE_PASS_THRESHOLD=7` 미만 → 미분류 강등 + `judge_reasoning` 로그.

## ③ RPA 실행 검증 (`Verify_RPA_Results.xaml`)

14주차 코칭의 "RPA 실행 결과 검증" 요구. 결과물이 실제로 만들어졌는지 확인.

| 항목 | 방법 | 실패 |
|---|---|---|
| 생성 파일 존재 | Path Exists | ERROR |
| 필수 12컬럼 포함 | Read Range 헤더 확인 | ERROR |
| 처리 건수 일치 | 추가행수 == 입력수 | ERROR |
| 빈 셀 없음 | For Each Row(카테고리/요약) | WARNING |
| 메일 발송 성공 | Outlook 보낸편지함 1분내 "[긴급]" | ERROR |
| 로그 기록 | execution_log.txt 존재 | 권한 확인 |

## 검증 통합 흐름 (`pipeline.py`)

```
analyze_review (Main Agent + Self-check)
   → Rule-based  ─FAIL→ 미분류 강등 (Judge skip)
   → PASS → Judge ─FAIL(<7)→ 미분류 강등
   → PASS → final_status = verified
```

콘솔 로그(데모 하이라이트): `[R001] Rule-based: PASS` / `[R001] Judge: 9/10 → PASS → verified`.

## 엑셀 하이라이트 규칙 (tech-spec §9.4)
| 조건 | 색 |
|---|---|
| category=미분류 **또는** confidence<0.7 | RED |
| urgency=high | YELLOW |

## External — 정확도 측정 (`ground_truth.json` + `evaluate_accuracy.py`)
- 사람이 라벨링한 정답셋 20건 대비 category/urgency 정확도 산출.
- 현재 실측: **정확도 90%, verification_pass_rate 0.95** (손으로 만든 가짜 리뷰 20건 기준).
- 실제 올리브영 데이터 수집 후 재측정 필요.
- ⚠️ `data/ground_truth.json`의 `true_*` 라벨은 **예시** — 사람이 최종 확정해야 함(D6).
