# HANDOFF — 세션 인계 문서

> 세션 재시작 후 이걸 먼저 읽고 이어가면 됨. 작성: 2026-05-28. 갱신: 2026-05-28 (Mac 검증 한계 규명).

## 🚨 결론: XAML 재생성은 Windows에서 해야 함 (Mac 검증 불가 확정)

`uipath-rpa` 스킬의 validate/build/run 루프가 **Windows 타깃 프로젝트에선 Mac서 안 돔.**
macOS Helm 호스트가 `targetFramework:"Windows"` 프로젝트 자체를 못 엶:
```
Cannot execute Windows projects on Linux platform
```
→ validate / build / run / `activities get-default-xaml` / `.local/docs` 생성 전부 프로젝트 open 선행이라 **Mac서 전부 막힘.** Outlook·Excel classic·browser UIAutomation이 Windows 전용이라 Portable 변환도 불가.

**∴ "스킬로 재생성"은 Windows 머신에서 진행해야 함.** 어차피 봇 실행도 Windows.

### 🎯 Windows에서 첫 액션
Windows에 repo clone → uip CLI 설치(`npm i -g @uipath/cli`, dotnet SDK는 Windows Studio에 포함) → `uip login` → Claude Code 켜고 이 프롬프트:
> "uipath-rpa 스킬로 rpa_workflow xaml 6개 재생성. PRD.md / tech-spec.md 가 스펙, 기존 xaml은 로직 설계서. validate/build 클린까지 돌려. UI automation(Scrape_Reviews) 셀렉터는 Indicate placeholder stub으로."

스킬 로드 확인: 사용 가능 스킬 목록에 **`uipath-rpa`** 떠야 함.

---

## 📍 왜 재생성하나 (핵심 배경)

기존 `rpa_workflow/*.xaml` 6개는 **Mac서 hand-author** (UiPath 스킬/Studio 없이 손으로 작성). → **Studio 검증 실패, 액티비티 에러 다수.**

에러 증거: `docs/errors/다운로드 (1).png` (사용자가 Windows Studio서 캡처). 2개 층:

1. **NuGet 복원 실패** — `project.json` 패키지 버전 오타.
   `NU1102: UiPath.Mail.Activities (= 1.23.4) 없음, 최근 1.23.10`. 다른 패키지도 의심.
2. **XAML 스키마 불일치** — hand-author 추측이 실제 UiPath와 안 맞음:
   - `HttpClient.ResponseContentFormat` 멤버 없음
   - `BuildDataTable.TableName` / `.DataTableInput` 멤버 없음
   - `DeserializeJson` 형식 자체 못 찾음
   - `ExcelApplicationScope` Body 구조 틀림 (Sequence에 Body 없음 / ActivityAction(WorkbookApplication) 할당 불가)
   - `ReadRange/WriteRange/AppendRange` Body·Result·`ContinueOnError` 문제
   - `SetRangeColor` 못 찾음, `OutlookMailMessage`/`RetryScope` Body 없음
   - `InvokeMethod` TargetObject에 String 할당 불가

→ Mac서 XML 더 손보는 건 추측 = 두더지잡기. **스킬로 재생성이 정석.**

---

## ✅ 2026-05-28 (2번째 세션) 한 것
- **project.json 버전 오타 2개 교정** (live 피드 검증): `UiPath.Mail.Activities [1.23.4]→[1.23.10]` (1.23.4 피드에 없음=NU1102 원인), `UiPath.UIAutomation.Activities [23.10.5]→[23.10.6]` (23.10.5도 피드에 없음 — 핸드오프가 못 잡은 2번째 오타). System 23.10.3 / Excel 2.23.4 / WebAPI 1.16.2는 존재 확인됨.
- 검증 툴체인 게이트 규명: dotnet SDK `~/.dotnet`에 격리 설치(8.0.421) + `uip login` 완료 → 피드 조회는 됨. 그러나 위 플랫폼 한계로 프로젝트 open 단계서 막힘.
- 프로젝트 컨텍스트 문서 생성: `rpa_workflow/.claude/rules/project-context.md` + `rpa_workflow/AGENTS.md`.
- ⚠️ **정리 잔재**: 버전 조회용 임시 Portable 프로젝트 `VerProbe/`가 repo 루트에 남음 (rm 권한 거부됨). 수동 삭제 요망. `~/.dotnet`은 격리 설치라 삭제 자유.

## ✅ 방금(직전 세션) 한 것

- `npm install -g @uipath/cli` → `uip` v1.1.0 설치됨 (`/opt/homebrew/bin/uip`).
- `uip skills install --agent claude` → **20개 스킬 설치 성공** (`uipath-rpa` 포함).
  - 플러그인 등록: `uipath@uipath-marketplace` v0.0.32
  - 위치: `~/.claude/plugins/marketplaces/uipath-marketplace/skills/uipath-rpa/SKILL.md`
- ⚠️ **로그인 안 함.** `uip login` (브라우저, UiPath Cloud 계정) — 패키지 피드 접근/pack/publish 필요 시. 재생성 중 버전 검증에 필요하면 사용자가 터미널에 `! uip login` 실행.
- ⚠️ 스킬은 **이번 재시작 후에야 로드됨** (이전 세션엔 미로드라 못 씀).

---

## 📦 프로젝트 상태 (Phase별)

| Phase | 내용 | 상태 |
|---|---|---|
| A | AI 서버 (`ai_server/`, FastAPI+OpenAI, 분석·Rule·Judge·종합) | ✅ 완료·실호출 검증 (정확도 90%, pass_rate 0.95) |
| B | 정답셋 + 정확도 스크립트 | ✅ 완료. `ai_server/data/ground_truth.json` 라벨 사람 확정 필요 |
| C | UiPath xaml 6 + project.json | ❌ **재생성 필요** (위 에러). 현재 hand-author = 설계서 |
| D | docs (`docs/`) | ✅ 완료 |

**AI 서버는 건드리지 마라 — 검증 끝남.** RPA만 다시.

### 데이터 계약 (재생성 시 반드시 유지)
- 엔드포인트: `POST http://localhost:8000/analyze-reviews` (스키마: `docs/api_spec.md`)
- 요청: `{batch_id, reviews:[{review_id,text,rating,review_date}]}`
- 응답 results 필드 → Master_Log **12컬럼**: 분석일시·리뷰ID·원본텍스트·별점·작성일·카테고리·요약·담당부서·담당메일·긴급도·확신도·판단근거
- 하이라이트: 🔴 미분류 OR confidence<0.7 / 🟡 urgency=high (tech-spec §9.4)
- 워크플로 6개 역할: `tech-spec §9.1`, 흐름: `PRD §5.3~5.10`
- 인자: `in_GoodsUrl` (올리브영 상품 URL, 403 차단 때문에 사용자가 Windows 브라우저서 복붙)
- 스크래핑 타겟/셀렉터: `docs/scraping_target.md` (라운드랩 1025 독도 토너)

---

## 🌿 Git 상태

- 레포: **public** `https://github.com/KoSeonJe/shopping-review` (main)
- `.env`(실키)는 `.gitignore`로 차단됨 — **절대 커밋 금지**. 푸시 전 항상 `git status`로 `.env` 미포함 확인.
- **미커밋 변경분 있음**: `implement.md`(Phase C 에러 반영·C0 스킬설치 추가), `docs/errors/`(에러 이미지), 이 `HANDOFF.md`.
- 정리 대상: `docs/errors/band_0~3.png` (에러 이미지 분석용 임시 크롭 — 지워도 됨).

---

## 🪟 Windows에서 할 일 (재생성·검증 후)

1. `git clone` → `ai_server` 띄우기 (README "빠른 시작" 참고).
2. Studio서 `rpa_workflow/project.json` 열기 → 패키지 복원.
3. `Scrape_Reviews.xaml` 셀렉터 Indicate 재캡처.
4. `Send_Urgent_Mail.xaml` Outlook 연결.
5. `Main.xaml` 실행 (`in_GoodsUrl` 주입) → E2E: 수집→분석→엑셀(RED/YELLOW)→메일.

---

## 📚 참고 문서
`README.md` · `PRD.md` · `tech-spec.md` · `implement.md`
`docs/api_spec.md` · `docs/scraping_target.md` · `docs/demo_script.md` · `docs/verification_strategy.md`
