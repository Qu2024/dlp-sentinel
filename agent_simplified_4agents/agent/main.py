import sys
from orchestrator import MultiAgentOrchestrator


def run(csv_path: str, output_dir: str = "output", mode: str = "multi_agent"):
    """项目入口。mode 参数保留是为了兼容旧命令。"""
    print(f"\n>>> 加载数据: {csv_path}")
    print(">>> 启动简化版多 Agent 风险识别工作流")
    print(">>> 架构：数据加载模块 → 规则识别Agent → 行为理解Agent → 风险评分Agent → 研判处置Agent → 反馈记录模块")

    orchestrator = MultiAgentOrchestrator(output_dir=output_dir)
    result = orchestrator.run(csv_path)

    print(f">>> 原始事件数：{len(result['events'])}")
    print(f">>> 会话数：{len(result['candidates'])}")
    print(f">>> 入候选池事件数：{len(result['candidate_pool'])}")
    print(f">>> 已评分风险事件数：{len(result['scored_events'])}")
    print(f">>> 已生成研判报告数：{len(result['reports'])}")
    print(f">>> 输出目录：{output_dir}/")
    print(">>> 关键输出：workflow_trace.json、agent_trace.json、risk_events.json、reports.json、feedback.json")

    return result


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/test_events.csv"
    mode = sys.argv[2] if len(sys.argv) > 2 else "multi_agent"
    run(csv_path, mode=mode)
