from .base_agent import BaseAgent
from layer2 import llm_analyst
from layer3 import report_generator


class DispositionAgent(BaseAgent):
    name = "结果研判与处置Agent"

    def run(self, scored_events):
        reports = []
        for event in scored_events:
            # LLM分析失败时 llm_analyst 内部会自动降级为规则研判
            event.llm_analysis = llm_analyst.analyze(event)
            report = report_generator.generate(event)
            reports.append(report)

        trace = self.trace(
            {"scored_event_count": len(scored_events)},
            {"report_count": len(reports), "generated_disposition": True},
        )
        return reports, trace
