"""정확도 측정 (PRD §4.10.3 External verification).

사용법:
  1) 서버 기동 후 sample_20.json POST → 응답 JSON을 predictions.json으로 저장
     curl -s -X POST localhost:8000/analyze-reviews \\
       -H 'Content-Type: application/json' -d @tests/sample_20.json > predictions.json
  2) python tests/evaluate_accuracy.py predictions.json

predictions 파일이 없으면 ground_truth만 검증하고 사용법을 안내한다.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GT_PATH = BASE / "data" / "ground_truth.json"


def evaluate(predictions: list[dict], ground_truth: list[dict]) -> dict:
    gt_by_id = {g["review_id"]: g for g in ground_truth}
    correct = 0
    total = 0
    per_cat = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for pred in predictions:
        rid = pred.get("review_id")
        gt = gt_by_id.get(rid)
        if gt is None:
            continue
        total += 1
        pc, tc = pred.get("category"), gt["true_category"]
        if pc == tc:
            correct += 1
            per_cat[tc]["tp"] += 1
        else:
            per_cat[pc]["fp"] += 1
            per_cat[tc]["fn"] += 1

    metrics = {}
    for cat, c in per_cat.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        metrics[cat] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}

    return {
        "accuracy": round(correct / total, 3) if total else 0.0,
        "total": total,
        "correct": correct,
        "category_metrics": metrics,
    }


def main() -> None:
    ground_truth = json.loads(GT_PATH.read_text(encoding="utf-8"))["labeled_reviews"]
    print(f"ground_truth 로드: {len(ground_truth)}건")

    if len(sys.argv) < 2:
        print("\npredictions 파일 미지정. 사용법은 파일 상단 docstring 참고.")
        return

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    predictions = data["results"] if isinstance(data, dict) and "results" in data else data

    report = evaluate(predictions, ground_truth)
    print(f"\n정확도: {report['accuracy']:.0%} ({report['correct']}/{report['total']})")
    print("카테고리별 지표:")
    for cat, m in report["category_metrics"].items():
        print(f"  {cat}: P={m['precision']} R={m['recall']} F1={m['f1']}")


if __name__ == "__main__":
    main()
