from .base_agent import BaseAgent
from modules import evidence_extractor, llm_explainer, report_generator


class DispositionAgent(BaseAgent):
    name = "研判处置Agent"

    def run(self, scored_events):
        reports = []
        for event in scored_events:
            event.llm_analysis = llm_explainer.analyze_context(event)
            evidence = evidence_extractor.extract(event)
            explanation_result = llm_explainer.explain(event, evidence)
            report = report_generator.generate(event, evidence, explanation_result)
            reports.append(report)
        trace = self.trace(
            {"scored_event_count": len(scored_events)},
            {"report_count": len(reports), "generated_disposition": True},
        )
        return reports, trace
