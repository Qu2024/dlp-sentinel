from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_agent(
    events_csv: str | Path,
    agent_dir: str | Path = "agent",
    output_dir: str | Path = "output",
    python: str | None = None,
    adaptive_rule_dir: str | Path | None = None,
) -> subprocess.CompletedProcess:
    agent_path = Path(agent_dir).resolve()
    events_path = Path(events_csv).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if adaptive_rule_dir:
        env["DLP_ADAPTIVE_RULE_DIR"] = str(Path(adaptive_rule_dir).resolve())

    code = (
        "import sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "from main import run; "
        "run(sys.argv[2], output_dir=sys.argv[3])"
    )
    return subprocess.run(
        [python or sys.executable, "-c", code, str(agent_path), str(events_path), str(output_path)],
        cwd=agent_path,
        env=env,
        check=True,
    )


def evaluate_candidates(labels_csv: str | Path, candidate_events_json: str | Path) -> dict[str, Any]:
    labels = _read_labels(labels_csv)
    candidates = _read_json(candidate_events_json)
    predicted = {
        item.get("candidate_event_id"): int(item.get("candidate_flag", 0) == 1)
        for item in candidates
    }

    tp = fp = tn = fn = 0
    missing_predictions: list[str] = []
    false_positives: list[str] = []
    false_negatives: list[str] = []

    for candidate_id, label in labels.items():
        actual = int(label["is_anomaly"])
        if candidate_id not in predicted:
            missing_predictions.append(candidate_id)
        pred = predicted.get(candidate_id, 0)
        if pred == 1 and actual == 1:
            tp += 1
        elif pred == 1 and actual == 0:
            fp += 1
            false_positives.append(candidate_id)
        elif pred == 0 and actual == 0:
            tn += 1
        else:
            fn += 1
            false_negatives.append(candidate_id)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    return {
        "total_sessions": len(labels),
        "predicted_candidate_sessions": sum(predicted.values()),
        "actual_anomaly_sessions": sum(int(item["is_anomaly"]) for item in labels.values()),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "missing_predictions": missing_predictions[:20],
        "false_positive_examples": false_positives[:20],
        "false_negative_examples": false_negatives[:20],
    }


def write_evaluation(path: str | Path, result: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _read_labels(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return {
            row["candidate_event_id"]: row
            for row in csv.DictReader(f)
        }


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
