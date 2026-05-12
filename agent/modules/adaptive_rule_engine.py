from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any


DEFAULT_RULE_DIR = Path("knowledge") / "adaptive_rules"
RULE_DIR_ENV = "DLP_ADAPTIVE_RULE_DIR"
ACTIVE_RULES_FILE = "active_rules.json"
SUGGESTED_RULES_FILE = "suggested_rules.json"
LATEST_RUN_FILE = "latest_run.json"
LEARNING_LOG_FILE = "learning_log.jsonl"
RUNS_DIR = "runs"

HIGH_RISK_LEVELS = {"高风险", "极高风险"}
POSITIVE_RISK_LEVELS = {"中风险", "高风险", "极高风险"}

FIELD_LABELS = {
    "approval_missing": "未审批",
    "business_missing": "业务缺失",
    "business_flag": "业务标记",
    "compress_flag": "压缩打包",
    "copy_count": "拷贝次数",
    "cross_dept_flag": "跨部门",
    "cross_domain_count": "跨域访问数",
    "delete_flag": "删除清痕",
    "deviation_person": "个人偏离度",
    "deviation_role": "岗位偏离度",
    "device_new_flag": "新设备",
    "encrypt_flag": "加密处理",
    "export_count": "导出量",
    "external_send_count": "外发次数",
    "off_work_flag": "非工作时间",
    "print_pages": "打印页数",
    "query_count": "查询量",
    "sensitivity_level": "敏感等级",
    "screenshot_count": "截图次数",
    "tool_abnormal_flag": "异常工具",
    "usb_registered_flag": "USB备案",
    "usb_unregistered": "未备案USB",
}

BOOLEAN_ATOMS = [
    {"field": "off_work_flag", "op": "==", "value": 1},
    {"field": "device_new_flag", "op": "==", "value": 1},
    {"field": "cross_dept_flag", "op": "==", "value": 1},
    {"field": "approval_missing", "op": "==", "value": 1},
    {"field": "business_missing", "op": "==", "value": 1},
    {"field": "usb_unregistered", "op": "==", "value": 1},
    {"field": "tool_abnormal_flag", "op": "==", "value": 1},
    {"field": "compress_flag", "op": "==", "value": 1},
    {"field": "encrypt_flag", "op": "==", "value": 1},
    {"field": "delete_flag", "op": "==", "value": 1},
]

NUMERIC_ATOM_SPECS = {
    "sensitivity_level": ">=",
    "query_count": ">",
    "export_count": ">",
    "print_pages": ">",
    "screenshot_count": ">",
    "external_send_count": ">",
    "copy_count": ">",
    "cross_domain_count": ">=",
    "deviation_person": ">=",
    "deviation_role": ">=",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_run_id() -> str:
    return datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")


def _default_active_rules() -> dict[str, Any]:
    return {'version': 2, 'updated_at': '2026-05-11 00:00:00', 'scene_rules': [{'id': 'scene_01_offwork_sensitive_access', 'name': '场景1：非工作时段异常登录后访问敏感数据', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'off_work_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'access_count', 'op': '>=', 'value': 10, 'learnable': True}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}]}, {'id': 'scene_02_multi_region_device_login', 'name': '场景2：同一账号短时多地点/多设备登录', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'unique_region_count', 'op': '>=', 'value': 2, 'learnable': False}, {'field': 'unique_device_count', 'op': '>=', 'value': 2, 'learnable': False}]}, {'id': 'scene_03_new_device_high_risk_action', 'name': '场景3：新设备首次登录后立即执行高风险操作', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'device_new_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'high_risk_action_count', 'op': '>=', 'value': 1, 'learnable': True}]}, {'id': 'scene_04_profile_mutation', 'name': '场景4：账号行为画像突变', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'deviation_person', 'op': '>=', 'value': 3, 'learnable': True}, {'field': 'deviation_role', 'op': '>=', 'value': 2, 'learnable': True}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}]}, {'id': 'scene_05_unauthorized_no_business', 'name': '场景5：越权访问核心数据且无业务关联', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'business_flag', 'op': '==', 'value': 0, 'learnable': False}, {'field': 'approval_flag', 'op': '==', 'value': 0, 'learnable': False}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}, {'field': 'access_count', 'op': '>=', 'value': 5, 'learnable': True}]}, {'id': 'scene_06_cross_dept_sensitive_access', 'name': '场景6：跨部门敏感数据访问异常', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'cross_dept_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'access_count', 'op': '>=', 'value': 10, 'learnable': True}, {'field': 'business_flag', 'op': '==', 'value': 0, 'learnable': False}]}, {'id': 'scene_07_high_sensitive_page_frequency', 'name': '场景7：访问高敏感页面频率异常', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}, {'field': 'access_count', 'op': '>=', 'value': 50, 'learnable': True}, {'field': 'business_flag', 'op': '==', 'value': 0, 'learnable': False}]}, {'id': 'scene_08_concentrated_multi_domain_access', 'name': '场景8：短时集中访问多个高敏对象', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}, {'field': 'access_count', 'op': '>=', 'value': 20, 'learnable': True}, {'field': 'cross_domain_count', 'op': '>=', 'value': 3, 'learnable': True}]}, {'id': 'scene_09_high_precise_query', 'name': '场景9：单日精准查询异常偏高', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'query_count', 'op': '>=', 'value': 200, 'learnable': True}, {'field': 'deviation_role', 'op': '>=', 'value': 10, 'learnable': True}, {'field': 'business_flag', 'op': '==', 'value': 0, 'learnable': False}]}, {'id': 'scene_10_cross_table_reidentify', 'name': '场景10：跨表关联拼接还原敏感身份', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'cross_table_count', 'op': '>=', 'value': 5, 'learnable': True}, {'field': 'query_count', 'op': '>=', 'value': 20, 'learnable': True}, {'field': 'unique_id_ratio', 'op': '>=', 'value': 0.3, 'learnable': True}]}, {'id': 'scene_11_batch_condition_filter', 'name': '场景11：按名单/条件批量筛选敏感对象', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'query_count', 'op': '>=', 'value': 500, 'learnable': True}, {'field': 'export_count', 'op': '>=', 'value': 1, 'learnable': True}]}, {'id': 'scene_12_query_then_export_chain', 'name': '场景12：短时构建先查后导完整链路', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'query_count', 'op': '>=', 'value': 100, 'learnable': True}, {'field': 'export_count', 'op': '>=', 'value': 1, 'learnable': True}]}, {'id': 'scene_13_offwork_bulk_export', 'name': '场景13：非工作时段高频批量导出敏感数据', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'off_work_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'export_count', 'op': '>=', 'value': 30, 'learnable': True}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}]}, {'id': 'scene_14_unapproved_sensitive_export', 'name': '场景14：绕过审批违规导出/下载高敏数据', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'approval_flag', 'op': '==', 'value': 0, 'learnable': False}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}, {'field': 'export_count', 'op': '>=', 'value': 1, 'learnable': True}]}, {'id': 'scene_15_screenshot_external_send', 'name': '场景15：敏感页面高频截图并伴随外发', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'screenshot_count', 'op': '>=', 'value': 5, 'learnable': True}, {'field': 'external_send_count', 'op': '>=', 'value': 3, 'learnable': True}, {'field': 'sensitive_hit_ratio', 'op': '>=', 'value': 0.5, 'learnable': True}]}, {'id': 'scene_16_abnormal_sensitive_print', 'name': '场景16：敏感文档异常打印', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'print_pages', 'op': '>=', 'value': 100, 'learnable': True}, {'field': 'business_flag', 'op': '==', 'value': 0, 'learnable': False}]}, {'id': 'scene_17_prod_to_test_unmasked', 'name': '场景17：生产数据违规同步至测试/开发环境', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'target_path_type', 'op': '==', 'value': '测试环境', 'learnable': False}, {'field': 'data_mask_flag', 'op': '==', 'value': 0, 'learnable': False}, {'field': 'keep_days', 'op': '>', 'value': 7, 'learnable': True}]}, {'id': 'scene_18_sensitive_local_or_shared_landing', 'name': '场景18：敏感数据落地本地终端或共享目录', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'target_path_type', 'op': '==', 'value': '共享目录', 'learnable': False}, {'field': 'copy_count', 'op': '>=', 'value': 3, 'learnable': True}, {'field': 'sensitivity_level', 'op': '>=', 'value': 4, 'learnable': True}]}, {'id': 'scene_19_usb_sensitive_copy', 'name': '场景19：移动介质/外设拷贝敏感数据', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'target_path_type', 'op': '==', 'value': 'USB', 'learnable': False}, {'field': 'usb_registered_flag', 'op': '==', 'value': 0, 'learnable': False}, {'field': 'copy_count', 'op': '>=', 'value': 10, 'learnable': True}]}, {'id': 'scene_20_compress_encrypt_delete_trace', 'name': '场景20：异常压缩加密/清痕规避', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'compress_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'encrypt_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'delete_flag', 'op': '==', 'value': 1, 'learnable': False}, {'field': 'tool_abnormal_flag', 'op': '==', 'value': 1, 'learnable': False}]}], 'high_risk_thresholds': [{'field': 'export_count', 'op': '>=', 'value': 100, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': True}, {'field': 'print_pages', 'op': '>=', 'value': 100, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': True}, {'field': 'screenshot_count', 'op': '>=', 'value': 20, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': True}, {'field': 'external_send_count', 'op': '>=', 'value': 5, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': True}, {'field': 'deviation_person', 'op': '>=', 'value': 5, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': True}, {'field': 'tool_abnormal_flag', 'op': '==', 'value': 1, 'scope': 'session', 'source': 'seed_20_scenes', 'learnable': False}], 'weak_rules': [{'id': 'weak_off_work', 'name': '非工作时间', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'off_work_flag', 'op': '==', 'value': 1}]}, {'id': 'weak_new_device', 'name': '新设备', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'device_new_flag', 'op': '==', 'value': 1}]}, {'id': 'weak_cross_dept', 'name': '跨部门', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'cross_dept_flag', 'op': '==', 'value': 1}]}, {'id': 'weak_unapproved', 'name': '未审批', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'approval_flag', 'op': '==', 'value': 0}]}, {'id': 'weak_no_business', 'name': '无业务支撑', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'business_flag', 'op': '==', 'value': 0}]}, {'id': 'weak_sensitive', 'name': '高敏对象', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'sensitivity_level', 'op': '>=', 'value': 4}]}, {'id': 'weak_large_export', 'name': '较大导出', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'export_count', 'op': '>=', 'value': 30}]}, {'id': 'weak_abnormal_tool', 'name': '异常工具', 'scope': 'session', 'status': 'active', 'source': 'seed_20_scenes', 'conditions': [{'field': 'tool_abnormal_flag', 'op': '==', 'value': 1}]}]}

def _default_suggested_rules() -> dict[str, Any]:
    return {
        "generated_at": _now(),
        "rules": [],
        "reviewed_rules": [],
        "rejected_rule_ids": [],
    }


def _rule_dir(rule_dir: str | Path | None = None) -> Path:
    return Path(rule_dir or os.getenv(RULE_DIR_ENV) or DEFAULT_RULE_DIR)


def resolve_rule_dir(rule_dir: str | Path | None = None) -> Path:
    return _rule_dir(rule_dir)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return deepcopy(default)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def ensure_store(rule_dir: str | Path | None = None) -> Path:
    store_dir = _rule_dir(rule_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / RUNS_DIR).mkdir(parents=True, exist_ok=True)

    active_path = store_dir / ACTIVE_RULES_FILE
    suggested_path = store_dir / SUGGESTED_RULES_FILE
    if not active_path.exists():
        _write_json(active_path, _default_active_rules())
    if not suggested_path.exists():
        _write_json(suggested_path, _default_suggested_rules())
    return store_dir


def load_active_rules(rule_dir: str | Path | None = None) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    data = _read_json(store_dir / ACTIVE_RULES_FILE, _default_active_rules())
    data.setdefault("scene_rules", [])
    data.setdefault("high_risk_thresholds", [])
    data.setdefault("weak_rules", [])
    return data


def load_suggested_rules(rule_dir: str | Path | None = None) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    data = _read_json(store_dir / SUGGESTED_RULES_FILE, _default_suggested_rules())
    data.setdefault("rules", [])
    data.setdefault("reviewed_rules", [])
    data.setdefault("rejected_rule_ids", [])
    return data


def review_suggested_rule(
    rule_id: str,
    action: str,
    rule_dir: str | Path | None = None,
    review_comment: str = "",
) -> dict[str, Any]:
    """Approve or reject one mined suggestion and remove it from the pending pool."""
    store_dir = ensure_store(rule_dir)
    active_rules = load_active_rules(store_dir)
    suggested_rules = load_suggested_rules(store_dir)
    action = action.lower().strip()
    if action not in {"approve", "accept", "activate", "reject", "discard"}:
        return {"ok": False, "error": f"Unsupported action: {action}"}

    target = None
    remaining_rules = []
    for rule in suggested_rules["rules"]:
        if rule.get("id") == rule_id:
            target = deepcopy(rule)
        else:
            remaining_rules.append(rule)

    if not target:
        return {
            "ok": False,
            "error": "Suggested rule not found",
            "active_rules": active_rules,
            "suggested_rules": suggested_rules,
        }

    now = _now()
    reviewed = deepcopy(target)
    reviewed["reviewed_at"] = now
    reviewed["review_comment"] = review_comment

    if action in {"approve", "accept", "activate"}:
        active_ids = {rule.get("id") for rule in active_rules["scene_rules"]}
        active_signatures = {
            _condition_signature(rule.get("conditions", []))
            for rule in active_rules["scene_rules"]
        }
        target_signature = _condition_signature(target.get("conditions", []))
        if target.get("id") not in active_ids and target_signature not in active_signatures:
            promoted = deepcopy(target)
            promoted["status"] = "active"
            promoted["approved"] = True
            promoted["source"] = "approved_suggestion"
            promoted["activated_at"] = now
            promoted["review_comment"] = review_comment
            active_rules["scene_rules"].append(promoted)
            active_rules["updated_at"] = now
            _write_json(store_dir / ACTIVE_RULES_FILE, active_rules)

        reviewed["status"] = "active"
        reviewed["approved"] = True
        reviewed["activated_at"] = now
        result_action = "approved"
    else:
        reviewed["status"] = "rejected"
        reviewed["approved"] = False
        reviewed["rejected_at"] = now
        rejected_ids = set(suggested_rules.get("rejected_rule_ids", []))
        rejected_ids.add(rule_id)
        suggested_rules["rejected_rule_ids"] = sorted(rejected_ids)
        result_action = "rejected"

    reviewed_rules = suggested_rules.get("reviewed_rules", [])
    reviewed_rules = [rule for rule in reviewed_rules if rule.get("id") != rule_id]
    reviewed_rules.insert(0, reviewed)
    suggested_rules["reviewed_rules"] = reviewed_rules[:100]
    suggested_rules["rules"] = remaining_rules
    suggested_rules["generated_at"] = now
    _write_json(store_dir / SUGGESTED_RULES_FILE, suggested_rules)

    return {
        "ok": True,
        "action": result_action,
        "rule_id": rule_id,
        "active_rules": active_rules,
        "suggested_rules": suggested_rules,
    }


def prepare_runtime(output_dir: str | Path = "output", rule_dir: str | Path | None = None) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    feedback_sync = sync_feedback_from_output(output_dir=output_dir, rule_dir=store_dir)
    activation = apply_approved_suggestions(rule_dir=store_dir)
    active_rules = load_active_rules(store_dir)
    suggested_rules = load_suggested_rules(store_dir)

    return {
        "feedback_sync": feedback_sync,
        "activated_rules": activation["activated_count"],
        "active_scene_rules": len(active_rules["scene_rules"]),
        "active_high_risk_thresholds": len(active_rules["high_risk_thresholds"]),
        "active_weak_rules": len(active_rules["weak_rules"]),
        "pending_suggested_rules": sum(
            1 for rule in suggested_rules["rules"]
            if rule.get("status", "suggested") == "suggested" and not rule.get("approved", False)
        ),
    }


def sync_feedback_from_output(output_dir: str | Path = "output", rule_dir: str | Path | None = None) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    latest_run = _read_json(store_dir / LATEST_RUN_FILE, {})
    run_id = latest_run.get("run_id")
    if not run_id:
        return {"synced": False, "updated_items": 0}

    output_path = Path(output_dir) / "feedback.json"
    run_feedback_path = store_dir / RUNS_DIR / run_id / "feedback.json"
    if not output_path.exists() or not run_feedback_path.exists():
        return {"synced": False, "updated_items": 0}

    output_items = _read_json(output_path, [])
    run_items = _read_json(run_feedback_path, [])
    run_index = {item.get("candidate_event_id"): item for item in run_items}
    updated_items = 0

    for output_item in output_items:
        candidate_id = output_item.get("candidate_event_id")
        if candidate_id not in run_index:
            continue
        target = run_index[candidate_id]
        changed = False
        for field in ("human_confirmed", "false_positive", "review_comment", "risk_level"):
            if output_item.get(field) != target.get(field):
                target[field] = output_item.get(field)
                changed = True
        if changed:
            updated_items += 1

    if updated_items:
        _write_json(run_feedback_path, list(run_index.values()))

    return {"synced": True, "updated_items": updated_items}


def apply_approved_suggestions(rule_dir: str | Path | None = None) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    active_rules = load_active_rules(store_dir)
    suggested_rules = load_suggested_rules(store_dir)
    active_ids = {rule.get("id") for rule in active_rules["scene_rules"]}

    activated = 0
    changed = False
    for rule in suggested_rules["rules"]:
        if not rule.get("approved", False):
            continue
        if rule.get("status") == "active":
            continue

        if rule.get("id") not in active_ids:
            promoted = deepcopy(rule)
            promoted["status"] = "active"
            promoted["source"] = "approved_suggestion"
            promoted["activated_at"] = _now()
            active_rules["scene_rules"].append(promoted)
            active_ids.add(promoted.get("id"))
        rule["status"] = "active"
        rule["activated_at"] = _now()
        activated += 1
        changed = True

    if changed:
        active_rules["updated_at"] = _now()
        _write_json(store_dir / ACTIVE_RULES_FILE, active_rules)
        suggested_rules["generated_at"] = _now()
        _write_json(store_dir / SUGGESTED_RULES_FILE, suggested_rules)

    return {"activated_count": activated}


def summarize_session_events(events: list[Any]) -> dict[str, Any]:
    rows = []
    for event in events:
        if is_dataclass(event):
            rows.append(asdict(event))
        elif isinstance(event, dict):
            rows.append(event)
        else:
            rows.append(getattr(event, "__dict__", {}))

    if not rows:
        return {}

    numeric_max_fields = [
        "sensitivity_level",
        "query_count",
        "export_count",
        "print_pages",
        "screenshot_count",
        "external_send_count",
        "copy_count",
        "access_count",
        "cross_table_count",
        "cross_domain_count",
        "file_size_mb",
        "sensitive_hit_ratio",
        "unique_id_ratio",
        "data_mask_flag",
        "keep_days",
        "deviation_person",
        "deviation_role",
        "tool_abnormal_flag",
        "device_new_flag",
        "cross_dept_flag",
        "off_work_flag",
        "compress_flag",
        "encrypt_flag",
        "delete_flag",
    ]

    summary = {
        field: max(_to_number(row.get(field, 0)) for row in rows)
        for field in numeric_max_fields
    }
    summary["approval_missing"] = 1 if any(_to_number(row.get("approval_flag", 1)) == 0 for row in rows) else 0
    summary["business_missing"] = 1 if any(_to_number(row.get("business_flag", 1)) == 0 for row in rows) else 0
    summary["usb_unregistered"] = 1 if any(_to_number(row.get("usb_registered_flag", 1)) == 0 for row in rows) else 0
    summary["unique_device_count"] = len({str(row.get("device_id", "")) for row in rows if row.get("device_id")})
    summary["unique_region_count"] = len({str(row.get("ip_region", "")) for row in rows if row.get("ip_region")})
    summary["target_path_type"] = next((str(row.get("target_path_type")) for row in rows if row.get("target_path_type") in {"USB", "共享目录", "测试环境"}), str(rows[-1].get("target_path_type", "")))
    summary["high_risk_action_count"] = sum(
        1 for row in rows
        if str(row.get("event_type", "")) in {"export", "download", "print", "query", "screenshot", "copy", "external_send"}
        and (
            _to_number(row.get("export_count", 0)) > 0
            or _to_number(row.get("print_pages", 0)) > 0
            or _to_number(row.get("query_count", 0)) > 0
            or _to_number(row.get("screenshot_count", 0)) > 0
            or _to_number(row.get("copy_count", 0)) > 0
            or _to_number(row.get("external_send_count", 0)) > 0
        )
    )
    summary["event_count"] = len(rows)
    return summary


def update_after_run(
    run_id: str,
    source_csv: str,
    candidates: list[Any],
    scored_events: list[Any],
    reports: list[Any],
    feedback_items: list[dict[str, Any]],
    output_dir: str | Path = "output",
    rule_dir: str | Path | None = None,
) -> dict[str, Any]:
    store_dir = ensure_store(rule_dir)
    run_dir = store_dir / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    candidate_payload = _serialize_items(candidates)
    scored_payload = _serialize_items(scored_events)
    report_payload = _serialize_items(reports)
    feedback_payload = deepcopy(feedback_items)

    _write_json(run_dir / "candidate_events.json", candidate_payload)
    _write_json(run_dir / "risk_events.json", scored_payload)
    _write_json(run_dir / "reports.json", report_payload)
    _write_json(run_dir / "feedback.json", feedback_payload)
    _write_json(run_dir / "meta.json", {
        "run_id": run_id,
        "source_csv": source_csv,
        "saved_at": _now(),
        "candidate_count": len(candidate_payload),
        "scored_event_count": len(scored_payload),
        "report_count": len(report_payload),
    })
    _write_json(store_dir / LATEST_RUN_FILE, {
        "run_id": run_id,
        "feedback_file": str(Path(output_dir) / "feedback.json"),
        "snapshot_feedback_file": str(run_dir / "feedback.json"),
        "updated_at": _now(),
    })

    samples = _load_learning_samples(store_dir)
    active_rules = load_active_rules(store_dir)
    threshold_updates = _learn_threshold_updates(samples, active_rules)
    if threshold_updates:
        active_rules["updated_at"] = _now()
        _write_json(store_dir / ACTIVE_RULES_FILE, active_rules)

    suggested_summary = _refresh_suggested_rules(samples, active_rules, store_dir)
    labeled_count = sum(1 for sample in samples if sample["hard_label"] is not None)

    log_entry = {
        "time": _now(),
        "run_id": run_id,
        "history_run_count": len(list((store_dir / RUNS_DIR).glob("run_*"))),
        "labeled_sample_count": labeled_count,
        "threshold_updates": threshold_updates,
        "suggested_rule_count": suggested_summary["suggested_rule_count"],
    }
    _append_jsonl(store_dir / LEARNING_LOG_FILE, log_entry)

    return {
        "run_id": run_id,
        "history_run_count": log_entry["history_run_count"],
        "labeled_sample_count": labeled_count,
        "threshold_updates": threshold_updates,
        "suggested_rule_count": suggested_summary["suggested_rule_count"],
        "pending_suggested_rules": suggested_summary["pending_suggested_rules"],
    }


def _serialize_items(items: list[Any]) -> list[dict[str, Any]]:
    payload = []
    for item in items:
        if is_dataclass(item):
            payload.append(asdict(item))
        elif isinstance(item, dict):
            payload.append(deepcopy(item))
        else:
            payload.append(deepcopy(getattr(item, "__dict__", {})))
    return payload


def _load_learning_samples(store_dir: Path) -> list[dict[str, Any]]:
    sample_index = {}
    for run_dir in sorted((store_dir / RUNS_DIR).glob("run_*")):
        candidates = _read_json(run_dir / "candidate_events.json", [])
        scored_map = {
            item.get("candidate_event_id"): item
            for item in _read_json(run_dir / "risk_events.json", [])
        }
        report_map = {
            item.get("candidate_event_id"): item
            for item in _read_json(run_dir / "reports.json", [])
        }
        feedback_map = {
            item.get("candidate_event_id"): item
            for item in _read_json(run_dir / "feedback.json", [])
        }

        for candidate in candidates:
            candidate_id = candidate.get("candidate_event_id", "")
            feedback = feedback_map.get(candidate_id, {})
            report = report_map.get(candidate_id, {})
            scored = scored_map.get(candidate_id, {})
            risk_level = feedback.get("risk_level") or report.get("risk_level") or scored.get("risk_level", "")
            hard_label, hard_source = _resolve_hard_label(feedback)
            pseudo_label, pseudo_source, pseudo_weight = _resolve_pseudo_label(candidate, risk_level, hard_label)
            sample = {
                "run_id": run_dir.name,
                "candidate_event_id": candidate_id,
                "candidate_flag": candidate.get("candidate_flag", 0),
                "matched_scene_list": candidate.get("matched_scene_list", []),
                "risk_level": risk_level,
                "features": summarize_session_events(candidate.get("events", [])),
                "hard_label": hard_label,
                "hard_label_source": hard_source,
                "pseudo_label": pseudo_label,
                "pseudo_label_source": pseudo_source,
                "pseudo_weight": pseudo_weight,
            }
            fingerprint = json.dumps(
                {
                    "candidate_event_id": candidate_id,
                    "events": candidate.get("events", []),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            current = sample_index.get(fingerprint)
            if not current or _prefer_sample(sample, current):
                sample_index[fingerprint] = sample
    return list(sample_index.values())


def _prefer_sample(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_score = _sample_priority(candidate)
    current_score = _sample_priority(current)
    if candidate_score != current_score:
        return candidate_score > current_score
    return candidate.get("run_id", "") >= current.get("run_id", "")


def _sample_priority(sample: dict[str, Any]) -> int:
    if sample.get("hard_label") is not None:
        return 2
    if sample.get("pseudo_label") is not None:
        return 1
    return 0


def _resolve_hard_label(feedback: dict[str, Any]) -> tuple[int | None, str]:
    if not feedback:
        return None, ""
    if feedback.get("false_positive") is True:
        return 0, "false_positive"
    if feedback.get("human_confirmed") is True:
        return 1, "human_confirmed"
    if feedback.get("human_confirmed") is False:
        return 0, "human_rejected"
    return None, ""


def _resolve_pseudo_label(candidate: dict[str, Any], risk_level: str, hard_label: int | None) -> tuple[int | None, str, float]:
    if hard_label is not None:
        return None, "", 0.0
    if risk_level in HIGH_RISK_LEVELS:
        return 1, "high_risk_proxy", 0.35
    if candidate.get("candidate_flag", 0) == 0:
        return 0, "background_proxy", 0.15
    return None, "", 0.0


def _build_training_rows(samples: list[dict[str, Any]], allow_pseudo: bool) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        if sample["hard_label"] is not None:
            rows.append({
                "features": sample["features"],
                "label": sample["hard_label"],
                "weight": 1.0,
                "is_hard_label": True,
            })
        elif allow_pseudo and sample["pseudo_label"] is not None:
            rows.append({
                "features": sample["features"],
                "label": sample["pseudo_label"],
                "weight": sample["pseudo_weight"],
                "is_hard_label": False,
            })
    return rows


def _learn_threshold_updates(samples: list[dict[str, Any]], active_rules: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _build_training_rows(samples, allow_pseudo=False)
    hard_positive = sum(1 for row in rows if row["label"] == 1)
    hard_negative = sum(1 for row in rows if row["label"] == 0)
    if hard_positive < 1 or hard_negative < 1 or len(rows) < 4:
        return []

    updates = []
    for rule in active_rules["scene_rules"]:
        for index, condition in enumerate(rule.get("conditions", [])):
            if not condition.get("learnable"):
                continue
            other_conditions = [
                cond for offset, cond in enumerate(rule.get("conditions", []))
                if offset != index
            ]
            base_filter = lambda features, conditions=other_conditions: all(
                _condition_matches_feature(features, cond) for cond in conditions
            )
            result = _optimize_threshold(rows, condition, base_filter)
            if not result:
                continue
            old_value = condition["value"]
            condition["value"] = result["new_value"]
            condition["updated_at"] = _now()
            condition["learning"] = {
                "method": "f0.5_threshold_search",
                "support": result["support_count"],
                "precision": result["precision"],
                "recall": result["recall"],
                "f0.5": result["f05"],
            }
            updates.append({
                "type": "scene_rule",
                "rule_id": rule.get("id"),
                "rule_name": rule.get("name"),
                "field": condition.get("field"),
                "old_value": old_value,
                "new_value": result["new_value"],
                "support_count": result["support_count"],
                "precision": result["precision"],
                "recall": result["recall"],
                "f0.5": result["f05"],
            })

    for threshold in active_rules["high_risk_thresholds"]:
        if not threshold.get("learnable"):
            continue
        result = _optimize_threshold(rows, threshold, lambda _: True)
        if not result:
            continue
        old_value = threshold["value"]
        threshold["value"] = result["new_value"]
        threshold["updated_at"] = _now()
        threshold["learning"] = {
            "method": "f0.5_threshold_search",
            "support": result["support_count"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f0.5": result["f05"],
        }
        updates.append({
            "type": "high_risk_threshold",
            "field": threshold.get("field"),
            "old_value": old_value,
            "new_value": result["new_value"],
            "support_count": result["support_count"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f0.5": result["f05"],
        })

    return updates


def _optimize_threshold(
    rows: list[dict[str, Any]],
    condition: dict[str, Any],
    base_filter,
) -> dict[str, Any] | None:
    subset = [row for row in rows if base_filter(row["features"])]
    if len(subset) < 4:
        return None

    current_value = condition["value"]
    field = condition["field"]
    op = condition["op"]
    values = [float(_feature_value(row["features"], field)) for row in subset if _feature_value(row["features"], field) is not None]
    if len(set(values)) < 2:
        return None

    baseline = _condition_metrics(subset, field, op, current_value)
    best = baseline
    best_value = current_value
    for candidate in _candidate_thresholds(values, current_value):
        metrics = _condition_metrics(subset, field, op, candidate)
        if _is_better_metrics(metrics, best):
            best = metrics
            best_value = candidate

    if best_value == current_value:
        return None
    if best["f05"] < baseline["f05"] + 0.05:
        return None
    if best["precision"] < baseline["precision"]:
        return None
    return {
        "new_value": _cast_threshold(best_value, current_value),
        **best,
    }


def _candidate_thresholds(values: list[float], current_value: float) -> list[float]:
    unique_values = sorted(set(values + [float(current_value)]))
    if len(unique_values) <= 20:
        return unique_values

    indices = [0, 1, 3, 5, 7, 9]
    thresholds = set()
    for index in indices:
        pos = int(index * (len(unique_values) - 1) / max(indices))
        thresholds.add(unique_values[pos])
    thresholds.add(float(current_value))
    thresholds.add(unique_values[-1])
    return sorted(thresholds)


def _condition_metrics(rows: list[dict[str, Any]], field: str, op: str, threshold: float) -> dict[str, Any]:
    tp = fp = fn = 0.0
    support_count = positive_hits = negative_hits = 0

    for row in rows:
        value = _feature_value(row["features"], field)
        predicted = _compare(value, op, threshold)
        label = row["label"]
        weight = row["weight"]
        if predicted:
            support_count += 1
            if label == 1:
                positive_hits += 1
                tp += weight
            else:
                negative_hits += 1
                fp += weight
        elif label == 1:
            fn += weight

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    beta = 0.5
    beta_sq = beta * beta
    f05 = ((1 + beta_sq) * precision * recall / (beta_sq * precision + recall)) if (precision and recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f05": round(f05, 4),
        "support_count": support_count,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
    }


def _is_better_metrics(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    if candidate["f05"] > baseline["f05"] + 1e-6:
        return True
    if candidate["f05"] == baseline["f05"] and candidate["precision"] > baseline["precision"] + 1e-6:
        return True
    if candidate["f05"] == baseline["f05"] and candidate["precision"] == baseline["precision"] and candidate["support_count"] > baseline["support_count"]:
        return True
    return False


def _refresh_suggested_rules(samples: list[dict[str, Any]], active_rules: dict[str, Any], store_dir: Path) -> dict[str, Any]:
    rows = _build_training_rows(samples, allow_pseudo=True)
    positive_rows = sum(1 for row in rows if row["label"] == 1)
    negative_rows = sum(1 for row in rows if row["label"] == 0)
    existing = load_suggested_rules(store_dir)
    if positive_rows < 2 or negative_rows < 2:
        pending = sum(
            1 for rule in existing["rules"]
            if rule.get("status", "suggested") == "suggested" and not rule.get("approved", False)
        )
        return {"suggested_rule_count": len(existing["rules"]), "pending_suggested_rules": pending}

    active_signatures = {
        _condition_signature(rule.get("conditions", []))
        for rule in active_rules["scene_rules"]
    }
    rejected_ids = set(existing.get("rejected_rule_ids", []))
    rejected_signatures = {
        _condition_signature(rule.get("conditions", []))
        for rule in existing.get("reviewed_rules", [])
        if rule.get("status") in {"rejected", "discarded"}
    }
    atomic_rules = []
    for atom in BOOLEAN_ATOMS:
        metrics = _condition_metrics(rows, atom["field"], atom["op"], atom["value"])
        if metrics["support_count"] >= 2 and metrics["precision"] >= 0.55:
            atomic_rules.append({"condition": atom, "metrics": metrics})

    for field, op in NUMERIC_ATOM_SPECS.items():
        atom = _discover_best_atomic_rule(rows, field, op)
        if atom:
            atomic_rules.append(atom)

    atomic_rules = sorted(
        atomic_rules,
        key=lambda item: (item["metrics"]["f05"], item["metrics"]["precision"], item["metrics"]["support_count"]),
        reverse=True,
    )[:8]

    new_rules = []
    for size in (2, 3):
        for combo in combinations(atomic_rules, size):
            conditions = [item["condition"] for item in combo]
            if len({condition["field"] for condition in conditions}) != len(conditions):
                continue
            signature = _condition_signature(conditions)
            if signature in active_signatures:
                continue
            rule_id = _rule_id_from_conditions(sorted(conditions, key=lambda item: (item["field"], item["op"], str(item["value"]))))
            if rule_id in rejected_ids or signature in rejected_signatures:
                continue
            metrics = _combo_metrics(rows, conditions)
            if metrics["support_count"] < 2:
                continue
            if metrics["precision"] < 0.78 or metrics["f05"] < 0.55:
                continue
            new_rules.append(_build_suggested_rule(conditions, metrics))

    new_rules = sorted(
        new_rules,
        key=lambda item: (item["metrics"]["f05"], item["metrics"]["precision"], item["metrics"]["support_count"]),
        reverse=True,
    )[:5]

    existing_index = {rule.get("id"): rule for rule in existing["rules"]}
    merged_rules = []
    seen_ids = set()
    seen_signatures = set()
    for rule in new_rules:
        current = existing_index.get(rule["id"], {})
        if current:
            rule["approved"] = current.get("approved", False)
            rule["status"] = current.get("status", "suggested")
            rule["review_comment"] = current.get("review_comment", "")
            rule["last_seen_at"] = _now()
            if rule["status"] == "active":
                rule["activated_at"] = current.get("activated_at", "")
        merged_rules.append(rule)
        seen_ids.add(rule["id"])
        seen_signatures.add(_condition_signature(rule.get("conditions", [])))

    for old_rule in existing["rules"]:
        if old_rule.get("id") in seen_ids:
            continue
        signature = _condition_signature(old_rule.get("conditions", []))
        if signature in seen_signatures:
            continue
        if old_rule.get("status") == "active":
            merged_rules.append(old_rule)
            seen_signatures.add(signature)
            continue
        if old_rule.get("status", "suggested") == "suggested":
            old_rule = deepcopy(old_rule)
            old_rule["stale"] = True
            old_rule["last_seen_at"] = old_rule.get("last_seen_at", old_rule.get("generated_at", ""))
            merged_rules.append(old_rule)
            seen_signatures.add(signature)
            continue
        if old_rule.get("approved", False):
            merged_rules.append(old_rule)
            seen_signatures.add(signature)

    payload = {
        "generated_at": _now(),
        "rules": merged_rules,
        "reviewed_rules": existing.get("reviewed_rules", []),
        "rejected_rule_ids": sorted(rejected_ids),
    }
    _write_json(store_dir / SUGGESTED_RULES_FILE, payload)

    pending = sum(
        1 for rule in merged_rules
        if rule.get("status", "suggested") == "suggested" and not rule.get("approved", False)
    )
    return {"suggested_rule_count": len(merged_rules), "pending_suggested_rules": pending}


def _discover_best_atomic_rule(rows: list[dict[str, Any]], field: str, op: str) -> dict[str, Any] | None:
    values = [
        float(_feature_value(row["features"], field))
        for row in rows
        if _feature_value(row["features"], field) is not None
    ]
    if len(set(values)) < 2:
        return None

    best = None
    for candidate in _candidate_thresholds(values, values[len(values) // 2]):
        metrics = _condition_metrics(rows, field, op, candidate)
        if metrics["support_count"] < 2 or metrics["precision"] < 0.55:
            continue
        if not best or _is_better_metrics(metrics, best["metrics"]):
            best = {
                "condition": {"field": field, "op": op, "value": _normalize_value(candidate)},
                "metrics": metrics,
            }
    return best


def _combo_metrics(rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = fn = 0.0
    support_count = positive_hits = negative_hits = 0

    for row in rows:
        predicted = all(_condition_matches_feature(row["features"], condition) for condition in conditions)
        label = row["label"]
        weight = row["weight"]
        if predicted:
            support_count += 1
            if label == 1:
                positive_hits += 1
                tp += weight
            else:
                negative_hits += 1
                fp += weight
        elif label == 1:
            fn += weight

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    beta = 0.5
    beta_sq = beta * beta
    f05 = ((1 + beta_sq) * precision * recall / (beta_sq * precision + recall)) if (precision and recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f05": round(f05, 4),
        "support_count": support_count,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
    }


def _build_suggested_rule(conditions: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    ordered_conditions = sorted(conditions, key=lambda item: (item["field"], item["op"], str(item["value"])))
    return {
        "id": _rule_id_from_conditions(ordered_conditions),
        "name": _rule_name_from_conditions(ordered_conditions),
        "scope": "session",
        "status": "suggested",
        "approved": False,
        "source": "ml_rule_mining",
        "generated_at": _now(),
        "last_seen_at": _now(),
        "review_comment": "",
        "conditions": ordered_conditions,
        "metrics": metrics,
        "explanation": "根据历史反馈样本与风险分布挖掘出的候选组合规则，需人工确认后生效。",
    }


def _rule_id_from_conditions(conditions: list[dict[str, Any]]) -> str:
    op_map = {
        ">": "gt",
        ">=": "ge",
        "<": "lt",
        "<=": "le",
        "==": "eq",
        "!=": "ne",
    }
    parts = []
    for condition in conditions:
        op = op_map.get(condition["op"], condition["op"])
        parts.append(f"{condition['field']}_{op}_{_normalize_value(condition['value'])}")
    return "ml_" + "__".join(parts)


def _rule_name_from_conditions(conditions: list[dict[str, Any]]) -> str:
    phrases = [_condition_phrase(condition) for condition in conditions]
    return "建议规则-" + " + ".join(phrases)


def _condition_signature(conditions: list[dict[str, Any]]) -> str:
    normalized = [
        f"{item.get('field')}|{item.get('op')}|{_normalize_value(item.get('value'))}"
        for item in sorted(conditions, key=lambda cond: (cond.get("field"), cond.get("op"), str(_normalize_value(cond.get("value")))))
    ]
    return "__".join(normalized)


def _condition_phrase(condition: dict[str, Any]) -> str:
    field_label = FIELD_LABELS.get(condition["field"], condition["field"])
    if condition["op"] == "==" and condition["value"] == 1:
        return field_label
    return f"{field_label}{condition['op']}{_normalize_value(condition['value'])}"


def _condition_matches_feature(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    value = _feature_value(features, condition["field"])
    return _compare(value, condition["op"], condition["value"])


def _feature_value(features: dict[str, Any], field: str) -> Any:
    if field == "approval_flag":
        return 0 if features.get("approval_missing", 0) else 1
    if field == "business_flag":
        return 0 if features.get("business_missing", 0) else 1
    if field == "usb_registered_flag":
        return 0 if features.get("usb_unregistered", 0) else 1
    return features.get(field)


def _compare(value: Any, op: str, target: Any) -> bool:
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


def _to_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _cast_threshold(candidate: float, reference: Any) -> Any:
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(round(candidate))
    if isinstance(reference, float):
        return round(float(candidate), 4)
    if float(candidate).is_integer():
        return int(candidate)
    return round(float(candidate), 4)


def _normalize_value(value: Any) -> Any:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return value
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 4)
