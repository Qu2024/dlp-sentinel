from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawEvent:
    event_id: str
    session_id: str
    event_time: str
    user_id: str
    dept: str
    role: str
    device_id: str
    device_new_flag: int
    ip_region: str
    event_type: str
    object_domain: str
    sensitivity_level: int
    query_count: int
    export_count: int
    file_size_mb: float
    print_pages: int
    screenshot_count: int
    external_send_count: int
    copy_count: int
    target_path_type: str
    usb_registered_flag: int
    approval_flag: int
    business_flag: int
    case_id: str
    cross_dept_flag: int
    off_work_flag: int
    deviation_person: float
    deviation_role: float
    sensitive_hit_ratio: float
    unique_id_ratio: float
    cross_domain_count: int
    compress_flag: int
    encrypt_flag: int
    delete_flag: int
    tool_abnormal_flag: int


@dataclass
class CandidateEvent:
    candidate_event_id: str
    user_id: str
    events: list[RawEvent]
    candidate_flag: int
    matched_scene_list: list[str]
    rule_strength: str  # strong / medium / weak
    rule_priority: int


@dataclass
class ScoredEvent:
    candidate_event_id: str
    user_id: str
    candidate_flag: int
    matched_scene_list: list[str]
    rule_strength: str
    base_risk_score: float
    final_risk_score: float
    coverage: float
    risk_level: str
    top_drivers: list[dict]
    behavior_chain: list[str]
    llm_analysis: Optional[str] = None  # Layer2 LLM 业务关联分析结果
    raw_events: list = field(default_factory=list)


@dataclass
class RiskReport:
    report_id: str
    user_id: str
    risk_level: str
    final_risk_score: float
    evidence_summary: str
    risk_explanation: str
    disposition: dict
    llm_generated: bool
