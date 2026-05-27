# 구현 계획 체크리스트: AI 리뷰 결함 분석 시스템

> PRD.md(무엇/왜) + tech-spec.md(어떻게)를 받아 **실행 단위**로 쪼갠 구현 문서.
> LLM = OpenAI 전면 통일 (메인 `gpt-5.4-mini`, Judge `gpt-5.4-nano`). API = Responses API + function calling(strict) + structured outputs + hosted `web_search`.
> 플랫폼 분리: AI 서버(Python)는 Mac서 완전 구현·검증. UiPath xaml은 Windows Studio.

---

## Phase A — AI 서버 (Mac서 구현·검증 가능) · PRD Day1~2

디렉토리: `ai_server/`

| # | 단계 | 파일 | 검증 | 상태 |
|---|---|---|---|---|
| A1 | 프로젝트 셋업 | `requirements.txt`, `.env.example`, `.gitignore`, `config.py` | `python -c "import config"` | ✅ |
| A2 | 부서매핑 데이터 | `data/department_map.json` | json 로드 OK | ✅ |
| A3 | 프롬프트 | `agent/prompts.py` | import OK | ✅ |
| A4 | Tool 정의 | `agent/tools.py` | lookup 호출→부서 반환 | ✅ |
| A5 | Agent 루프 | `agent/core.py` | A8서 통합검증 | ✅ |
| A6 | Rule-based 검증 | `agent/validators.py` | `pytest test_validators.py` | ✅ |
| A7 | Judge | `agent/judge.py` | mock/실호출 1건 | ✅ |
| A8 | 검증 통합 | `agent/pipeline.py` | 단건→verified JSON | ✅ |
| A9 | 종합분석 | `agent/aggregator.py` | 5건→summary_analysis | ✅ |
| A10 | FastAPI | `main.py` | `uvicorn main:app` 기동 | ✅ |
| A11 | 테스트 | `tests/test_scenarios.py`, `tests/test_validators.py` | `pytest` 통과 | ✅ |
| A12 | E2E 단건/배치 | `tests/sample_20.json` | curl → PRD §4.3 스키마 | ✅ 실호출 검증 (정확도 90%, pass_rate 0.95) |

**마일스톤**: `curl POST /analyze-reviews`에 20건 → 검증된 results + summary_analysis JSON. 콘솔 `[R001] Rule:PASS Judge:9/10 → verified` 로그.

> 실호출엔 `OPENAI_API_KEY` 필요. 코드 + mock 테스트는 키 없이 완성. A7 실측/A12는 키 확보 후.

---

## Phase B — 외부 검증 데이터 (Mac) · PRD Day4 일부

| # | 단계 | 파일 | 상태 |
|---|---|---|---|
| B1 | 정답셋 | `data/ground_truth.json` (스켈레톤+예시, 라벨은 사용자) | ✅ |
| B2 | 정확도 스크립트 | `tests/evaluate_accuracy.py` | ✅ |

---

## Phase C — UiPath RPA · PRD Day3

**Mac서 xaml 골격 전부 생성 완료.** 셀렉터 재캡처·실행은 Windows Studio.

| # | 산출 | 내용 | 상태 |
|---|---|---|---|
| C0 | `rpa_workflow/project.json` | 호환성 Windows, VB.NET, 패키지 5종, 인자 `in_GoodsUrl` | ✅ Mac |
| C1 | `Main.xaml` | 오케스트레이션(§5.3): 수집→0건체크→JSON→HTTP POST→처리→결함메일→종합→RPA검증→로그 | ✅ Mac 골격 |
| C2 | `Scrape_Reviews.xaml` | 라이브 수집(§5.4): Open Browser→리뷰탭→Extract Data 20건→수집검증→Retry 3회(§9.7). **셀렉터 placeholder** | ✅ Mac 골격 / ⏳ Indicate |
| C3 | `Process_Results.xaml` | JSON 파싱(§5.5)→Master_Log 12컬럼 누적→RED/YELLOW 하이라이트→out defect_count·summary | ✅ Mac 골격 |
| C4 | `Send_Urgent_Mail.xaml` | 결함필터→긴급리포트 xlsx→Outlook "[긴급]..." 3회 재시도 | ✅ Mac 골격 / ⏳ Outlook |
| C5 | `Generate_Summary_Report.xaml` | 종합리포트 4시트(§5.7) | ✅ Mac 골격 |
| C6 | `Verify_RPA_Results.xaml` | RPA 실행검증 6항목(§5.9)→execution_log.txt | ✅ Mac 골격 |

- xaml 6개 XML well-formed 검증 통과, project.json JSON 파싱 OK.
- skills 설치(`uip skills install`) 불필요 — hand-author로 대체.
- ⚠️ Studio 스키마 엄격 → 안 열리면 액티비티 재배치 필요. 골격/인자/로직 유효.

**마일스톤(나중·Windows)**: Studio서 셀렉터 재캡처 → 서버 기동 → Main 실행 → 라이브 수집→분석→엑셀(RED/YELLOW)→Outlook E2E 1회 + 백업영상.

## Phase D — 미구현분 정리 (문서)

| # | 산출 | 상태 |
|---|---|---|
| D1 | `docs/scraping_target.md` (타겟 라운드랩 1025 독도 토너/URL/셀렉터/절차) | ✅ |
| D2 | `docs/api_spec.md` (PRD §4.3 요청·응답·12컬럼 매핑) | ✅ |
| D3 | `docs/demo_script.md` (PRD §8 시연 흐름) | ✅ |
| D4 | `docs/verification_strategy.md` (3계층 검증) | ✅ |
| D5 | `README.md` (실행법·아키텍처·Windows 이전) | ✅ |
| D6 | `ai_server/data/ground_truth.json` 라벨 사람 최종 확정 | ⏳ 사용자 |
| D7 | implement.md 갱신 | ✅ |

> `docs/14week_presentation.md`는 정확도/수치 확정 후 별도. web_search hosted는 batch 대부분 high-conf라 미발동(정상), 저신뢰 케이스 발동 확인은 실데이터 후.

---

## 검증 (전체)
1. `cd ai_server && pip install -r requirements.txt`
2. `pytest` — validator/시나리오 통과 (mock)
3. `.env`에 키 넣고 `uvicorn main:app --reload`
4. `curl -X POST localhost:8000/analyze-reviews -d @tests/sample_20.json` → PRD §4.3 스키마, `verification`/`summary_analysis` 포함, 콘솔 단계 로그
5. (Windows) skills → xaml → E2E

## 결정 사항 (구현 중 확정)
- 모순(긍정+high): **강등으로 단순화** (데모 명확). `no_positive_high_urgency` rule fail → 미분류.
- Judge 모델: `gpt-5.4-nano` 분리 (교차검증 어필).
- web_search hosted: 실호출 시 가용성/요금 확인. 불가면 `.env`에 `ENABLE_WEB_SEARCH=false` → Rule+Judge 2개로 검증 충족.
- OpenAI strict는 `maxLength` 미지원 가능 → length는 validator가 강제, 스키마는 enum/type/required만 strict.
