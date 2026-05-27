"""환경 설정 + OpenAI 클라이언트 singleton.

tech-spec §6. 키 없이도 import 가능해야 함 (mock 테스트용) → 클라이언트는 lazy 생성.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# ai_server/.env 우선, 없으면 repo 루트 .env
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


# --- 설정값 (tech-spec §6 .env) ---
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
SERVER_PORT: int = _get_int("SERVER_PORT", 8000)
MAIN_MODEL: str = os.getenv("MAIN_MODEL", "gpt-5.4-mini")
JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", "gpt-5.4-nano")
MAX_ITERATIONS: int = _get_int("MAX_ITERATIONS", 5)
JUDGE_PASS_THRESHOLD: int = _get_int("JUDGE_PASS_THRESHOLD", 7)
CONFIDENCE_THRESHOLD: float = _get_float("CONFIDENCE_THRESHOLD", 0.7)
ENABLE_WEB_SEARCH: bool = _get_bool("ENABLE_WEB_SEARCH", True)

# 분류 카테고리 (PRD §4.4)
CATEGORIES: list[str] = ["제품결함", "배송문제", "단순불만", "긍정"]
UNCLASSIFIED: str = "미분류"

DEPARTMENT_MAP_PATH = BASE_DIR / "data" / "department_map.json"
GROUND_TRUTH_PATH = BASE_DIR / "data" / "ground_truth.json"


@lru_cache(maxsize=1)
def get_client():
    """OpenAI 클라이언트 singleton. 키 없으면 RuntimeError (호출 시점에만)."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY 미설정. ai_server/.env 에 키를 넣으세요 (.env.example 참고)."
        )
    from openai import OpenAI

    return OpenAI(api_key=OPENAI_API_KEY)
