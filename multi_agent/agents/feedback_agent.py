import json
from pathlib import Path
from .base_agent import BaseAgent


class FeedbackAgent(BaseAgent):
    name = "反馈优化Agent"

    def __init__(self, feedback_path="output/feedback.json"):
        self.feedback_path = Path(feedback_path)

    def run(self, reports):
        feedback_items = []
        for r in reports:
            feedback_items.append({
                "candidate_event_id": getattr(r, "candidate_event_id", ""),
                "user_id": r.user_id,
                "risk_level": r.risk_level,
                "need_human_review": r.risk_level in ["中风险", "高风险", "极高风险"],
                "human_confirmed": None,
                "false_positive": None,
                "review_comment": "",
            })

        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_path.write_text(json.dumps(feedback_items, ensure_ascii=False, indent=2), encoding="utf-8")

        trace = self.trace(
            {"report_count": len(reports)},
            {"feedback_items": len(feedback_items), "feedback_file": str(self.feedback_path)},
        )
        return feedback_items, trace
