# DLP Sentinel 本地演示系统

这是一个用于数据防泄漏风险识别的本地原型系统。当前重点不是生产部署，而是把“数据生成 -> Agent 识别 -> 风险评分 -> 报告生成 -> 前端展示 -> 规则自适应”的完整流程跑通，并能用于演示。


## 本次修改说明：20 个场景规则判定 + 数据格式统一

本版已完成两项整合：

1. **场景规则判定落地**：在 `agent/modules/adaptive_rule_engine.py` 和 `agent/knowledge/adaptive_rules/active_rules.json` 中，将 20 个内部数据泄露场景转化为可执行的固定阈值规则。规则识别 Agent 会按 `user_id + session_id` 聚合事件，并根据 `off_work_flag`、`query_count`、`export_count`、`approval_flag`、`business_flag`、`sensitivity_level` 等字段判断是否命中场景。
2. **数据输出格式统一**：在 `data_generator/engine.py` 中，将 `EVENT_FIELDNAMES` 对齐《数据库表设计（可落地）》里的“统一事件日志主表”。生成的 `events.csv` 可直接作为 Agent 输入，也方便后续导入数据库。

详细说明见：`docs/场景规则判定与数据整合说明.md`。

快速验证命令：

```bash
python -m data_generator.cli batch --users 10 --days 1 --sessions-per-user-day 3 --anomaly-rate 0.2 --output-dir data_generator/output/rule_test --run-agent --evaluate
```

## 目录说明

```text
dlp-sentinel/
├── agent/                 # DLP 多 Agent 风险识别主流程
├── data_generator/        # 独立数据引擎和实时流服务
├── frontend/              # 本地静态前端监控台
├── agent/adaptive_rules_test/   # 测试用自适应规则库，已被 git ignore
└── data_generator/output/       # 生成数据和测试输出，已被 git ignore
```

核心代码在三个目录：

- `agent/`：负责规则识别、行为理解、风险评分、研判报告、反馈记录、规则学习。
- `data_generator/`：负责生成可控的正常/异常行为数据，并从外部调用 `agent/`。
- `frontend/`：负责展示批量复盘结果和实时滚动演示。

## 总流程

整体流程如下：

```text
数据生成器
  ↓
events.csv / 实时事件流
  ↓
Agent 数据加载
  ↓
规则识别 Agent
  ↓
行为理解 Agent
  ↓
风险评分 Agent
  ↓
研判处置 Agent
  ↓
reports.json / risk_events.json / feedback.json
  ↓
前端总览、风险详情、规则、审计展示
```

自适应规则流程是：

```text
运行前：同步上一次人工反馈，激活已批准建议规则
运行中：使用 active_rules.json 做候选识别
运行后：沉淀本次候选、报告、反馈快照
学习：已有规则做阈值微调，新规则只进入 suggested_rules.json
人工确认：把 suggested rule 的 approved 改成 true 后，下次运行生效
```

## 环境准备

建议在仓库根目录执行命令。

如果使用你的 conda base 环境：

```bash
/opt/anaconda3/bin/python --version
```

确认依赖：

```bash
/opt/anaconda3/bin/python -c "import openai, dotenv; print('ok')"
```

如果环境里没有依赖：

```bash
/opt/anaconda3/bin/python -m pip install -r agent/requirements.txt
```

LLM 配置放在：

```text
agent/.env
```

示例：

```text
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.xxx.com/v1
DEEPSEEK_MODEL=deepseek-v3.2
DEEPSEEK_TIMEOUT_SECONDS=20
DEEPSEEK_MAX_RETRIES=0
```

如果没有 API key，系统会自动降级为本地规则解释；流程仍能跑通。

## 模式一：批量生成 + 离线评测

适合做指标评测、规则调参、复盘展示。

```bash
/opt/anaconda3/bin/python -m data_generator.cli batch \
  --users 100 \
  --days 10 \
  --sessions-per-user-day 8 \
  --anomaly-rate 0.035 \
  --seed 20260508 \
  --output-dir data_generator/output/adaptive_rules_test_large \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --run-agent \
  --evaluate
```

输出目录：

```text
data_generator/output/adaptive_rules_test_large/
├── events.csv
├── labels.csv
├── generation_meta.json
├── evaluation.json
└── agent_output/
    ├── candidate_events.json
    ├── risk_events.json
    ├── reports.json
    ├── feedback.json
    ├── workflow_trace.json
    └── agent_trace.json
```

`events.csv` 是给 agent 使用的日志数据。  
`labels.csv` 是数据生成器保存的真值标签，只用于评测，不会给 agent 使用。  
`evaluation.json` 用于看 precision、recall、f1、tp、fp、fn、tn。

## 模式二：只运行 Agent

如果已经有一份事件 CSV，可以直接跑 agent：

```bash
/opt/anaconda3/bin/python -m data_generator.cli run-agent \
  --events data_generator/output/adaptive_rules_test_large/events.csv \
  --labels data_generator/output/adaptive_rules_test_large/labels.csv \
  --agent-output-dir data_generator/output/adaptive_rules_test_large/agent_output \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --evaluate
```

适合在不重新生成数据的情况下，测试规则或 LLM 配置修改后的效果。

## 模式三：实时滚动演示

实时演示由两个本地服务组成。

先启动前端静态服务：

```bash
python3 -m http.server 5173
```

再启动实时数据流服务：

```bash
python3 -m data_generator.live_server
```

访问：

```text
http://127.0.0.1:5173/frontend/
```

在页面中点击“实时演示 -> 启动”。

实时演示会做这些事：

- 数据引擎持续生成事件；
- 事件按不固定时间间隔进入页面；
- 会话结束后调用 agent 风格的规则识别、行为理解和评分；
- 如果是风险候选，插入“风险滚动队列”；
- 总览页会切换为本轮实时流数据，从 0 开始累计；
- TP/FP/TN/FN/F1 会根据生成器 label 和 agent 结果实时更新。

注意：实时演示为了展示流畅，默认使用本地解释，不对每个实时风险调用 LLM。批量 agent 模式会根据 `.env` 调用 LLM。

## 模式四：LLM 报告测试

可以使用已经生成过的小样本：

```bash
/opt/anaconda3/bin/python -m data_generator.cli run-agent \
  --events data_generator/output/llm_smoke_pair/events.csv \
  --labels data_generator/output/llm_smoke_pair/labels.csv \
  --agent-output-dir data_generator/output/llm_smoke_pair/agent_output \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --evaluate
```

网页查看：

```text
http://127.0.0.1:5173/frontend/?dataset=llm_smoke_pair
```

在“总览”里点击风险会话，可以看到：

- 证据摘要；
- 研判解释；
- `LLM 生成` 或 `本地解释` 标记；
- 行为链；
- 风险因子；
- 处置建议。

如果要测试 timeout 降级，可以临时在 `agent/.env` 设置：

```text
DEEPSEEK_TIMEOUT_SECONDS=0.001
DEEPSEEK_MAX_RETRIES=0
```

预期结果是流程不会卡住，报告仍然生成，但 `llm_generated=false`。

## 模式五：微批流式评测

这个模式会持续写 `stream_events.csv`，并按事件数触发 agent 微批运行。

```bash
/opt/anaconda3/bin/python -m data_generator.cli stream \
  --max-events 300 \
  --microbatch-events 100 \
  --output-dir data_generator/output/stream \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --run-agent \
  --evaluate
```

它适合测试“数据持续到达、按窗口处理”的效果。和实时前端演示不同，这个模式主要用于命令行评测。

## 前端数据集

前端右上角有“数据集”下拉框，当前支持：

- `大样本复盘`：读取 `data_generator/output/adaptive_rules_test_large`
- `LLM 混合样本`：读取 `data_generator/output/llm_smoke_pair`
- `LLM 异常样本`：读取 `data_generator/output/llm_smoke_high`
- `正常样本`：读取 `data_generator/output/llm_smoke_normal`

如果点击“实时演示 -> 启动”，总览会临时切换成本轮实时流数据。切换下拉框会停止实时流并回到静态复盘数据。

## 数据生成策略

数据生成器不是纯随机噪声，而是“模板场景 + 随机扰动”：

- 用户有角色、部门、设备、地区、常规业务范围；
- 正常行为按业务链路生成，如登录、查询、导出、打印、截图、复制；
- 异常行为按场景生成，如非工作时间高敏导出、新设备导出、跨部门查询导出、截图外发、USB 拷贝清痕、测试环境未脱敏保留；
- 每个会话保留 label，用于评测；
- 事件间隔按动作类型随机，不是固定时间；
- 实时推送也有 jitter，不是固定毫秒流入。

## 常用检查命令

检查 Python 文件：

```bash
/opt/anaconda3/bin/python -m py_compile \
  agent/config.py \
  agent/modules/llm_explainer.py \
  data_generator/engine.py \
  data_generator/live_server.py
```

检查前端脚本：

```bash
node --check frontend/app.js
```

检查实时服务：

```bash
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8765/health').read().decode())"
```

## Git Ignore 约定

以下内容不提交：

```text
.DS_Store
.venv/
data_generator/output/
agent/adaptive_rules_test/
__pycache__/
*.pyc
```

`agent/knowledge/adaptive_rules/` 中的示例规则和示例输出保留在仓库中，便于展示和说明。

## 推荐演示路径

1. 打开前端：

```text
http://127.0.0.1:5173/frontend/
```

2. 先看“实时演示”，点击“启动”，展示事件持续进入和风险滚动队列。

3. 切到“总览”，展示本轮实时流的指标和最新风险详情。

4. 用右上角数据集切到“LLM 混合样本”，展示 LLM 生成的研判解释。

5. 切到“自适应规则”，展示生效规则和建议规则池。

6. 切到“审计”，展示反馈复核和学习日志。
