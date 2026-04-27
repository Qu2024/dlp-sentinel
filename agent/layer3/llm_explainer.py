from schemas import ScoredEvent
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import json

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SYSTEM_PROMPT = """你是一名数据防泄露研判专家。根据风险事件信息，严格以JSON格式返回，不要输出任何其他内容：
{"explanation": "一句话说明风险原因（50字以内）", "disposition": {"action": "一句话处置动作", "suggestions": ["建议1", "建议2"]}}"""


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
    }
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
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"explanation": content[:200], "disposition": {"action": "人工复核", "suggestions": []}}
