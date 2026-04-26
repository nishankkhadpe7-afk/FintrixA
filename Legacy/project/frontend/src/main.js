import "./index.css";
import { buildInitialInput, simulatorDomains, simulatorPresets } from "./utils/simulatorConfig.js";
import { sampleCirculars, sampleDashboardStats, sampleRules } from "./utils/sampleData.js";

const root = document.getElementById("app");

const state = {
  circulars: [],
  rules: [],
  stats: null,
  loading: true,
  error: "",
  route: getRoute(),
  evaluationInput: buildInitialInput("lending"),
  evaluationResult: null,
  evaluating: false,
};

function getRoute() {
  const hash = window.location.hash.replace(/^#/, "");
  return hash || "/";
}

function navigate(route) {
  window.location.hash = route;
}

function setRoute(route) {
  state.route = route;
  render();
}

function formatNumber(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "0";
  return new Intl.NumberFormat("en-IN").format(value);
}

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function apiGet(path) {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error(`GET ${path} failed with ${response.status}`);
  return response.json();
}

async function apiPost(path, body, params = "") {
  const response = await fetch(`/api${path}${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `POST ${path} failed with ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function normalizeAction(action) {
  if (["ALLOW", "DENY", "FLAG"].includes(action)) return action;
  return "FLAG";
}

function normalizeOperator(operator) {
  switch (operator) {
    case "==":
      return "eq";
    case "!=":
      return "neq";
    case ">":
      return "gt";
    case ">=":
      return "gte";
    case "<":
      return "lt";
    case "<=":
      return "lte";
    default:
      return operator || "eq";
  }
}

function toRule(rule) {
  const ruleId = String(rule.rule_id ?? rule.id ?? "unknown-rule");
  const action = normalizeAction(rule.action);
  const conditions = Array.isArray(rule.conditions) ? rule.conditions : [];
  return {
    id: ruleId,
    title: typeof rule.title === "string" && rule.title.trim() ? rule.title : ruleId,
    description:
      typeof rule.description === "string" && rule.description.trim()
        ? rule.description
        : `Matched ${String(rule.type ?? "regulatory")} rule`,
    action,
    source_section: typeof rule.source_section === "string" ? rule.source_section : String(rule.type ?? "Unknown"),
    confidence_score: typeof rule.confidence_score === "number" ? rule.confidence_score : 1,
    full_json: rule,
    conditions: conditions.map((condition, index) => ({
      field: String(condition.field ?? `condition_${index + 1}`),
      operator: normalizeOperator(condition.operator),
      value: condition.value ?? null,
    })),
  };
}

function flattenTraceNode(node, ruleId, ruleTitle, results) {
  if (node?.type === "atomic") {
    results.push({
      field: String(node.field ?? "unknown"),
      expected: String(node.expected ?? ""),
      actual: node.actual,
      result: node.result ? "PASS" : "FAIL",
      rule_id: ruleId,
      rule_title: ruleTitle,
    });
    return;
  }
  (node?.children || []).forEach((child) => flattenTraceNode(child, ruleId, ruleTitle, results));
}

function flattenBackendTrace(traceItems) {
  if (!Array.isArray(traceItems)) return [];
  const flattened = [];
  traceItems.forEach((item) => {
    const ruleId = String(item.rule_id ?? "unknown-rule");
    const ruleTitle = typeof item.rule_title === "string" ? item.rule_title : ruleId;
    if (item.trace) {
      flattenTraceNode(item.trace, ruleId, ruleTitle, flattened);
    }
  });
  return flattened;
}

function determineEvaluationResult(matchingRules) {
  if (matchingRules.some((rule) => rule.action === "DENY")) return "DENY";
  if (matchingRules.some((rule) => rule.action === "FLAG")) return "FLAG";
  return "ALLOW";
}

async function evaluateInput(input) {
  const requestBody = { inputs: [input] };
  let response;
  try {
    response = await apiPost("/simulate", requestBody, "?debug=true");
  } catch (error) {
    if (!String(error.message || "").includes("404")) throw error;
    response = await apiPost("/rules/simulate", requestBody, "?debug=true");
  }

  if (!response.results || response.results.length === 0) {
    throw new Error("No results returned from backend");
  }

  const backendResult = response.results[0];
  const matchingRules = Array.isArray(backendResult.matched_rules)
    ? backendResult.matched_rules.filter(Boolean).map((rule) => toRule(rule))
    : [];

  return {
    id: response.request_id || `req-${Date.now()}`,
    input: backendResult.input,
    result: determineEvaluationResult(matchingRules),
    matching_rules: matchingRules,
    failed_rules: [],
    debug_trace: flattenBackendTrace(backendResult.trace),
    evaluated_at: new Date().toISOString(),
  };
}

async function loadData() {
  state.loading = true;
  state.error = "";
  render();

  try {
    const [circulars, rules, stats] = await Promise.all([
      apiGet("/circulars"),
      apiGet("/rules"),
      apiGet("/stats"),
    ]);
    state.circulars = Array.isArray(circulars) ? circulars : [];
    state.rules = Array.isArray(rules) ? rules : [];
    state.stats = stats || null;
  } catch (error) {
    state.circulars = sampleCirculars;
    state.rules = sampleRules;
    state.stats = sampleDashboardStats;
    state.error = "Live API data could not be loaded. Showing sample data instead.";
  } finally {
    state.loading = false;
    render();
  }
}

function getCurrentDomainConfig() {
  return simulatorDomains.find((domain) => domain.id === state.evaluationInput.domain) || simulatorDomains[0];
}

function getPresetsForCurrentDomain() {
  return simulatorPresets.filter((preset) => preset.domain === state.evaluationInput.domain);
}

function setDomain(domainId) {
  state.evaluationInput = buildInitialInput(domainId);
  state.evaluationResult = null;
  render();
}

function setPreset(presetId) {
  const preset = simulatorPresets.find((item) => item.id === presetId);
  if (!preset) return;
  state.evaluationInput = { ...preset.values };
  state.evaluationResult = null;
  render();
}

function updateInputField(key, value, type) {
  state.evaluationInput = {
    ...state.evaluationInput,
    [key]: type === "number" ? Number(value || 0) : value,
  };
}

async function onEvaluateSubmit(event) {
  event.preventDefault();
  state.evaluating = true;
  state.error = "";
  render();
  try {
    state.evaluationResult = await evaluateInput(state.evaluationInput);
  } catch (error) {
    state.error = error.message || "Evaluation failed";
  } finally {
    state.evaluating = false;
    render();
  }
}

function renderSidebar() {
  const navItems = [
    { path: "/", label: "Dashboard" },
    { path: "/circulars", label: "Circulars" },
    { path: "/rules", label: "Rules" },
    { path: "/evaluate", label: "Evaluate" },
    { path: "/traceability", label: "Traceability" },
  ];

  return `
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-badge">R</div>
        <div>
          <h1>RegTech</h1>
          <p>Rule Engine Dashboard</p>
        </div>
      </div>
      <nav class="nav">
        ${navItems
          .map(
            (item) => `
          <a href="#${item.path}" class="nav-link ${state.route === item.path ? "active" : ""}">
            <span>${escapeHtml(item.label)}</span>
          </a>`
          )
          .join("")}
      </nav>
      <div class="sidebar-footer">
        <div>RBI Regulatory Rule Engine</div>
        <div>Version 1.0.0</div>
      </div>
    </aside>
  `;
}

function renderDashboard() {
  const stats = state.stats || sampleDashboardStats;
  const recent = Array.isArray(stats.recent_ingestions) ? stats.recent_ingestions : [];
  return `
    <section>
      <div class="page-header">
        <h2>Dashboard</h2>
        <p>Overview of regulatory ingestion and rule extraction</p>
      </div>
      <div class="grid stats">
        <div class="stat-card"><div class="stat-label">Total Circulars</div><div class="stat-value">${formatNumber(stats.total_circulars || state.circulars.length)}</div></div>
        <div class="stat-card"><div class="stat-label">Total Rules</div><div class="stat-value">${formatNumber(stats.total_rules || state.rules.length)}</div></div>
        <div class="stat-card"><div class="stat-label">Success Rate</div><div class="stat-value">${Math.round((stats.success_rate || 0) * 100)}%</div></div>
        <div class="stat-card"><div class="stat-label">Failure Rate</div><div class="stat-value">${Math.round((stats.failure_rate || 0) * 100)}%</div></div>
      </div>
      <div class="panel" style="margin-top:18px;">
        <div class="panel-head"><h3>Recent Ingestion Activity</h3></div>
        <div class="list">
          ${recent.length
            ? recent
                .map(
                  (item) => `
              <div class="list-item">
                <div class="row">
                  <div>
                    <div><strong>${escapeHtml(item.title)}</strong></div>
                    <div class="meta">${formatDate(item.ingested_at)}</div>
                  </div>
                  <span class="pill primary">${formatNumber(item.rules_extracted || 0)} rules extracted</span>
                </div>
              </div>`
                )
                .join("")
            : `<div class="empty">No recent ingestions yet.</div>`}
        </div>
      </div>
    </section>
  `;
}

function renderCirculars() {
  return `
    <section>
      <div class="page-header">
        <h2>Circulars</h2>
        <p>Browse ingested regulator documents and source links.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Available Circulars</h3></div>
        <div class="list">
          ${state.circulars.length
            ? state.circulars
                .map(
                  (item) => `
              <div class="list-item">
                <div class="row">
                  <div>
                    <div><strong>${escapeHtml(item.title || item.id)}</strong></div>
                    <div class="meta">${escapeHtml(item.source || "Unknown source")} • ${formatDate(item.published_date || item.date || item.ingested_at)}</div>
                    ${item.url || item.source_url ? `<div class="meta"><a class="pill primary" href="${escapeHtml(item.url || item.source_url)}" target="_blank" rel="noreferrer">Open source</a></div>` : ""}
                  </div>
                  <span class="pill ${item.status === "failed" ? "danger" : "success"}">${escapeHtml(item.status || "stored")}</span>
                </div>
              </div>`
                )
                .join("")
            : `<div class="empty">No circulars available.</div>`}
        </div>
      </div>
    </section>
  `;
}

function renderRules() {
  return `
    <section>
      <div class="page-header">
        <h2>Rules</h2>
        <p>Explore the executable rules currently available to the simulator.</p>
      </div>
      <div class="grid">
        ${state.rules.length
          ? state.rules
              .map(
                (rule) => `
            <article class="rule-card">
              <div class="row">
                <h4>${escapeHtml(rule.title || rule.rule_id || rule.id || "Untitled rule")}</h4>
                <span class="pill ${String(rule.action || "").toUpperCase() === "DENY" ? "danger" : String(rule.action || "").toUpperCase() === "FLAG" ? "warn" : "success"}">${escapeHtml(String(rule.action || "FLAG").toUpperCase())}</span>
              </div>
              <p class="meta">${escapeHtml(rule.description || "No description available.")}</p>
              <div class="meta">Section: ${escapeHtml(rule.source_section || rule.type || "Unknown")}</div>
            </article>`
              )
              .join("")
          : `<div class="panel"><div class="empty">No rules available yet.</div></div>`}
      </div>
    </section>
  `;
}

function renderEvaluation() {
  const domain = getCurrentDomainConfig();
  const presets = getPresetsForCurrentDomain();
  const result = state.evaluationResult;

  return `
    <section>
      <div class="page-header">
        <h2>Evaluation Panel</h2>
        <p>Explore scenarios against regulatory rules with traceable outcomes.</p>
      </div>
      <div class="banner">
        Choose a domain, load a preset or build your own scenario, and the system will evaluate the submission against active regulatory rules.
      </div>
      <div class="panel">
        <div class="panel-head">
          <h3>Scenario Builder</h3>
          <p>${escapeHtml(domain.hero)}</p>
        </div>
        <div class="panel-body">
          <div class="card-grid">
            ${simulatorDomains
              .map(
                (item) => `
              <button class="domain-card ${item.id === domain.id ? "active" : ""}" type="button" data-action="switch-domain" data-domain="${item.id}">
                <h4>${escapeHtml(item.label)}</h4>
                <div class="meta">${escapeHtml(item.description)}</div>
              </button>`
              )
              .join("")}
          </div>
          <div class="form-grid" style="margin-top:18px;">
            <div class="field">
              <label>Regulator</label>
              <select data-field="regulator">
                ${domain.regulators.map((option) => `<option value="${escapeHtml(option)}" ${state.evaluationInput.regulator === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
              </select>
            </div>
            <div class="field">
              <label>Jurisdiction</label>
              <select data-field="jurisdiction">
                ${domain.jurisdictions.map((option) => `<option value="${escapeHtml(option)}" ${state.evaluationInput.jurisdiction === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
              </select>
            </div>
          </div>
          <div style="margin-top:18px;">
            <div class="meta" style="margin-bottom:8px;">Preset Scenarios</div>
            <div class="card-grid">
              ${presets
                .map(
                  (preset) => `
                <button class="preset-card" type="button" data-action="apply-preset" data-preset="${preset.id}">
                  <h4>${escapeHtml(preset.title)}</h4>
                  <div class="meta">${escapeHtml(preset.description)}</div>
                </button>`
                )
                .join("")}
            </div>
          </div>
          <form id="evaluation-form" style="margin-top:18px;">
            <div class="form-grid">
              ${domain.fields
                .map((field) => renderField(field, state.evaluationInput[field.key]))
                .join("")}
            </div>
            <div class="actions">
              <button class="btn secondary" type="button" data-action="clear-form">Clear</button>
              <button class="btn primary" type="submit">${state.evaluating ? "Evaluating..." : "Evaluate Application"}</button>
            </div>
          </form>
        </div>
      </div>
      ${result ? renderEvaluationResult(result) : ""}
    </section>
  `;
}

function renderField(field, currentValue) {
  if (field.type === "select") {
    return `
      <div class="field">
        <label>${escapeHtml(field.label)}</label>
        <select data-field="${escapeHtml(field.key)}" data-type="select">
          ${(field.options || [])
            .map(
              (option) => `<option value="${escapeHtml(option.value)}" ${String(currentValue) === String(option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`
            )
            .join("")}
        </select>
      </div>
    `;
  }

  return `
    <div class="field">
      <label>${escapeHtml(field.label)}</label>
      <input data-field="${escapeHtml(field.key)}" data-type="${escapeHtml(field.type)}" type="${escapeHtml(field.type)}" value="${escapeHtml(currentValue ?? "")}" placeholder="${escapeHtml(field.placeholder || "")}" />
    </div>
  `;
}

function renderEvaluationResult(result) {
  const matchRows = result.matching_rules
    .map(
      (rule) => `
      <article class="rule-card">
        <div class="row">
          <h4>${escapeHtml(rule.title)}</h4>
          <span class="pill ${rule.action === "DENY" ? "danger" : rule.action === "FLAG" ? "warn" : "success"}">${escapeHtml(rule.action)}</span>
        </div>
        <p class="meta">${escapeHtml(rule.description)}</p>
      </article>`
    )
    .join("");

  const traceRows = result.debug_trace
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.rule_title)}</td>
          <td>${escapeHtml(item.field)}</td>
          <td class="mono">${escapeHtml(item.expected)}</td>
          <td class="mono">${escapeHtml(item.actual)}</td>
          <td><span class="pill ${item.result === "PASS" ? "success" : "danger"}">${escapeHtml(item.result)}</span></td>
        </tr>`
    )
    .join("");

  return `
    <div class="panel" style="margin-top:18px;">
      <div class="panel-head"><h3>Evaluation Result</h3></div>
      <div class="panel-body">
        <div class="result-box">
          <div class="result-badge ${escapeHtml(result.result)}">${escapeHtml(result.result)}</div>
          <div class="meta">${formatDate(result.evaluated_at)}</div>
        </div>
      </div>
    </div>
    <div class="panel" style="margin-top:18px;">
      <div class="panel-head"><h3>Reasoning</h3></div>
      <div class="panel-body">
        <div class="card-grid">
          <div class="stat-card"><div class="stat-label">Matched Rules</div><div class="stat-value">${formatNumber(result.matching_rules.length)}</div></div>
          <div class="stat-card"><div class="stat-label">Trace Checks</div><div class="stat-value">${formatNumber(result.debug_trace.length)}</div></div>
        </div>
        <div class="grid" style="margin-top:18px;">
          ${matchRows || `<div class="empty">No matching rules returned.</div>`}
        </div>
      </div>
    </div>
    <div class="panel" style="margin-top:18px;">
      <div class="panel-head"><h3>Traceability</h3></div>
      <div class="panel-body">
        <div class="table-wrap">
          <table>
            <thead><tr><th>Rule</th><th>Field</th><th>Expected</th><th>Actual</th><th>Result</th></tr></thead>
            <tbody>
              ${traceRows || `<tr><td colspan="5" class="empty">No trace rows available.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderTraceability() {
  const result = state.evaluationResult;
  return `
    <section>
      <div class="page-header">
        <h2>Traceability</h2>
        <p>Inspect the latest evaluation request, matched rules, and atomic trace checks.</p>
      </div>
      ${
        !result
          ? `<div class="panel"><div class="empty">Run an evaluation first to see traceability details here.</div></div>`
          : `
            <div class="panel">
              <div class="panel-head"><h3>Latest Request</h3></div>
              <div class="panel-body"><pre class="mono">${escapeHtml(JSON.stringify(result.input, null, 2))}</pre></div>
            </div>
            <div class="panel" style="margin-top:18px;">
              <div class="panel-head"><h3>Rule Trace</h3></div>
              <div class="panel-body"><pre class="mono">${escapeHtml(JSON.stringify(result.debug_trace, null, 2))}</pre></div>
            </div>`
      }
    </section>
  `;
}

function renderPage() {
  switch (state.route) {
    case "/circulars":
      return renderCirculars();
    case "/rules":
      return renderRules();
    case "/evaluate":
      return renderEvaluation();
    case "/traceability":
      return renderTraceability();
    default:
      return renderDashboard();
  }
}

function render() {
  root.innerHTML = `
    <div class="layout">
      ${renderSidebar()}
      <main class="main">
        ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ""}
        ${state.loading ? `<div class="loading">Loading data...</div>` : renderPage()}
      </main>
    </div>
  `;

  bindEvents();
}

function bindEvents() {
  document.querySelectorAll("[data-action='switch-domain']").forEach((button) => {
    button.addEventListener("click", () => setDomain(button.dataset.domain));
  });

  document.querySelectorAll("[data-action='apply-preset']").forEach((button) => {
    button.addEventListener("click", () => setPreset(button.dataset.preset));
  });

  document.querySelectorAll("[data-field]").forEach((element) => {
    element.addEventListener("change", () => updateInputField(element.dataset.field, element.value, element.dataset.type));
    if (element.tagName === "INPUT") {
      element.addEventListener("input", () => updateInputField(element.dataset.field, element.value, element.dataset.type));
    }
  });

  document.querySelectorAll("[data-action='clear-form']").forEach((button) => {
    button.addEventListener("click", () => {
      state.evaluationInput = buildInitialInput(state.evaluationInput.domain);
      state.evaluationResult = null;
      render();
    });
  });

  const form = document.getElementById("evaluation-form");
  if (form) {
    form.addEventListener("submit", onEvaluateSubmit);
  }
}

window.addEventListener("hashchange", () => setRoute(getRoute()));

if (!window.location.hash) {
  navigate("/");
} else {
  setRoute(getRoute());
}

loadData();
