from schemas import CandidateEvent, ScoredEvent, RawEvent
from config import L1_WEIGHTS, L2_WEIGHTS, RISK_THRESHOLDS


def _score_C4(e: RawEvent) -> dict:
    # S1: 对象敏感等级分
    s1 = {1: 0, 2: 25, 3: 50, 4: 75, 5: 100}.get(e.sensitivity_level, 0)
    # S2: 敏感内容暴露分
    r = e.sensitive_hit_ratio
    s2 = 0 if r < 0.05 else 30 if r < 0.2 else 60 if r < 0.5 else 85 if r < 0.8 else 100
    s2_active = e.export_count > 0 or e.print_pages > 0 or e.screenshot_count > 0
    # S3: 唯一识别性分
    u = e.unique_id_ratio
    s3 = 0 if u < 0.1 else 40 if u < 0.3 else 70 if u < 0.5 else 90 if u < 0.8 else 100
    # S4: 高敏对象覆盖分
    s4 = min(e.cross_domain_count * 25, 100) if e.cross_domain_count > 0 else 0
    s4_map = {0: 0, 1: 20, 2: 50, 3: 80}
    s4 = s4_map.get(min(e.cross_domain_count, 3), 100)
    # S5: 泄露规模分
    total = e.export_count + e.print_pages + e.screenshot_count
    s5 = 0 if total == 0 else 20 if total < 20 else 50 if total < 100 else 80 if total < 300 else 100
    s5_active = total > 0

    scores = {"S1": (s1, True), "S2": (s2, s2_active), "S3": (s3, True), "S4": (s4, True), "S5": (s5, s5_active)}
    return scores


def _score_C5(e: RawEvent, chain: list[str]) -> dict:
    # L1: 泄露链条完整度
    has_query = any("query" in c for c in chain)
    has_export = any(x in chain for x in ["export", "print", "screenshot"])
    has_land = e.copy_count > 0 or e.target_path_type in ["本地", "共享目录"]
    has_send = e.external_send_count > 0
    has_evade = e.compress_flag or e.encrypt_flag or e.delete_flag
    if has_evade and has_send:
        l1 = 100
    elif has_send or (has_land and has_export):
        l1 = 90
    elif has_land:
        l1 = 70
    elif has_export:
        l1 = 50
    else:
        l1 = 20
    l1_active = len(chain) >= 2

    # L2: 扩散落地程度
    if e.external_send_count > 0 and e.usb_registered_flag == 0:
        l2 = 100
    elif e.external_send_count > 0:
        l2 = 85
    elif e.copy_count > 0 and e.target_path_type == "共享目录":
        l2 = 60
    elif e.copy_count > 0:
        l2 = 30
    else:
        l2 = 0
    l2_active = e.copy_count > 0 or e.external_send_count > 0

    # L3: 接收方风险分 (简化：无接收方信息时用 external_send_count 代理)
    l3 = 85 if e.external_send_count > 0 else 0
    l3_active = e.external_send_count > 0

    # L4: 规避清痕
    evade_count = e.compress_flag + e.encrypt_flag + e.delete_flag + e.tool_abnormal_flag
    l4 = {0: 0, 1: 35, 2: 75}.get(min(evade_count, 2), 100)
    l4_active = (e.copy_count > 0 or e.export_count > 0) and evade_count > 0

    # L5: 时序紧凑度 (无精确时间差时跳过)
    l5, l5_active = 0, False

    return {"L1": (l1, l1_active), "L2": (l2, l2_active), "L3": (l3, l3_active),
            "L4": (l4, l4_active), "L5": (l5, l5_active)}


def _score_C2(e: RawEvent) -> dict:
    # B1: 个人行为偏离
    d = e.deviation_person
    b1 = 0 if d < 1.5 else 40 if d < 3 else 75 if d < 5 else 100

    # B2: 岗位同群偏离
    dr = e.deviation_role
    b2 = 0 if dr < 1.5 else 35 if dr < 3 else 70 if dr < 5 else 100

    # B3: 时空环境异常
    anomalies = e.off_work_flag + e.device_new_flag
    b3 = {0: 0, 1: 35, 2: 70}.get(min(anomalies, 2), 100)

    # B4: 访问范围偏离
    b4 = 0 if e.cross_dept_flag == 0 and e.cross_domain_count == 0 else \
         30 if e.cross_dept_flag == 0 else 70 if e.cross_domain_count < 3 else 100

    return {"B1": (b1, True), "B2": (b2, True), "B3": (b3, True), "B4": (b4, True)}


def _score_C3(e: RawEvent) -> dict:
    # A1: 审批缺失
    a1 = 0 if e.approval_flag == 1 else 90
    a1_active = e.export_count > 0 or e.print_pages > 0

    # A2: 案件/业务关联缺失
    a2 = 0 if e.business_flag == 1 else 90
    if e.sensitivity_level >= 4 and e.business_flag == 0:
        a2 = 100

    # A3: 权限不匹配 (无权限字段，用 cross_dept_flag 代理)
    a3 = 80 if e.cross_dept_flag == 1 and e.business_flag == 0 else 0

    # A4: 协同任务缺失
    a4 = 85 if e.cross_dept_flag == 1 and e.business_flag == 0 else 0
    a4_active = e.cross_dept_flag == 1

    return {"A1": (a1, a1_active), "A2": (a2, True), "A3": (a3, True), "A4": (a4, a4_active)}


def _dim_score(scores: dict, weights: dict) -> tuple[float, float]:
    """Returns (dim_score, coverage_numerator/denominator pair)"""
    num = denom = 0.0
    for code, (s, active) in scores.items():
        w = weights[code]
        if active:
            num += w * s
            denom += w
    return (num / denom if denom > 0 else 0.0), denom


def _protection_factor(e: RawEvent) -> float:
    if e.data_mask_flag if hasattr(e, "data_mask_flag") else False:
        return 0.70
    if e.encrypt_flag and e.target_path_type != "USB":
        return 0.85
    return 1.00


def _risk_level(score: float) -> str:
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return "低风险"


def score_candidate(candidate: CandidateEvent) -> ScoredEvent:
    if candidate.candidate_flag == 0:
        return ScoredEvent(
            candidate_event_id=candidate.candidate_event_id,
            user_id=candidate.user_id,
            candidate_flag=0,
            matched_scene_list=[],
            rule_strength=candidate.rule_strength,
            base_risk_score=0.0,
            final_risk_score=0.0,
            coverage=0.0,
            risk_level="低风险",
            top_drivers=[],
            behavior_chain=[],
            raw_events=candidate.events,
        )

    # 聚合事件：取最高风险的单条事件代表（简化）
    e = max(candidate.events, key=lambda x: x.sensitivity_level * 10 + x.export_count)
    seen = set()
    chain = [seen.add(ev.event_type) or ev.event_type
             for ev in sorted(candidate.events, key=lambda x: x.event_time)
             if ev.event_type not in seen]

    c4_scores = _score_C4(e)
    c5_scores = _score_C5(e, chain)
    c2_scores = _score_C2(e)
    c3_scores = _score_C3(e)

    c2, c2_w = _dim_score(c2_scores, L2_WEIGHTS["C2"])
    c3, c3_w = _dim_score(c3_scores, L2_WEIGHTS["C3"])
    c4, c4_w = _dim_score(c4_scores, L2_WEIGHTS["C4"])
    c5, c5_w = _dim_score(c5_scores, L2_WEIGHTS["C5"])

    base = (L1_WEIGHTS["C2"] * c2 + L1_WEIGHTS["C3"] * c3 +
            L1_WEIGHTS["C4"] * c4 + L1_WEIGHTS["C5"] * c5)

    pf = _protection_factor(e)
    final = base * pf

    # 封顶规则
    l2_score = c5_scores["L2"][0]
    l3_score = c5_scores["L3"][0]
    if l2_score < 60 and l3_score < 85:
        final = min(final, 79)

    # 证据覆盖率
    all_scores = {**c2_scores, **c3_scores, **c4_scores, **c5_scores}
    all_weights = {**{k: L2_WEIGHTS["C2"][k] * L1_WEIGHTS["C2"] for k in L2_WEIGHTS["C2"]},
                   **{k: L2_WEIGHTS["C3"][k] * L1_WEIGHTS["C3"] for k in L2_WEIGHTS["C3"]},
                   **{k: L2_WEIGHTS["C4"][k] * L1_WEIGHTS["C4"] for k in L2_WEIGHTS["C4"]},
                   **{k: L2_WEIGHTS["C5"][k] * L1_WEIGHTS["C5"] for k in L2_WEIGHTS["C5"]}}
    cov_num = sum(all_weights[k] for k, (_, active) in all_scores.items() if active)
    cov_denom = sum(all_weights.values())
    coverage = cov_num / cov_denom if cov_denom > 0 else 0.0

    # top_drivers
    contributions = []
    indicator_names = {
        "S1": "对象敏感等级分", "S2": "敏感内容暴露分", "S3": "唯一识别性分",
        "S4": "高敏对象覆盖分", "S5": "泄露规模分",
        "L1": "泄露链条完整度分", "L2": "扩散落地程度分", "L3": "接收方风险分",
        "L4": "规避清痕程度分", "L5": "时序紧凑度分",
        "B1": "个人行为偏离分", "B2": "岗位同群偏离分", "B3": "时空环境异常分", "B4": "访问范围偏离分",
        "A1": "审批缺失分", "A2": "案件/业务关联缺失分", "A3": "权限不匹配分", "A4": "协同任务缺失分",
    }
    for code, (s, active) in all_scores.items():
        if active:
            contributions.append({"indicator": indicator_names[code], "contribution": round(all_weights[code] * s, 3)})
    top_drivers = sorted(contributions, key=lambda x: -x["contribution"])[:3]

    return ScoredEvent(
        candidate_event_id=candidate.candidate_event_id,
        user_id=candidate.user_id,
        candidate_flag=1,
        matched_scene_list=candidate.matched_scene_list,
        rule_strength=candidate.rule_strength,
        base_risk_score=round(base, 2),
        final_risk_score=round(final, 2),
        coverage=round(coverage, 3),
        risk_level=_risk_level(final),
        top_drivers=top_drivers,
        behavior_chain=chain,
        raw_events=candidate.events,
    )
