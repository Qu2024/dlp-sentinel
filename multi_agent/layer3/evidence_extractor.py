from schemas import ScoredEvent


def extract(event: ScoredEvent) -> str:
    """从结构化评分事件中提取关键证据摘要；按会话聚合，而不是只看第一条日志。"""
    parts = []
    events = event.raw_events or []

    if event.matched_scene_list:
        parts.append(f"命中场景：{'、'.join(event.matched_scene_list)}")
    if event.behavior_chain:
        parts.append(f"行为链：{' → '.join(event.behavior_chain)}")

    total_query = sum(e.query_count for e in events)
    total_export = sum(e.export_count for e in events)
    total_print = sum(e.print_pages for e in events)
    total_screenshot = sum(e.screenshot_count for e in events)
    total_external_send = sum(e.external_send_count for e in events)
    total_copy = sum(e.copy_count for e in events)
    max_sensitivity = max((e.sensitivity_level for e in events), default=0)

    if max_sensitivity:
        parts.append(f"最高敏感等级：{max_sensitivity}")
    if total_query > 0:
        parts.append(f"累计查询{total_query}次")
    if total_export > 0:
        parts.append(f"累计导出{total_export}条记录")
    if total_print > 0:
        parts.append(f"累计打印{total_print}页")
    if total_screenshot > 0:
        parts.append(f"累计截图{total_screenshot}次")
    if total_external_send > 0:
        parts.append(f"累计外发{total_external_send}次")
    if total_copy > 0:
        paths = sorted({e.target_path_type for e in events if e.copy_count > 0 and e.target_path_type})
        parts.append(f"累计拷贝{total_copy}次，目标位置：{'、'.join(paths) if paths else '未知'}")

    if any(e.off_work_flag for e in events):
        parts.append("存在非工作时间操作")
    if any(e.device_new_flag for e in events):
        parts.append("存在新设备登录")
    if any(e.approval_flag == 0 and (e.export_count > 0 or e.print_pages > 0) for e in events):
        parts.append("存在未审批导出/打印")
    if any(e.business_flag == 0 for e in events):
        parts.append("缺少明确业务关联")
    if any(e.delete_flag for e in events):
        parts.append("存在清痕删除行为")

    if event.business_result.get("business_problems"):
        parts.append("业务问题：" + "、".join(event.business_result["business_problems"][:3]))
    if event.chain_result.get("chain_flags"):
        parts.append("链路问题：" + "、".join(event.chain_result["chain_flags"][:3]))
    if event.top_drivers:
        drivers = "、".join(d["indicator"] for d in event.top_drivers)
        parts.append(f"主要风险因子：{drivers}")

    return "；".join(parts) if parts else "无明显证据"
