from schemas import ScoredEvent


def extract(event: ScoredEvent) -> str:
    """从结构化评分事件中提取关键证据摘要"""
    parts = []
    e = event.raw_events[0] if event.raw_events else None

    if event.matched_scene_list:
        parts.append(f"命中场景：{'、'.join(event.matched_scene_list)}")
    if event.behavior_chain:
        parts.append(f"行为链：{' → '.join(event.behavior_chain)}")
    if e:
        if e.export_count > 0:
            parts.append(f"导出{e.export_count}条记录")
        if e.external_send_count > 0:
            parts.append(f"外发{e.external_send_count}次")
        if e.copy_count > 0:
            parts.append(f"拷贝至{e.target_path_type}")
        if e.off_work_flag:
            parts.append("非工作时间操作")
        if e.approval_flag == 0 and e.export_count > 0:
            parts.append("缺少审批")
    if event.top_drivers:
        drivers = "、".join(d["indicator"] for d in event.top_drivers)
        parts.append(f"主要风险因子：{drivers}")

    return "；".join(parts) if parts else "无明显证据"
