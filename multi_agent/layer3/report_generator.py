from schemas import ScoredEvent, RiskReport
from layer3 import evidence_extractor, llm_explainer
from datetime import date


DISPOSITION_MAP = {
    "极高风险": {"action": "立即阻断并升级处置", "suggestions": ["冻结账号", "隔离终端", "启动应急响应"]},
    "高风险":   {"action": "触发告警，优先调查", "suggestions": ["降低导出权限", "人工复核", "调取操作日志"]},
    "中风险":   {"action": "自动补证或人工复核", "suggestions": ["补充审批记录", "核实业务关联"]},
}


def generate(event: ScoredEvent) -> RiskReport:
    evidence = evidence_extractor.extract(event)
    use_llm = event.risk_level in ("中风险", "高风险", "极高风险")

    if use_llm:
        llm_result = llm_explainer.explain(event, evidence)
        explanation = llm_result.get("explanation", "")
        disposition = llm_result.get(
            "disposition",
            DISPOSITION_MAP.get(event.risk_level, {"action": "留痕观察", "suggestions": []})
        )
        llm_generated = bool(llm_result.get("_llm_generated", False))
    else:
        explanation = f"风险评分{event.risk_level}，主要因子：{'、'.join(d['indicator'] for d in event.top_drivers)}"
        disposition = {"action": "留痕观察", "suggestions": []}
        llm_generated = False

    agent_trace = dict(event.agent_trace or {})
    agent_trace["disposition_agent"] = {
        "evidence_summary": evidence,
        "explanation": explanation,
        "disposition": disposition,
    }

    return RiskReport(
        report_id=f"RPT_{event.user_id}_{date.today().strftime('%Y%m%d')}",
        user_id=event.user_id,
        risk_level=event.risk_level,
        final_risk_score=event.final_risk_score,
        evidence_summary=evidence,
        risk_explanation=explanation,
        disposition=disposition,
        llm_generated=llm_generated,
        candidate_event_id=event.candidate_event_id,
        matched_scene_list=event.matched_scene_list,
        behavior_chain=event.behavior_chain,
        agent_trace=agent_trace,
    )
