from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


EVENT_FIELDNAMES = [
    "event_id",
    "session_id",
    "event_time",
    "user_id",
    "account_type",
    "dept",
    "role",
    "device_id",
    "device_new_flag",
    "ip_region",
    "event_type",
    "action_object",
    "object_type",
    "object_domain",
    "sensitivity_level",
    "query_count",
    "access_count",
    "cross_table_count",
    "cross_domain_count",
    "export_count",
    "file_size_mb",
    "print_pages",
    "screenshot_count",
    "external_send_count",
    "copy_count",
    "target_path_type",
    "usb_registered_flag",
    "approval_flag",
    "business_flag",
    "case_id",
    "task_id",
    "cross_dept_flag",
    "off_work_flag",
    "deviation_person",
    "deviation_role",
    "sensitive_hit_ratio",
    "unique_id_ratio",
    "data_mask_flag",
    "keep_days",
    "compress_flag",
    "encrypt_flag",
    "delete_flag",
    "tool_abnormal_flag",
]

LABEL_FIELDNAMES = [
    "candidate_event_id",
    "session_id",
    "user_id",
    "is_anomaly",
    "scene_type",
    "scene_hint",
    "expected_risk",
    "start_time",
    "object_domain",
]

ROLE_PERMISSION_FIELDNAMES = [
    "role",
    "object_domain",
    "event_type",
    "max_export_count",
    "need_approval",
    "allow_cross_dept",
]

ROLE_PERMISSIONS = [
    {"role": "民警", "object_domain": "人口", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 0},
    {"role": "民警", "object_domain": "人口", "event_type": "export", "max_export_count": 30, "need_approval": 1, "allow_cross_dept": 0},
    {"role": "民警", "object_domain": "案件", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 0},
    {"role": "民警", "object_domain": "案件", "event_type": "export", "max_export_count": 30, "need_approval": 1, "allow_cross_dept": 0},
    {"role": "内勤", "object_domain": "人口", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 0},
    {"role": "内勤", "object_domain": "人口", "event_type": "export", "max_export_count": 10, "need_approval": 1, "allow_cross_dept": 0},
    {"role": "内勤", "object_domain": "案件", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 0},
    {"role": "内勤", "object_domain": "案件", "event_type": "export", "max_export_count": 10, "need_approval": 1, "allow_cross_dept": 0},
    {"role": "管理员", "object_domain": "系统", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 1},
    {"role": "管理员", "object_domain": "系统", "event_type": "export", "max_export_count": 50, "need_approval": 1, "allow_cross_dept": 1},
    {"role": "运维", "object_domain": "系统", "event_type": "query", "max_export_count": 0, "need_approval": 0, "allow_cross_dept": 1},
    {"role": "运维", "object_domain": "系统", "event_type": "export", "max_export_count": 20, "need_approval": 1, "allow_cross_dept": 1},
    {"role": "外包人员", "object_domain": "人口", "event_type": "query", "max_export_count": 0, "need_approval": 1, "allow_cross_dept": 0},
    {"role": "外包人员", "object_domain": "人口", "event_type": "export", "max_export_count": 0, "need_approval": 1, "allow_cross_dept": 0},
]

ARCHETYPES = [
    {
        "dept": "刑侦",
        "role": "内勤",
        "account_type": "内部",
        "clearance_level": 4,
        "allow_cross_dept": 0,
        "normal_work_start": 8,
        "normal_work_end": 17,
        "normal_region": "北京",
        "avg_daily_query": 45,
        "avg_daily_export": 1,
        "avg_daily_print_pages": 8,
        "role_avg_query": 60,
        "role_avg_export": 1,
        "allowed_domains": ["人口", "案件"],
    },
    {
        "dept": "网安",
        "role": "民警",
        "account_type": "内部",
        "clearance_level": 5,
        "allow_cross_dept": 1,
        "normal_work_start": 8,
        "normal_work_end": 18,
        "normal_region": "北京",
        "avg_daily_query": 80,
        "avg_daily_export": 2,
        "avg_daily_print_pages": 15,
        "role_avg_query": 90,
        "role_avg_export": 2,
        "allowed_domains": ["人口", "案件", "车辆", "通信"],
    },
    {
        "dept": "科信",
        "role": "管理员",
        "account_type": "内部",
        "clearance_level": 5,
        "allow_cross_dept": 1,
        "normal_work_start": 9,
        "normal_work_end": 18,
        "normal_region": "北京",
        "avg_daily_query": 30,
        "avg_daily_export": 1,
        "avg_daily_print_pages": 2,
        "role_avg_query": 35,
        "role_avg_export": 1,
        "allowed_domains": ["系统", "认证域"],
    },
    {
        "dept": "运维",
        "role": "运维",
        "account_type": "内部",
        "clearance_level": 5,
        "allow_cross_dept": 1,
        "normal_work_start": 9,
        "normal_work_end": 18,
        "normal_region": "北京",
        "avg_daily_query": 20,
        "avg_daily_export": 0.5,
        "avg_daily_print_pages": 2,
        "role_avg_query": 25,
        "role_avg_export": 1,
        "allowed_domains": ["系统", "认证域"],
    },
    {
        "dept": "外协",
        "role": "外包人员",
        "account_type": "外包",
        "clearance_level": 2,
        "allow_cross_dept": 0,
        "normal_work_start": 9,
        "normal_work_end": 18,
        "normal_region": "北京",
        "avg_daily_query": 18,
        "avg_daily_export": 0.2,
        "avg_daily_print_pages": 1,
        "role_avg_query": 20,
        "role_avg_export": 0.5,
        "allowed_domains": ["人口"],
    },
]

OBJECT_SENSITIVITY = {
    "认证域": 2,
    "系统": 2,
    "案件": 3,
    "车辆": 3,
    "通信": 4,
    "涉案财产": 4,
    "人口": 5,
}

ANOMALY_SCENES = [
    "offhour_query_export_delete",
    "new_device_export",
    "cross_dept_query_export",
    "screenshot_send_copy",
    "usb_copy_delete",
    "test_env_unmasked_keep",
]

REGIONS = ["北京", "上海", "广州", "深圳", "天津", "成都", "杭州"]


@dataclass
class DataEngineConfig:
    user_count: int = 50
    days: int = 7
    sessions_per_user_day: float = 8.0
    anomaly_rate: float = 0.03
    seed: int = 42
    start_date: str = "2026-04-20"


class DataEngine:
    def __init__(self, config: DataEngineConfig):
        self.config = config
        self.random = random.Random(config.seed)
        self.users = self._build_users(config.user_count)
        self.event_counter = 1
        self.session_counter = 1

    def generate_batch(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        labels: list[dict[str, Any]] = []
        start = datetime.strptime(self.config.start_date, "%Y-%m-%d")

        for day_offset in range(self.config.days):
            day = start + timedelta(days=day_offset)
            for user in self.users:
                session_count = self._daily_session_count(user)
                for _ in range(session_count):
                    is_anomaly = self.random.random() < self.config.anomaly_rate
                    ctx = self._create_session(user, day, is_anomaly)
                    labels.append(ctx["label"])
                    rows.extend(self._rows_for_session(ctx))

        rows.sort(key=lambda item: (item["event_time"], item["session_id"], item["event_type"]))
        self._renumber_events(rows)

        meta = self._build_meta(rows, labels)
        return rows, labels, meta

    def iter_stream(
        self,
        max_events: int | None = None,
        max_active_sessions: int = 8,
    ) -> Iterable[tuple[dict[str, Any], dict[str, Any], bool, bool]]:
        active_sessions: list[dict[str, Any]] = []
        emitted = 0
        base_day = datetime.now().replace(microsecond=0)

        while max_events is None or emitted < max_events:
            while len(active_sessions) < max_active_sessions:
                user = self.random.choice(self.users)
                is_anomaly = self.random.random() < self.config.anomaly_rate
                ctx = self._create_session(user, base_day, is_anomaly, live=True)
                active_sessions.append(ctx)

            ctx = self.random.choice(active_sessions)
            is_first_event = ctx["step_index"] == 0
            row = self._row_for_current_step(ctx)
            ctx["step_index"] += 1
            finished = ctx["step_index"] >= len(ctx["chain"])
            if finished:
                active_sessions.remove(ctx)
            emitted += 1
            yield row, ctx["label"], is_first_event, finished

    def _build_users(self, count: int) -> list[dict[str, Any]]:
        users = []
        for index in range(1, count + 1):
            base = dict(ARCHETYPES[(index - 1) % len(ARCHETYPES)])
            user = {
                **base,
                "user_id": f"U{index:04d}",
                "user_name": f"用户{index:04d}",
                "normal_devices": [f"D{index:04d}{suffix}" for suffix in ("A", "B")],
            }
            users.append(user)
        return users

    def _daily_session_count(self, user: dict[str, Any]) -> int:
        multiplier = 0.65 if user["account_type"] == "外包" else 1.0
        mean = max(self.config.sessions_per_user_day * multiplier, 0.2)
        value = int(round(self.random.gauss(mean, max(mean * 0.25, 1.0))))
        return max(value, 0)

    def _create_session(self, user: dict[str, Any], day: datetime, is_anomaly: bool, live: bool = False) -> dict[str, Any]:
        session_id = self._next_session_id()
        if is_anomaly:
            scene_type = self.random.choice(ANOMALY_SCENES)
            chain, hint = self._anomaly_chain(scene_type)
            start_time = self._anomaly_start_time(day, scene_type, live)
            object_domain = self.random.choice(["人口", "案件", "通信", "涉案财产"])
            sensitivity_level = self.random.randint(4, 5)
            device_id = f"D{self.random.randint(9000, 9999)}X"
            device_new_flag = 1
            ip_region = self.random.choice([r for r in REGIONS if r != user["normal_region"]])
            case_id = ""
            task_id = ""
            approval_flag = 0
            business_flag = 0
            expected_risk = "high"
        else:
            scene_type = "normal"
            chain, hint = self._normal_chain()
            start_time = self._normal_start_time(day, user, live)
            object_domain = self.random.choice(user["allowed_domains"])
            sensitivity_level = min(OBJECT_SENSITIVITY.get(object_domain, 2), user["clearance_level"], 3)
            device_id = self.random.choice(user["normal_devices"])
            device_new_flag = 0
            ip_region = user["normal_region"]
            case_id = f"C{day.strftime('%Y%m%d')}{user['user_id'][-4:]}"
            task_id = f"T{day.strftime('%Y%m%d')}{user['user_id'][-4:]}"
            approval_flag = 1
            business_flag = 1
            expected_risk = "low"

        label = {
            "candidate_event_id": f"{user['user_id']}_{session_id}",
            "session_id": session_id,
            "user_id": user["user_id"],
            "is_anomaly": int(is_anomaly),
            "scene_type": scene_type,
            "scene_hint": hint,
            "expected_risk": expected_risk,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "object_domain": object_domain,
        }
        return {
            "session_id": session_id,
            "user": user,
            "is_anomaly": is_anomaly,
            "scene_type": scene_type,
            "scene_hint": hint,
            "chain": chain,
            "step_offsets": self._step_offsets(chain, is_anomaly),
            "step_index": 0,
            "base_time": start_time,
            "object_domain": object_domain,
            "sensitivity_level": sensitivity_level,
            "device_id": device_id,
            "device_new_flag": device_new_flag,
            "ip_region": ip_region,
            "case_id": case_id,
            "task_id": task_id,
            "approval_flag": approval_flag,
            "business_flag": business_flag,
            "label": label,
        }

    def _normal_chain(self) -> tuple[list[str], str]:
        chain = self.random.choice([
            ["login", "query"],
            ["login", "query", "query"],
            ["login", "query", "export"],
            ["login", "query", "print"],
            ["login", "query", "screenshot"],
            ["login", "query", "copy"],
        ])
        return chain, "正常业务会话"

    def _step_offsets(self, chain: list[str], is_anomaly: bool) -> list[int]:
        offsets = [0]
        elapsed = 0
        for previous, current in zip(chain, chain[1:]):
            elapsed += self._step_gap_seconds(previous, current, is_anomaly)
            offsets.append(elapsed)
        return offsets

    def _step_gap_seconds(self, previous: str, current: str, is_anomaly: bool) -> int:
        ranges = {
            ("login", "query"): (12, 150),
            ("query", "query"): (25, 360),
            ("query", "export"): (45, 900),
            ("query", "print"): (35, 720),
            ("query", "screenshot"): (10, 240),
            ("query", "copy"): (45, 840),
            ("query", "external_send"): (25, 480),
            ("export", "copy"): (20, 360),
            ("export", "delete"): (15, 240),
            ("copy", "delete"): (10, 210),
            ("screenshot", "external_send"): (15, 300),
            ("external_send", "copy"): (25, 420),
        }
        low, high = ranges.get((previous, current), (20, 420))
        if is_anomaly:
            low = max(5, int(low * 0.45))
            high = max(low + 15, int(high * 0.72))
        else:
            high = int(high * 1.25)

        gap = self.random.randint(low, high)
        if not is_anomaly and self.random.random() < 0.18:
            gap += self.random.randint(300, 1800)
        elif is_anomaly and self.random.random() < 0.08:
            gap += self.random.randint(180, 900)
        return gap

    def _anomaly_chain(self, scene_type: str) -> tuple[list[str], str]:
        if scene_type == "offhour_query_export_delete":
            return ["login", "query", "export", "copy", "delete"], "非工作时段高敏查询、批量导出、落地后清痕"
        if scene_type == "new_device_export":
            return ["login", "query", "export"], "新设备登录后高敏批量导出"
        if scene_type == "cross_dept_query_export":
            return ["login", "query", "query", "export"], "跨部门高频查询后导出"
        if scene_type == "screenshot_send_copy":
            return ["login", "query", "screenshot", "external_send", "copy"], "敏感页面截图后外发并拷贝"
        if scene_type == "usb_copy_delete":
            return ["login", "query", "export", "copy", "delete"], "高敏数据导出后拷贝到未备案 USB 并删除痕迹"
        return ["login", "query", "export", "copy"], "未脱敏数据同步到测试环境并长期保留"

    def _normal_start_time(self, day: datetime, user: dict[str, Any], live: bool) -> datetime:
        if live:
            return datetime.now().replace(microsecond=0)
        hour = self.random.randint(user["normal_work_start"], max(user["normal_work_end"] - 1, user["normal_work_start"]))
        return day.replace(hour=hour, minute=self.random.randint(0, 59), second=self.random.randint(0, 59))

    def _anomaly_start_time(self, day: datetime, scene_type: str, live: bool) -> datetime:
        if live:
            return datetime.now().replace(microsecond=0)
        if scene_type in {"offhour_query_export_delete", "usb_copy_delete"}:
            hour = self.random.choice([1, 2, 3, 22, 23])
        else:
            hour = self.random.choice([7, 12, 19, 21, 22])
        return day.replace(hour=hour, minute=self.random.randint(0, 59), second=self.random.randint(0, 59))

    def _rows_for_session(self, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        rows = []
        while ctx["step_index"] < len(ctx["chain"]):
            rows.append(self._row_for_current_step(ctx))
            ctx["step_index"] += 1
        return rows

    def _row_for_current_step(self, ctx: dict[str, Any]) -> dict[str, Any]:
        step_index = ctx["step_index"]
        event_type = ctx["chain"][step_index]
        event_time = ctx["base_time"] + timedelta(seconds=ctx["step_offsets"][step_index])
        row = self._base_row(ctx, event_time, event_type)

        if ctx["is_anomaly"]:
            self._apply_anomaly_event(row, ctx, event_type)
        else:
            self._apply_normal_event(row, ctx, event_type)
        return row

    def _base_row(self, ctx: dict[str, Any], event_time: datetime, event_type: str) -> dict[str, Any]:
        user = ctx["user"]
        return {
            "event_id": self._next_event_id(),
            "session_id": ctx["session_id"],
            "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user["user_id"],
            "account_type": user["account_type"],
            "dept": user["dept"],
            "role": user["role"],
            "device_id": ctx["device_id"],
            "device_new_flag": ctx["device_new_flag"],
            "ip_region": ctx["ip_region"],
            "event_type": event_type,
            "action_object": "",
            "object_type": "表",
            "object_domain": ctx["object_domain"],
            "sensitivity_level": ctx["sensitivity_level"],
            "query_count": 0,
            "access_count": 0,
            "cross_table_count": 0,
            "cross_domain_count": 0,
            "export_count": 0,
            "file_size_mb": 0.0,
            "print_pages": 0,
            "screenshot_count": 0,
            "external_send_count": 0,
            "copy_count": 0,
            "target_path_type": "本地",
            "usb_registered_flag": 1,
            "approval_flag": ctx["approval_flag"],
            "business_flag": ctx["business_flag"],
            "case_id": ctx["case_id"],
            "task_id": ctx["task_id"],
            "cross_dept_flag": 0,
            "off_work_flag": self._is_off_work(user, event_time),
            "deviation_person": 1.0,
            "deviation_role": 1.0,
            "sensitive_hit_ratio": round(self.random.uniform(0.02, 0.25), 2),
            "unique_id_ratio": round(self.random.uniform(0.01, 0.12), 2),
            "data_mask_flag": 1,
            "keep_days": 0,
            "compress_flag": 0,
            "encrypt_flag": 0,
            "delete_flag": 0,
            "tool_abnormal_flag": 0,
        }

    def _apply_normal_event(self, row: dict[str, Any], ctx: dict[str, Any], event_type: str) -> None:
        user = ctx["user"]
        if event_type == "login":
            row.update({
                "action_object": "系统登录",
                "object_type": "系统",
                "object_domain": "认证域",
                "sensitivity_level": 1,
                "access_count": 1,
            })
        elif event_type == "query":
            query_count = self.random.randint(3, 25)
            row.update({
                "action_object": f"{ctx['object_domain']}信息查询",
                "query_count": query_count,
                "access_count": self.random.randint(1, 6),
                "cross_table_count": self.random.randint(0, 2),
                "cross_domain_count": self.random.randint(0, 1),
                "deviation_person": self._deviation(query_count, user["avg_daily_query"]),
                "deviation_role": self._deviation(query_count, user["role_avg_query"]),
            })
        elif event_type == "export":
            export_count = self.random.randint(1, 6)
            row.update({
                "action_object": f"{ctx['object_domain']}数据导出",
                "object_type": "文件",
                "export_count": export_count,
                "file_size_mb": round(self.random.uniform(0.5, 6.0), 2),
                "deviation_person": self._deviation(export_count, user["avg_daily_export"]),
                "deviation_role": self._deviation(export_count, user["role_avg_export"]),
            })
        elif event_type == "print":
            pages = self.random.randint(1, 12)
            row.update({
                "action_object": f"{ctx['object_domain']}文档打印",
                "object_type": "文件",
                "print_pages": pages,
                "deviation_person": self._deviation(pages, user["avg_daily_print_pages"]),
            })
        elif event_type == "screenshot":
            row.update({
                "action_object": "页面截图",
                "object_type": "页面",
                "screenshot_count": self.random.randint(1, 2),
            })
        elif event_type == "copy":
            row.update({
                "action_object": "文件复制",
                "object_type": "文件",
                "copy_count": self.random.randint(1, 3),
                "target_path_type": self.random.choice(["本地", "共享目录"]),
            })

    def _apply_anomaly_event(self, row: dict[str, Any], ctx: dict[str, Any], event_type: str) -> None:
        user = ctx["user"]
        scene_type = ctx["scene_type"]
        row.update({
            "approval_flag": 0,
            "business_flag": 0,
            "case_id": "",
            "task_id": "",
            "data_mask_flag": 0,
            "sensitive_hit_ratio": round(self.random.uniform(0.55, 0.95), 2),
            "unique_id_ratio": round(self.random.uniform(0.25, 0.75), 2),
        })

        if scene_type in {"offhour_query_export_delete", "usb_copy_delete"}:
            row["off_work_flag"] = 1
        if scene_type == "cross_dept_query_export":
            row["cross_dept_flag"] = 1
        if scene_type == "test_env_unmasked_keep":
            row["target_path_type"] = "测试环境"
            row["keep_days"] = self.random.randint(30, 90)

        if event_type == "login":
            row.update({
                "action_object": "异常登录",
                "object_type": "系统",
                "object_domain": "认证域",
                "sensitivity_level": 1,
                "access_count": 1,
            })
        elif event_type == "query":
            query_count = self.random.randint(80, 320)
            row.update({
                "action_object": f"{ctx['object_domain']}高敏查询",
                "query_count": query_count,
                "access_count": self.random.randint(12, 45),
                "cross_table_count": self.random.randint(4, 10),
                "cross_domain_count": self.random.randint(3, 6),
                "deviation_person": self._deviation(query_count, user["avg_daily_query"]),
                "deviation_role": self._deviation(query_count, user["role_avg_query"]),
            })
        elif event_type == "export":
            export_count = self.random.randint(55, 360)
            row.update({
                "action_object": f"{ctx['object_domain']}批量导出",
                "object_type": "文件",
                "export_count": export_count,
                "file_size_mb": round(self.random.uniform(20.0, 500.0), 2),
                "deviation_person": self._deviation(export_count, user["avg_daily_export"]),
                "deviation_role": self._deviation(export_count, user["role_avg_export"]),
            })
        elif event_type == "print":
            row.update({
                "action_object": f"{ctx['object_domain']}批量打印",
                "object_type": "文件",
                "print_pages": self.random.randint(60, 200),
            })
        elif event_type == "screenshot":
            row.update({
                "action_object": "敏感页面截图",
                "object_type": "页面",
                "screenshot_count": self.random.randint(6, 25),
                "external_send_count": self.random.randint(1, 6),
            })
        elif event_type == "external_send":
            row.update({
                "action_object": "敏感文件外发",
                "object_type": "文件",
                "external_send_count": self.random.randint(2, 8),
                "target_path_type": self.random.choice(["个人邮箱", "外部IM", "网盘"]),
            })
        elif event_type == "copy":
            row.update({
                "action_object": "敏感文件拷贝",
                "object_type": "文件",
                "copy_count": self.random.randint(10, 80),
                "file_size_mb": round(self.random.uniform(50.0, 800.0), 2),
            })
            if scene_type == "usb_copy_delete":
                row["target_path_type"] = "USB"
                row["usb_registered_flag"] = 0
            elif scene_type == "screenshot_send_copy":
                row["target_path_type"] = "共享目录"
                row["external_send_count"] = self.random.randint(2, 6)
            elif scene_type == "test_env_unmasked_keep":
                row["target_path_type"] = "测试环境"
        elif event_type == "delete":
            row.update({
                "action_object": "删除原文件/日志",
                "object_type": "文件",
                "compress_flag": 1,
                "encrypt_flag": 1,
                "delete_flag": 1,
                "tool_abnormal_flag": 1,
            })

    def _build_meta(self, rows: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
        scene_counts: dict[str, int] = {}
        for label in labels:
            scene_counts[label["scene_type"]] = scene_counts.get(label["scene_type"], 0) + 1
        return {
            "config": asdict(self.config),
            "event_count": len(rows),
            "session_count": len(labels),
            "user_count": len(self.users),
            "anomaly_session_count": sum(int(item["is_anomaly"]) for item in labels),
            "scene_counts": scene_counts,
            "event_fields": EVENT_FIELDNAMES,
        }

    def _next_event_id(self) -> str:
        value = f"E{self.event_counter:08d}"
        self.event_counter += 1
        return value

    def _next_session_id(self) -> str:
        value = f"S{self.session_counter:08d}"
        self.session_counter += 1
        return value

    def _renumber_events(self, rows: list[dict[str, Any]]) -> None:
        for index, row in enumerate(rows, start=1):
            row["event_id"] = f"E{index:08d}"

    @staticmethod
    def _deviation(actual: float, baseline: float) -> float:
        if baseline <= 0:
            return round(float(actual), 2)
        return round(float(actual) / baseline, 2)

    @staticmethod
    def _is_off_work(user: dict[str, Any], dt: datetime) -> int:
        return int(dt.hour < user["normal_work_start"] or dt.hour >= user["normal_work_end"])


def write_events_csv(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    return _write_csv(path, rows, EVENT_FIELDNAMES)


def write_labels_csv(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    return _write_csv(path, rows, LABEL_FIELDNAMES)


def write_role_permissions_csv(path: str | Path) -> Path:
    return _write_csv(path, ROLE_PERMISSIONS, ROLE_PERMISSION_FIELDNAMES)


def append_event_csv(path: str | Path, row: dict[str, Any]) -> None:
    _append_csv(path, row, EVENT_FIELDNAMES)


def append_label_csv(path: str | Path, row: dict[str, Any]) -> None:
    _append_csv(path, row, LABEL_FIELDNAMES)


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return output


def _append_csv(path: str | Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output.exists()
    with output.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
