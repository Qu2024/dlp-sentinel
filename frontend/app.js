const datasetOptions = {
  adaptive_rules_test_large: {
    label: "大样本复盘",
    root: "../data_generator/output/adaptive_rules_test_large",
    agentRoot: "../data_generator/output/adaptive_rules_test_large/agent_output",
    evaluation: ["../data_generator/output/adaptive_rules_test_large/evaluation.json"],
  },
  llm_smoke_pair: {
    label: "LLM 混合样本",
    root: "../data_generator/output/llm_smoke_pair",
    agentRoot: "../data_generator/output/llm_smoke_pair/agent_output",
    evaluation: [
      "../data_generator/output/llm_smoke_pair/evaluation.json",
      "../data_generator/output/llm_smoke_pair/agent_output/evaluation.json",
    ],
  },
  llm_smoke_high: {
    label: "LLM 异常样本",
    root: "../data_generator/output/llm_smoke_high",
    agentRoot: "../data_generator/output/llm_smoke_high/agent_output",
    evaluation: ["../data_generator/output/llm_smoke_high/evaluation.json"],
  },
  llm_smoke_normal: {
    label: "正常样本",
    root: "../data_generator/output/llm_smoke_normal",
    agentRoot: "../data_generator/output/llm_smoke_normal/agent_output",
    evaluation: ["../data_generator/output/llm_smoke_normal/evaluation.json"],
  },
};

const defaultDatasetId = "adaptive_rules_test_large";
const defaultDemoMode = "live";
const liveApiBase = "http://127.0.0.1:8765";
const ruleApiBase = liveApiBase;

const demoModeOptions = {
  live: {
    label: "实时生成",
    description: "实时生成数据并同步处理风险",
    targetView: "live",
    datasetId: defaultDatasetId,
  },
  replay_large: {
    label: "大样本复盘",
    description: "查看离线批量评测结果",
    targetView: "overview",
    datasetId: "adaptive_rules_test_large",
  },
  llm_report: {
    label: "LLM 报告样例",
    description: "查看带 LLM 研判解释的样例",
    targetView: "overview",
    datasetId: "llm_smoke_pair",
  },
  anomaly_case: {
    label: "单异常报告",
    description: "查看单个高危异常会话",
    targetView: "agents",
    datasetId: "llm_smoke_high",
  },
  normal_check: {
    label: "正常样本对照",
    description: "查看正常样本误报情况",
    targetView: "events",
    datasetId: "llm_smoke_normal",
  },
};

const agentDefs = [
  {
    key: "rule",
    short: "R",
    title: "规则识别 Agent",
    role: "原始日志 -> 候选风险会话",
  },
  {
    key: "behavior",
    short: "B",
    title: "行为理解 Agent",
    role: "画像偏离 / 业务合理性 / 行为链",
  },
  {
    key: "scoring",
    short: "S",
    title: "风险评分 Agent",
    role: "AHP 指标评分与风险分级",
  },
  {
    key: "disposition",
    short: "D",
    title: "研判处置 Agent",
    role: "证据摘要 / 解释报告 / 处置建议",
  },
];

const fallback = {
  reports: [
    {
      report_id: "RPT_U0001_SAMPLE",
      user_id: "U0001",
      risk_level: "极高风险",
      final_risk_score: 90.2,
      evidence_summary:
        "命中场景：未审批高敏导出、跨域大量查询；行为链：login -> query -> export -> copy；最高敏感等级：5；累计查询220次；累计导出180条记录。",
      risk_explanation: "本地样例风险报告。",
      disposition: { action: "立即阻断并升级处置", suggestions: ["冻结账号", "隔离终端", "核查外发去向"] },
      llm_generated: false,
      candidate_event_id: "U0001_S0001",
      matched_scene_list: ["未审批高敏导出", "跨域大量查询"],
      behavior_chain: ["login", "query", "export", "copy"],
      agent_trace: {
        profile_agent: { profile_abnormal_flags: ["新设备登录", "非工作时间操作"] },
        business_agent: { business_problems: ["缺少明确业务关联", "导出行为缺少审批"] },
        chain_agent: { chain_flags: ["形成登录-查询-导出链条", "存在本地/USB/共享目录拷贝"] },
        scoring_agent: {
          top_drivers: [
            { indicator: "对象敏感等级分", contribution: 15.468 },
            { indicator: "扩散落地程度分", contribution: 9.393 },
          ],
        },
      },
    },
  ],
  riskEvents: [
    {
      candidate_event_id: "U0001_S0001",
      user_id: "U0001",
      final_risk_score: 90.2,
      base_risk_score: 84.7,
      coverage: 0.77,
      risk_level: "极高风险",
      matched_scene_list: ["未审批高敏导出", "跨域大量查询"],
      top_drivers: [
        { indicator: "对象敏感等级分", contribution: 15.468 },
        { indicator: "扩散落地程度分", contribution: 9.393 },
      ],
      raw_events: [
        { event_time: "2026-04-20 02:10:00", event_type: "login", action_object: "异常登录", ip_region: "上海" },
        { event_time: "2026-04-20 02:12:00", event_type: "query", action_object: "人口高敏查询", query_count: 220 },
        { event_time: "2026-04-20 02:14:00", event_type: "export", action_object: "人口批量导出", export_count: 180 },
      ],
    },
  ],
  feedback: [],
  evaluation: {
    total_sessions: 1,
    predicted_candidate_sessions: 1,
    actual_anomaly_sessions: 1,
    tp: 1,
    fp: 0,
    tn: 0,
    fn: 0,
    precision: 1,
    recall: 1,
    f1: 1,
  },
  meta: {
    event_count: 3,
    session_count: 1,
    anomaly_session_count: 1,
    scene_counts: { normal: 0, sample_risk: 1 },
    config: { user_count: 1, days: 1, anomaly_rate: 1 },
  },
  activeRules: { scene_rules: [], high_risk_thresholds: [], weak_rules: [] },
  suggestedRules: { rules: [] },
  learningLog: "",
};

const state = {
  reports: [],
  riskEvents: [],
  riskById: new Map(),
  feedback: [],
  evaluation: {},
  meta: {},
  activeRules: {},
  suggestedRules: {},
  learningLog: "",
  selectedId: "",
  ruleActionMessage: "",
  ruleActionBusyId: "",
  demoMode: demoModeFromUrl(),
  datasetId: datasetIdForDemoMode(demoModeFromUrl()),
  currentView: "live",
  live: {
    source: null,
    runId: "",
    hasStarted: false,
    rawFeed: [],
    riskFeed: [],
    selectedRisk: null,
    counts: emptyLiveCounts(),
    connected: false,
    paused: false,
    overviewActive: false,
    overviewSnapshot: null,
  },
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setToday();
  bindNavigation();
  bindFilters();
  bindLiveControls();
  await loadData();
  setActiveView((demoModeOptions[state.demoMode] || demoModeOptions[defaultDemoMode]).targetView);
  renderAll();
  renderLive();
}

async function loadData() {
  if (state.live.overviewActive) storeLiveOverviewSnapshot();
  state.live.overviewActive = false;
  const paths = buildPaths(state.datasetId);
  const [reports, riskEvents, feedback, evaluation, meta, ruleStore, learningLog] = await Promise.all([
    loadJson(paths.reports, fallback.reports),
    loadJson(paths.riskEvents, fallback.riskEvents),
    loadJson(paths.feedback, fallback.feedback),
    loadJson(paths.evaluation, fallback.evaluation),
    loadJson(paths.meta, fallback.meta),
    loadRuleStore(paths),
    loadText(paths.learningLog, fallback.learningLog),
  ]);

  state.reports = [...reports].sort((a, b) => (b.final_risk_score || 0) - (a.final_risk_score || 0));
  state.riskEvents = riskEvents;
  state.riskById = new Map(riskEvents.map((item) => [item.candidate_event_id, item]));
  state.feedback = feedback;
  state.evaluation = evaluation;
  state.meta = normalizeMeta(meta, evaluation);
  state.activeRules = ruleStore.activeRules;
  state.suggestedRules = ruleStore.suggestedRules;
  state.learningLog = learningLog;
  state.selectedId = state.reports[0]?.candidate_event_id || "";

  const fromRealData = reports !== fallback.reports;
  const dataset = datasetOptions[state.datasetId] || datasetOptions[defaultDatasetId];
  const mode = demoModeOptions[state.demoMode] || demoModeOptions[defaultDemoMode];
  if (state.demoMode === "live") {
    restoreLiveOverviewSnapshot();
    document.getElementById("dataSourceLine").textContent = state.live.hasStarted
      ? "实时生成模式：已保留本轮历史，可继续"
      : "实时生成模式：点击启动开始";
    return;
  }

  document.getElementById("dataSourceLine").textContent = fromRealData
    ? `${mode.label}：${mode.description}`
    : `${dataset.label} 缺失，使用内置样例数据`;
}

function buildPaths(datasetId) {
  const dataset = datasetOptions[datasetId] || datasetOptions[defaultDatasetId];
  return {
    reports: `${dataset.agentRoot}/reports.json`,
    riskEvents: `${dataset.agentRoot}/risk_events.json`,
    feedback: `${dataset.agentRoot}/feedback.json`,
    evaluation: dataset.evaluation,
    meta: `${dataset.root}/generation_meta.json`,
    activeRules: "../agent/adaptive_rules_test/active_rules.json",
    suggestedRules: "../agent/adaptive_rules_test/suggested_rules.json",
    learningLog: "../agent/adaptive_rules_test/learning_log.jsonl",
  };
}

async function loadJson(pathOrPaths, backup) {
  const paths = Array.isArray(pathOrPaths) ? pathOrPaths : [pathOrPaths];
  for (const path of paths) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) throw new Error(response.statusText);
      return await response.json();
    } catch {
      // Try the next candidate path.
    }
  }
  return backup;
}

async function loadRuleStore(paths) {
  try {
    const response = await fetch(`${ruleApiBase}/rules`, { cache: "no-store" });
    if (!response.ok) throw new Error(response.statusText);
    const payload = await response.json();
    if (payload.ok) {
      return {
        activeRules: payload.active_rules || fallback.activeRules,
        suggestedRules: payload.suggested_rules || fallback.suggestedRules,
      };
    }
  } catch {
    // The live server is optional for static viewing; fall back to files.
  }

  const [activeRules, suggestedRules] = await Promise.all([
    loadJson(paths.activeRules, fallback.activeRules),
    loadJson(paths.suggestedRules, fallback.suggestedRules),
  ]);
  return { activeRules, suggestedRules };
}

async function loadText(path, backup) {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(response.statusText);
    return await response.text();
  } catch {
    return backup;
  }
}

function bindNavigation() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveView(button.dataset.view);
    });
  });
}

function setActiveView(view) {
  state.currentView = view;
  document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
}

function bindFilters() {
  ["riskSearch", "riskLevelFilter", "eventTableSearch", "eventTableLevel"].forEach((id) => {
    const node = document.getElementById(id);
    if (node) node.addEventListener("input", renderAll);
  });
}

function renderAll() {
  renderLive();
  renderMetrics();
  renderRiskList();
  renderDetail();
  renderAgentView();
  renderEvaluation();
  renderSceneBars();
  renderSuggestions();
  renderEventTable();
  renderRules();
  renderAudit();
}

function emptyLiveCounts() {
  return {
    events: 0,
    sessions_started: 0,
    sessions_completed: 0,
    candidate_events: 0,
    high_or_above: 0,
    anomalies: 0,
  };
}

function cloneData(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}

function storeLiveOverviewSnapshot() {
  if (!state.live.overviewActive) return;
  state.live.overviewSnapshot = {
    reports: cloneData(state.reports) || [],
    riskEvents: cloneData(state.riskEvents) || [],
    feedback: cloneData(state.feedback) || [],
    evaluation: cloneData(state.evaluation) || {},
    meta: cloneData(state.meta) || {},
    selectedId: state.selectedId,
  };
}

function restoreLiveOverviewSnapshot() {
  const snapshot = state.live.overviewSnapshot;
  if (!snapshot) {
    resetOverviewForLive();
    return;
  }
  state.live.overviewActive = true;
  state.reports = cloneData(snapshot.reports) || [];
  state.riskEvents = cloneData(snapshot.riskEvents) || [];
  state.riskById = new Map(state.riskEvents.map((item) => [item.candidate_event_id, item]));
  state.feedback = cloneData(snapshot.feedback) || [];
  state.evaluation = cloneData(snapshot.evaluation) || {};
  state.meta = cloneData(snapshot.meta) || {};
  state.selectedId = snapshot.selectedId || state.reports[0]?.candidate_event_id || "";
}

function newLiveRunId() {
  return `live-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function prepareNewLiveRun() {
  state.live.runId = newLiveRunId();
  state.live.hasStarted = true;
  state.live.rawFeed = [];
  state.live.riskFeed = [];
  state.live.selectedRisk = null;
  state.live.counts = emptyLiveCounts();
  state.live.paused = false;
  state.live.overviewSnapshot = null;
  resetOverviewForLive();
}

function resetLiveRun(restart = false) {
  stopLiveStream(false);
  state.live.runId = "";
  state.live.hasStarted = false;
  state.live.rawFeed = [];
  state.live.riskFeed = [];
  state.live.selectedRisk = null;
  state.live.counts = emptyLiveCounts();
  state.live.paused = false;
  state.live.overviewSnapshot = null;
  resetOverviewForLive();
  document.getElementById("liveSourceLine").textContent = "已重置，点击启动开始新一轮实时流";
  updateLiveStatus("已重置", false);
  renderLive();
  renderOverviewFromLive(true);
  if (restart) startLiveStream({ reset: true });
}

function resetOverviewForLive() {
  state.live.overviewActive = true;
  state.reports = [];
  state.riskEvents = [];
  state.riskById = new Map();
  state.feedback = [];
  state.selectedId = "";
  state.meta = {
    event_count: 0,
    session_count: 0,
    anomaly_session_count: 0,
    scene_counts: {},
    config: {},
  };
  state.evaluation = {
    total_sessions: 0,
    predicted_candidate_sessions: 0,
    actual_anomaly_sessions: 0,
    tp: 0,
    fp: 0,
    tn: 0,
    fn: 0,
    precision: 0,
    recall: 0,
    f1: 0,
  };
  document.getElementById("dataSourceLine").textContent = "实时生成数据流";
  storeLiveOverviewSnapshot();
}

function applyLiveEventToOverview(data) {
  if (!state.live.overviewActive) return;
  const label = data.label || {};
  state.meta.event_count = state.live.counts.events || state.meta.event_count;
  state.meta.session_count = state.live.counts.sessions_completed || 0;
  state.meta.anomaly_session_count = state.live.counts.anomalies || 0;
  if (data.is_first_event) {
    const scene = label.scene_type || "unknown";
    state.meta.scene_counts[scene] = (state.meta.scene_counts[scene] || 0) + 1;
  }
}

function applyLiveSessionToOverview(data) {
  if (!state.live.overviewActive) return;
  const label = data.label || data.risk?.label || {};
  const isAnomaly = Number(label.is_anomaly || 0) === 1;
  state.meta.session_count = state.live.counts.sessions_completed || state.meta.session_count;
  state.meta.anomaly_session_count = state.live.counts.anomalies || state.meta.anomaly_session_count;
  state.evaluation.total_sessions = state.meta.session_count;
  state.evaluation.actual_anomaly_sessions = state.meta.anomaly_session_count;
  state.evaluation.predicted_candidate_sessions = state.live.counts.candidate_events || 0;

  if (data.candidate && isAnomaly) state.evaluation.tp += 1;
  if (data.candidate && !isAnomaly) state.evaluation.fp += 1;
  if (!data.candidate && isAnomaly) state.evaluation.fn += 1;
  if (!data.candidate && !isAnomaly) state.evaluation.tn += 1;
  updateEvaluationRates();
}

function addLiveRiskToOverview(payload) {
  if (!state.live.overviewActive) return;
  const report = payload.report || {};
  const risk = payload.risk_event || {};
  const id = report.candidate_event_id || risk.candidate_event_id;
  if (!id) return;

  state.reports = [report, ...state.reports.filter((item) => item.candidate_event_id !== id)]
    .sort((a, b) => (b.final_risk_score || 0) - (a.final_risk_score || 0));
  state.riskEvents = [risk, ...state.riskEvents.filter((item) => item.candidate_event_id !== id)];
  state.riskById.set(id, risk);
  state.selectedId = id;
}

function updateEvaluationRates() {
  const { tp, fp, fn } = state.evaluation;
  const precision = tp + fp ? tp / (tp + fp) : 0;
  const recall = tp + fn ? tp / (tp + fn) : 0;
  state.evaluation.precision = precision;
  state.evaluation.recall = recall;
  state.evaluation.f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
}

function pendingSuggestedRules() {
  return (state.suggestedRules.rules || []).filter((rule) =>
    rule.status !== "active"
    && rule.status !== "rejected"
    && !rule.approved
  );
}

async function reviewSuggestedRule(ruleId, action) {
  if (!ruleId || state.ruleActionBusyId) return;
  const rule = (state.suggestedRules.rules || []).find((item) => item.id === ruleId);
  state.ruleActionBusyId = ruleId;
  state.ruleActionMessage = action === "approve" ? "正在加入规则库..." : "正在移出建议池...";
  renderRules();

  try {
    const response = await fetch(`${ruleApiBase}/rules/suggestions/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_id: ruleId, action }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || response.statusText);
    }
    state.activeRules = payload.active_rules || state.activeRules;
    state.suggestedRules = payload.suggested_rules || state.suggestedRules;
    state.ruleActionMessage = action === "approve"
      ? `已加入规则库：${rule?.name || ruleId}`
      : `已拒绝并移出建议池：${rule?.name || ruleId}`;
  } catch (error) {
    state.ruleActionMessage = `规则操作失败：${error.message || error}`;
  } finally {
    state.ruleActionBusyId = "";
    renderRules();
    renderSuggestions();
    renderMetrics();
  }
}

function renderOverviewFromLive(includeRiskViews) {
  if (!state.live.overviewActive) return;
  storeLiveOverviewSnapshot();
  renderMetrics();
  renderEvaluation();
  renderSceneBars();
  if (includeRiskViews) {
    renderRiskList();
    renderDetail();
    renderAgentView();
    renderEventTable();
    renderAudit();
  }
}

function bindLiveControls() {
  document.getElementById("liveStart")?.addEventListener("click", () => startLiveStream());
  document.getElementById("liveStop")?.addEventListener("click", stopLiveStream);
  document.getElementById("liveReset")?.addEventListener("click", () => resetLiveRun(false));
  document.getElementById("liveSpeed")?.addEventListener("change", () => {
    if (state.live.connected) startLiveStream();
  });
  document.getElementById("liveAnomalyRate")?.addEventListener("change", () => {
    if (state.live.connected) resetLiveRun(true);
    else if (state.live.hasStarted) resetLiveRun(false);
  });
}

function startLiveStream(options = {}) {
  if (state.demoMode !== "live") {
    state.demoMode = "live";
    state.datasetId = datasetIdForDemoMode("live");
    const url = new URL(window.location.href);
    url.searchParams.set("mode", "live");
    url.searchParams.delete("dataset");
    window.history.replaceState(null, "", url);
  }
  const requestedReset = Boolean(options.reset);
  stopLiveStream(false);
  const resetRun = requestedReset || !state.live.runId || !state.live.hasStarted || !state.live.overviewActive;
  if (resetRun) {
    prepareNewLiveRun();
  } else {
    state.live.overviewActive = true;
  }
  state.live.connected = true;
  state.live.paused = false;
  renderLive();
  renderOverviewFromLive(true);

  const speed = document.getElementById("liveSpeed")?.value || "420";
  const anomalyRate = document.getElementById("liveAnomalyRate")?.value || "0.18";
  const params = new URLSearchParams({
    speed_ms: speed,
    anomaly_rate: anomalyRate,
    users: "100",
    max_active_sessions: "16",
    max_events: "0",
    run_id: state.live.runId,
    reset: resetRun ? "1" : "0",
  });
  const url = `${liveApiBase}/stream?${params.toString()}`;
  const source = new EventSource(url);
  state.live.source = source;

  source.addEventListener("meta", (event) => {
    const data = safeParse(event.data);
    if (data.counts) state.live.counts = data.counts;
    document.getElementById("liveSourceLine").textContent = data.rule_dir
      ? `${data.resumed ? "继续" : "已连接"} ${data.rule_dir}`
      : `${data.resumed ? "继续" : "已连接"}本地实时流`;
    updateLiveStatus("运行中", true);
    renderLiveMetrics();
  });

  source.addEventListener("event", (event) => {
    const data = safeParse(event.data);
    state.live.counts = data.counts || state.live.counts;
    state.live.rawFeed.unshift(data);
    state.live.rawFeed = state.live.rawFeed.slice(0, 80);
    applyLiveEventToOverview(data);
    renderLiveMetrics();
    renderLiveAgentPipeline();
    renderLiveRawFeed();
    renderOverviewFromLive(false);
  });

  source.addEventListener("session", (event) => {
    const data = safeParse(event.data);
    state.live.counts = data.counts || state.live.counts;
    applyLiveSessionToOverview(data);
    if (data.candidate && data.risk) {
      state.live.riskFeed.unshift(data.risk);
      state.live.riskFeed = state.live.riskFeed.slice(0, 60);
      state.live.selectedRisk = data.risk;
      addLiveRiskToOverview(data.risk);
      renderLiveAgentPipeline();
      renderLiveRiskFeed();
      renderLiveInspector();
      renderOverviewFromLive(true);
    } else {
      renderOverviewFromLive(false);
    }
    renderLiveMetrics();
    renderLiveAgentPipeline();
  });

  source.addEventListener("done", () => {
    stopLiveStream(false);
    updateLiveStatus("完成", false);
  });

  source.onerror = () => {
    source.close();
    if (state.live.source === source) {
      state.live.source = null;
      state.live.connected = false;
      state.live.paused = state.live.hasStarted;
      updateLiveStatus("连接失败", false);
      document.getElementById("liveSourceLine").textContent = `未连接 ${liveApiBase}`;
      renderLive();
    }
  };
}

function stopLiveStream(render = true) {
  if (state.live.source) {
    state.live.source.close();
    state.live.source = null;
  }
  state.live.connected = false;
  state.live.paused = state.live.hasStarted;
  updateLiveStatus("已暂停", false);
  if (render) renderLive();
}

function renderLive() {
  updateLiveStartLabel();
  renderLiveMetrics();
  renderLiveAgentPipeline();
  renderLiveRawFeed();
  renderLiveRiskFeed();
  renderLiveInspector();
}

function renderLiveMetrics() {
  const counts = state.live.counts;
  const metrics = [
    ["实时事件", counts.events, "进入原始流", "#dbeafe"],
    ["已完成会话", counts.sessions_completed, `${fmt(counts.sessions_started)} 个已启动`, "#e0f2fe"],
    ["候选风险", counts.candidate_events, `${fmt(counts.high_or_above)} 个高危以上`, "#fee2e2"],
    ["真实异常", counts.anomalies, "生成器标签", "#ffedd5"],
  ];
  const node = document.getElementById("liveMetricGrid");
  if (!node) return;
  node.innerHTML = metrics.map(([label, value, note, tint]) => `
    <article class="metricCard liveMetric" style="--tint:${tint}">
      <span>${escapeHtml(label)}</span>
      <strong>${fmt(value)}</strong>
      <small>${escapeHtml(note)}</small>
    </article>
  `).join("");
}

function renderLiveAgentPipeline() {
  const node = document.getElementById("liveAgentPipeline");
  if (!node) return;
  const selected = state.live.selectedRisk;
  const counts = state.live.counts;
  const steps = liveAgentSteps(selected, counts);
  document.getElementById("agentPipelineHint").textContent = selected
    ? `${selected.report?.candidate_event_id || ""} 已完成智能体链路`
    : counts.events
      ? "规则识别 Agent 正在消费实时事件"
      : "等待实时事件进入";
  document.getElementById("agentPipelineCount").textContent = `${steps.filter((item) => item.status === "done").length}/4`;
  node.innerHTML = steps.map((step, index) => `
    <article class="agentStep ${step.status}">
      <div class="agentStepMark">${escapeHtml(step.short)}</div>
      <div class="agentStepBody">
        <strong>${escapeHtml(step.title)}</strong>
        <span>${escapeHtml(step.role)}</span>
        <p>${escapeHtml(step.summary)}</p>
      </div>
      ${index < steps.length - 1 ? `<i class="agentConnector"></i>` : ""}
    </article>
  `).join("");
}

function liveAgentSteps(selected, counts) {
  if (selected) {
    const report = selected.report || {};
    const risk = selected.risk_event || {};
    return buildAgentCards(report, risk).map((card) => ({
      ...card,
      status: "done",
      summary: card.summary,
    }));
  }
  return agentDefs.map((agent, index) => {
    let status = "waiting";
    let summary = "等待上游输入";
    if (index === 0 && counts.events > 0) {
      status = "active";
      summary = `已接收 ${fmt(counts.events)} 条实时事件`;
    } else if (index === 1 && counts.sessions_completed > 0) {
      status = "active";
      summary = `已完成 ${fmt(counts.sessions_completed)} 个会话窗口`;
    } else if (index > 1 && counts.candidate_events > 0) {
      status = "done";
      summary = `已输出 ${fmt(counts.candidate_events)} 个风险候选`;
    }
    return { ...agent, status, summary };
  });
}

function renderLiveRawFeed() {
  const countNode = document.getElementById("liveEventCount");
  const feedNode = document.getElementById("liveRawFeed");
  if (!countNode || !feedNode) return;
  countNode.textContent = `${fmt(state.live.counts.events)} 条事件`;
  feedNode.innerHTML = state.live.rawFeed.map((item) => {
    const event = item.event || {};
    const label = item.label || {};
    const isAnomaly = Number(label.is_anomaly || 0) === 1;
    return `
      <article class="streamItem ${isAnomaly ? "anomaly" : ""}">
        <div class="streamTop">
          <strong>${escapeHtml(event.event_type)} · ${escapeHtml(event.user_id)}</strong>
          <span>${escapeHtml(event.event_time || "")}</span>
        </div>
        <p>${escapeHtml(event.action_object || event.object_domain || "")}</p>
        <div class="streamMeta">
          <span>${escapeHtml(event.session_id || "")}</span>
          <span>${escapeHtml(event.role || "")}</span>
          <span>查 ${fmt(event.query_count)} / 导 ${fmt(event.export_count)} / 拷 ${fmt(event.copy_count)}</span>
          <span>${isAnomaly ? sceneName(label.scene_type) : "正常"}</span>
        </div>
      </article>
    `;
  }).join("") || `<div class="emptyState">点击启动后开始滚动</div>`;
}

function renderLiveRiskFeed() {
  const countNode = document.getElementById("liveRiskCount");
  const highNode = document.getElementById("liveHighCount");
  const feedNode = document.getElementById("liveRiskFeed");
  if (!countNode || !highNode || !feedNode) return;
  countNode.textContent = `${fmt(state.live.counts.candidate_events)} 个候选`;
  highNode.textContent = fmt(state.live.counts.high_or_above);
  feedNode.innerHTML = state.live.riskFeed.map((item, index) => {
    const report = item.report || {};
    const risk = item.risk_event || {};
    const style = levelStyle(report.risk_level);
    const label = item.label || {};
    return `
      <button class="streamItem riskTick ${state.live.selectedRisk === item ? "active" : ""}" data-index="${index}" style="--level-color:${style.color}">
        <div class="streamTop">
          <strong>${escapeHtml(report.user_id)} · ${escapeHtml(report.candidate_event_id)}</strong>
          <span class="scoreText">${num(report.final_risk_score, 1)}</span>
        </div>
        <p>${escapeHtml(report.evidence_summary || "")}</p>
        <div class="streamMeta">
          <span class="riskLevel" style="--level-color:${style.color};--level-bg:${style.bg}">${escapeHtml(report.risk_level)}</span>
          <span>${escapeHtml((report.matched_scene_list || []).slice(0, 2).join(" / ") || "规则命中")}</span>
          <span>${Number(label.is_anomaly || 0) === 1 ? "标签异常" : "标签正常"}</span>
          <span>覆盖 ${pct(risk.coverage)}</span>
        </div>
      </button>
    `;
  }).join("") || `<div class="emptyState">暂无风险候选</div>`;

  feedNode.querySelectorAll(".riskTick").forEach((button) => {
    button.addEventListener("click", () => {
      state.live.selectedRisk = state.live.riskFeed[Number(button.dataset.index)];
      state.selectedId = state.live.selectedRisk?.report?.candidate_event_id || state.selectedId;
      renderLiveRiskFeed();
      renderLiveInspector();
      renderAgentView();
    });
  });
}

function renderLiveInspector() {
  const node = document.getElementById("liveInspector");
  const item = state.live.selectedRisk;
  if (!node) return;
  if (!item) {
    node.innerHTML = `<div class="emptyState">暂无实时风险</div>`;
    return;
  }
  const report = item.report || {};
  const risk = item.risk_event || {};
  const style = levelStyle(report.risk_level);
  const drivers = risk.top_drivers || report.agent_trace?.scoring_agent?.top_drivers || [];
  const rawEvents = risk.raw_events || [];
  const trace = report.agent_trace || risk.agent_trace || {};
  const flags = [
    ...(trace.profile_agent?.profile_abnormal_flags || []),
    ...(trace.business_agent?.business_problems || []),
    ...(trace.chain_agent?.chain_flags || []),
  ].slice(0, 10);
  node.innerHTML = `
    <div class="detailHeader compact">
      <div>
        <h2>${escapeHtml(report.user_id)} 实时风险</h2>
        <p>${escapeHtml(report.candidate_event_id || "")}</p>
      </div>
      <div class="detailScore" style="--level-color:${style.color};--level-bg:${style.bg}">
        <strong>${num(report.final_risk_score, 1)}</strong>
        <span class="riskLevel">${escapeHtml(report.risk_level)}</span>
      </div>
    </div>
    <div class="liveInspectorBody">
      <section class="sectionBlock">
        <h3>证据</h3>
        <p class="evidenceText">${escapeHtml(report.evidence_summary || "")}</p>
      </section>
      <section class="sectionBlock">
        <div class="sectionTitleRow">
          <h3>研判解释</h3>
          <span class="reportSource">${report.llm_generated ? "LLM 生成" : "本地解释"}</span>
        </div>
        <p class="evidenceText narrativeText">${escapeHtml(report.risk_explanation || "暂无研判解释")}</p>
      </section>
      <section class="sectionBlock">
        <h3>行为链</h3>
        <div class="chain compactChain">
          ${(risk.behavior_chain || report.behavior_chain || []).map((step, index) => `<div class="chainStep"><b>${index + 1}</b>${escapeHtml(step)}</div>`).join("")}
        </div>
      </section>
      <section class="sectionBlock">
        <h3>关键因子</h3>
        <div class="flagList">
          ${drivers.map((item) => `<span class="tag">${escapeHtml(item.indicator)} ${num(item.contribution, 1)}</span>`).join("")}
          ${flags.map((flag) => `<span class="tag mutedTag">${escapeHtml(flag)}</span>`).join("")}
        </div>
      </section>
      <section class="sectionBlock">
        <h3>事件片段</h3>
        <div class="timeline compactTimeline">
          ${rawEvents.map((event) => `
            <div class="timelineItem">
              <strong>${escapeHtml(event.event_type)} · ${escapeHtml(event.action_object || "")}</strong>
              <span>${escapeHtml(event.event_time || "")} · ${escapeHtml(event.ip_region || "")}</span>
            </div>
          `).join("")}
        </div>
      </section>
    </div>
  `;
}

function renderMetrics() {
  const riskCounts = countBy(state.reports, "risk_level");
  const activeRuleCount = ruleCount(state.activeRules);
  const metrics = [
    ["事件总量", fmt(state.meta.event_count), `${fmt(state.meta.session_count)} 个会话`, "#dbeafe"],
    ["候选风险", fmt(state.evaluation.predicted_candidate_sessions ?? state.reports.length), `${fmt(state.meta.anomaly_session_count)} 个真实异常`, "#fee2e2"],
    ["极高风险", fmt(riskCounts["极高风险"] || 0), "处置优先级最高", "#fee2e2"],
    ["Precision", pct(state.evaluation.precision), `FP ${fmt(state.evaluation.fp)}`, "#d1fae5"],
    ["Recall", pct(state.evaluation.recall), `FN ${fmt(state.evaluation.fn)}`, "#e0f2fe"],
    ["规则在线", fmt(activeRuleCount), `${fmt(state.suggestedRules.rules?.length || 0)} 条建议`, "#ffedd5"],
  ];
  document.getElementById("metricGrid").innerHTML = metrics
    .map(([label, value, note, tint]) => `
      <article class="metricCard" style="--tint:${tint}">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
        <small>${escapeHtml(note)}</small>
      </article>
    `)
    .join("");
}

function renderRiskList() {
  const query = (document.getElementById("riskSearch")?.value || "").trim().toLowerCase();
  const level = document.getElementById("riskLevelFilter")?.value || "all";
  const reports = filteredReports(query, level);
  document.getElementById("riskListCount").textContent = `${reports.length} 个候选`;
  if (!reports.length) {
    document.getElementById("riskList").innerHTML = `<div class="emptyState">没有匹配的风险会话</div>`;
    return;
  }
  if (!reports.some((item) => item.candidate_event_id === state.selectedId)) {
    state.selectedId = reports[0].candidate_event_id;
  }
  document.getElementById("riskList").innerHTML = reports
    .slice(0, 80)
    .map((report) => {
      const style = levelStyle(report.risk_level);
      const scenes = (report.matched_scene_list || []).slice(0, 2).join(" / ");
      return `
        <button class="riskItem ${report.candidate_event_id === state.selectedId ? "active" : ""}"
          style="--level-color:${style.color}"
          data-id="${escapeAttr(report.candidate_event_id)}">
          <div class="riskItemTop">
            <div>
              <strong>${escapeHtml(report.user_id)} · ${escapeHtml(report.candidate_event_id || "")}</strong>
              <span class="riskLevel" style="--level-color:${style.color};--level-bg:${style.bg}">${escapeHtml(report.risk_level)}</span>
            </div>
            <div class="scoreText">${num(report.final_risk_score, 1)}</div>
          </div>
          <p>${escapeHtml(report.evidence_summary || "")}</p>
          <div class="riskMeta">
            <span>${escapeHtml(scenes || "未命名场景")}</span>
            <span>${report.llm_generated ? "LLM" : "本地解释"}</span>
          </div>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll(".riskItem").forEach((item) => {
    item.addEventListener("click", () => {
      state.selectedId = item.dataset.id;
      renderRiskList();
      renderDetail();
      renderAgentView();
    });
  });
}

function renderDetail() {
  const report = state.reports.find((item) => item.candidate_event_id === state.selectedId) || state.reports[0];
  if (!report) {
    document.getElementById("detailPanel").innerHTML = `<div class="emptyState">暂无风险报告</div>`;
    return;
  }
  const risk = state.riskById.get(report.candidate_event_id) || {};
  const style = levelStyle(report.risk_level);
  const trace = report.agent_trace || {};
  const profileFlags = trace.profile_agent?.profile_abnormal_flags || risk.profile_result?.profile_abnormal_flags || [];
  const businessProblems = trace.business_agent?.business_problems || risk.business_result?.business_problems || [];
  const chainFlags = trace.chain_agent?.chain_flags || risk.chain_result?.chain_flags || [];
  const drivers = report.agent_trace?.scoring_agent?.top_drivers || risk.top_drivers || [];
  const rawEvents = risk.raw_events || [];
  const maxDriver = Math.max(...drivers.map((item) => item.contribution || 0), 1);

  document.getElementById("detailPanel").innerHTML = `
    <div class="detailHeader">
      <div class="detailTitle">
        <div class="userToken">${escapeHtml((report.user_id || "U").slice(-2))}</div>
        <div>
          <h2>${escapeHtml(report.user_id)} 风险会话</h2>
          <p>${escapeHtml(report.candidate_event_id)} · ${escapeHtml((report.matched_scene_list || []).join(" / "))}</p>
        </div>
      </div>
      <div class="detailScore" style="--level-color:${style.color};--level-bg:${style.bg}">
        <strong>${num(report.final_risk_score, 1)}</strong>
        <span class="riskLevel">${escapeHtml(report.risk_level)}</span>
      </div>
    </div>
    <div class="detailBody">
      <div class="detailMain">
        <section class="sectionBlock">
          <h3>证据摘要</h3>
          <p class="evidenceText">${escapeHtml(report.evidence_summary || report.risk_explanation || "")}</p>
        </section>
        <section class="sectionBlock">
          <div class="sectionTitleRow">
            <h3>研判解释</h3>
            <span class="reportSource">${report.llm_generated ? "LLM 生成" : "本地解释"}</span>
          </div>
          <p class="evidenceText narrativeText">${escapeHtml(report.risk_explanation || "暂无研判解释")}</p>
        </section>
        <section class="sectionBlock">
          <h3>行为链</h3>
          <div class="chain">
            ${(report.behavior_chain || risk.behavior_chain || []).map((step, index) => `
              <div class="chainStep"><b>${index + 1}</b>${escapeHtml(step)}</div>
            `).join("")}
          </div>
        </section>
        <section class="sectionBlock">
          <h3>智能体协同轨迹</h3>
          <div class="agentMiniGrid">
            ${renderAgentCards(buildAgentCards(report, risk), true)}
          </div>
        </section>
        <section class="sectionBlock">
          <h3>原始事件时间线</h3>
          <div class="timeline">
            ${rawEvents.slice(0, 8).map((event) => `
              <div class="timelineItem">
                <strong>${escapeHtml(event.event_type)} · ${escapeHtml(event.action_object || event.object_domain || "")}</strong>
                <span>${escapeHtml(event.event_time || "")} · ${escapeHtml(event.ip_region || "")} · 查询 ${fmt(event.query_count)} / 导出 ${fmt(event.export_count)} / 拷贝 ${fmt(event.copy_count)}</span>
              </div>
            `).join("") || `<div class="emptyState">暂无原始事件</div>`}
          </div>
        </section>
      </div>
      <div class="detailSide">
        <section class="sectionBlock">
          <h3>主要风险因子</h3>
          <div class="driverList">
            ${drivers.map((item) => `
              <div class="driverRow">
                <span>${escapeHtml(item.indicator)}</span>
                <div class="barTrack"><div class="barFill" style="width:${Math.max(4, (item.contribution || 0) / maxDriver * 100)}%"></div></div>
                <b>${num(item.contribution, 1)}</b>
              </div>
            `).join("")}
          </div>
        </section>
        <section class="sectionBlock">
          <h3>异常标记</h3>
          <div class="flagList">
            ${[...profileFlags, ...businessProblems, ...chainFlags].slice(0, 12).map((flag) => `<span class="tag">${escapeHtml(flag)}</span>`).join("")}
          </div>
        </section>
        <section class="sectionBlock">
          <h3>处置建议</h3>
          <div class="flagList">
            <span class="tag">${escapeHtml(report.disposition?.action || "待复核")}</span>
            ${(report.disposition?.suggestions || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}
          </div>
        </section>
      </div>
    </div>
  `;
}

function renderEvaluation() {
  const f1 = state.evaluation.f1 ?? 0;
  document.getElementById("scoreDial").style.setProperty("--pct", String(Math.round(f1 * 100)));
  document.getElementById("f1Value").textContent = pct(f1);
  const stats = [
    ["TP", state.evaluation.tp],
    ["FP", state.evaluation.fp],
    ["FN", state.evaluation.fn],
    ["TN", state.evaluation.tn],
  ];
  document.getElementById("evalMiniStats").innerHTML = stats
    .map(([label, value]) => `<div class="miniStat"><span>${label}</span><strong>${fmt(value)}</strong></div>`)
    .join("");
}

function renderSceneBars() {
  const counts = state.meta.scene_counts || {};
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 7);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  const colors = ["#2563eb", "#dc2626", "#f97316", "#0891b2", "#059669", "#7c3aed", "#64748b"];
  document.getElementById("sceneBars").innerHTML = entries
    .map(([name, value], index) => `
      <div class="sceneRow">
        <span title="${escapeAttr(name)}">${escapeHtml(sceneName(name))}</span>
        <strong>${fmt(value)}</strong>
        <div class="sceneBar"><i style="--w:${Math.max(3, value / max * 100)}%;--c:${colors[index % colors.length]}"></i></div>
      </div>
    `)
    .join("");
}

function renderSuggestions() {
  const rules = pendingSuggestedRules();
  document.getElementById("suggestionCount").textContent = String(rules.length);
  document.getElementById("suggestionList").innerHTML = rules.slice(0, 4).map((rule) => `
    <article class="suggestionCard">
      <strong>${escapeHtml(rule.name || rule.id)}</strong>
      <p>${escapeHtml(conditionText(rule.conditions || []))}</p>
      <div class="suggestionMetric">
        <span>P ${pct(rule.metrics?.precision)}</span>
        <span>R ${pct(rule.metrics?.recall)}</span>
        <span>Support ${fmt(rule.metrics?.support_count)}</span>
      </div>
    </article>
  `).join("") || `<div class="emptyState">暂无建议规则</div>`;
}

function renderEventTable() {
  const query = (document.getElementById("eventTableSearch")?.value || "").trim().toLowerCase();
  const level = document.getElementById("eventTableLevel")?.value || "all";
  const rows = filteredReports(query, level);
  document.getElementById("eventTableBody").innerHTML = rows.map((report) => {
    const risk = state.riskById.get(report.candidate_event_id) || {};
    const style = levelStyle(report.risk_level);
    return `
      <tr>
        <td class="mono">${escapeHtml(report.candidate_event_id || "")}</td>
        <td>${escapeHtml(report.user_id || "")}</td>
        <td><span class="riskLevel" style="--level-color:${style.color};--level-bg:${style.bg}">${escapeHtml(report.risk_level)}</span></td>
        <td><strong>${num(report.final_risk_score, 1)}</strong></td>
        <td>${escapeHtml((report.matched_scene_list || []).slice(0, 3).join(" / "))}</td>
        <td>${pct(risk.coverage)}</td>
        <td>${escapeHtml(report.disposition?.action || "")}</td>
      </tr>
    `;
  }).join("");
}

function renderRules() {
  const groups = [
    ["场景规则", state.activeRules.scene_rules || []],
    ["高危阈值", state.activeRules.high_risk_thresholds || []],
    ["弱规则", state.activeRules.weak_rules || []],
  ];
  document.getElementById("activeRuleCount").textContent = String(ruleCount(state.activeRules));
  document.getElementById("activeRuleGroups").innerHTML = groups.map(([title, rules]) => `
    <div class="ruleGroup">
      <h3>${escapeHtml(title)} · ${rules.length}</h3>
      <ul>
        ${rules.slice(0, 8).map((rule) => `
          <li>
            <div>
              <strong>${escapeHtml(rule.name || rule.field || rule.id || "规则")}</strong>
              <div class="conditionText">${escapeHtml(conditionText(rule.conditions || [rule]))}</div>
            </div>
            <span class="statusPill">${escapeHtml(rule.status || "active")}</span>
          </li>
        `).join("")}
      </ul>
    </div>
  `).join("");

  const suggested = pendingSuggestedRules();
  document.getElementById("pendingRuleCount").textContent = String(suggested.length);
  document.getElementById("suggestedRuleTable").innerHTML = `
    ${state.ruleActionMessage ? `<div class="ruleActionNotice">${escapeHtml(state.ruleActionMessage)}</div>` : ""}
    ${suggested.map((rule) => `
    <article class="suggestedRule" data-rule-id="${escapeAttr(rule.id)}">
      <div>
        <h3>${escapeHtml(rule.name || rule.id)}</h3>
        <p>${escapeHtml(conditionText(rule.conditions || []))}</p>
        <div class="suggestionMetric">
          <span>Precision ${pct(rule.metrics?.precision)}</span>
          <span>Recall ${pct(rule.metrics?.recall)}</span>
          <span>F0.5 ${pct(rule.metrics?.f05)}</span>
          <span>Support ${fmt(rule.metrics?.support_count)}</span>
        </div>
      </div>
      <div class="suggestedRuleSide">
        <span class="statusPill">待确认</span>
        <div class="ruleActionRow">
          <button class="miniActionButton approve" data-rule-action="approve" data-rule-id="${escapeAttr(rule.id)}" ${state.ruleActionBusyId === rule.id ? "disabled" : ""}>加入规则</button>
          <button class="miniActionButton reject" data-rule-action="reject" data-rule-id="${escapeAttr(rule.id)}" ${state.ruleActionBusyId === rule.id ? "disabled" : ""}>弃用</button>
        </div>
      </div>
    </article>
  `).join("") || `<div class="emptyState">暂无建议规则</div>`}
  `;

  document.getElementById("suggestedRuleTable").querySelectorAll("[data-rule-action]").forEach((button) => {
    button.addEventListener("click", () => {
      reviewSuggestedRule(button.dataset.ruleId, button.dataset.ruleAction);
    });
  });
}

function renderAudit() {
  const feedback = state.feedback.length ? state.feedback : state.reports.map((report) => ({
    candidate_event_id: report.candidate_event_id,
    user_id: report.user_id,
    risk_level: report.risk_level,
    final_risk_score: report.final_risk_score,
    need_human_review: true,
  }));
  document.getElementById("feedbackList").innerHTML = feedback.slice(0, 80).map((item) => {
    const style = levelStyle(item.risk_level);
    return `
      <article class="auditItem">
        <div>
          <strong>${escapeHtml(item.candidate_event_id || "")}</strong>
          <span>${escapeHtml(item.user_id || "")} · 评分 ${num(item.final_risk_score, 1)}</span>
        </div>
        <span class="riskLevel" style="--level-color:${style.color};--level-bg:${style.bg}">${escapeHtml(item.risk_level || "待复核")}</span>
      </article>
    `;
  }).join("");

  const lines = state.learningLog
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-12)
    .map((line) => {
      try {
        const item = JSON.parse(line);
        return `<div class="logLine">${escapeHtml(item.time || "")}<br/>run=${escapeHtml(item.run_id || "")}<br/>suggested=${fmt(item.suggested_rule_count)} · labeled=${fmt(item.labeled_sample_count)}</div>`;
      } catch {
        return `<div class="logLine">${escapeHtml(line)}</div>`;
      }
    })
    .join("");
  document.getElementById("learningLog").innerHTML = lines || `<div class="emptyState">暂无学习日志</div>`;
}

function renderAgentView() {
  const caseList = document.getElementById("agentCaseList");
  const caseCount = document.getElementById("agentCaseCount");
  const title = document.getElementById("agentTraceTitle");
  const body = document.getElementById("agentTraceBody");
  if (!caseList || !caseCount || !title || !body) return;

  const reports = state.reports.slice(0, 80);
  caseCount.textContent = `${reports.length} 个风险会话`;
  if (!reports.length) {
    caseList.innerHTML = `<div class="emptyState">暂无智能体轨迹</div>`;
    title.textContent = "暂无风险会话";
    body.innerHTML = `<div class="emptyState">启动实时流或切换到有风险的复盘模式</div>`;
    return;
  }

  if (!reports.some((report) => report.candidate_event_id === state.selectedId)) {
    state.selectedId = reports[0].candidate_event_id;
  }

  caseList.innerHTML = reports.map((report) => {
    const style = levelStyle(report.risk_level);
    return `
      <button class="agentCaseItem ${report.candidate_event_id === state.selectedId ? "active" : ""}"
        data-id="${escapeAttr(report.candidate_event_id)}"
        style="--level-color:${style.color};--level-bg:${style.bg}">
        <strong>${escapeHtml(report.user_id)} · ${escapeHtml(report.candidate_event_id || "")}</strong>
        <span>${escapeHtml(report.risk_level)} · ${num(report.final_risk_score, 1)}</span>
      </button>
    `;
  }).join("");

  caseList.querySelectorAll(".agentCaseItem").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.id;
      renderAgentView();
      renderRiskList();
      renderDetail();
    });
  });

  const report = state.reports.find((item) => item.candidate_event_id === state.selectedId) || reports[0];
  const risk = state.riskById.get(report.candidate_event_id) || {};
  const cards = buildAgentCards(report, risk);
  title.textContent = `${report.user_id} · ${report.candidate_event_id}`;
  body.innerHTML = `
    <div class="agentTraceSummary">
      <div>
        <span class="reportSource">${report.llm_generated ? "LLM 生成报告" : "本地解释报告"}</span>
        <h3>${escapeHtml(report.risk_level)} · ${num(report.final_risk_score, 1)}</h3>
        <p>${escapeHtml(report.evidence_summary || report.risk_explanation || "")}</p>
      </div>
      <div class="agentTraceScore">${num(report.final_risk_score, 1)}</div>
    </div>
    <div class="agentCardsGrid">
      ${renderAgentCards(cards)}
    </div>
  `;
}

function buildAgentCards(report = {}, risk = {}) {
  const trace = report.agent_trace || risk.agent_trace || {};
  const profile = trace.profile_agent || risk.profile_result || {};
  const business = trace.business_agent || risk.business_result || {};
  const chain = trace.chain_agent || risk.chain_result || {};
  const scoring = trace.scoring_agent || {};
  const disposition = trace.disposition_agent || {};
  const scenes = report.matched_scene_list || risk.matched_scene_list || [];
  const drivers = scoring.top_drivers || risk.top_drivers || [];
  const behaviorChain = report.behavior_chain || risk.behavior_chain || [];
  const profileFlags = profile.profile_abnormal_flags || [];
  const businessProblems = business.business_problems || [];
  const chainFlags = chain.chain_flags || [];

  return [
    {
      ...agentDefs[0],
      status: "done",
      summary: scenes.length ? `命中 ${scenes.length} 条场景规则` : "通过弱规则/阈值进入候选池",
      chips: [
        `候选 ID ${report.candidate_event_id || risk.candidate_event_id || "-"}`,
        ...(scenes.slice(0, 3)),
      ],
      detail: `规则入口层把同一用户会话聚合后判断是否进入候选池，当前规则强度为 ${risk.rule_strength || report.rule_strength || "strong"}。`,
    },
    {
      ...agentDefs[1],
      status: "done",
      summary: [...profileFlags, ...businessProblems, ...chainFlags][0] || "完成画像、业务和链路分析",
      chips: [
        ...profileFlags.slice(0, 2),
        ...businessProblems.slice(0, 2),
        ...chainFlags.slice(0, 2),
      ],
      detail: behaviorChain.length
        ? `抽取行为链：${behaviorChain.join(" -> ")}`
        : "综合岗位权限、业务编号、设备和时段等上下文判断行为合理性。",
    },
    {
      ...agentDefs[2],
      status: "done",
      summary: `${report.risk_level || risk.risk_level || "风险"}，最终评分 ${num(report.final_risk_score ?? risk.final_risk_score, 1)}`,
      chips: drivers.slice(0, 4).map((item) => `${item.indicator} ${num(item.contribution, 1)}`),
      detail: `覆盖度 ${pct(risk.coverage)}，基础分 ${num(risk.base_risk_score, 1)}，按 C2/C3/C4/C5 多维指标加权。`,
    },
    {
      ...agentDefs[3],
      status: "done",
      summary: report.disposition?.action || "生成研判解释和处置建议",
      chips: [
        report.llm_generated ? "LLM 生成" : "本地解释",
        ...(report.disposition?.suggestions || []).slice(0, 3),
      ],
      detail: disposition.explanation || report.risk_explanation || "汇总证据、风险原因和处置动作，形成可复核报告。",
    },
  ];
}

function renderAgentCards(cards, compact = false) {
  return cards.map((card) => `
    <article class="agentCard ${compact ? "compact" : ""} ${card.status || "done"}">
      <div class="agentCardTop">
        <div class="agentAvatar">${escapeHtml(card.short)}</div>
        <div>
          <strong>${escapeHtml(card.title)}</strong>
          <span>${escapeHtml(card.role)}</span>
        </div>
      </div>
      <p>${escapeHtml(card.summary || "")}</p>
      <div class="agentChipRow">
        ${(card.chips || []).filter(Boolean).slice(0, compact ? 4 : 8).map((chip) => `<span>${escapeHtml(chip)}</span>`).join("")}
      </div>
      ${compact ? "" : `<small>${escapeHtml(card.detail || "")}</small>`}
    </article>
  `).join("");
}

function filteredReports(query, level) {
  return state.reports.filter((report) => {
    const text = [
      report.user_id,
      report.candidate_event_id,
      report.risk_level,
      report.evidence_summary,
      ...(report.matched_scene_list || []),
    ].join(" ").toLowerCase();
    return (!query || text.includes(query)) && (level === "all" || report.risk_level === level);
  });
}

function levelStyle(level = "") {
  if (level.includes("极高")) return { color: "#dc2626", bg: "#fee2e2" };
  if (level.includes("高")) return { color: "#f97316", bg: "#ffedd5" };
  if (level.includes("中")) return { color: "#2563eb", bg: "#dbeafe" };
  return { color: "#059669", bg: "#d1fae5" };
}

function conditionText(conditions) {
  return conditions.map((item) => `${item.field || "field"} ${item.op || ""} ${item.value ?? ""}`).join(" AND ");
}

function sceneName(name) {
  const map = {
    normal: "正常会话",
    test_env_unmasked_keep: "测试环境未脱敏",
    screenshot_send_copy: "截图外发拷贝",
    cross_dept_query_export: "跨部门查询导出",
    offhour_query_export_delete: "非工作时段导出清痕",
    new_device_export: "新设备导出",
    usb_copy_delete: "USB 拷贝清痕",
  };
  return map[name] || name;
}

function ruleCount(ruleSet) {
  return (ruleSet.scene_rules?.length || 0) + (ruleSet.high_risk_thresholds?.length || 0) + (ruleSet.weak_rules?.length || 0);
}

function countBy(items, key) {
  return items.reduce((acc, item) => {
    const value = item[key] || "未知";
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
}

function demoModeFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  if (demoModeOptions[mode]) return mode;

  const legacyDataset = params.get("dataset");
  const legacyMode = Object.entries(demoModeOptions).find(([, item]) => item.datasetId === legacyDataset && item.targetView !== "live");
  return legacyMode?.[0] || defaultDemoMode;
}

function datasetIdForDemoMode(mode) {
  const datasetId = (demoModeOptions[mode] || demoModeOptions[defaultDemoMode]).datasetId;
  return datasetOptions[datasetId] ? datasetId : defaultDatasetId;
}

function normalizeMeta(meta, evaluation) {
  return {
    ...meta,
    session_count: meta.session_count ?? evaluation.total_sessions ?? 0,
    anomaly_session_count: meta.anomaly_session_count ?? evaluation.actual_anomaly_sessions ?? 0,
    event_count: meta.event_count ?? 0,
    scene_counts: meta.scene_counts || {},
  };
}

function updateLiveStatus(label, active) {
  const node = document.getElementById("liveStatus");
  if (!node) return;
  node.textContent = label;
  node.classList.toggle("active", Boolean(active));
  updateLiveStartLabel();
}

function updateLiveStartLabel() {
  const node = document.getElementById("liveStart");
  if (!node) return;
  if (state.live.connected) {
    node.textContent = "运行中";
    node.disabled = true;
    return;
  }
  node.textContent = state.live.paused ? "继续" : "启动";
  node.disabled = false;
}

function safeParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function setToday() {
  const now = new Date();
  document.getElementById("todayText").textContent = now.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function fmt(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : "0";
}

function pct(value) {
  const number = Number(value || 0);
  return `${Math.round(number * 1000) / 10}%`;
}

function num(value, digits = 0) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toFixed(digits) : "0";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
