# 数据防泄露智能体

## 项目结构

```
agent/
├── main.py                  # 入口脚本
├── config.py                # API配置与AHP权重常量
├── schemas.py               # 数据结构定义
├── requirements.txt
├── .env.example             # 环境变量模板
├── data/
│   └── test_events.csv      # 测试数据（含合规/违规/边界场景）
├── layer2/
│   ├── rule_engine.py       # 阶段0：规则入口，生成 candidate_flag
│   ├── scorer.py            # 阶段1+2：AHP评分 + 保护措施校正
│   ├── chain_builder.py     # 行为链重构
│   ├── llm_analyst.py       # LLM业务关联与链路分析
│   └── risk_ranker.py       # 按风险等级排序
└── layer3/
    ├── evidence_extractor.py  # 结构化证据摘要（无LLM）
    ├── llm_explainer.py       # DeepSeek生成解释+处置建议
    └── report_generator.py    # 整合输出 RiskReport
```

## 实现思路

### 数据流

```
event_log.csv
    ↓
[Layer 2] 风险计算与识别
  1. rule_engine   → 规则筛选，输出 candidate_flag + matched_scene_list
  2. scorer        → AHP评分（C2/C3/C4/C5四维度），输出 final_risk_score
  3. llm_analyst   → DeepSeek分析业务关联性与链路异常（仅候选事件）
  4. risk_ranker   → 按风险等级排序
    ↓ output/risk_events.json
[Layer 3] 结果研判与处置
  5. evidence_extractor → 结构化证据摘要（规则提取，无LLM）
  6. llm_explainer      → DeepSeek生成自然语言解释+处置建议（中风险及以上）
  7. report_generator   → 整合输出 RiskReport
    ↓ output/reports.json
```

### 评分模型（AHP，两阶段）

- **阶段0（规则入口）**：命中场景规则、高危动作阈值、复合弱规则叠加 → 生成 `candidate_flag`
- **阶段1（正式评分）**：四个一级维度加权求和
  - C2 用户/基线画像偏离（权重 0.1931）
  - C3 业务关联缺少（权重 0.0746）
  - C4 敏感影响面（权重 0.4388）
  - C5 链条与扩散证据（权重 0.2935）
- **阶段2（校正）**：保护措施抵扣因子 × BaseRiskScore

### LLM调用策略

| 位置 | 触发条件 | 用途 |
|---|---|---|
| layer2/llm_analyst | candidate_flag=1 的所有事件 | 业务关联性判断、链路异常识别 |
| layer3/llm_explainer | 中风险及以上（final_risk_score≥30） | 自然语言风险解释、处置建议 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 串行模式（展示详细中间过程，适合测试/演示）
python main.py data/test_events.csv serial

# 4. 并行模式（简洁进度日志，适合生产）
python main.py data/test_events.csv parallel

# 输出到 output/risk_events.json 和 output/reports.json
```

### 串行模式日志示例

```
>>> 加载数据: data/test_events.csv
>>> 共加载 25 条原始事件

>>> [规则引擎] 按 user_id+session_id 聚合并进行规则筛选...
>>> [规则引擎] 共 8 个会话，4 个进入候选池，4 个过滤

>>> 串行模式：逐个处理候选事件（展示详细中间过程）

============================================================
[候选事件] U001_S000004  用户=U001  规则强度=strong
  [规则判断] 命中场景: ['大批量导出', '非工作时间高危操作', '未备案USB拷贝', '未审批高敏导出']
  [AHP评分] 计算中...
  [AHP评分] 基础分=88.5  最终分=88.5  覆盖率=0.91  风险等级=极高风险
  [AHP评分] Top驱动因子: ['对象敏感等级分', '扩散落地程度分', '个人行为偏离分']
  [LLM分析] 调用DeepSeek进行业务关联与链路分析...
  [LLM分析] 结果: 该用户在凌晨通过新设备异地登录，批量导出高敏人口数据后拷贝至未备案USB并清除痕迹，无任何业务关联或审批记录，链路完整且具有明显主观规避意图。
  [研判报告] 生成中...
  [研判报告] 证据摘要: 命中场景：大批量导出、未备案USB拷贝；行为链：login → query → export → copy → delete；...
  [研判报告] 风险解释: ...
  [研判报告] 处置建议: {'action': '立即阻断并升级处置', 'suggestions': [...]}
```

### 并行模式日志示例

```
>>> 并行模式：并发处理所有候选事件
[U001_S000004] AHP评分完成 → 极高风险 (88.5分)
[U003_S000006] AHP评分完成 → 高风险 (67.2分)
[U002_S000005] AHP评分完成 → 中风险 (42.1分)
[U001_S000004] LLM分析完成
[U003_S000006] 研判报告完成 → 处置: 触发告警，优先调查
```

## 测试数据说明

`data/test_events.csv` 包含8个会话，覆盖以下场景：

| 会话 | 用户 | 场景类型 | 预期风险等级 |
|---|---|---|---|
| S000001 | U001 | 正常工作时间查询，有审批有业务 | 低风险（不入候选池） |
| S000002 | U002 | 正常查询+小量导出，有审批 | 低风险 |
| S000003 | U004 | 正常查询+打印，有审批 | 低风险（不入候选池） |
| S000004 | U001 | **极高风险**：凌晨新设备异地登录→高敏批量导出→未备案USB拷贝→清痕 | 极高风险 |
| S000005 | U002 | **边界**：有审批但导出量偏高（deviation=4倍），敏感度4级 | 中/高风险 |
| S000006 | U003 | **高风险**：深夜新设备异地→跨域查询→截图外发→共享目录拷贝+清痕 | 高风险 |
| S000007 | U002 | **边界**：有业务无审批，导出量适中 | 中风险 |
| S000008 | U003 | 正常运维操作，有审批有业务 | 低风险（不入候选池） |

## 验证各环节输出

```bash
# 查看候选事件（Layer 2输出）
cat output/risk_events.json | python -m json.tool | grep -E '"risk_level"|"final_risk_score"|"candidate_event_id"'

# 查看研判报告（Layer 3输出）
cat output/reports.json | python -m json.tool | grep -E '"risk_level"|"evidence_summary"|"action"'
```
