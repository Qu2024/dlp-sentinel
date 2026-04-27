import csv
import json
import sys
import concurrent.futures
from dataclasses import asdict
from schemas import RawEvent
from layer2 import rule_engine, scorer, llm_analyst, risk_ranker
from layer3 import report_generator

_log_file = None


def log(msg: str):
    print(msg)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()


def load_events(csv_path: str) -> list[RawEvent]:
    events = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            events.append(RawEvent(
                event_id=row["event_id"],
                session_id=row["session_id"],
                event_time=row["event_time"],
                user_id=row["user_id"],
                dept=row["dept"],
                role=row["role"],
                device_id=row["device_id"],
                device_new_flag=int(row["device_new_flag"]),
                ip_region=row["ip_region"],
                event_type=row["event_type"],
                object_domain=row["object_domain"],
                sensitivity_level=int(row["sensitivity_level"]),
                query_count=int(row["query_count"]),
                export_count=int(row["export_count"]),
                file_size_mb=float(row["file_size_mb"]),
                print_pages=int(row["print_pages"]),
                screenshot_count=int(row["screenshot_count"]),
                external_send_count=int(row["external_send_count"]),
                copy_count=int(row["copy_count"]),
                target_path_type=row["target_path_type"],
                usb_registered_flag=int(row["usb_registered_flag"]),
                approval_flag=int(row["approval_flag"]),
                business_flag=int(row["business_flag"]),
                case_id=row["case_id"],
                cross_dept_flag=int(row["cross_dept_flag"]),
                off_work_flag=int(row["off_work_flag"]),
                deviation_person=float(row["deviation_person"]),
                deviation_role=float(row["deviation_role"]),
                sensitive_hit_ratio=float(row["sensitive_hit_ratio"]),
                unique_id_ratio=float(row["unique_id_ratio"]),
                cross_domain_count=int(row["cross_domain_count"]),
                compress_flag=int(row["compress_flag"]),
                encrypt_flag=int(row["encrypt_flag"]),
                delete_flag=int(row["delete_flag"]),
                tool_abnormal_flag=int(row["tool_abnormal_flag"]),
            ))
    return events


def process_one_serial(candidate):
    cid = candidate.candidate_event_id
    log(f"\n{'='*60}")
    log(f"[候选事件] {cid}  用户={candidate.user_id}  规则强度={candidate.rule_strength}")

    if candidate.candidate_flag == 0:
        log(f"  [规则判断] 未入候选池，跳过评分")
        return None

    log(f"  [规则判断] 命中场景: {candidate.matched_scene_list or '无场景规则，弱规则叠加入池'}")

    log(f"  [AHP评分] 计算中...")
    scored = scorer.score_candidate(candidate)
    log(f"  [AHP评分] 基础分={scored.base_risk_score}  最终分={scored.final_risk_score}"
        f"  覆盖率={scored.coverage}  风险等级={scored.risk_level}")
    log(f"  [AHP评分] Top驱动因子: {[d['indicator'] for d in scored.top_drivers]}")

    log(f"  [LLM分析] 调用DeepSeek进行业务关联与链路分析...")
    scored.llm_analysis = llm_analyst.analyze(scored)
    log(f"  [LLM分析] 结果: {scored.llm_analysis}")

    log(f"  [研判报告] 生成中...")
    report = report_generator.generate(scored)
    log(f"  [研判报告] 证据摘要: {report.evidence_summary}")
    if report.llm_generated:
        log(f"  [研判报告] 风险解释: {report.risk_explanation}")
        log(f"  [研判报告] 处置建议: {report.disposition}")
    else:
        log(f"  [研判报告] 低风险，跳过LLM解释")

    return scored, report


def process_one_parallel(candidate):
    cid = candidate.candidate_event_id
    if candidate.candidate_flag == 0:
        log(f"[{cid}] 规则判断完成 → 未入候选池")
        return None

    scored = scorer.score_candidate(candidate)
    log(f"[{cid}] AHP评分完成 → {scored.risk_level} ({scored.final_risk_score}分)")

    scored.llm_analysis = llm_analyst.analyze(scored)
    log(f"[{cid}] LLM分析完成")

    report = report_generator.generate(scored)
    log(f"[{cid}] 研判报告完成 → 处置: {report.disposition.get('action', '-')}")

    return scored, report


def run(csv_path: str, output_dir: str = "output", mode: str = "serial"):
    global _log_file
    import os
    os.makedirs(output_dir, exist_ok=True)
    _log_file = open(f"{output_dir}/example.log", "w", encoding="utf-8")

    try:
        log(f"\n>>> 加载数据: {csv_path}")
        events = load_events(csv_path)
        log(f">>> 共加载 {len(events)} 条原始事件")

        log(f"\n>>> [规则引擎] 按 user_id+session_id 聚合并进行规则筛选...")
        candidates = rule_engine.run(events)
        total = len(candidates)
        flagged = sum(1 for c in candidates if c.candidate_flag == 1)
        log(f">>> [规则引擎] 共 {total} 个会话，{flagged} 个进入候选池，{total - flagged} 个过滤")

        scored_list, report_list = [], []

        if mode == "serial":
            log(f"\n>>> 串行模式：逐个处理候选事件（展示详细中间过程）")
            for candidate in candidates:
                result = process_one_serial(candidate)
                if result:
                    scored_list.append(result[0])
                    report_list.append(result[1])
        else:
            log(f"\n>>> 并行模式：并发处理所有候选事件")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(process_one_parallel, c): c for c in candidates}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        scored_list.append(result[0])
                        report_list.append(result[1])

        ranked = risk_ranker.rank(scored_list)

        with open(f"{output_dir}/risk_events.json", "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in ranked], f, ensure_ascii=False, indent=2, default=str)

        with open(f"{output_dir}/reports.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in report_list], f, ensure_ascii=False, indent=2)

        log(f"\n>>> 完成：{len(ranked)} 条候选事件，{len(report_list)} 份报告 -> {output_dir}/")
    finally:
        _log_file.close()
        _log_file = None


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/test_events.csv"
    mode = sys.argv[2] if len(sys.argv) > 2 else "serial"
    run(csv_path, mode=mode)
