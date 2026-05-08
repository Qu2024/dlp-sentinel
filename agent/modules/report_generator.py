from datetime import date
from schemas import ScoredEvent, RiskReport


def generate(event: ScoredEvent, evidence_summary: str, llm_result: dict) -> RiskReport:
    explanation = llm_result.get("explanation", "")
    disposition = llm_result.get("disposition", {"action": "留痕观察", "suggestions": []})
    llm_generated = bool(llm_result.get("_llm_generated", False))

    agent_trace = dict(event.agent_trace or {})
    agent_trace["disposition_agent"] = {
        "evidence_summary": evidence_summary,
        "explanation": explanation,
        "disposition": disposition,
    }

    return RiskReport(
        report_id=f"RPT_{event.user_id}_{date.today().strftime('%Y%m%d')}",
        user_id=event.user_id,
        risk_level=event.risk_level,
        final_risk_score=event.final_risk_score,
        evidence_summary=evidence_summary,
        risk_explanation=explanation,
        disposition=disposition,
        llm_generated=llm_generated,
        candidate_event_id=event.candidate_event_id,
        matched_scene_list=event.matched_scene_list,
        behavior_chain=event.behavior_chain,
        agent_trace=agent_trace,
    )
