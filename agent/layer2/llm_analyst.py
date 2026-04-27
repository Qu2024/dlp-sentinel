from schemas import ScoredEvent
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import json

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SYSTEM_PROMPT = """你是一名数据防泄露分析专家。给定一条候选风险事件的结构化信息，请从业务关联性和行为链路两个角度进行分析：
1. 判断该行为是否有合理的业务解释
2. 识别行为链中是否存在异常跳跃或缺失环节
3. 输出简洁的分析结论（100字以内）"""


def analyze(event: ScoredEvent) -> str:
    payload = {
        "user_id": event.user_id,
        "matched_scenes": event.matched_scene_list,
        "behavior_chain": event.behavior_chain,
        "risk_score": event.final_risk_score,
        "top_drivers": event.top_drivers,
    }
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()
