# 数据防泄漏智能体（DLP）Agent 原型系统（简化多 Agent 版）

本版本将上一版的 8 个 Agent 重新整理为更清晰的结构：

- 数据加载、反馈记录、规则计算、评分计算、证据提取等作为普通功能模块；
- 只有具有独立判断职责的环节封装为 Agent；
- `orchestrator.py` 是唯一的流程调度中心。
- 新增“规则自适应模块”，基于历史运行数据与人工反馈持续调整阈值、挖掘候选新规则。

## 一、最终架构

```text
main.py
  ↓
orchestrator.py（统一调度器）
  ↓
规则自适应准备模块（同步反馈 / 激活已批准建议规则）
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
  ↓
modules/adaptive_rule_engine.py（规则自适应模块）
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
│   ├── adaptive_rule_engine.py
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
│   ├── role_permissions.csv
│   └── adaptive_rules/
│       ├── active_rules.json
│       ├── suggested_rules.json
│       └── runs/
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

此外还会维护一套规则学习资产：

| 文件 | 说明 |
|---|---|
| `knowledge/adaptive_rules/active_rules.json` | 当前已生效规则，规则引擎运行时直接读取 |
| `knowledge/adaptive_rules/suggested_rules.json` | 机器学习/统计挖掘出的建议规则，需人工确认 |
| `knowledge/adaptive_rules/runs/` | 每次运行的快照，用于后续学习 |
| `knowledge/adaptive_rules/learning_log.jsonl` | 每次学习的简要日志 |

## 六、规则自适应说明

### 1. 学习数据来源

- 历史运行快照；
- `feedback.json` 中人工补充的 `human_confirmed` / `false_positive`；
- 当前版本会优先使用人工反馈，反馈不足时再用高风险结果作为弱监督信号做建议规则挖掘。

### 2. 当前学习策略

- 已有规则阈值：使用可解释的阈值搜索，根据历史反馈自动微调；
- 新规则发现：基于候选特征组合做可解释规则挖掘，生成建议规则；
- 建议规则默认不直接生效，必须人工确认。

### 3. 如何确认建议规则

编辑：

```text
knowledge/adaptive_rules/suggested_rules.json
```

把希望启用的建议规则改成：

```json
"approved": true
```

下次运行时，系统会自动把它加入：

```text
knowledge/adaptive_rules/active_rules.json
```

### 4. 反馈闭环

每次运行后：

1. 查看 `output/feedback.json`
2. 补充 `human_confirmed` 或 `false_positive`
3. 下次运行前，系统会先同步上一次反馈，再更新规则

## 七、提示词位置

提示词统一放在：

```text
prompts.py
```

其中：

- `ANALYST_SYSTEM_PROMPT`：用于业务/链路中间研判；
- `EXPLAINER_SYSTEM_PROMPT`：用于最终风险解释和处置建议生成。

如果没有配置 DeepSeek API Key，系统会自动使用本地规则解释，保证演示稳定。

可选 LLM 超时配置：

```text
DEEPSEEK_TIMEOUT_SECONDS=20
DEEPSEEK_MAX_RETRIES=0
```

如果希望使用通用变量名，也支持 `LLM_TIMEOUT_SECONDS` 和 `LLM_MAX_RETRIES`。展示场景建议保持较短超时，让 API 慢或不可用时快速降级到本地解释。
