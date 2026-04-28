# 数据防泄漏智能体（DLP）Agent 原型系统（简化多 Agent 版）

本版本将上一版的 8 个 Agent 重新整理为更清晰的结构：

- 数据加载、反馈记录、规则计算、评分计算、证据提取等作为普通功能模块；
- 只有具有独立判断职责的环节封装为 Agent；
- `orchestrator.py` 是唯一的流程调度中心。

## 一、最终架构

```text
main.py
  ↓
orchestrator.py（统一调度器）
  ↓
modules/data_loader.py（数据加载模块，非 Agent）
  ↓
RuleAgent（规则识别 Agent）
  ↓
BehaviorAgent（行为理解 Agent：画像/基线 + 业务关联 + 行为链）
  ↓
ScoringAgent（风险评分 Agent）
  ↓
DispositionAgent（研判处置 Agent）
  ↓
modules/feedback_recorder.py（反馈记录模块，非 Agent）
```

## 二、为什么这样整理

上一版为了对标多 Agent，把数据读取、画像分析、业务关联、链路重构、反馈记录等都封装成独立 Agent，结构偏碎。本版将其调整为：

```text
4 个核心 Agent + modules 底层功能模块
```

四个核心 Agent 分别是：

| Agent | 作用 |
|---|---|
| 规则识别 Agent | 根据阈值和风险场景筛选候选风险事件 |
| 行为理解 Agent | 综合用户画像、岗位基线、业务关联、行为链理解行为是否合理 |
| 风险评分 Agent | 基于 AHP 模型计算风险分数和风险等级 |
| 研判处置 Agent | 提取证据、调用大模型/本地降级解释、生成处置建议 |

## 三、目录结构

```text
agent/
├── main.py
├── orchestrator.py
├── schemas.py
├── config.py
├── prompts.py
├── agents/
│   ├── base_agent.py
│   ├── rule_agent.py
│   ├── behavior_agent.py
│   ├── scoring_agent.py
│   └── disposition_agent.py
├── modules/
│   ├── data_loader.py
│   ├── rule_engine.py
│   ├── profile_analyzer.py
│   ├── business_analyzer.py
│   ├── chain_builder.py
│   ├── scorer.py
│   ├── risk_ranker.py
│   ├── evidence_extractor.py
│   ├── llm_explainer.py
│   ├── report_generator.py
│   └── feedback_recorder.py
├── knowledge/
│   └── role_permissions.csv
├── data/
│   └── test_events.csv
└── output/
```

## 四、运行方式

```bash
python main.py data/test_events.csv
```

旧命令仍兼容：

```bash
python main.py data/test_events.csv serial
python main.py data/test_events.csv parallel
```

## 五、输出文件

运行后生成：

| 文件 | 说明 |
|---|---|
| `workflow_trace.json` | 完整流程轨迹，包含数据加载和反馈记录模块 |
| `agent_trace.json` | 只记录 4 个核心 Agent 的执行轨迹 |
| `candidate_events.json` | 规则识别后的候选事件 |
| `risk_events.json` | 风险评分后的事件 |
| `reports.json` | 最终研判报告 |
| `feedback.json` | 人工复核反馈记录 |

## 六、提示词位置

提示词统一放在：

```text
prompts.py
```

其中：

- `ANALYST_SYSTEM_PROMPT`：用于业务/链路中间研判；
- `EXPLAINER_SYSTEM_PROMPT`：用于最终风险解释和处置建议生成。

如果没有配置 DeepSeek API Key，系统会自动使用本地规则解释，保证演示稳定。
