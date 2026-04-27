import csv
from .base_agent import BaseAgent
from schemas import RawEvent


def _int(row, key, default=0):
    try:
        return int(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _float(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


class DataAgent(BaseAgent):
    name = "数据接入Agent"

    def run(self, csv_path: str):
        events = []
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                events.append(RawEvent(
                    event_id=row.get("event_id", ""),
                    session_id=row.get("session_id", ""),
                    event_time=row.get("event_time", ""),
                    user_id=row.get("user_id", ""),
                    dept=row.get("dept", ""),
                    role=row.get("role", ""),
                    device_id=row.get("device_id", ""),
                    device_new_flag=_int(row, "device_new_flag"),
                    ip_region=row.get("ip_region", ""),
                    event_type=row.get("event_type", ""),
                    object_domain=row.get("object_domain", ""),
                    sensitivity_level=_int(row, "sensitivity_level"),
                    query_count=_int(row, "query_count"),
                    export_count=_int(row, "export_count"),
                    file_size_mb=_float(row, "file_size_mb"),
                    print_pages=_int(row, "print_pages"),
                    screenshot_count=_int(row, "screenshot_count"),
                    external_send_count=_int(row, "external_send_count"),
                    copy_count=_int(row, "copy_count"),
                    target_path_type=row.get("target_path_type", ""),
                    usb_registered_flag=_int(row, "usb_registered_flag"),
                    approval_flag=_int(row, "approval_flag"),
                    business_flag=_int(row, "business_flag"),
                    case_id=row.get("case_id", ""),
                    cross_dept_flag=_int(row, "cross_dept_flag"),
                    off_work_flag=_int(row, "off_work_flag"),
                    deviation_person=_float(row, "deviation_person"),
                    deviation_role=_float(row, "deviation_role"),
                    sensitive_hit_ratio=_float(row, "sensitive_hit_ratio"),
                    unique_id_ratio=_float(row, "unique_id_ratio"),
                    cross_domain_count=_int(row, "cross_domain_count"),
                    compress_flag=_int(row, "compress_flag"),
                    encrypt_flag=_int(row, "encrypt_flag"),
                    delete_flag=_int(row, "delete_flag"),
                    tool_abnormal_flag=_int(row, "tool_abnormal_flag"),
                    account_type=row.get("account_type", ""),
                    action_object=row.get("action_object", ""),
                    object_type=row.get("object_type", ""),
                    access_count=_int(row, "access_count"),
                    cross_table_count=_int(row, "cross_table_count"),
                    data_mask_flag=_int(row, "data_mask_flag"),
                    keep_days=_int(row, "keep_days"),
                    task_id=row.get("task_id", ""),
                ))

        trace = self.trace(
            {"csv_path": csv_path},
            {"raw_event_count": len(events), "unique_sessions": len({(e.user_id, e.session_id) for e in events})},
        )
        return events, trace
