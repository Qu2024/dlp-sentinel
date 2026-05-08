import csv
from pathlib import Path


def load_permissions(permission_path="knowledge/role_permissions.csv") -> list[dict]:
    rules = []
    p = Path(permission_path)
    if not p.exists():
        return rules
    with p.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rules.append({
                "role": row.get("role", ""),
                "object_domain": row.get("object_domain", ""),
                "event_type": row.get("event_type", ""),
                "max_export_count": int(row.get("max_export_count", 0) or 0),
                "need_approval": int(row.get("need_approval", 0) or 0),
                "allow_cross_dept": int(row.get("allow_cross_dept", 0) or 0),
            })
    return rules


def _match_rule(rules, role, object_domain, event_type):
    for r in rules:
        if r["role"] == role and r["object_domain"] == object_domain and r["event_type"] == event_type:
            return r
    return None


def analyze(candidate, permission_rules=None) -> dict:
    permission_rules = permission_rules if permission_rules is not None else load_permissions()
    problems = []
    evidence = []
    matched_permissions = []

    for e in candidate.events:
        action_type = "export" if (e.export_count > 0 or e.print_pages > 0 or e.copy_count > 0 or e.external_send_count > 0) else e.event_type
        rule = _match_rule(permission_rules, e.role, e.object_domain, action_type)

        if e.case_id:
            evidence.append(f"案件编号：{e.case_id}")
        if e.task_id:
            evidence.append(f"任务编号：{e.task_id}")
        if e.business_flag == 0:
            problems.append("缺少明确业务关联")
        if not e.case_id and not e.task_id and e.sensitivity_level >= 3:
            problems.append("高敏操作缺少案件或任务编号")
        if e.approval_flag == 0 and (e.export_count > 0 or e.print_pages > 0):
            problems.append("导出/打印行为缺少审批")

        if rule is None and action_type in ("query", "export"):
            problems.append(f"未匹配到岗位权限规则：{e.role}-{e.object_domain}-{action_type}")
        elif rule is not None:
            matched_permissions.append(f"{e.role}-{e.object_domain}-{action_type}")
            if action_type == "export" and e.export_count > rule["max_export_count"]:
                problems.append(f"导出数量超过岗位限制：{e.export_count}>{rule['max_export_count']}")
            if rule["need_approval"] == 1 and e.approval_flag == 0:
                problems.append("该类操作需要审批但未审批")
            if rule["allow_cross_dept"] == 0 and e.cross_dept_flag == 1:
                problems.append("岗位权限不支持跨部门访问")

    unique_problems = list(dict.fromkeys(problems))
    return {
        "business_reasonable": len(unique_problems) == 0,
        "business_problems": unique_problems,
        "business_evidence": list(dict.fromkeys(evidence)),
        "matched_permissions": list(dict.fromkeys(matched_permissions)),
        "permission_rule_count": len(permission_rules),
    }
