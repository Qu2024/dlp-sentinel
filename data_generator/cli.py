from __future__ import annotations

import argparse
import time
from pathlib import Path

from .agent_runner import evaluate_candidates, run_agent, write_evaluation
from .engine import (
    DataEngine,
    DataEngineConfig,
    append_event_csv,
    append_label_csv,
    write_events_csv,
    write_json,
    write_labels_csv,
    write_role_permissions_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DLP demo data outside the agent package.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    batch = subparsers.add_parser("batch", help="Generate a complete data set.")
    _add_generation_args(batch)
    _add_agent_args(batch)
    batch.add_argument("--output-dir", default="data_generator/output/batch")
    batch.add_argument("--run-agent", action="store_true")
    batch.add_argument("--evaluate", action="store_true")
    batch.set_defaults(func=_cmd_batch)

    stream = subparsers.add_parser("stream", help="Generate events continuously and optionally run micro-batches.")
    _add_generation_args(stream)
    _add_agent_args(stream)
    stream.add_argument("--output-dir", default="data_generator/output/stream")
    stream.add_argument("--max-events", type=int, default=200)
    stream.add_argument("--max-active-sessions", type=int, default=16)
    stream.add_argument("--interval", type=float, default=0.0)
    stream.add_argument("--microbatch-events", type=int, default=100)
    stream.add_argument("--run-agent", action="store_true")
    stream.add_argument("--evaluate", action="store_true")
    stream.set_defaults(func=_cmd_stream)

    run = subparsers.add_parser("run-agent", help="Run the existing agent against a generated CSV.")
    _add_agent_args(run)
    run.add_argument("--events", required=True)
    run.add_argument("--labels")
    run.add_argument("--evaluate", action="store_true")
    run.set_defaults(func=_cmd_run_agent)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate candidate detection against generator labels.")
    evaluate.add_argument("--labels", required=True)
    evaluate.add_argument("--candidate-events", required=True)
    evaluate.add_argument("--output", default="data_generator/output/evaluation.json")
    evaluate.set_defaults(func=_cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


def _add_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--sessions-per-user-day", type=float, default=8.0)
    parser.add_argument("--anomaly-rate", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-date", default="2026-04-20")


def _add_agent_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent-dir", default="agent")
    parser.add_argument("--agent-output-dir", default="")
    parser.add_argument("--adaptive-rule-dir", default="")


def _config_from_args(args: argparse.Namespace) -> DataEngineConfig:
    return DataEngineConfig(
        user_count=args.users,
        days=args.days,
        sessions_per_user_day=args.sessions_per_user_day,
        anomaly_rate=args.anomaly_rate,
        seed=args.seed,
        start_date=args.start_date,
    )


def _cmd_batch(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    engine = DataEngine(_config_from_args(args))
    rows, labels, meta = engine.generate_batch()

    events_path = write_events_csv(output_dir / "events.csv", rows)
    labels_path = write_labels_csv(output_dir / "labels.csv", labels)
    permissions_path = write_role_permissions_csv(output_dir / "role_permissions.csv")
    meta_path = write_json(output_dir / "generation_meta.json", meta)

    print(f"Generated events: {events_path}")
    print(f"Generated labels: {labels_path}")
    print(f"Generated role permissions copy: {permissions_path}")
    print(f"Generated metadata: {meta_path}")
    print(f"Events={meta['event_count']} Sessions={meta['session_count']} Anomalies={meta['anomaly_session_count']}")

    if args.run_agent:
        agent_output = Path(args.agent_output_dir or (output_dir / "agent_output"))
        run_agent(
            events_path,
            agent_dir=args.agent_dir,
            output_dir=agent_output,
            adaptive_rule_dir=args.adaptive_rule_dir or None,
        )
        print(f"Agent output: {agent_output.resolve()}")
        if args.evaluate:
            _evaluate_and_print(labels_path, agent_output / "candidate_events.json", output_dir / "evaluation.json")


def _cmd_stream(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    events_path = output_dir / "stream_events.csv"
    labels_path = output_dir / "stream_labels.csv"
    meta_path = output_dir / "stream_meta.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    if events_path.exists():
        events_path.unlink()
    if labels_path.exists():
        labels_path.unlink()

    engine = DataEngine(_config_from_args(args))
    label_ids = set()
    event_count = 0
    microbatch_index = 0

    for row, label, is_first_event, finished in engine.iter_stream(
        max_events=args.max_events,
        max_active_sessions=args.max_active_sessions,
    ):
        append_event_csv(events_path, row)
        if is_first_event and label["candidate_event_id"] not in label_ids:
            append_label_csv(labels_path, label)
            label_ids.add(label["candidate_event_id"])

        event_count += 1
        print(
            f"{event_count:06d} {row['event_time']} {row['session_id']} "
            f"{row['user_id']} {row['event_type']} finished={int(finished)}"
        )

        if args.run_agent and event_count % args.microbatch_events == 0:
            microbatch_index += 1
            agent_output = Path(args.agent_output_dir or (output_dir / "agent_output")) / f"microbatch_{microbatch_index:04d}"
            run_agent(
                events_path,
                agent_dir=args.agent_dir,
                output_dir=agent_output,
                adaptive_rule_dir=args.adaptive_rule_dir or None,
            )
            print(f"Agent microbatch output: {agent_output.resolve()}")
            if args.evaluate:
                _evaluate_and_print(labels_path, agent_output / "candidate_events.json", output_dir / f"evaluation_{microbatch_index:04d}.json")

        if args.interval > 0:
            time.sleep(args.interval)

    write_json(meta_path, {
        "event_count": event_count,
        "session_count": len(label_ids),
        "events_file": str(events_path),
        "labels_file": str(labels_path),
    })
    print(f"Stream events: {events_path}")
    print(f"Stream labels: {labels_path}")


def _cmd_run_agent(args: argparse.Namespace) -> None:
    events_path = Path(args.events)
    agent_output = Path(args.agent_output_dir or "data_generator/output/agent_output")
    run_agent(
        events_path,
        agent_dir=args.agent_dir,
        output_dir=agent_output,
        adaptive_rule_dir=args.adaptive_rule_dir or None,
    )
    print(f"Agent output: {agent_output.resolve()}")
    if args.evaluate:
        if not args.labels:
            raise SystemExit("--labels is required when --evaluate is used")
        _evaluate_and_print(Path(args.labels), agent_output / "candidate_events.json", agent_output / "evaluation.json")


def _cmd_evaluate(args: argparse.Namespace) -> None:
    _evaluate_and_print(Path(args.labels), Path(args.candidate_events), Path(args.output))


def _evaluate_and_print(labels_path: Path, candidate_events_path: Path, output_path: Path) -> None:
    result = evaluate_candidates(labels_path, candidate_events_path)
    write_evaluation(output_path, result)
    print(
        "Evaluation: "
        f"precision={result['precision']} recall={result['recall']} f1={result['f1']} "
        f"tp={result['tp']} fp={result['fp']} fn={result['fn']} tn={result['tn']}"
    )
    print(f"Evaluation file: {output_path.resolve()}")


if __name__ == "__main__":
    main()
