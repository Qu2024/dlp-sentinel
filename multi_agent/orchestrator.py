import json
from dataclasses import asdict
from pathlib import Path

from agents.data_agent import DataAgent
from agents.rule_agent import RuleAgent
from agents.profile_agent import ProfileAgent
from agents.business_agent import BusinessAgent
from agents.chain_agent import ChainAgent
from agents.scoring_agent import ScoringAgent
from agents.disposition_agent import DispositionAgent
from agents.feedback_agent import FeedbackAgent
from layer2 import risk_ranker


class MultiAgentOrchestrator:
    """集中式多 Agent 调度器，对标开题报告中的多 Agent 系统设计。"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.data_agent = DataAgent()
        self.rule_agent = RuleAgent()
        self.profile_agent = ProfileAgent()
        self.business_agent = BusinessAgent()
        self.chain_agent = ChainAgent()
        self.scoring_agent = ScoringAgent()
        self.disposition_agent = DispositionAgent()
        self.feedback_agent = FeedbackAgent(str(self.output_dir / "feedback.json"))

    def _save_json(self, name: str, data):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    def run(self, csv_path: str):
        agent_trace = []

        events, trace = self.data_agent.run(csv_path)
        agent_trace.append(trace)

        candidates, trace = self.rule_agent.run(events)
        agent_trace.append(trace)

        # 只对候选池事件做后续 Agent 分析，降低计算量
        candidate_pool = [c for c in candidates if c.candidate_flag == 1]

        profile_results, trace = self.profile_agent.run(candidate_pool)
        agent_trace.append(trace)

        business_results, trace = self.business_agent.run(candidate_pool)
        agent_trace.append(trace)

        chain_results, trace = self.chain_agent.run(candidate_pool)
        agent_trace.append(trace)

        scored_events, trace = self.scoring_agent.run(
            candidate_pool,
            profile_results=profile_results,
            business_results=business_results,
            chain_results=chain_results,
        )
        agent_trace.append(trace)

        ranked_events = risk_ranker.rank(scored_events)

        reports, trace = self.disposition_agent.run(ranked_events)
        agent_trace.append(trace)

        feedback_items, trace = self.feedback_agent.run(reports)
        agent_trace.append(trace)

        self._save_json("agent_trace.json", agent_trace)
        self._save_json("risk_events.json", [asdict(e) for e in ranked_events])
        self._save_json("reports.json", [asdict(r) for r in reports])
        self._save_json("candidate_events.json", [asdict(c) for c in candidates])
        self._save_json("feedback.json", feedback_items)

        return {
            "events": events,
            "candidates": candidates,
            "candidate_pool": candidate_pool,
            "profile_results": profile_results,
            "business_results": business_results,
            "chain_results": chain_results,
            "scored_events": ranked_events,
            "reports": reports,
            "feedback_items": feedback_items,
            "agent_trace": agent_trace,
        }
