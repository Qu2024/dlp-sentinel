from schemas import ScoredEvent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import json

# SYSTEM_PROMPT = """你是一名数据防泄露研判专家。根据风险事件信息，严格以JSON格式返回，不要输出任何其他内容：
# {"explanation": "一句话说明风险原因（50字以内）", "disposition": {"action": "一句话处置动作", "suggestions": ["建议1", "建议2"]}}"""

SYSTEM_PROMPT = """你是一名数据防泄露研判专家，负责生成风险解释与处置建议。

请严格基于输入数据，从【用户画像基线】、【业务合理性】、【行为链完整性】三个维度进行综合判断，并输出标准化JSON结果。

【分析要求】

1. 用户画像基线：
- 判断是否偏离个人或岗位正常行为
- 提炼关键异常（如：异常高频查询、异常导出等）

2. 业务合理性：
- 判断是否存在审批、案件、工单等支撑
- 若缺失或不匹配，明确指出（如：无审批、无业务关联）

3. 行为链完整性：
- 判断行为链是否合理（登录→查询→导出→清痕）
- 识别跳跃行为或清痕行为

【解释生成要求】
- explanation必须为一句话（≤50字）
- 必须同时体现：异常行为 + 业务问题 + 链路问题（至少2个维度）
- 风格：审计报告式，客观、简洁、无不确定词（禁止“可能/疑似”）

【处置策略要求】
- 根据风险等级生成action与suggestions
- 极高/高风险：偏“阻断+调查”
- 中风险：偏“复核+补充材料”
- 低风险：偏“观察+监控”

【输出格式要求】
- 必须返回合法JSON
- 不得输出任何额外文本
- suggestions必须为2~4条简短措施

【输出示例】
{
  "explanation": "行为偏离基线且无审批，存在导出及清痕链路异常",
  "disposition": {
    "action": "立即阻断并升级调查",
    "suggestions": ["冻结账号", "隔离终端", "调取日志"]
  }
}
"""

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
