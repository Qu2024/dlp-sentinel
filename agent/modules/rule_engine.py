from schemas import RawEvent, CandidateEvent
from itertools import groupby

from modules import adaptive_rule_engine


def _compare(value, op: str, target) -> bool:
    if value is None:
        return False
    if op == ">":
        return value > target
    if op == ">=":
        return value >= target
    if op == "<":
        return value < target
    if op == "<=":
        return value <= target
    if op == "==":
        return value == target
    if op == "!=":
        return value != target
    return False


def _match_rule_on_event(event: RawEvent, rule: dict) -> bool:
    return all(
        _compare(getattr(event, condition["field"], None), condition["op"], condition["value"])
        for condition in rule.get("conditions", [])
    )


def _match_rule_on_session(session_summary: dict, rule: dict) -> bool:
    return all(
        _compare(adaptive_rule_engine._feature_value(session_summary, condition["field"]), condition["op"], condition["value"])
        for condition in rule.get("conditions", [])
    )


def _rule_matches(events: list[RawEvent], rule: dict, session_summary: dict) -> bool:
    if rule.get("scope") == "session":
        return _match_rule_on_session(session_summary, rule)
    return any(_match_rule_on_event(event, rule) for event in events)


def _match_scenes(events: list[RawEvent], scene_rules: list[dict], session_summary: dict) -> list[str]:
    matched = []
    for rule in scene_rules:
        if _rule_matches(events, rule, session_summary) and rule.get("name") not in matched:
            matched.append(rule.get("name", "未命名规则"))
    return matched


def _high_risk_gate(events: list[RawEvent], thresholds: list[dict], session_summary: dict) -> bool:
    for threshold in thresholds:
        if threshold.get("scope") == "session":
            value = adaptive_rule_engine._feature_value(session_summary, threshold["field"])
            if _compare(value, threshold["op"], threshold["value"]):
                return True
            continue

        for event in events:
            value = getattr(event, threshold["field"], 0)
            if _compare(value, threshold["op"], threshold["value"]):
                return True
    return False


def _weak_rule_count(events: list[RawEvent], weak_rules: list[dict], session_summary: dict) -> int:
    triggered = set()
    for index, rule in enumerate(weak_rules):
        if _rule_matches(events, rule, session_summary):
            triggered.add(index)
    return len(triggered)


def _rule_strength(scenes: list[str], high_risk: bool) -> str:
    if high_risk or len(scenes) >= 2:
        return "strong"
    if len(scenes) == 1:
        return "medium"
    return "weak"


def run(events: list[RawEvent]) -> tuple[list[CandidateEvent], dict]:
    runtime_rules = adaptive_rule_engine.load_active_rules()
    sorted_events = sorted(events, key=lambda e: (e.user_id, e.session_id))
    candidates = []

    for (uid, sid), group in groupby(sorted_events, key=lambda e: (e.user_id, e.session_id)):
        group = list(group)
        session_summary = adaptive_rule_engine.summarize_session_events(group)
        scenes = _match_scenes(group, runtime_rules["scene_rules"], session_summary)
        high_risk = _high_risk_gate(group, runtime_rules["high_risk_thresholds"], session_summary)
        weak_count = _weak_rule_count(group, runtime_rules["weak_rules"], session_summary)

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

    meta = {
        "scene_rule_count": len(runtime_rules["scene_rules"]),
        "high_risk_threshold_count": len(runtime_rules["high_risk_thresholds"]),
        "weak_rule_count": len(runtime_rules["weak_rules"]),
        "approved_ml_rule_count": sum(
            1 for rule in runtime_rules["scene_rules"]
            if rule.get("source") == "approved_suggestion"
        ),
    }
    return candidates, meta
