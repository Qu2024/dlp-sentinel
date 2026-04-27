from schemas import ScoredEvent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
import json

# SYSTEM_PROMPT = """你是一名数据防泄露分析专家。给定一条候选风险事件的结构化信息，请从业务关联性和行为链路两个角度进行分析：
# 1. 判断该行为是否有合理的业务解释
# 2. 识别行为链中是否存在异常跳跃或缺失环节
# 3. 输出简洁的分析结论（100字以内）"""

SYSTEM_PROMPT = """你是一名数据防泄露分析专家，擅长基于结构化日志进行风险研判。

请严格基于输入数据，从【用户画像基线】、【业务合理性】、【行为链完整性】三个维度进行分析，并遵循以下规则：

【分析要求】

1. 用户画像基线（Behavior vs Baseline）：
- 判断该行为是否明显偏离个人或岗位基线
- 若存在异常，指出偏离类型（如：高频查询、异常导出、跨部门异常等）

2. 业务合理性（Business Context）：
- 判断是否存在审批、案件、工单等业务支撑
- 若缺失或不匹配，明确指出（如：无审批、审批无效、无业务关联）

3. 行为链完整性（Behavior Chain）：
- 判断行为链（如 登录→查询→导出→清痕）是否合理完整
- 识别是否存在异常跳跃（如直接导出）、缺失环节或清痕行为

【输出要求】
- 输出必须为一句话，总长度 ≤ 150字
- 必须包含三个部分（用“；”分隔）：
  ① 基线判断
  ② 业务判断
  ③ 行为链判断

【风格要求】
- 简洁、客观、审计报告风格
- 禁止使用不确定表达（如“可能”、“疑似”）
- 禁止复述输入数据

【示例输出】
行为明显偏离个人基线且导出频次异常；无审批且无业务关联；存在查询后直接导出并伴随清痕行为，链路异常
"""


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


def analyze(event: ScoredEvent) -> str:
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

    # 未配置 API 时自动降级，保证课堂演示不失败。
    if not DEEPSEEK_API_KEY:
        return _local_analysis(event)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        return f"{_local_analysis(event)}（LLM调用失败，已使用本地规则研判：{str(exc)[:60]}）"
