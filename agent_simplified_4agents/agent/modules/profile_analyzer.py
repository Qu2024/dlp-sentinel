def analyze(candidate) -> dict:
    events = candidate.events
    max_person_dev = max((e.deviation_person for e in events), default=0)
    max_role_dev = max((e.deviation_role for e in events), default=0)
    has_new_device = any(e.device_new_flag == 1 for e in events)
    has_off_work = any(e.off_work_flag == 1 for e in events)
    cross_dept = any(e.cross_dept_flag == 1 for e in events)
    max_cross_domain = max((e.cross_domain_count for e in events), default=0)

    flags = []
    if max_person_dev >= 5:
        flags.append("个人历史行为极端偏离")
    elif max_person_dev >= 3:
        flags.append("个人历史行为显著偏离")
    elif max_person_dev >= 1.5:
        flags.append("个人历史行为轻度偏离")

    if max_role_dev >= 5:
        flags.append("岗位群体行为极端偏离")
    elif max_role_dev >= 3:
        flags.append("岗位群体行为显著偏离")
    elif max_role_dev >= 1.5:
        flags.append("岗位群体行为轻度偏离")

    if has_new_device:
        flags.append("新设备登录")
    if has_off_work:
        flags.append("非工作时间操作")
    if cross_dept:
        flags.append("跨部门访问")
    if max_cross_domain >= 3:
        flags.append("跨域访问范围偏大")

    return {
        "max_person_deviation": max_person_dev,
        "max_role_deviation": max_role_dev,
        "has_new_device": has_new_device,
        "has_off_work": has_off_work,
        "cross_dept": cross_dept,
        "max_cross_domain": max_cross_domain,
        "profile_abnormal_flags": flags,
    }
