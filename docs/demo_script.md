# 데모 대본 (D3)

> 14주차 발표 5~7분 시연 흐름. PRD §8 기준. 라이브 + 백업 영상 둘 다 준비.

## 사전 준비 (발표 전)

- [ ] Windows: UiPath Studio서 `Scrape_Reviews.xaml` 셀렉터 Indicate 재캡처 완료.
- [ ] AI 서버 기동: `cd ai_server && uvicorn main:app --reload` (포트 8000, `.env`에 `OPENAI_API_KEY`).
- [ ] `GET /health` 200 확인.
- [ ] 올리브영 라운드랩 1025 독도 토너 URL 확보 → `in_GoodsUrl`.
- [ ] Outlook 로그인 (본인 메일 a01039261344@gmail.com).
- [ ] 화면 3분할: UiPath Studio · FastAPI 콘솔 · Outlook.
- [ ] **백업 영상** 1회 녹화(차단 대비).

## 시연 흐름

### 1. (30초) 시작 멘트
> "12주차 피드백을 반영해 시스템을 강화했습니다. 특히 Agentic AI의 역할 확장과 **검증 시스템** 도입에 집중했습니다."

### 2. (30초) 환경 소개
- 3분할 화면 설명: RPA(UiPath) = 손발, AI(Python) = 두뇌, 검증 = 안전망.

### 3. (2분) UiPath 봇 실행 — 수집
- `Main.xaml` 실행 (`in_GoodsUrl` 주입).
- 올리브영 자동 접속 → 리뷰 탭 클릭 → 리뷰 20건 스크래핑 → DataTable.
- 수집 검증(건수/빈텍스트/중복) 통과 멘트.

### 4. (2분) AI 분석 + 검증 ★핵심★
- FastAPI 콘솔 실시간 로그:
  ```
  [R001] Main Agent 분석 중...
  [R001] 분석 완료: 제품결함 (conf 0.95)
  [R001] Rule-based: PASS
  [R001] Judge: 9/10 → PASS → verified

  [R002] Main Agent 분석 중...
  [R002] Rule-based: PASS
  [R002] Judge: 6/10 → FAIL → 미분류 (사람 확인)
  ```
- 멘트: **"AI 결과를 그냥 믿지 않습니다. Rule-based + Judge LLM 이중 검증."**

### 5. (1.5분) 엑셀 + 메일 결과
- `Master_Log.xlsx`: **RED**(미분류/conf<0.7) · **YELLOW**(urgency=high) 하이라이트.
- `종합_분석_리포트.xlsx` ★신규 차별점★: 결함 유형별 빈도 / key_findings 4시트.
- Outlook: `[긴급] 제품결함 N건 탐지` 메일 도착 확인 + 첨부 리포트.

### 6. (30초) 검증 결과 어필
> "정답셋 20건 대비 정확도 90% 달성. 검증 시스템으로 AI 오류를 사전 탐지."
- `tests/evaluate_accuracy.py` 수치 화면.

### 7. (30초) 마무리
> "단순히 작동하는 시스템이 아니라, **AI 결과를 신뢰할 수 있게 만드는** 시스템을 구현했습니다."

## 리스크 & 대응
| 리스크 | 대응 |
|---|---|
| 올리브영 차단(라이브 실패) | **백업 영상** 재생. fallback 없음(설계 선택). |
| 셀렉터 변경으로 수집 0건 | Retry 3회 후 안전종료 로그 노출 → 백업 영상. |
| OpenAI API 지연/에러 | 해당 건만 미분류, 배치 계속(§6) — 오히려 견고성 어필 |
| web_search 미발동 | batch 대부분 high-conf라 정상. 저신뢰 케이스서만 발동 설명. |
