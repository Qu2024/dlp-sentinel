from .base_agent import BaseAgent
from layer2 import scorer


class ScoringAgent(BaseAgent):
    name = "风险评分Agent"

    def run(self, candidates, profile_results=None, business_results=None, chain_results=None):
        profile_results = profile_results or {}
        business_results = business_results or {}
        chain_results = chain_results or {}
        scored_events = []

        for c in candidates:
            if c.candidate_flag == 0:
                continue
            scored = scorer.score_candidate(
                c,
                profile_result=profile_results.get(c.candidate_event_id, {}),
                business_result=business_results.get(c.candidate_event_id, {}),
                chain_result=chain_results.get(c.candidate_event_id, {}),
            )
            scored_events.append(scored)

        trace = self.trace(
            {
                "candidate_count": len(candidates),
                "use_profile_result": True,
                "use_business_result": True,
                "use_chain_result": True,
            },
            {
                "scored_event_count": len(scored_events),
                "high_risk_count": sum(1 for e in scored_events if e.risk_level in ["高风险", "极高风险"]),
            },
        )
        return scored_events, trace
