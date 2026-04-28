from schemas import ScoredEvent


def rank(events: list[ScoredEvent]) -> list[ScoredEvent]:
    """按风险等级和分数排序，只返回 candidate_flag=1 的事件"""
    level_order = {"极高风险": 0, "高风险": 1, "中风险": 2, "低风险": 3}
    candidates = [e for e in events if e.candidate_flag == 1]
    return sorted(candidates, key=lambda e: (level_order.get(e.risk_level, 9), -e.final_risk_score))
