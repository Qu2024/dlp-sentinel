import json
from dataclasses import asdict
from pathlib import Path

from modules.data_loader import load_events
from modules import risk_ranker
from modules.feedback_recorder import save_feedback_records
from agents.rule_agent import RuleAgent
from agents.behavior_agent import BehaviorAgent
from agents.scoring_agent import ScoringAgent
from agents.disposition_agent import DispositionAgent


class MultiAgentOrchestrator:
    """统一调度器：唯一的流程控制中心。

    设计原则：
    - 数据加载、反馈记录是普通流程模块，不封装为 Agent；
    - 只有具有明确判断职责的环节封装为 Agent；
    - Agent 内部再调用 modules 中的底层功能函数。
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.rule_agent = RuleAgent()
        self.behavior_agent = BehaviorAgent()
        self.scoring_agent = ScoringAgent()
        self.disposition_agent = DispositionAgent()

    def _save_json(self, name: str, data):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    def run(self, csv_path: str):
        workflow_trace = []
        agent_trace = []

        # 0. 数据加载：普通模块，不作为 Agent
        events = load_events(csv_path)
        workflow_trace.append({
            "step": "数据加载模块",
            "input": {"csv_path": csv_path},
            "output": {
                "raw_event_count": len(events),
                "unique_sessions": len({(e.user_id, e.session_id) for e in events}),
            },
        })

        # 1. 规则识别 Agent
        candidates, trace = self.rule_agent.run(events)
        agent_trace.append(trace)
        workflow_trace.append(trace)
        candidate_pool = [c for c in candidates if c.candidate_flag == 1]

        # 2. 行为理解 Agent：统一封装画像、业务关联、行为链
        behavior_results, trace = self.behavior_agent.run(candidate_pool)
        agent_trace.append(trace)
        workflow_trace.append(trace)

        # 3. 风险评分 Agent
        scored_events, trace = self.scoring_agent.run(candidate_pool, behavior_results=behavior_results)
        agent_trace.append(trace)
        workflow_trace.append(trace)
        ranked_events = risk_ranker.rank(scored_events)

        # 4. 研判处置 Agent
        reports, trace = self.disposition_agent.run(ranked_events)
        agent_trace.append(trace)
        workflow_trace.append(trace)

        # 5. 反馈记录：普通模块，不作为 Agent
        feedback_items = save_feedback_records(reports, self.output_dir)
        workflow_trace.append({
            "step": "反馈记录模块",
            "input": {"report_count": len(reports)},
            "output": {"feedback_items": len(feedback_items), "feedback_file": str(self.output_dir / "feedback.json")},
        })

        self._save_json("workflow_trace.json", workflow_trace)
        self._save_json("agent_trace.json", agent_trace)
        self._save_json("risk_events.json", [asdict(e) for e in ranked_events])
        self._save_json("reports.json", [asdict(r) for r in reports])
        self._save_json("candidate_events.json", [asdict(c) for c in candidates])
        self._save_json("feedback.json", feedback_items)

        return {
            "events": events,
            "candidates": candidates,
            "candidate_pool": candidate_pool,
            "behavior_results": behavior_results,
            "scored_events": ranked_events,
            "reports": reports,
            "feedback_items": feedback_items,
            "agent_trace": agent_trace,
            "workflow_trace": workflow_trace,
        }
