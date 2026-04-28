import json
from schemas import ScoredEvent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from prompts import ANALYST_SYSTEM_PROMPT, EXPLAINER_SYSTEM_PROMPT


def _local_analysis(event: ScoredEvent) -> str:
    problems = event.business_result.get("business_problems", []) if event.business_result else []
    chain_flags = event.chain_result.get("chain_flags", []) if event.chain_result else []
    parts = []
    if problems:
        parts.append("业务关联存在问题：" + "、".join(problems[:3]))
    if chain_flags:
        parts.append("行为链异常：" + "、".join(chain_flags[:3]))
    if not parts:
        parts.append(f"该事件风险等级为{event.risk_level}，建议结合审批和业务记录复核。")
    return "；".join(parts)[:200]


def analyze_context(event: ScoredEvent) -> str:
    payload = {
        "user_id": event.user_id,
        "matched_scenes": event.matched_scene_list,
        "behavior_chain": event.behavior_chain,
        "risk_score": event.final_risk_score,
        "top_drivers": event.top_drivers,
        "profile_result": event.profile_result,
        "business_result": event.business_result,
        "chain_result": event.chain_result,
    }
    if not DEEPSEEK_API_KEY:
        return _local_analysis(event)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        return f"{_local_analysis(event)}（LLM调用失败，已使用本地规则研判：{str(exc)[:60]}）"


def _fallback_report(event: ScoredEvent, evidence_summary: str) -> dict:
    if event.risk_level == "极高风险":
        action = "立即阻断并升级处置"
        suggestions = ["冻结账号", "隔离终端", "调取完整操作日志", "核查外发和拷贝去向"]
    elif event.risk_level == "高风险":
        action = "触发告警并优先调查"
        suggestions = ["人工复核审批记录", "核查业务关联", "临时降低导出权限"]
    elif event.risk_level == "中风险":
        action = "进入复核队列"
        suggestions = ["补充审批证明", "核实案件或任务编号"]
    else:
        action = "留痕观察"
        suggestions = ["持续监控后续行为"]
    return {
        "explanation": f"该事件为{event.risk_level}，主要证据包括：{evidence_summary[:120]}",
        "disposition": {"action": action, "suggestions": suggestions},
        "_llm_generated": False,
    }


def explain(event: ScoredEvent, evidence_summary: str) -> dict:
    payload = {
        "user_id": event.user_id,
        "risk_level": event.risk_level,
        "final_risk_score": event.final_risk_score,
        "matched_scenes": event.matched_scene_list,
        "top_drivers": event.top_drivers,
        "evidence_summary": evidence_summary,
        "llm_analysis": event.llm_analysis,
        "coverage": event.coverage,
        "agent_trace": event.agent_trace,
    }
    if not DEEPSEEK_API_KEY:
        return _fallback_report(event, evidence_summary)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        result["_llm_generated"] = True
        return result
    except Exception as exc:
        result = _fallback_report(event, evidence_summary)
        result["explanation"] += f"（LLM调用失败，已使用本地解释：{str(exc)[:60]}）"
        return result
