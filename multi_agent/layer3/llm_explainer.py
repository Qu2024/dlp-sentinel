from schemas import ScoredEvent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import json

SYSTEM_PROMPT = """你是一名数据防泄露研判专家。根据风险事件信息，严格以JSON格式返回，不要输出任何其他内容：
{"explanation": "一句话说明风险原因（50字以内）", "disposition": {"action": "一句话处置动作", "suggestions": ["建议1", "建议2"]}}"""


def _fallback(event: ScoredEvent, evidence_summary: str) -> dict:
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
        return _fallback(event, evidence_summary)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        result = json.loads(content)
        result["_llm_generated"] = True
        return result
    except Exception as exc:
        result = _fallback(event, evidence_summary)
        result["explanation"] += f"（LLM调用失败，已使用本地解释：{str(exc)[:60]}）"
        return result
