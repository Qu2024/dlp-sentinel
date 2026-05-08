# DLP Frontend

静态前端监控台，读取当前仓库中的 `data_generator/output/adaptive_rules_test_large` 和 `agent/adaptive_rules_test` 运行结果。

启动静态页面：

```bash
python3 -m http.server 5173
```

启动实时数据流：

```bash
python3 -m data_generator.live_server
```

访问：

```text
http://localhost:5173/frontend/
```

`实时演示` 页面通过 `http://127.0.0.1:8765/stream` 订阅本地生成事件，并在会话结束后实时显示 agent 规则识别、行为理解和风险评分结果。如果测试数据不存在，复盘页面会自动使用内置样例。
