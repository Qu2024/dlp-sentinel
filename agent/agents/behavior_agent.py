from .base_agent import BaseAgent
from modules import profile_analyzer, business_analyzer, chain_builder


class BehaviorAgent(BaseAgent):
    """行为理解 Agent：统一封装画像/基线、业务关联和行为链三类上下文分析。"""

    name = "行为理解Agent"

    def __init__(self, permission_path="knowledge/role_permissions.csv"):
        self.permission_path = permission_path
        self.permission_rules = business_analyzer.load_permissions(permission_path)

    def run(self, candidates):
        results = {}
        for c in candidates:
            profile_result = profile_analyzer.analyze(c)
            business_result = business_analyzer.analyze(c, self.permission_rules)
            chain_result = chain_builder.build(c)

            c.profile_result = profile_result
            c.business_result = business_result
            c.chain_result = chain_result

            results[c.candidate_event_id] = {
                "profile_result": profile_result,
                "business_result": business_result,
                "chain_result": chain_result,
            }

        trace = self.trace(
            {"candidate_count": len(candidates), "permission_rule_count": len(self.permission_rules)},
            {
                "behavior_analyzed_count": len(results),
                "business_unreasonable_count": sum(1 for r in results.values() if not r["business_result"].get("business_reasonable", True)),
                "high_chain_count": sum(1 for r in results.values() if r["chain_result"].get("chain_completeness", 0) >= 0.6),
                "high_deviation_count": sum(1 for r in results.values() if r["profile_result"].get("max_person_deviation", 0) >= 3 or r["profile_result"].get("max_role_deviation", 0) >= 3),
            },
        )
        return results, trace
