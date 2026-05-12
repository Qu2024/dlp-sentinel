# DLP Data Generator

这个目录是独立的数据引擎，不放在 `agent/` 内部。它生成当前 agent 可直接读取的事件 CSV，并提供外部命令调用现有 agent。

## 批量生成

```bash
python3 -m data_generator.cli batch \
  --users 50 \
  --days 7 \
  --sessions-per-user-day 8 \
  --anomaly-rate 0.03 \
  --output-dir data_generator/output/batch
```

输出：

- `events.csv`：给 agent 使用的事件表
- `labels.csv`：生成器保留的会话级真值标签，只用于评测
- `role_permissions.csv`：与生成器人群匹配的权限规则副本
- `generation_meta.json`：规模、异常数量、场景分布

## 批量生成后运行 agent

```bash
python3 -m data_generator.cli batch \
  --users 50 \
  --days 7 \
  --sessions-per-user-day 8 \
  --anomaly-rate 0.03 \
  --output-dir data_generator/output/batch \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --run-agent \
  --evaluate
```

这会从外部调用 `agent/main.py`，不需要修改 agent 代码。agent 输出默认写到：

```text
data_generator/output/batch/agent_output/
```

## 实时/微批生成

```bash
python3 -m data_generator.cli stream \
  --max-events 300 \
  --max-active-sessions 8 \
  --microbatch-events 100 \
  --output-dir data_generator/output/stream
```

如需每 100 条事件触发一次 agent：

```bash
python3 -m data_generator.cli stream \
  --max-events 300 \
  --microbatch-events 100 \
  --output-dir data_generator/output/stream \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --run-agent \
  --evaluate
```

实时模式会不断追加 `stream_events.csv`，然后按微批调用现有 agent。因为当前 agent 是会话聚合模型，实时模式采用“微批评测”，不是每条日志单独评测。

## 前端实时演示流

```bash
python3 -m data_generator.live_server
```

这个服务会启动 `http://127.0.0.1:8765/stream`，前端 `实时演示` 页可直接订阅。它每条事件实时推送到浏览器；当一个会话结束时，服务会在内存中调用现有 agent 的规则识别、行为理解和风险评分模块，并把风险候选结果推送给前端。前端会传入 `run_id`，所以暂停后重连会复用服务端同一条实时管道并继续累计；只有显式重置才新建一轮。它还提供 `/rules` 和 `/rules/suggestions/review`，供前端在 `自适应规则` 页确认或弃用机器挖掘建议。

## 单独运行 agent

```bash
python3 -m data_generator.cli run-agent \
  --events data_generator/output/batch/events.csv \
  --labels data_generator/output/batch/labels.csv \
  --adaptive-rule-dir agent/adaptive_rules_test \
  --evaluate
```

## 使用独立自适应规则测试目录

默认情况下，agent 会使用 `agent/knowledge/adaptive_rules/`。如果要把学习快照和阈值更新写到独立测试目录，先准备目录：

```bash
mkdir -p agent/adaptive_rules_test
python3 -c "import sys; sys.path.insert(0, 'agent'); from modules import adaptive_rule_engine; adaptive_rule_engine.ensure_store('agent/adaptive_rules_test')"
```

然后运行数据生成器时加：

```bash
--adaptive-rule-dir agent/adaptive_rules_test
```

`agent/adaptive_rules_test/` 已建议加入 `.gitignore`，适合放测试运行产生的 `runs/`、`latest_run.json`、`learning_log.jsonl` 等文件。

## 说明

- 主评测建议用批量模式：随机种子固定，结果可复现，适合比较规则调整前后的效果。
- 实时模式适合演示：数据持续到达，agent 按窗口/事件数微批触发。
- 当前不覆盖 `agent/knowledge/role_permissions.csv`。如果后续希望 agent 使用生成器输出的权限表，再单独加一个显式同步命令。
