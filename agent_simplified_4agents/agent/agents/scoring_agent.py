from .base_agent import BaseAgent
from modules import scorer


class ScoringAgent(BaseAgent):
    name = "风险评分Agent"

    def run(self, candidates, behavior_results=None):
        behavior_results = behavior_results or {}
        scored_events = []
        for c in candidates:
            if c.candidate_flag == 0:
                continue
            behavior = behavior_results.get(c.candidate_event_id, {})
            scored = scorer.score_candidate(
                c,
                profile_result=behavior.get("profile_result", {}),
                business_result=behavior.get("business_result", {}),
                chain_result=behavior.get("chain_result", {}),
            )
            scored_events.append(scored)
        trace = self.trace(
            {"candidate_count": len(candidates), "use_behavior_result": True},
            {
                "scored_event_count": len(scored_events),
                "high_risk_count": sum(1 for e in scored_events if e.risk_level in ["高风险", "极高风险"]),
            },
        )
        return scored_events, trace
