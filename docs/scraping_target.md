# 스크래핑 타겟 명세 (D1)

> Phase C `Scrape_Reviews.xaml`가 수집할 대상·URL·셀렉터·획득 절차. PRD §5.4 / tech-spec §9.7 근거.

## 1. 타겟 상품

| 항목 | 값 |
|---|---|
| 상품 | **라운드랩 1025 독도 토너** (올리브영 토너 베스트셀러, 리뷰 수천 건) |
| 카테고리 | 스킨케어 / 토너 |
| 선정 이유 | 리뷰 표본 풍부 → 결함/배송/단순불만/긍정 4분류 골고루 나옴. 데모 설득력. |
| 대안 | 아누아 어성초 토너 / 토리든 다이브인 세럼 |

## 2. URL 구조

```
https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=<상품번호>&dispCatNo=<카테고리번호>
```

- 실제 `goodsNo` / `dispCatNo`는 **Mac서 획득 불가** — 올리브영 메인 **HTTP 403**(봇 차단)으로 requests 직접 호출 불가.
- → **`project.json` 인자 `in_GoodsUrl`로 분리.** 사용자가 Windows 브라우저서 상품 페이지를 열고 주소창 URL을 복붙해 주입.

## 3. 수집 방식 (확정)

- **라이브 스크래핑만.** 고정 샘플 fallback 없음.
- 올리브영 메인 403 → 직접 requests 불가 → **브라우저 자동화(UiPath UIAutomation) 필수**.
- 차단 위험은 **§9.7 Retry 3회 + 안전 종료**로만 방어. 데모 중 차단되면 실패 감수.

## 4. 리뷰 영역 셀렉터 (참고 — 실제는 Studio Indicate로 재캡처)

| 요소 | 셀렉터(참고) |
|---|---|
| 리뷰 탭 | XPath `//*[@id="reviewInfo"]/a` |
| 리뷰 리스트 컨테이너 | `#gdasContentsArea #gdasList` |
| 개별 리뷰 | `#gdasList > li` |
| 리뷰 텍스트 | `.review_cont .txt` |
| 별점 | `.review_point .point` (또는 `.grade_img` width %) |
| 작성일 | `.review_info .date` |
| 페이지네이션 | `#gdasContentsArea .pageing a` |

> ⚠️ 올리브영은 DOM/클래스명을 수시 변경. 위 셀렉터는 **레퍼런스**일 뿐, Windows Studio의 **Data Scraping 마법사 + Indicate**로 재캡처해 `ExtractMetadata`를 새로 생성해야 한다.

## 5. 수집 스키마 (Scrape 출력 DataTable)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| `review_id` | String | 행번호 기반 R001~ 부여 (페이지엔 ID 없음) |
| `text` | String | 리뷰 본문 |
| `rating` | Int32 | 별점(1~5). width% → 점수 환산 필요할 수 있음 |
| `review_date` | String | `yyyy-MM-dd` 또는 페이지 표기 그대로 |

- 목표 **20건** 수집(데모 표본). 1페이지 내에서 충분.
- AI 서버 요청은 이 4컬럼 → `{batch_id, reviews:[{review_id,text,rating,review_date}]}` ([api_spec.md](api_spec.md)).

## 6. 획득/실행 절차 (Windows)

1. Chrome서 올리브영 → 라운드랩 1025 독도 토너 상품 페이지 열기.
2. 주소창 URL 복사 → `Main.xaml` 실행 시 `in_GoodsUrl` 인자에 붙여넣기.
3. UiPath Studio서 `Scrape_Reviews.xaml` 열기 → Data Scraping 마법사로 리뷰 텍스트/별점/작성일 Indicate → `ExtractMetadata` 갱신.
4. 헤드리스 해제(사람처럼), 페이지 대기 1.5→3s 권장(§9.7).
5. 실행 → 20건 DataTable 확인.

## 7. 차단 대응 (§9.7 요약)

- Try-Catch + Retry 3회: `SelectorNotFoundException` / 로딩 >5s / "차단되었습니다" 텍스트 감지.
- 3회 실패 → 관리자 경고 메일 + `execution_log.txt` 기록 + 안전 종료.
- 추가책: User-Agent 변경, 페이지 대기 증가, 헤드리스 해제.
