import json
from pathlib import Path


def build_feedback_records(reports) -> list[dict]:
    items = []
    for r in reports:
        items.append({
            "candidate_event_id": getattr(r, "candidate_event_id", ""),
            "user_id": r.user_id,
            "risk_level": r.risk_level,
            "need_human_review": r.risk_level in ["中风险", "高风险", "极高风险"],
            "human_confirmed": None,
            "false_positive": None,
            "review_comment": "",
        })
    return items


def save_feedback_records(reports, output_dir="output") -> list[dict]:
    items = build_feedback_records(reports)
    path = Path(output_dir) / "feedback.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return items
