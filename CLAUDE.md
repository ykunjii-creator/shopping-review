# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Respond to the user in Korean (한국어). Code, file contents, commit messages, and technical identifiers stay as written unless the user asks otherwise.

## What this is

A review-defect analysis pipeline for Olive Young (올리브영) product reviews. Two independent subsystems that talk **only over HTTP at `localhost:8000`**:

- **`ai_server/`** — Python / FastAPI + OpenAI. The "brain": classifies reviews, self-verifies, aggregates. **Phase A is complete and verified (90% accuracy) — treat it as stable; don't refactor it without reason.**
- **`rpa_workflow/`** — UiPath (Windows, VB.NET). The "hands": scrapes reviews, writes Excel, sends Outlook mail, verifies execution.

Project docs (Korean): `PRD.md`, `tech-spec.md`, `implement.md`, `docs/*`. **`docs/HANDOFF.md` is the live session-handoff doc — read it first for current state.**

## ai_server commands

Run from `ai_server/`:

```bash
python -m venv .venv && .venv\Scripts\activate    # Windows (.venv already present in repo)
pip install -r requirements.txt
copy .env.example .env                            # then set OPENAI_API_KEY=sk-...
uvicorn main:app --reload                         # serves http://localhost:8000
pytest                                            # all tests (mocked — no API key needed)
pytest tests/test_validators.py                  # single file
pytest tests/test_scenarios.py::<name>           # single test
```

Accuracy eval (needs a running server + key):
```bash
curl -s -X POST localhost:8000/analyze-reviews -H 'Content-Type: application/json' -d @tests/sample_20.json > predictions.json
python tests/evaluate_accuracy.py predictions.json
```

Tests are **fully mocked** (`analyze_review` / `judge_evaluate` patched), so `pytest` runs with no `OPENAI_API_KEY`. The OpenAI client is lazy (`config.get_client()`), so importing modules never requires a key.

## ai_server architecture

Single review flows through `agent/pipeline.py::analyze_and_verify`, a **3-layer trust chain** (this is the project's whole point — AI output is never trusted raw):

1. **`agent/core.py::analyze_review`** — agentic loop on the **OpenAI Responses API** (not Chat Completions). Up to `MAX_ITERATIONS` turns; the model autonomously calls `web_search`, `lookup_department_mapping`, and finally `submit_analysis`.
2. **`agent/validators.py::rule_based_validate`** — 9 deterministic checks (summary ≤30 chars, confidence 0–1, valid category/urgency, dept matches category, no positive+high, no defect+low, hallucination heuristic). Any fail → downgrade to 미분류, **Judge skipped**.
3. **`agent/judge.py::judge_evaluate`** — a *different* model (`JUDGE_MODEL`) scores 1–10. Below `JUDGE_PASS_THRESHOLD` (7) → downgrade to 미분류.

`final_status` ends up one of `verified` / `rule_based_failed` / `judge_failed` / `error`. Batch-level rollup is `agent/aggregator.py` (category distribution, defect clustering via LLM re-call with regex fallback, pass rate, key findings, trending keywords).

Categories (`config.py`): `제품결함`, `배송문제`, `단순불만`, `긍정`, plus `미분류` fallback. Each maps to a department/email in `data/department_map.json`. Ground truth for accuracy is `data/ground_truth.json` (labels may still need human confirmation).

### Responses API gotchas (don't regress these)

- Function tools use the **flat** schema (`{"type":"function","name":...,"parameters":...,"strict":true}`), **not** the nested Chat-Completions shape. Don't use `pydantic_function_tool()`.
- `strict: true` requires **every** property in `required` and `additionalProperties: false`. `maxLength` etc. are ignored under strict, so length limits are enforced in `validators.py`, not the schema.
- `web_search` is a hosted tool (`{"type":"web_search"}`), toggled by `ENABLE_WEB_SEARCH`.
- Agent loop accumulates `resp.output` back into `input_list`; only `function_call` items are dispatched (`reasoning`/`message`/hosted tools pass through).

## rpa_workflow (UiPath)

Project: `ReviewDefectRPA`, Windows target, VisualBasic expressions. `Main.xaml` orchestrates via sequential `InvokeWorkflowFile`:

`Scrape_Reviews` → (0 reviews ⇒ safe exit) → HTTP POST `/analyze-reviews` → `Process_Results` → (defects > 0 ⇒ `Send_Urgent_Mail`) → `Generate_Summary_Report` → `Verify_RPA_Results`.

- Single input arg: `in_GoodsUrl` (Olive Young product URL — pasted manually on Windows because the site 403s headless scraping).
- **Data contract**: `dtReviews` (4 cols: `review_id,text,rating,review_date`) → POST → `Master_Log.xlsx` (**12 cols**: 분석일시·리뷰ID·원본텍스트·별점·작성일·카테고리·요약·담당부서·담당메일·긴급도·확신도·판단근거). Highlights: 🔴 미분류 or confidence<0.7, 🟡 urgency=high.
- Conventions: Hungarian prefixes (`str`/`int`/`dt`/`jobj`/`jarr`/`lst`), `in_`/`out_` args, `RetryScope` (×3) for flaky steps, `lstErrors: List(Of String)` accumulation.
- `Scrape_Reviews.xaml` is a **build-clean skeleton** — its UIA activities (`Use Application/Browser`, `Data Scraping`) must be filled in via **Indicate inside Windows Studio** (can't capture headless). See `docs/HANDOFF.md` §B and `docs/scraping_target.md`.

### Validate / build the UiPath project

The bundled Studio dotnet has **runtime only, no SDK**. A .NET 8 SDK was installed *into the Studio folder*; every `uip rpa` compile command must prepend that folder to PATH (the restore packager spawns PATH's `dotnet`). Bash doesn't persist env between calls, so prefix each time:

```bash
export PATH="/c/Users/PC/AppData/Local/Programs/UiPathPlatform/Studio/26.0.193-cloud.23060:$PATH"
uip rpa validate --file-path "Main.xaml" --project-dir "C:\Users\PC\Desktop\shopping-review\rpa_workflow" --output json
uip rpa build "C:\Users\PC\Desktop\shopping-review\rpa_workflow" --output json
```

`read`/`restore`/`validate`/`build` need no login (robot creds). `uip login` is only for pack/publish. Prefer the **`uipath-rpa` skill** for `.xaml` work.

### XAML traps that pass `validate` but fail `build`

- **`LogMessage` strings must be bracketed VB expressions**: `Message="[&quot;텍스트&quot;]"`. Unbracketed strings get normalized to `[""텍스트""]` → `BC30198`/`BC30451`.
- Use **`DateTime.Now`**, not bare `Now` (VB intrinsic needs Microsoft.VisualBasic ref).
- **Two Excel families**: Workbook `ReadRange/WriteRange/AppendRange` (need `WorkbookPath`, used outside a scope) vs scope-child `ExcelReadRange/ExcelWriteRange/ExcelAppendRange` (inside `ExcelApplicationScope`, no path). `ExcelSetRangeColor` requires the scope.
- `InvokeWorkflowFile` args: direct `InArgument`/`OutArgument` + `x:Key`, **not** a `scg:Dictionary` wrapper.
- UIA activities won't build until targets are captured via Indicate.

Confirm exact activity class names with `uip rpa activities find` / `get-default-xaml --project-dir` (the global find index may show a newer package version than the project pins).

## Notes

- `.env` (real key) is gitignored — never commit it. Verify with `git status` before any push.
- `data/department_map.json` currently routes all departments to one demo email.
- Untracked temp files may appear (`*.tmp.json`, `rpa_workflow/.objects/`, `.project/`, `.tmh/`, `Main.xaml.json`); these are Studio scratch — clean via `git clean`, don't commit.
