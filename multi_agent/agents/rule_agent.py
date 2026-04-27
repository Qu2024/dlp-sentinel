from .base_agent import BaseAgent
from layer2 import rule_engine


class RuleAgent(BaseAgent):
    name = "规则识别Agent"

    def run(self, events):
        candidates = rule_engine.run(events)
        scene_counter = {}
        for c in candidates:
            for scene in c.matched_scene_list:
                scene_counter[scene] = scene_counter.get(scene, 0) + 1
        trace = self.trace(
            {"raw_event_count": len(events)},
            {
                "session_count": len(candidates),
                "candidate_count": sum(1 for c in candidates if c.candidate_flag),
                "matched_scene_summary": scene_counter,
            },
        )
        return candidates, trace
