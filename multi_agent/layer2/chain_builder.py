from schemas import RawEvent
from collections import defaultdict


def build_chains(events: list[RawEvent]) -> dict[str, list[str]]:
    """按 user_id 重构行为链，返回 {user_id: [event_type, ...]}"""
    user_events = defaultdict(list)
    for e in sorted(events, key=lambda x: x.event_time):
        user_events[e.user_id].append(e.event_type)
    return dict(user_events)
