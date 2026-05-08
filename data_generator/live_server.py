from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import asdict, is_dataclass
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


def _raw_event(row: dict[str, Any]) -> RawEvent:
    fields = RawEvent.__dataclass_fields__
    return RawEvent(**{name: row.get(name) for name in fields})


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

    def iter_messages(self, max_events: int | None = None):
        yield {
            "type": "meta",
            "rule_dir": str(self.rule_dir),
            "config": asdict(self.config),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        for row, label, is_first_event, finished in self.engine.iter_stream(max_events=max_events):
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
        if parsed.path == "/stream":
            self._send_stream(parsed.query)
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
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
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

    def _send_stream(self, query: str) -> None:
        params = parse_qs(query)
        speed_ms = max(int(params.get("speed_ms", [420])[0]), 50)
        max_events_raw = int(params.get("max_events", [0])[0])
        max_events = max_events_raw if max_events_raw > 0 else None
        jitter = params.get("jitter", ["1"])[0].lower() not in {"0", "false", "no"}
        seed = int(params.get("seed", [20260508])[0])
        sleep_rng = random.Random(time.time_ns() ^ seed)

        config = DataEngineConfig(
            user_count=int(params.get("users", [40])[0]),
            days=1,
            sessions_per_user_day=float(params.get("sessions_per_user_day", [5])[0]),
            anomaly_rate=float(params.get("anomaly_rate", [0.18])[0]),
            seed=seed,
            start_date="2026-05-08",
        )
        pipeline = LivePipeline(config, self.server.rule_dir, self.server.permission_path)

        self.send_response(HTTPStatus.OK)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            for index, message in enumerate(pipeline.iter_messages(max_events=max_events), start=1):
                event_name = message.get("type", "message")
                payload = f"id: {index}\nevent: {event_name}\ndata: {_to_json(message)}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
                time.sleep(_stream_sleep_seconds(speed_ms, event_name, sleep_rng, jitter))
            self.wfile.write(b"event: done\ndata: {\"type\":\"done\"}\n\n")
            self.wfile.flush()
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
    print(f"DLP live server listening on http://{args.host}:{args.port}")
    print(f"Using rule dir: {server.rule_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping DLP live server")


if __name__ == "__main__":
    main()
