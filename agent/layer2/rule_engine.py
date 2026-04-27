from schemas import RawEvent, CandidateEvent
from itertools import groupby


SCENE_RULES = [
    ("大批量导出", lambda e: e.export_count > 50),
    ("非工作时间高危操作", lambda e: e.off_work_flag == 1 and e.export_count > 10),
    ("未审批高敏导出", lambda e: e.approval_flag == 0 and e.sensitivity_level >= 4),
    ("未备案USB拷贝", lambda e: e.copy_count > 0 and e.usb_registered_flag == 0),
    ("外发敏感数据", lambda e: e.external_send_count > 0 and e.sensitivity_level >= 3),
    ("跨域大量查询", lambda e: e.cross_domain_count >= 3 and e.query_count > 30),
    ("截图高敏内容", lambda e: e.screenshot_count > 5 and e.sensitivity_level >= 4),
]

HIGH_RISK_THRESHOLDS = [
    ("export_count", 100),
    ("print_pages", 50),
    ("screenshot_count", 20),
    ("external_send_count", 5),
]

WEAK_RULES = [
    lambda e: e.off_work_flag == 1,
    lambda e: e.device_new_flag == 1,
    lambda e: e.cross_dept_flag == 1,
    lambda e: e.approval_flag == 0,
    lambda e: e.business_flag == 0,
    lambda e: e.tool_abnormal_flag == 1,
]


def _match_scenes(events: list[RawEvent]) -> list[str]:
    matched = set()
    for e in events:
        for name, rule in SCENE_RULES:
            if rule(e):
                matched.add(name)
    return list(matched)


def _high_risk_gate(events: list[RawEvent]) -> bool:
    for e in events:
        for field, threshold in HIGH_RISK_THRESHOLDS:
            if getattr(e, field, 0) > threshold:
                return True
    return False


def _weak_rule_count(events: list[RawEvent]) -> int:
    triggered = set()
    for e in events:
        for i, rule in enumerate(WEAK_RULES):
            if rule(e):
                triggered.add(i)
    return len(triggered)


def _rule_strength(scenes: list[str], high_risk: bool) -> str:
    if high_risk or len(scenes) >= 2:
        return "strong"
    if len(scenes) == 1:
        return "medium"
    return "weak"


def run(events: list[RawEvent]) -> list[CandidateEvent]:
    # 按 user_id + session_id 聚合
    sorted_events = sorted(events, key=lambda e: (e.user_id, e.session_id))
    candidates = []
    idx = 0
    for (uid, sid), group in groupby(sorted_events, key=lambda e: (e.user_id, e.session_id)):
        group = list(group)
        scenes = _match_scenes(group)
        high_risk = _high_risk_gate(group)
        weak_count = _weak_rule_count(group)

        candidate_flag = 1 if (scenes or high_risk or weak_count >= 2) else 0
        strength = _rule_strength(scenes, high_risk)
        priority = {"strong": 1, "medium": 2, "weak": 3}[strength]

        candidates.append(CandidateEvent(
            candidate_event_id=f"{uid}_{sid}",
            user_id=uid,
            events=group,
            candidate_flag=candidate_flag,
            matched_scene_list=scenes,
            rule_strength=strength,
            rule_priority=priority,
        ))
        idx += 1
    return candidates
