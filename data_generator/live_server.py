from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .engine import DataEngine, DataEngineConfig


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"
DEFAULT_RULE_DIR = AGENT_DIR / "adaptive_rules_test"
DEFAULT_PERMISSION_PATH = AGENT_DIR / "knowledge" / "role_permissions.csv"
UI_STATE_FILENAME = "ui_state.json"

if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from agents.behavior_agent import BehaviorAgent  # noqa: E402
from agents.rule_agent import RuleAgent  # noqa: E402
from agents.scoring_agent import ScoringAgent  # noqa: E402
from modules import adaptive_rule_engine, evidence_extractor, report_generator  # noqa: E402
from schemas import RawEvent, ScoredEvent  # noqa: E402


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _stream_sleep_seconds(speed_ms: int, event_name: str, rng: random.Random, jitter: bool) -> float:
    if not jitter:
        return speed_ms / 1000
    if event_name == "session":
        return rng.uniform(0.04, 0.16)

    low = max(25, int(speed_ms * 0.35))
    high = max(low + 1, int(speed_ms * 1.85))
    value = rng.randint(low, high)
    if rng.random() < 0.12:
        value += rng.randint(max(80, speed_ms), max(160, speed_ms * 4))
    return value / 1000


def time_now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _raw_event(row: dict[str, Any]) -> RawEvent:
    fields = RawEvent.__dataclass_fields__
    return RawEvent(**{name: row.get(name) for name in fields})


def _default_ui_state() -> dict[str, Any]:
    return {
        "updated_at": "",
        "risk_weights": {"C2": 19.31, "C3": 7.46, "C4": 43.88, "C5": 29.35},
        "ai_settings": {
            "sensitivity": 68,
            "optimization_cycle": "daily",
            "self_learning_enabled": True,
        },
        "automation": {
            "suspend_process": True,
            "freeze_account": False,
        },
        "feedback_reviews": [],
        "actions": [],
    }


def _ui_state_path(rule_dir: Path) -> Path:
    return rule_dir / UI_STATE_FILENAME


def _load_ui_state(rule_dir: Path) -> dict[str, Any]:
    path = _ui_state_path(rule_dir)
    if not path.exists():
        return _default_ui_state()
    try:
        with path.open("r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        state = {}
    defaults = _default_ui_state()
    return {
        **defaults,
        **state,
        "risk_weights": {**defaults["risk_weights"], **state.get("risk_weights", {})},
        "ai_settings": {**defaults["ai_settings"], **state.get("ai_settings", {})},
        "automation": {**defaults["automation"], **state.get("automation", {})},
        "feedback_reviews": state.get("feedback_reviews", []),
        "actions": state.get("actions", []),
    }


def _save_ui_state(rule_dir: Path, state: dict[str, Any]) -> None:
    rule_dir.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with _ui_state_path(rule_dir).open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _record_ui_state_action(
    rule_dir: Path,
    action: str,
    action_payload: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = state or _load_ui_state(rule_dir)
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "payload": action_payload,
    }
    state.setdefault("actions", []).append(entry)
    state["actions"] = state["actions"][-200:]
    _save_ui_state(rule_dir, state)
    return entry, state


RULE_COLLECTIONS = {
    "scene": "scene_rules",
    "scene_rules": "scene_rules",
    "threshold": "high_risk_thresholds",
    "high_risk_thresholds": "high_risk_thresholds",
    "weak": "weak_rules",
    "weak_rules": "weak_rules",
}


def _rule_collection(rule_type: str) -> str | None:
    return RULE_COLLECTIONS.get(str(rule_type or "").strip())


def _find_active_rule(active_rules: dict[str, Any], rule_type: str, rule_index: Any, rule_id: str) -> tuple[str, int, dict[str, Any]] | None:
    collection = _rule_collection(rule_type)
    if not collection:
        return None

    rules = active_rules.get(collection, [])
    try:
        index = int(rule_index)
    except (TypeError, ValueError):
        index = -1

    if 0 <= index < len(rules):
        return collection, index, rules[index]

    for idx, rule in enumerate(rules):
        if rule_id and rule_id in {str(rule.get("id", "")), str(rule.get("name", ""))}:
            return collection, idx, rule
    return None


def _write_active_rules(rule_dir: Path, active_rules: dict[str, Any]) -> None:
    active_rules["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    path = rule_dir / adaptive_rule_engine.ACTIVE_RULES_FILE
    path.write_text(json.dumps(active_rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _local_llm_result(event: ScoredEvent, evidence_summary: str) -> dict[str, Any]:
    if event.risk_level == "极高风险":
        action = "立即阻断并升级处置"
        suggestions = ["冻结账号", "隔离终端", "调取完整操作日志", "核查外发和拷贝去向"]
    elif event.risk_level == "高风险":
        action = "触发告警并优先调查"
        suggestions = ["人工复核审批记录", "核查业务关联", "临时降低导出权限"]
    elif event.risk_level == "中风险":
        action = "进入复核队列"
        suggestions = ["补充审批证明", "核实案件或任务编号"]
    else:
        action = "留痕观察"
        suggestions = ["持续监控后续行为"]
    return {
        "explanation": f"实时规则链路判定为{event.risk_level}，关键证据：{evidence_summary[:120]}",
        "disposition": {"action": action, "suggestions": suggestions},
        "_llm_generated": False,
    }


class LivePipeline:
    def __init__(self, config: DataEngineConfig, rule_dir: Path, permission_path: Path):
        os.environ[adaptive_rule_engine.RULE_DIR_ENV] = str(rule_dir)
        adaptive_rule_engine.ensure_store(rule_dir)
        self.engine = DataEngine(config)
        self.rule_agent = RuleAgent()
        self.behavior_agent = BehaviorAgent(permission_path=str(permission_path))
        self.scoring_agent = ScoringAgent()
        self.session_events: dict[str, list[RawEvent]] = {}
        self.labels: dict[str, dict[str, Any]] = {}
        self.active_sessions: list[dict[str, Any]] = []
        self.counts = {
            "events": 0,
            "sessions_started": 0,
            "sessions_completed": 0,
            "candidate_events": 0,
            "high_or_above": 0,
            "anomalies": 0,
        }
        self.rule_dir = rule_dir
        self.config = config
        self.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def iter_messages(self, max_events: int | None = None, max_active_sessions: int = 8):
        yield {
            "type": "meta",
            "rule_dir": str(self.rule_dir),
            "config": asdict(self.config),
            "started_at": self.started_at,
            "counts": dict(self.counts),
        }

        emitted = 0
        while max_events is None or emitted < max_events:
            while len(self.active_sessions) < max_active_sessions:
                user = self.engine.random.choice(self.engine.users)
                is_anomaly = self.engine.random.random() < self.config.anomaly_rate
                ctx = self.engine._create_session(user, time_now(), is_anomaly, live=True)
                self.active_sessions.append(ctx)

            ctx = self.engine.random.choice(self.active_sessions)
            is_first_event = ctx["step_index"] == 0
            row = self.engine._row_for_current_step(ctx)
            ctx["step_index"] += 1
            finished = ctx["step_index"] >= len(ctx["chain"])
            if finished:
                self.active_sessions.remove(ctx)
            emitted += 1

            label = ctx["label"]
            raw_event = _raw_event(row)
            self.session_events.setdefault(raw_event.session_id, []).append(raw_event)
            self.labels[raw_event.session_id] = label
            self.counts["events"] += 1

            if is_first_event:
                self.counts["sessions_started"] += 1
                self.counts["anomalies"] += int(label.get("is_anomaly", 0))

            yield {
                "type": "event",
                "event": row,
                "label": label,
                "is_first_event": is_first_event,
                "finished": finished,
                "counts": dict(self.counts),
            }

            if finished:
                session_id = raw_event.session_id
                events = self.session_events.pop(session_id, [])
                risk_payload = self._process_session(events, self.labels.pop(session_id, label))
                self.counts["sessions_completed"] += 1
                yield {
                    "type": "session",
                    "session_id": session_id,
                    "label": label,
                    "candidate": risk_payload is not None,
                    "risk": risk_payload,
                    "counts": dict(self.counts),
                }

    def _process_session(self, events: list[RawEvent], label: dict[str, Any]) -> dict[str, Any] | None:
        candidates, rule_trace = self.rule_agent.run(events)
        candidate_pool = [candidate for candidate in candidates if candidate.candidate_flag]
        if not candidate_pool:
            return None

        behavior_results, behavior_trace = self.behavior_agent.run(candidate_pool)
        scored_events, scoring_trace = self.scoring_agent.run(candidate_pool, behavior_results)
        if not scored_events:
            return None

        scored = scored_events[0]
        evidence_summary = evidence_extractor.extract(scored)
        report = report_generator.generate(scored, evidence_summary, _local_llm_result(scored, evidence_summary))
        self.counts["candidate_events"] += 1
        if scored.risk_level in {"高风险", "极高风险"}:
            self.counts["high_or_above"] += 1

        return {
            "label": label,
            "report": report,
            "risk_event": scored,
            "trace": {
                "rule_agent": rule_trace,
                "behavior_agent": behavior_trace,
                "scoring_agent": scoring_trace,
            },
        }


class LiveRequestHandler(BaseHTTPRequestHandler):
    server_version = "DLPLiveServer/0.1"

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"ok": True, "service": "dlp-live-server"})
            return
        if parsed.path == "/rules":
            self._send_rules()
            return
        if parsed.path == "/rules/active/log":
            self._send_active_rule_log(parsed.query)
            return
        if parsed.path == "/ui-state":
            self._send_ui_state()
            return
        if parsed.path == "/stream":
            self._send_stream(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/rules/active/update":
            self._update_active_rule()
            return
        if parsed.path == "/rules/suggestions/review":
            self._review_rule_suggestion()
            return
        if parsed.path == "/ui-state/action":
            self._record_ui_action()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[live-server] {self.address_string()} {format % args}\n")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _to_json(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_rules(self) -> None:
        rule_dir = self.server.rule_dir
        adaptive_rule_engine.ensure_store(rule_dir)
        self._send_json({
            "ok": True,
            "rule_dir": str(rule_dir),
            "active_rules": adaptive_rule_engine.load_active_rules(rule_dir),
            "suggested_rules": adaptive_rule_engine.load_suggested_rules(rule_dir),
        })

    def _send_ui_state(self) -> None:
        self._send_json({
            "ok": True,
            "rule_dir": str(self.server.rule_dir),
            "ui_state": _load_ui_state(self.server.rule_dir),
        })

    def _record_ui_action(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        action = str(payload.get("action", "")).strip()
        if not action:
            self._send_json({"ok": False, "error": "action is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        state = _load_ui_state(self.server.rule_dir)
        action_payload = payload.get("payload", {})
        if not isinstance(action_payload, dict):
            action_payload = {"value": action_payload}

        if action == "save_settings":
            state["risk_weights"] = {
                **state.get("risk_weights", {}),
                **action_payload.get("risk_weights", {}),
            }
            state["ai_settings"] = {
                **state.get("ai_settings", {}),
                **action_payload.get("ai_settings", {}),
            }
            state["automation"] = {
                **state.get("automation", {}),
                **action_payload.get("automation", {}),
            }

        if action in {"mark_false_positive", "emergency_response", "approve_review"}:
            candidate_id = action_payload.get("candidate_event_id")
            if candidate_id:
                reviews = [
                    item for item in state.get("feedback_reviews", [])
                    if item.get("candidate_event_id") != candidate_id
                ]
                review = {
                    **action_payload,
                    "candidate_event_id": candidate_id,
                    "reviewed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                if action == "mark_false_positive":
                    review.update({"false_positive": True, "human_confirmed": False, "review_comment": "人工标记为误报"})
                elif action == "emergency_response":
                    review.update({"false_positive": False, "human_confirmed": True, "review_comment": "已触发紧急处置流程"})
                else:
                    review.update({"false_positive": False, "human_confirmed": True, "review_comment": "人工复核通过"})
                reviews.insert(0, review)
                state["feedback_reviews"] = reviews[:200]

        entry, state = _record_ui_state_action(self.server.rule_dir, action, action_payload, state)
        self._send_json({"ok": True, "entry": entry, "ui_state": state})

    def _update_active_rule(self) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        rule_ref = payload.get("rule_ref", {})
        if not isinstance(rule_ref, dict):
            rule_ref = {}
        action = str(payload.get("action", "")).strip()
        if action not in {"create_rule", "edit_rule", "pause_rule", "activate_rule", "batch_update_rules"}:
            self._send_json({"ok": False, "error": f"Unsupported action: {action}"}, status=HTTPStatus.BAD_REQUEST)
            return

        rule_dir = self.server.rule_dir
        active_rules = adaptive_rule_engine.load_active_rules(rule_dir)
        if action == "create_rule":
            collection = _rule_collection(str(rule_ref.get("rule_type", ""))) or "scene_rules"
            new_rule = payload.get("rule")
            if not isinstance(new_rule, dict):
                self._send_json({"ok": False, "error": "rule must be an object"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not new_rule.get("id"):
                new_rule["id"] = f"manual_rule_{int(time.time())}"
            new_rule.setdefault("status", "active")
            new_rule.setdefault("source", "manual")
            new_rule.setdefault("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))
            active_rules.setdefault(collection, []).append(new_rule)
            _write_active_rules(rule_dir, active_rules)
            entry, ui_state = _record_ui_state_action(rule_dir, action, {
                **rule_ref,
                "rule_type": rule_ref.get("rule_type") or collection,
                "rule_id": new_rule.get("id", ""),
                "rule_name": new_rule.get("name") or new_rule.get("field") or new_rule.get("id", ""),
                "status": new_rule.get("status", "active"),
            })
            self._send_json({
                "ok": True,
                "entry": entry,
                "ui_state": ui_state,
                "active_rules": active_rules,
                "suggested_rules": adaptive_rule_engine.load_suggested_rules(rule_dir),
                "updated_rule": new_rule,
            })
            return

        if action == "batch_update_rules":
            status = str(payload.get("status", "")).strip()
            if status not in {"active", "disabled"}:
                self._send_json({"ok": False, "error": "status must be active or disabled"}, status=HTTPStatus.BAD_REQUEST)
                return
            requested = str(rule_ref.get("rule_type", "all")).strip()
            collections = list(RULE_COLLECTIONS.values()) if requested == "all" else [_rule_collection(requested)]
            collections = [collection for collection in dict.fromkeys(collections) if collection]
            if not collections:
                self._send_json({"ok": False, "error": "rule_type is invalid"}, status=HTTPStatus.BAD_REQUEST)
                return
            changed = 0
            for collection in collections:
                for rule in active_rules.get(collection, []):
                    if rule.get("status", "active") != status:
                        rule["status"] = status
                        changed += 1
            _write_active_rules(rule_dir, active_rules)
            entry, ui_state = _record_ui_state_action(rule_dir, action, {
                **rule_ref,
                "status": status,
                "changed_count": changed,
            })
            self._send_json({
                "ok": True,
                "entry": entry,
                "ui_state": ui_state,
                "active_rules": active_rules,
                "suggested_rules": adaptive_rule_engine.load_suggested_rules(rule_dir),
                "changed_count": changed,
            })
            return

        found = _find_active_rule(
            active_rules,
            str(rule_ref.get("rule_type", "")),
            rule_ref.get("rule_index"),
            str(rule_ref.get("rule_id", "")),
        )
        if not found:
            self._send_json({"ok": False, "error": "Active rule not found"}, status=HTTPStatus.NOT_FOUND)
            return

        collection, index, old_rule = found
        if action == "edit_rule":
            new_rule = payload.get("rule")
            if not isinstance(new_rule, dict):
                self._send_json({"ok": False, "error": "rule must be an object"}, status=HTTPStatus.BAD_REQUEST)
                return
            if old_rule.get("id") and not new_rule.get("id"):
                new_rule["id"] = old_rule["id"]
            active_rules[collection][index] = new_rule
        else:
            status = "disabled" if action == "pause_rule" else "active"
            active_rules[collection][index]["status"] = status

        _write_active_rules(rule_dir, active_rules)
        updated_rule = active_rules[collection][index]
        entry, ui_state = _record_ui_state_action(rule_dir, action, {
            **rule_ref,
            "rule_name": updated_rule.get("name") or updated_rule.get("field") or updated_rule.get("id", ""),
            "status": updated_rule.get("status", "active"),
        })
        self._send_json({
            "ok": True,
            "entry": entry,
            "ui_state": ui_state,
            "active_rules": active_rules,
            "suggested_rules": adaptive_rule_engine.load_suggested_rules(rule_dir),
            "updated_rule": updated_rule,
        })

    def _send_active_rule_log(self, query: str) -> None:
        params = parse_qs(query)
        rule_type = params.get("rule_type", [""])[0]
        rule_index = params.get("rule_index", [""])[0]
        rule_id = params.get("rule_id", [""])[0]
        rule_dir = self.server.rule_dir
        active_rules = adaptive_rule_engine.load_active_rules(rule_dir)
        found = _find_active_rule(active_rules, rule_type, rule_index, rule_id)
        if not found:
            self._send_json({"ok": False, "error": "Active rule not found"}, status=HTTPStatus.NOT_FOUND)
            return

        collection, index, rule = found
        learning_entries = []
        log_path = rule_dir / adaptive_rule_engine.LEARNING_LOG_FILE
        if log_path.exists():
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        learning_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        learning_entries.append({"raw": line})

        actions = [
            item for item in _load_ui_state(rule_dir).get("actions", [])
            if item.get("payload", {}).get("rule_id") in {rule_id, rule.get("id"), rule.get("name")}
            or str(item.get("payload", {}).get("rule_index", "")) == str(index)
        ]
        self._send_json({
            "ok": True,
            "rule_ref": {"rule_type": rule_type, "rule_index": index, "rule_id": rule_id, "collection": collection},
            "rule": rule,
            "learning_entries": learning_entries[-20:],
            "actions": actions[-20:],
        })

    def _review_rule_suggestion(self) -> None:
        try:
            payload = self._read_json_body()
            result = adaptive_rule_engine.review_suggested_rule(
                rule_id=str(payload.get("rule_id", "")),
                action=str(payload.get("action", "")),
                rule_dir=self.server.rule_dir,
                review_comment=str(payload.get("review_comment", "")),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        if result.get("ok"):
            result["rule_dir"] = str(self.server.rule_dir)
        self._send_json(result, status=status)

    def _send_stream(self, query: str) -> None:
        params = parse_qs(query)
        speed_ms = max(int(params.get("speed_ms", [420])[0]), 50)
        max_events_raw = int(params.get("max_events", [0])[0])
        max_events = max_events_raw if max_events_raw > 0 else None
        max_active_sessions = int(params.get("max_active_sessions", [16])[0])
        jitter = params.get("jitter", ["1"])[0].lower() not in {"0", "false", "no"}
        seed = int(params.get("seed", [20260508])[0])
        run_id = params.get("run_id", ["default"])[0] or "default"
        reset_run = params.get("reset", ["0"])[0].lower() in {"1", "true", "yes"}
        sleep_rng = random.Random(time.time_ns() ^ seed)

        config = DataEngineConfig(
            user_count=int(params.get("users", [100])[0]),
            days=1,
            sessions_per_user_day=float(params.get("sessions_per_user_day", [5])[0]),
            anomaly_rate=float(params.get("anomaly_rate", [0.18])[0]),
            seed=seed,
            start_date="2026-05-08",
        )
        config_key = asdict(config)
        cached = self.server.pipelines.get(run_id)
        if reset_run or cached is None or cached["config_key"] != config_key:
            pipeline = LivePipeline(config, self.server.rule_dir, self.server.permission_path)
            self.server.pipelines[run_id] = {"config_key": config_key, "pipeline": pipeline}
            resumed = False
        else:
            pipeline = cached["pipeline"]
            resumed = True

        self.send_response(HTTPStatus.OK)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            for index, message in enumerate(pipeline.iter_messages(max_events=max_events, max_active_sessions=max_active_sessions), start=1):
                if message.get("type") == "meta":
                    message["run_id"] = run_id
                    message["resumed"] = resumed
                event_name = message.get("type", "message")
                payload = f"id: {index}\nevent: {event_name}\ndata: {_to_json(message)}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
                time.sleep(_stream_sleep_seconds(speed_ms, event_name, sleep_rng, jitter))
            self.wfile.write(b"event: done\ndata: {\"type\":\"done\"}\n\n")
            self.wfile.flush()
            self.close_connection = True
        except (BrokenPipeError, ConnectionResetError):
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local DLP live demo SSE server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rule-dir", type=Path, default=DEFAULT_RULE_DIR)
    parser.add_argument("--permission-path", type=Path, default=DEFAULT_PERMISSION_PATH)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), LiveRequestHandler)
    server.rule_dir = args.rule_dir.resolve()
    server.permission_path = args.permission_path.resolve()
    server.pipelines = {}
    print(f"DLP live server listening on http://{args.host}:{args.port}")
    print(f"Using rule dir: {server.rule_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping DLP live server")


if __name__ == "__main__":
    main()
