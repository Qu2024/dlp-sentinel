# 数据防泄露多 Agent 风险研判系统

本版本已从原来的“模块化流水线”重构为“集中式调度的多 Agent 工作流”，用于对标开题报告中的多个 agent 系统设计。

## 一、项目结构

```text
agent/
├── main.py
├── orchestrator.py              # 多 Agent 总控调度器
├── config.py
├── schemas.py
├── agents/
│   ├── base_agent.py
│   ├── data_agent.py            # 数据接入 Agent
│   ├── rule_agent.py            # 规则识别 Agent
│   ├── profile_agent.py         # 用户画像与岗位基线 Agent
│   ├── business_agent.py        # 业务关联分析 Agent
│   ├── chain_agent.py           # 行为链重构 Agent
│   ├── scoring_agent.py         # 风险评分 Agent
│   ├── disposition_agent.py     # 结果研判与处置 Agent
│   └── feedback_agent.py        # 反馈优化 Agent
├── knowledge/
│   └── role_permissions.csv     # 岗位权限/业务规则表
├── layer2/
│   ├── rule_engine.py
│   ├── scorer.py
│   ├── chain_builder.py
│   ├── llm_analyst.py
│   └── risk_ranker.py
├── layer3/
│   ├── evidence_extractor.py
│   ├── llm_explainer.py
│   └── report_generator.py
├── data/
│   └── test_events.csv
└── output/
```

## 二、多 Agent 工作流

```text
数据引擎输出 CSV
        ↓
数据接入 Agent：日志标准化、字段对齐
        ↓
规则识别 Agent：固定阈值、场景规则、候选池筛选
        ↓
用户画像与岗位基线 Agent：个人偏离、岗位偏离、非工作时间、新设备
        ↓
业务关联分析 Agent：审批、案件、任务、岗位权限、导出限制
        ↓
行为链重构 Agent：login → query → export → copy/external_send → delete
        ↓
风险评分 Agent：融合各 Agent 输出，基于 AHP 加权评分
        ↓
结果研判与处置 Agent：证据摘要、风险解释、处置建议
        ↓
反馈优化 Agent：生成人工复核记录，预留规则/权重优化接口
```

## 三、与开题报告的对应关系

| 开题报告设计 | 当前实现 |
|---|---|
| 数据构建与智慧数据引擎 | `DataAgent` 读取数据引擎 CSV |
| 规则判定模块 | `RuleAgent` + `layer2/rule_engine.py` |
| 岗位基线与用户画像模块 | `ProfileAgent` |
| 业务关联分析模块 | `BusinessAgent` + `knowledge/role_permissions.csv` |
| 链路重构模块 | `ChainAgent` |
| 风险评分模块 | `ScoringAgent` + `layer2/scorer.py` |
| 结果研判与处置智能体 | `DispositionAgent` + `layer3/report_generator.py` |
| 动态优化与系统闭环 | `FeedbackAgent` + `output/feedback.json` |

## 四、运行方式

```bash
pip install -r requirements.txt

# 若不配置 DEEPSEEK_API_KEY，系统会自动使用本地规则解释，不影响演示。
cp .env.example .env

python main.py data/test_events.csv
```

兼容旧命令：

```bash
python main.py data/test_events.csv serial
python main.py data/test_events.csv parallel
```

这两个命令现在也会走多 Agent 调度器。

## 五、输出文件

运行后生成：

```text
output/
├── agent_trace.json       # 每个 Agent 的输入输出轨迹，答辩展示重点
├── candidate_events.json  # 规则识别后的候选事件
├── risk_events.json       # 风险评分后的事件
├── reports.json           # 最终风险研判报告
└── feedback.json          # 人工复核与闭环优化预留记录
```

其中 `agent_trace.json` 用来证明这是多 Agent 协同工作流，例如：

```json
{
  "agent": "规则识别Agent",
  "input": {"raw_event_count": 25},
  "output": {
    "session_count": 8,
    "candidate_count": 4,
    "matched_scene_summary": {
      "未审批高敏导出": 2,
      "未备案USB拷贝": 1
    }
  }
}
```

## 六、答辩说明口径

当前系统采用“集中式调度的多 Agent 架构”。各 Agent 并不都依赖大模型，而是包括规则型 Agent、评分型 Agent、知识判断型 Agent 和大模型解释型 Agent。这样既保留了规则和 AHP 评分的稳定性，也利用大模型提升解释和处置建议生成能力。

若没有配置大模型 API，系统会自动降级为本地规则解释，保证课堂演示稳定运行。
