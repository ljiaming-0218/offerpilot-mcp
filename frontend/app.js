const state = {
  activeView: "dashboard",
  jobs: [],
  skills: [],
  tools: [],
  logs: [],
  traces: [],
  crawlRecords: [],
  profile: null,
  currentUser: null,
  profiles: [],
  authToken: localStorage.getItem("offerpilot_token") || "",
  authMode: "login",
  selectedJob: null,
  selectedTrace: null,
  selectedLog: null,
  lastAgentResult: null,
  lastCrawlResult: null,
};

const viewTitles = {
  dashboard: "概览",
  jobs: "岗位库",
  crawler: "岗位采集",
  skills: "运行记录",
  agent: "MCP Console",
  match: "匹配中心",
  interview: "面试训练",
  profile: "我的画像",
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  let response;
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(state.authToken ? { Authorization: `Bearer ${state.authToken}` } : {}),
    ...(options.headers || {}),
  };
  try {
    response = await fetch(path, {
      ...options,
      headers,
    });
  } catch (error) {
    throw new Error(`网络异常：${error.message}`);
  }

  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error("后端返回不是合法 JSON");
    }
  }

  if (!response.ok) {
    const message = formatApiError(data, response.status);
    const reason = data?.reason || data?.error_message || data?.error;
    throw new Error(reason ? `${message}；原因：${reason}` : message);
  }

  return data;
}

function formatApiError(data, status) {
  if (!data) return `请求失败：HTTP ${status}`;
  if (typeof data.message === "string") return data.message;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.join(".") : "field";
        return `${field}: ${item.msg}`;
      })
      .join("；");
  }
  if (typeof data.error === "string") return data.error;
  return `请求失败：HTTP ${status}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatValue(value, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  return value;
}

function formatDate(value) {
  if (!value) return "--";
  return String(value).replace("T", " ").slice(0, 19);
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function splitTextList(value) {
  return value
    .split(/[\n,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinTextList(values = []) {
  return values.join("\n");
}

function setBusy(element, isBusy, busyText, idleText) {
  element.disabled = isBusy;
  element.textContent = isBusy ? busyText : idleText;
}

function setView(viewName) {
  if (["agent", "skills"].includes(viewName) && state.currentUser?.role !== "admin") {
    showToast("普通用户不能访问开发者工具");
    viewName = "dashboard";
  }
  state.activeView = viewName;
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("is-active"));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("is-active"));
  $(`view-${viewName}`)?.classList.add("is-active");
  document.querySelector(`[data-view="${viewName}"]`)?.classList.add("is-active");
  $("view-title").textContent = viewTitles[viewName] || "概览";
}

function setAuthMode(mode) {
  state.authMode = mode;
  $("auth-login-tab").classList.toggle("is-active", mode === "login");
  $("auth-register-tab").classList.toggle("is-active", mode === "register");
  $("auth-submit").textContent = mode === "login" ? "登录" : "注册";
  $("auth-display-name-field").classList.toggle("is-hidden", mode === "login");
  $("auth-password").autocomplete = mode === "login" ? "current-password" : "new-password";
}

function applyAuthState(user) {
  state.currentUser = user;
  $("auth-view").classList.add("is-hidden");
  $("app-shell").classList.remove("is-hidden");
  $("current-user").textContent = `${user.display_name || user.username} · ${user.role}`;
  if (!$("profile-user-id").value.trim()) {
    $("profile-user-id").value = user.username;
  }
  document.body.dataset.role = user.role;
  document.querySelectorAll(".role-admin").forEach((element) => {
    element.classList.toggle("is-hidden", user.role !== "admin");
  });
  if (user.role !== "admin" && ["agent", "skills"].includes(state.activeView)) {
    setView("dashboard");
  }
}

function clearAuthState() {
  state.currentUser = null;
  state.authToken = "";
  localStorage.removeItem("offerpilot_token");
  document.body.dataset.role = "";
  $("app-shell").classList.add("is-hidden");
  $("auth-view").classList.remove("is-hidden");
}

async function submitAuth(event) {
  event.preventDefault();
  const username = $("auth-username").value.trim();
  const password = $("auth-password").value.trim();
  const displayName = $("auth-display-name").value.trim();

  if (!username || !password) {
    showToast("请输入用户名和密码");
    return;
  }

  const button = $("auth-submit");
  setBusy(button, true, "处理中", state.authMode === "login" ? "登录" : "注册");

  try {
    const body = state.authMode === "login"
      ? { username, password }
      : { username, password, display_name: displayName || null };
    const result = await api(`/auth/${state.authMode}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.authToken = result.token;
    localStorage.setItem("offerpilot_token", result.token);
    applyAuthState(result.user);
    await loadAll();
    showToast(state.authMode === "login" ? "登录成功" : "注册成功");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false, "处理中", state.authMode === "login" ? "登录" : "注册");
  }
}

async function restoreAuth() {
  if (!state.authToken) {
    setAuthMode("login");
    clearAuthState();
    return;
  }

  try {
    const user = await api("/auth/me");
    applyAuthState(user);
    await loadAll();
  } catch (error) {
    clearAuthState();
    showToast(error.message);
  }
}

function renderEmpty(text) {
  return `<div class="empty">${escapeHtml(text)}</div>`;
}

function statusPill(text, type = "neutral") {
  return `<span class="status-pill ${type}">${escapeHtml(text)}</span>`;
}

async function loadHealth() {
  const health = await api("/health");
  $("health-status").textContent = health.status || "--";
  $("db-status").textContent = health.database || "--";
  $("llm-status").textContent = health.llm_configured ? "已配置" : "未配置";
}

async function loadJobs() {
  state.jobs = await api("/jobs");
  renderDashboard();
  renderJobFilters();
  renderInterviewJobOptions();
  renderJobs();
}

async function loadSkills() {
  state.skills = await api("/skills");
  renderDashboard();
  renderSkills();
}

async function loadTools() {
  state.tools = await api("/tools");
}

async function loadLogs() {
  state.logs = await api("/tools/logs?limit=30");
  if (!state.logs.length) {
    state.selectedLog = null;
    renderLogDetail();
  } else if (!state.selectedLog || !state.logs.some((log) => log.call_id === state.selectedLog.call_id)) {
    await loadLogDetail(state.logs[0].call_id);
  } else {
    renderLogDetail();
  }
  renderDashboard();
  renderLogs();
  renderOpsMetrics();
}

async function loadTraces() {
  state.traces = await api("/agent/traces?limit=20");
  if (!state.traces.length) {
    state.selectedTrace = null;
    renderTraceDetail();
  } else if (!state.selectedTrace || !state.traces.some((trace) => trace.trace_id === state.selectedTrace.trace_id)) {
    await loadTraceDetail(state.traces[0].trace_id);
  } else {
    renderTraceDetail();
  }
  renderDashboard();
  renderTraceHistory();
  renderOpsMetrics();
}

async function loadTraceDetail(traceId) {
  state.selectedTrace = await api(`/agent/traces/${traceId}`);
  renderTraceDetail();
  renderTraceHistory();
  renderOpsMetrics();
}

async function loadLogDetail(callId) {
  state.selectedLog = await api(`/tools/logs/${callId}`);
  renderLogDetail();
  renderLogs();
  renderOpsMetrics();
}

async function loadCrawlRecords() {
  state.crawlRecords = await api("/crawler/records?limit=8");
  renderCrawlRecords();
}

async function loadProfiles() {
  state.profiles = await api("/profile");
  renderProfileList();
}

async function loadProfile() {
  const userId = $("profile-user-id").value.trim();
  if (!userId) {
    showToast("请输入用户 ID");
    return;
  }

  const button = $("load-profile");
  setBusy(button, true, "读取中", "读取画像");
  try {
    const profile = await api(`/profile/${encodeURIComponent(userId)}`);
    state.profile = profile;
    fillProfileForm(profile);
    $("match-user-id").value = profile.user_id;
    $("interview-user-id").value = profile.user_id;
    renderProfilePreview(profile);
    showToast("用户画像已读取");
  } catch (error) {
    state.profile = null;
    $("profile-preview").innerHTML = `<div class="result-box empty-box">${escapeHtml(error.message)}</div>`;
    showToast(error.message);
  } finally {
    setBusy(button, false, "读取中", "读取画像");
  }
}

async function loadAll() {
  const refreshButton = $("refresh-all");
  setBusy(refreshButton, true, "刷新中", "刷新数据");
  try {
    await Promise.all([
      loadHealth(),
      loadJobs(),
      loadSkills(),
      loadTools(),
      loadLogs(),
      loadTraces(),
      loadCrawlRecords(),
      loadProfiles(),
    ]);
    showToast("数据已刷新");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(refreshButton, false, "刷新中", "刷新数据");
  }
}

function renderDashboard() {
  $("job-count").textContent = state.jobs.length;
  $("jobs-total-text").textContent = state.jobs.length;
  $("company-count").textContent = new Set(state.jobs.map((job) => job.company_id).filter(Boolean)).size;
  $("skill-count").textContent = state.skills.length;
  $("tool-log-count").textContent = state.logs.length;

  const recentJobs = $("recent-jobs");
  if (!state.jobs.length) {
    recentJobs.innerHTML = renderEmpty("暂无岗位数据。可通过“网页采集”录入公开岗位 URL。");
  } else {
    recentJobs.innerHTML = state.jobs.slice(0, 5).map((job) => `
      <div class="list-item">
        <strong>${escapeHtml(job.title)}</strong>
        <p>${escapeHtml(formatValue(job.company_name))} · ${escapeHtml(formatValue(job.city, "城市未知"))} · ${escapeHtml(formatDate(job.created_at))}</p>
      </div>
    `).join("");
  }

  const recentAgent = $("recent-agent");
  const trace = state.traces[0];
  const log = state.logs[0];
  if (!trace && !log) {
    recentAgent.innerHTML = renderEmpty("暂无 Agent 或工具调用记录。");
    return;
  }
  recentAgent.innerHTML = `
    ${trace ? `<div class="list-item"><strong>${escapeHtml(trace.skill_name || "Agent Trace")}</strong><p>${escapeHtml(trace.task)} · ${escapeHtml(formatDate(trace.created_at))}</p></div>` : ""}
    ${log ? `<div class="list-item"><strong>${escapeHtml(log.tool_name)}</strong><p>${escapeHtml(log.status)} · ${escapeHtml(formatValue(log.latency_ms, "--"))}ms · ${escapeHtml(formatDate(log.created_at))}</p></div>` : ""}
  `;
}

function uniqueOptions(items, getter) {
  const values = [...new Set(items.map(getter).filter(Boolean))];
  return ["全部", ...values];
}

function renderSelect(select, values) {
  select.innerHTML = values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
}

function renderJobFilters() {
  renderSelect($("city-filter"), uniqueOptions(state.jobs, (job) => job.city));
  renderSelect($("type-filter"), uniqueOptions(state.jobs, (job) => job.job_type));
  renderSelect($("company-filter"), uniqueOptions(state.jobs, (job) => job.company_name));
}

function renderInterviewJobOptions() {
  const select = $("interview-job-id");
  if (!select) return;

  const currentValue = select.value;
  select.innerHTML = [
    `<option value="">选择岗位</option>`,
    ...state.jobs.map((job) => `
      <option value="${escapeHtml(job.job_id)}">
        #${escapeHtml(job.job_id)} ${escapeHtml(job.title)} · ${escapeHtml(formatValue(job.company_name))}
      </option>
    `),
  ].join("");

  if (currentValue && state.jobs.some((job) => String(job.job_id) === currentValue)) {
    select.value = currentValue;
  }
}

function getFilteredJobs() {
  const keyword = $("job-search").value.trim().toLowerCase();
  const city = $("city-filter").value;
  const type = $("type-filter").value;
  const company = $("company-filter").value;

  return state.jobs.filter((job) => {
    const haystack = [
      job.title,
      job.company_name,
      job.city,
      job.job_type,
      job.description_preview,
      ...(job.skill_names || []),
      ...(job.requirement_highlights || []),
    ].join(" ").toLowerCase();
    return (!keyword || haystack.includes(keyword))
      && (city === "全部" || job.city === city)
      && (type === "全部" || job.job_type === type)
      && (company === "全部" || job.company_name === company);
  });
}

function renderJobs() {
  const jobs = getFilteredJobs();
  const body = $("job-table-body");

  if (!jobs.length) {
    body.innerHTML = `<tr><td colspan="8">${renderEmpty("没有匹配的岗位数据。")}</td></tr>`;
    return;
  }

  body.innerHTML = jobs.map((job) => `
    <tr>
      <td class="table-title">${escapeHtml(job.title)}</td>
      <td>${escapeHtml(formatValue(job.company_name))}</td>
      <td>${escapeHtml(formatValue(job.city, "未知"))}</td>
      <td>${escapeHtml(formatValue(job.job_type, "未标注"))}</td>
      <td>${renderJobSkillSummary(job)}</td>
      <td>${job.source_url ? `<a class="link" href="${escapeHtml(job.source_url)}" target="_blank" rel="noreferrer">来源链接</a>` : "--"}</td>
      <td>${escapeHtml(formatDate(job.created_at))}</td>
      <td>
        <div class="row-actions">
          <button class="button button-ghost" data-job-view="${job.job_id}" type="button">详情</button>
          <button class="button button-secondary" data-job-extract="${job.job_id}" type="button">${job.extraction_status === "pending" ? "提取技能" : "重新提取"}</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderJobSkillSummary(job) {
  const labels = {
    completed: ["已提取", "success"],
    skills_only: ["已有技能", "warning"],
    pending: ["未提取", "neutral"],
  };
  const [label, type] = labels[job.extraction_status] || labels.pending;
  const visibleSkills = (job.skill_names || []).slice(0, 4);
  const remaining = Math.max((job.skill_count || 0) - visibleSkills.length, 0);
  const requirements = (job.requirement_highlights || []).slice(0, 2);

  return `
    <div class="job-skill-summary">
      ${statusPill(label, type)}
      ${visibleSkills.length ? `
        <div class="job-skill-tags">
          ${visibleSkills.map((skill) => `<span class="tag tag-compact">${escapeHtml(skill)}</span>`).join("")}
          ${remaining ? `<span class="muted">+${remaining}</span>` : ""}
        </div>
      ` : `<span class="muted">暂无技能标签</span>`}
      ${requirements.length ? `<small>${escapeHtml(requirements.join(" · "))}</small>` : ""}
    </div>
  `;
}

async function openJobDrawer(jobId) {
  const drawer = $("job-drawer");
  $("drawer-title").textContent = "加载中";
  $("drawer-body").innerHTML = renderEmpty("正在读取岗位详情...");
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");

  try {
    const job = await api(`/jobs/${jobId}`);
    state.selectedJob = job;
    $("drawer-title").textContent = job.title;
    renderJobDetail(job);
  } catch (error) {
    $("drawer-body").innerHTML = renderEmpty(error.message);
  }
}

function closeJobDrawer() {
  $("job-drawer").classList.remove("is-open");
  $("job-drawer").setAttribute("aria-hidden", "true");
}

function renderJobDetail(job, extracted = null) {
  const displayedSkills = extracted?.skills || job.skills || [];
  const hasExtractedData = displayedSkills.length > 0 || Boolean(job.requirement_json);
  $("drawer-body").innerHTML = `
    <div class="detail-stack">
      <div class="detail-block">
        <h3>基础信息</h3>
        <p>公司：${escapeHtml(formatValue(job.company_name))}
城市：${escapeHtml(formatValue(job.city, "未知"))}
类型：${escapeHtml(formatValue(job.job_type, "未标注"))}
创建时间：${escapeHtml(formatDate(job.created_at))}</p>
      </div>
      <div class="detail-block">
        <h3>来源 URL</h3>
        <p>${job.source_url ? `<a class="link" href="${escapeHtml(job.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(job.source_url)}</a>` : "未记录来源 URL"}</p>
      </div>
      <div class="detail-block">
        <h3>岗位描述</h3>
        <p>${escapeHtml(job.description)}</p>
      </div>
      <div class="detail-block">
        <h3>技能抽取</h3>
        <div class="row-actions">
          <button class="button button-primary" data-drawer-extract="${job.job_id}" type="button">${hasExtractedData ? "重新提取岗位技能" : "提取当前岗位技能"}</button>
        </div>
        <div class="tag-list" id="drawer-skill-result">
          ${displayedSkills.length ? renderExtractedSkillTags(displayedSkills) : `<span class="muted">该岗位尚未提取技能。</span>`}
        </div>
        ${extracted ? `
          <p class="muted">抽取方式：${escapeHtml(formatExtractionMode(extracted.generation_mode))}</p>
          <p class="muted">${escapeHtml(extracted.summary || "")}</p>
          ${renderSkillEvidence(extracted.skills)}
        ` : ""}
      </div>
      ${renderRequirementBlock(extracted?.requirement || job.requirement_json)}
    </div>
  `;
}

function renderRequirementBlock(requirement) {
  if (!requirement) {
    return `
      <div class="detail-block">
        <h3>完整岗位要求</h3>
        <p>尚未抽取完整岗位要求。</p>
      </div>
    `;
  }

  const groups = [
    ["学历要求", requirement.education_requirements],
    ["专业要求", requirement.major_requirements],
    ["语言要求", requirement.language_requirements],
    ["经验要求", requirement.experience_requirements],
    ["能力要求", requirement.soft_skill_requirements],
    ["加分项", requirement.bonus_requirements],
  ];

  return `
    <div class="detail-block">
      <h3>完整岗位要求</h3>
      ${groups.map(([label, items]) => `
        <div class="match-section">
          <span class="muted">${escapeHtml(label)}</span>
          <div class="tag-list">${renderSkillTagList(items || [], "未明确提到")}</div>
        </div>
      `).join("")}
      <div class="match-section">
        <span class="muted">岗位职责</span>
        <p>${escapeHtml((requirement.responsibilities || []).join("\n") || "未明确提到")}</p>
      </div>
    </div>
  `;
}

function renderExtractedSkillTags(skills = []) {
  if (!skills.length) return `<span class="muted">未抽取到技能。</span>`;
  return skills.map((skill) => `<span class="tag">${escapeHtml(skill.skill_name)}<small>${escapeHtml(skill.importance || skill.category || "")}</small></span>`).join("");
}

function formatExtractionMode(mode) {
  return mode === "llm" ? "LLM 语义抽取" : mode === "rules_fallback" ? "规则兜底" : "未知";
}

function renderSkillEvidence(skills = []) {
  const evidenceItems = skills.filter((skill) => skill.evidence);
  if (!evidenceItems.length) return "";
  return `
    <div class="match-section">
      <span class="muted">原文证据</span>
      <div class="evidence-list">
        ${evidenceItems.map((skill) => `
          <div class="evidence-item">
            <strong>${escapeHtml(skill.skill_name)}</strong>
            <p>${escapeHtml(skill.evidence)}</p>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

async function extractJobSkills(jobId, button = null) {
  const idleText = button?.textContent || "提取技能";
  if (button) setBusy(button, true, "抽取中", idleText);
  try {
    const result = await api(`/jobs/${jobId}/extract-skills`, { method: "POST" });
    showToast(`技能抽取完成：${result.skills.length} 个标签`);
    await Promise.all([loadJobs(), loadSkills(), loadLogs()]);
    if (state.selectedJob?.job_id === Number(jobId)) {
      renderJobDetail(state.selectedJob, result);
    }
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) setBusy(button, false, "抽取中", idleText);
  }
}

function renderSkills() {
  const summary = $("skill-category-summary");
  const grid = $("skill-grid");

  if (!state.skills.length) {
    summary.innerHTML = "";
    grid.innerHTML = renderEmpty("暂无技能标签。先对岗位执行技能抽取。");
    return;
  }

  const categories = state.skills.reduce((acc, skill) => {
    const category = skill.category || "未分类";
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  summary.innerHTML = Object.entries(categories)
    .map(([category, count]) => `<span class="tag">${escapeHtml(category)}<small>${count}</small></span>`)
    .join("");

  grid.innerHTML = state.skills.map((skill) => `
    <article class="skill-card">
      <strong>${escapeHtml(skill.skill_name)}</strong>
      <div class="skill-meta">
        <span>${escapeHtml(skill.category || "未分类")}</span>
        <span>${escapeHtml(skill.job_count)} 个岗位</span>
      </div>
    </article>
  `).join("");
}

function collectProfilePayload() {
  return {
    user_id: $("profile-user-id").value.trim(),
    name: $("profile-name").value.trim() || null,
    education: $("profile-education").value.trim() || null,
    target_roles: splitTextList($("profile-target-roles").value),
    target_cities: splitTextList($("profile-target-cities").value),
    preferred_work_type: $("profile-work-type").value.trim() || null,
    skills: splitTextList($("profile-skills").value),
    projects: splitTextList($("profile-projects").value),
    weaknesses: splitTextList($("profile-weaknesses").value),
  };
}

function fillProfileForm(profile) {
  $("profile-user-id").value = profile.user_id || $("profile-user-id").value || "";
  $("profile-name").value = profile.name || "";
  $("profile-education").value = profile.education || "";
  $("profile-target-roles").value = (profile.target_roles || []).join(", ");
  $("profile-target-cities").value = (profile.target_cities || []).join(", ");
  $("profile-work-type").value = profile.preferred_work_type || "";
  $("profile-skills").value = joinTextList(profile.skills || []);
  $("profile-projects").value = joinTextList(profile.projects || []);
  $("profile-weaknesses").value = joinTextList(profile.weaknesses || []);
}

function renderProfileList() {
  const target = $("profile-list");
  if (!target) return;

  if (!state.profiles.length) {
    target.innerHTML = renderEmpty("暂无画像。保存画像后会显示在这里。");
    return;
  }

  target.innerHTML = state.profiles.map((profile) => `
    <div class="list-item profile-list-item">
      <div>
        <strong>${escapeHtml(profile.name || profile.user_id)}</strong>
        <p>${escapeHtml(profile.user_id)} · ${escapeHtml(formatValue(profile.owner_username, "未绑定用户"))} · ${escapeHtml(formatDate(profile.updated_at))}</p>
      </div>
      <button class="button button-ghost" data-profile-load="${escapeHtml(profile.user_id)}" type="button">查看</button>
    </div>
  `).join("");
}

async function parseResume() {
  const fileInput = $("resume-file");
  const file = fileInput.files?.[0];
  if (!file) {
    showToast("请先选择 PDF 或 DOCX 简历");
    return;
  }

  const allowedTypes = [".pdf", ".docx"];
  const fileName = file.name.toLowerCase();
  if (!allowedTypes.some((suffix) => fileName.endsWith(suffix))) {
    showToast("仅支持 PDF 或 DOCX 简历");
    return;
  }

  const button = $("parse-resume");
  setBusy(button, true, "解析中", "解析简历");

  try {
    const formData = new FormData();
    formData.append("file", file);
    const result = await api("/profile/parse-resume", {
      method: "POST",
      headers: {},
      body: formData,
    });
    fillProfileForm(result.profile || {});
    $("profile-preview").innerHTML = `
      <div class="detail-stack">
        <div class="detail-block">
          <h3>简历解析完成</h3>
          <p>文件：${escapeHtml(result.source?.filename || file.name)}
文本长度：${escapeHtml(result.source?.text_length || 0)}
解析方式：${escapeHtml(formatResumeParseMethod(result.source?.parse_method))}
请检查左侧画像草稿，确认无误后点击“保存画像”。</p>
        </div>
        ${(result.source?.warnings || []).length ? `
          <div class="detail-block">
            <h3>解析提示</h3>
            <p>${escapeHtml((result.source.warnings || []).join("\n"))}</p>
          </div>
        ` : ""}
        <div class="detail-block">
          <h3>文本预览</h3>
          <p>${escapeHtml(result.text_preview || "暂无预览")}</p>
        </div>
      </div>
    `;
    showToast("简历解析完成，请确认画像草稿");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false, "解析中", "解析简历");
  }
}

function formatResumeParseMethod(method) {
  const labels = {
    llm: "LLM 语义抽取",
    rule_fallback: "规则兜底解析",
  };
  return labels[method] || "未知";
}

function renderProfilePreview(profile) {
  $("profile-preview").innerHTML = `
    <div class="detail-stack">
      <div class="detail-block">
        <h3>${escapeHtml(profile.name || profile.user_id)}</h3>
        <p>画像 ID：${escapeHtml(profile.user_id)}
所属用户：${escapeHtml(formatValue(profile.owner_username, "未绑定用户"))}
学历：${escapeHtml(formatValue(profile.education))}
工作类型：${escapeHtml(formatValue(profile.preferred_work_type))}
更新时间：${escapeHtml(formatDate(profile.updated_at))}</p>
      </div>
      <div class="detail-block">
        <h3>目标方向</h3>
        <div class="tag-list">
          ${(profile.target_roles || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") || '<span class="muted">未填写目标岗位</span>'}
          ${(profile.target_cities || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") || '<span class="muted">未填写目标城市</span>'}
        </div>
      </div>
      <div class="detail-block">
        <h3>已掌握技能</h3>
        <div class="tag-list">
          ${(profile.skills || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") || '<span class="muted">未填写技能</span>'}
        </div>
      </div>
      <div class="detail-block">
        <h3>项目经历</h3>
        <p>${escapeHtml((profile.projects || []).join("\n") || "未填写项目经历")}</p>
      </div>
      <div class="detail-block">
        <h3>当前短板</h3>
        <div class="tag-list">
          ${(profile.weaknesses || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") || '<span class="muted">未填写短板</span>'}
        </div>
      </div>
    </div>
  `;
}

async function runProfileMatch() {
  const userId = $("match-user-id").value.trim() || state.profile?.user_id || "";
  if (!userId) {
    showToast("请先保存或输入画像 ID");
    return;
  }
  $("match-user-id").value = userId;

  const button = $("run-match");
  setBusy(button, true, "匹配中", "开始匹配");
  $("match-list").innerHTML = renderEmpty("正在计算岗位匹配结果...");

  try {
    const result = await api(`/profile/${encodeURIComponent(userId)}/matches`);
    renderMatchResult(result);
    showToast("匹配分析完成");
  } catch (error) {
    $("match-summary").innerHTML = "";
    $("match-list").innerHTML = renderEmpty(error.message);
    showToast(error.message);
  } finally {
    setBusy(button, false, "匹配中", "开始匹配");
  }
}

async function runStudyPlan() {
  const button = $("generate-study-plan");
  setBusy(button, true, "生成中", "生成学习计划");
  $("study-plan-result").innerHTML = renderEmpty("正在统计真实岗位中的能力缺口...");

  try {
    const result = await api("/profile/study-plan", { method: "POST" });
    renderStudyPlan(result);
    showToast("学习计划已生成");
  } catch (error) {
    $("study-plan-result").innerHTML = renderEmpty(error.message);
    showToast(error.message);
  } finally {
    setBusy(button, false, "生成中", "生成学习计划");
  }
}

function renderStudyPlan(result) {
  const items = result.plan_items || [];
  if (!items.length) {
    $("study-plan-result").innerHTML = `
      <div class="study-plan-empty">
        ${statusPill("暂无明确缺口", "neutral")}
        <p>${escapeHtml(result.message)}</p>
        <small>已分析 ${escapeHtml(result.total_jobs)} 个具有技能标签的真实岗位。</small>
      </div>
    `;
    return;
  }

  $("study-plan-result").innerHTML = `
    <div class="study-plan-summary">
      <div>
        <strong>优先补齐 ${escapeHtml(items.length)} 项能力</strong>
        <p>${escapeHtml(result.message)}</p>
      </div>
      <span>${escapeHtml(result.total_jobs)} 个岗位样本</span>
    </div>
    <div class="study-plan-list">
      ${items.map((item) => `
        <article class="study-plan-item">
          <div class="study-plan-priority">${escapeHtml(item.priority)}</div>
          <div>
            <div class="study-plan-title">
              <strong>${escapeHtml(item.skill_name)}</strong>
              <span>${escapeHtml(item.target_job_count)} 个岗位涉及</span>
            </div>
            <p>${escapeHtml(item.action)}</p>
            <div class="tag-list">
              ${(item.matched_job_examples || []).map((job) => `<span class="tag tag-compact">${escapeHtml(job)}</span>`).join("") || '<span class="muted">暂无岗位示例</span>'}
            </div>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

async function runMockInterview() {
  const userId = $("interview-user-id").value.trim() || state.profile?.user_id || "";
  const jobId = Number($("interview-job-id").value);
  const difficulty = $("interview-difficulty").value;

  if (!userId) {
    showToast("请先保存或输入画像 ID");
    return;
  }
  $("interview-user-id").value = userId;
  if (!Number.isInteger(jobId) || jobId <= 0) {
    showToast("请输入有效的岗位 ID");
    return;
  }

  const button = $("run-interview");
  setBusy(button, true, "生成中", "生成面试题");
  $("interview-result").innerHTML = renderEmpty("正在基于用户画像和岗位要求生成面试追问...");

  try {
    const result = await api("/interview/mock", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        job_id: jobId,
        difficulty,
      }),
    });
    renderMockInterview(result);
    showToast("模拟面试题已生成");
  } catch (error) {
    $("interview-result").innerHTML = renderEmpty(error.message);
    showToast(error.message);
  } finally {
    setBusy(button, false, "生成中", "生成面试题");
  }
}

function renderMockInterview(result) {
  $("interview-result").innerHTML = `
    <div class="interview-header">
      <div>
        <strong>${escapeHtml(result.job_title)}</strong>
        <p class="muted">${escapeHtml(result.company_name)} · session_id=${escapeHtml(result.session_id)} · ${escapeHtml(formatDate(result.created_at))}</p>
      </div>
      ${statusPill(result.difficulty, "neutral")}
    </div>
    <div class="question-list">
      ${(result.questions || []).map((item) => `
        <article class="question-card">
          <div class="question-title">
            <span>${escapeHtml(item.question_id)}</span>
            <div>
              <div class="question-meta">
                ${statusPill(questionTypeLabel(item.question_type), "neutral")}
                <small>${escapeHtml(item.question_type || "unknown")}</small>
              </div>
              <strong>${escapeHtml(item.question)}</strong>
            </div>
          </div>
          <div class="interview-evidence-grid">
            <section>
              <span class="muted">为什么问</span>
              <p>${escapeHtml(item.why_ask || "该问题用于验证岗位要求和用户画像之间的匹配情况。")}</p>
            </section>
            <section>
              <span class="muted">出题依据</span>
              <div class="evidence-list">${renderEvidenceList(item.related_evidence || [])}</div>
            </section>
          </div>
          <div class="match-section answer-points">
            <span class="muted">回答要点</span>
            <ul>${(item.answer_points || []).map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>
          </div>
          <div class="row-actions match-section">
            <button class="button button-secondary" data-evaluate-session="${escapeHtml(result.session_id)}" data-evaluate-question="${encodeURIComponent(item.question)}" type="button">用于评分</button>
          </div>
        </article>
      `).join("")}
    </div>
  `;
  $("evaluation-session-id").value = result.session_id || "";
}

function questionTypeLabel(type) {
  const labels = {
    project_deep_dive: "项目深挖",
    requirement_gap: "岗位缺口",
    rag_engineering: "RAG 工程",
    agent_tool_calling: "Agent 工具调用",
    text2sql_safety: "Text2SQL 安全",
    backend_design: "后端设计",
    crawler_compliance: "采集合规",
    deployment_ops: "部署排障",
  };
  return labels[type] || "面试追问";
}

function renderEvidenceList(items) {
  if (!items.length) return `<span class="muted">暂无明确依据</span>`;
  return items.map((item) => {
    const parts = String(item).split("：");
    const label = parts.length > 1 ? parts.shift() : "依据";
    const value = parts.join("：") || item;
    return `
      <div class="evidence-item">
        <small>${escapeHtml(label)}</small>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `;
  }).join("");
}

async function runAnswerEvaluation() {
  const sessionId = Number($("evaluation-session-id").value);
  const question = $("evaluation-question").value.trim();
  const userAnswer = $("evaluation-answer").value.trim();

  if (!Number.isInteger(sessionId) || sessionId <= 0) {
    showToast("请输入有效的面试会话 ID");
    return;
  }
  if (!question) {
    showToast("请输入面试问题");
    return;
  }
  if (userAnswer.length < 10) {
    showToast("回答至少需要 10 个字");
    return;
  }

  const button = $("run-evaluation");
  setBusy(button, true, "评分中", "评分回答");
  $("evaluation-result").innerHTML = renderEmpty("正在评分回答...");

  try {
    const result = await api("/interview/evaluate", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        question,
        user_answer: userAnswer,
      }),
    });
    renderAnswerEvaluation(result);
    showToast("回答评分完成");
  } catch (error) {
    $("evaluation-result").innerHTML = renderEmpty(error.message);
    showToast(error.message);
  } finally {
    setBusy(button, false, "评分中", "评分回答");
  }
}

function renderAnswerEvaluation(result) {
  const dimensions = Object.entries(result.dimension_scores || {});
  $("evaluation-result").innerHTML = `
    <div class="evaluation-score">
      <strong>${escapeHtml(result.score)}</strong>
      <span>总分 / 100</span>
      <small>evaluation_id=${escapeHtml(result.evaluation_id)} · ${escapeHtml(formatDate(result.created_at))}</small>
    </div>
    <div class="match-section">
      <span class="muted">维度得分</span>
      <div class="dimension-grid">
        ${dimensions.map(([key, value]) => `
          <div>
            <span>${escapeHtml(dimensionLabel(key))}</span>
            <strong>${escapeHtml(value)}</strong>
          </div>
        `).join("")}
      </div>
    </div>
    <div class="match-section">
      <span class="muted">优点</span>
      <div class="tag-list">${renderSkillTagList(result.strengths || [], "暂无明显优点")}</div>
    </div>
    <div class="match-section">
      <span class="muted">待改进</span>
      <div class="tag-list">${renderSkillTagList(result.weaknesses || [], "暂无明显问题")}</div>
    </div>
    <div class="match-section">
      <span class="muted">改进表达</span>
      <p>${escapeHtml(result.improved_answer || "")}</p>
    </div>
    <div class="match-section">
      <span class="muted">可能追问</span>
      <ul>${(result.follow_up_questions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function dimensionLabel(key) {
  const labels = {
    accuracy: "准确性",
    completeness: "完整性",
    project_relevance: "项目结合",
    clarity: "表达清晰",
    engineering_thinking: "工程思维",
  };
  return labels[key] || key;
}

function renderMatchResult(result) {
  const minimumScore = 30;
  const visibleMatches = (result.matches || []).filter(
    (item) => Number(item.match_score || 0) >= minimumScore
  );
  const hiddenCount = Math.max((result.matches || []).length - visibleMatches.length, 0);

  $("match-summary").innerHTML = `
    <article class="metric-card">
      <span>可分析岗位</span>
      <strong>${escapeHtml(result.total_jobs)}</strong>
      <small>已有技能标签的岗位</small>
    </article>
    <article class="metric-card">
      <span>推荐岗位</span>
      <strong>${escapeHtml(visibleMatches.length)}</strong>
      <small>匹配度达到 ${minimumScore}%</small>
    </article>
    <article class="metric-card">
      <span>用户技能</span>
      <strong>${escapeHtml(result.user_skills.length)}</strong>
      <small>来自用户画像</small>
    </article>
  `;

  if (!(result.matches || []).length) {
    $("match-list").innerHTML = renderEmpty("暂无可分析岗位。请先对岗位执行技能抽取。");
    return;
  }

  if (!visibleMatches.length) {
    $("match-list").innerHTML = renderEmpty(`没有匹配度达到 ${minimumScore}% 的岗位。可继续补充画像技能后重新匹配。`);
    return;
  }

  $("match-list").innerHTML = `
    ${hiddenCount ? `<p class="match-filter-note">已隐藏 ${escapeHtml(hiddenCount)} 个匹配度低于 ${minimumScore}% 的岗位。</p>` : ""}
    ${visibleMatches.map((item) => `
    <details class="match-card">
      <summary class="match-card-summary">
        <div class="score-box">
          <strong>${escapeHtml(item.match_score)}%</strong>
          <span>技能覆盖</span>
        </div>
        <div class="match-card-heading">
          <h3>${escapeHtml(item.title)}</h3>
          <p class="muted">${escapeHtml(item.company_name)} · ${escapeHtml(formatValue(item.city, "城市未知"))} · ${escapeHtml(formatValue(item.job_type, "类型未标注"))}</p>
        </div>
        <span class="match-toggle-label" aria-hidden="true"></span>
      </summary>
      <div class="match-card-body">
        <div class="match-section">
          <span class="muted">已满足技能</span>
          <div class="tag-list">${renderSkillTagList(item.matched_skills, "暂无命中技能")}</div>
        </div>
        <div class="match-section">
          <span class="muted">缺失技能</span>
          <div class="tag-list">${renderSkillTagList(item.missing_skills, "暂无缺失技能")}</div>
        </div>
        ${renderRequirementChecks(item.requirement_checks)}
        <div class="row-actions match-section">
          <button class="button button-ghost" data-job-view="${escapeHtml(item.job_id)}" type="button">查看岗位</button>
          ${item.source_url ? `<a class="button button-secondary" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">打开来源</a>` : ""}
        </div>
      </div>
    </details>
  `).join("")}
  `;
}

function renderRequirementChecks(checks) {
  if (!checks || checks.status === "not_extracted") {
    return `
      <div class="match-section">
        <span class="muted">岗位要求检查</span>
        <div class="tag-list"><span class="muted">尚未抽取完整岗位要求</span></div>
      </div>
    `;
  }

  return `
    <div class="match-section">
      <span class="muted">已满足要求</span>
      <div class="tag-list">${renderRequirementTagGroups(checks.matched, "暂无命中要求")}</div>
    </div>
    <div class="match-section">
      <span class="muted">待补充要求</span>
      <div class="tag-list">${renderRequirementTagGroups(checks.missing, "暂无缺失要求")}</div>
    </div>
  `;
}

function renderRequirementTagGroups(groups, emptyText) {
  const items = Object.entries(groups || {}).flatMap(([field, values]) =>
    values.map((value) => `${requirementLabel(field)}：${value}`)
  );
  return renderSkillTagList(items, emptyText);
}

function requirementLabel(field) {
  const labels = {
    education_requirements: "学历",
    major_requirements: "专业",
    language_requirements: "语言",
    experience_requirements: "经验",
    soft_skill_requirements: "能力",
    bonus_requirements: "加分",
  };
  return labels[field] || field;
}

function renderSkillTagList(skills, emptyText) {
  if (!skills.length) return `<span class="muted">${escapeHtml(emptyText)}</span>`;
  return skills.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("");
}

async function saveProfile(event) {
  event.preventDefault();
  const payload = collectProfilePayload();
  if (!payload.user_id) {
    showToast("请输入用户 ID");
    return;
  }

  const button = $("save-profile");
  setBusy(button, true, "保存中", "保存画像");
  try {
    const profile = await api("/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.profile = profile;
    $("match-user-id").value = profile.user_id;
    $("interview-user-id").value = profile.user_id;
    fillProfileForm(profile);
    renderProfilePreview(profile);
    await loadProfiles();
    showToast("用户画像已保存");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(button, false, "保存中", "保存画像");
  }
}

function renderLogs() {
  const filter = $("log-status-filter")?.value || "";
  const logs = filter ? state.logs.filter((log) => log.status === filter) : state.logs;
  const renderList = (target, items, isInteractive) => {
    if (!target) return;
    if (!items.length) {
      target.innerHTML = renderEmpty(filter ? "当前筛选下没有工具调用。" : "暂无工具调用日志。");
      return;
    }

    target.innerHTML = items.map((log) => {
      const selected = state.selectedLog?.call_id === log.call_id;
      const body = `
        <div class="record-row-main">
          <strong>#${escapeHtml(log.call_id)} ${escapeHtml(log.tool_name)}</strong>
          ${statusPill(log.status, log.status === "success" ? "success" : "danger")}
        </div>
        <p>${escapeHtml(formatValue(log.latency_ms, "--"))}ms · ${escapeHtml(formatDate(log.created_at))}</p>
        ${log.error_message ? `<p class="record-error">${escapeHtml(log.error_message)}</p>` : ""}
      `;
      return isInteractive
        ? `<button class="record-row ${selected ? "is-selected" : ""}" data-log-id="${escapeHtml(log.call_id)}" type="button">${body}</button>`
        : `<div class="list-item">${body}</div>`;
    }).join("");
  };

  renderList($("log-list"), logs, true);
  renderList($("console-log-list"), state.logs.slice(0, 6), false);
}

function renderTraceHistory() {
  const keyword = ($("trace-search")?.value || "").trim().toLowerCase();
  const traces = keyword
    ? state.traces.filter((trace) => {
      const text = `${trace.trace_id} ${trace.skill_name || ""} ${trace.task || ""}`.toLowerCase();
      return text.includes(keyword);
    })
    : state.traces;

  const renderList = (target, items, isInteractive) => {
    if (!target) return;
    if (!items.length) {
      target.innerHTML = renderEmpty(keyword ? "当前搜索下没有运行记录。" : "暂无 Agent Trace 历史。");
      return;
    }

    target.innerHTML = items.map((trace) => {
      const selected = state.selectedTrace?.trace_id === trace.trace_id;
      const body = `
        <div class="record-row-main">
          <strong>#${escapeHtml(trace.trace_id)} ${escapeHtml(trace.skill_name || "--")}</strong>
          ${statusPill("trace", "neutral")}
        </div>
        <p>${escapeHtml(trace.task)}</p>
        <p>${escapeHtml(formatDate(trace.created_at))}</p>
      `;
      return isInteractive
        ? `<button class="record-row ${selected ? "is-selected" : ""}" data-trace-id="${escapeHtml(trace.trace_id)}" type="button">${body}</button>`
        : `<div class="list-item">${body}</div>`;
    }).join("");
  };

  renderList($("history-list"), traces, true);
  renderList($("console-history-list"), state.traces.slice(0, 6), false);
}

function renderCurrentTrace(trace = []) {
  const target = $("trace-list");
  if (!trace.length) {
    target.innerHTML = renderEmpty("等待 Agent 运行。");
    return;
  }

  target.innerHTML = renderTraceTimeline(trace);
}

function renderTraceTimeline(trace = []) {
  if (!trace.length) return renderEmpty("暂无 Trace 步骤。");
  return trace.map((step) => {
    const routeMode = step.generation_mode === "llm"
      ? "LLM 路由"
      : step.generation_mode === "rules_fallback" ? "规则兜底" : "";
    const confidence = Number.isFinite(step.confidence)
      ? `置信度 ${Math.round(step.confidence * 100)}%`
      : "";
    const meta = [step.type, step.skill_name, step.tool_name, routeMode, confidence, step.call_id ? `call_id=${step.call_id}` : ""]
      .filter(Boolean)
      .join(" · ");
    const allowedTools = Array.isArray(step.allowed_tools) && step.allowed_tools.length
      ? `<p>允许工具：${escapeHtml(step.allowed_tools.join("、"))}</p>`
      : "";
    const executionSteps = Array.isArray(step.execution_steps) && step.execution_steps.length
      ? `<p>执行步骤：${escapeHtml(step.execution_steps.join("；"))}</p>`
      : "";
    const stepInput = step.input
      ? `<details class="trace-json"><summary>Input</summary><pre>${escapeHtml(formatJson(step.input))}</pre></details>`
      : "";
    const stepOutput = step.output
      ? `<details class="trace-json"><summary>Output</summary><pre>${escapeHtml(formatJson(step.output))}</pre></details>`
      : "";
    return `
      <div class="timeline-item" data-step="${escapeHtml(step.step)}">
        <strong>${escapeHtml(step.content)}</strong>
        <p>${escapeHtml(meta)}</p>
        ${step.reason ? `<p>${escapeHtml(step.reason)}</p>` : ""}
        ${allowedTools}
        ${executionSteps}
        ${stepInput}
        ${stepOutput}
      </div>
    `;
  }).join("");
}

function renderTraceDetail() {
  const trace = state.selectedTrace;
  const title = $("trace-detail-title");
  const meta = $("trace-detail-meta");
  const status = $("trace-detail-status");
  const answer = $("trace-detail-answer");
  const timeline = $("trace-detail-timeline");
  if (!title || !meta || !status || !answer || !timeline) return;

  if (!trace) {
    title.textContent = "Trace Detail";
    meta.textContent = "选择左侧运行记录。";
    status.textContent = "trace";
    answer.textContent = "暂无运行详情。";
    timeline.innerHTML = renderEmpty("暂无 Trace 步骤。");
    return;
  }

  title.textContent = `#${trace.trace_id} ${trace.skill_name || "Agent Run"}`;
  meta.textContent = `${formatDate(trace.created_at)} · user=${formatValue(trace.user_id)}`;
  status.textContent = `${(trace.trace || []).length} steps`;
  answer.innerHTML = `
    <strong>最终回答</strong>
    <p>${escapeHtml(trace.final_answer || "无最终回答")}</p>
    <strong>任务输入</strong>
    <p>${escapeHtml(trace.task || "--")}</p>
  `;
  timeline.innerHTML = renderTraceTimeline(trace.trace || []);
}

function renderLogDetail() {
  const target = $("log-detail");
  if (!target) return;
  const log = state.selectedLog;
  if (!log) {
    target.innerHTML = renderEmpty("选择一条工具调用查看输入输出。");
    return;
  }

  target.innerHTML = `
    <div class="log-detail-head">
      <div>
        <strong>#${escapeHtml(log.call_id)} ${escapeHtml(log.tool_name)}</strong>
        <p>${escapeHtml(formatDate(log.created_at))} · ${escapeHtml(formatValue(log.latency_ms, "--"))}ms</p>
      </div>
      ${statusPill(log.status, log.status === "success" ? "success" : "danger")}
    </div>
    ${log.error_message ? `<p class="record-error">${escapeHtml(log.error_message)}</p>` : ""}
    <details open>
      <summary>Input</summary>
      <pre>${escapeHtml(formatJson(log.input))}</pre>
    </details>
    <details>
      <summary>Output</summary>
      <pre>${escapeHtml(formatJson(log.output))}</pre>
    </details>
  `;
}

function renderOpsMetrics() {
  const traceCount = $("ops-trace-count");
  const logCount = $("ops-log-count");
  const successRate = $("ops-success-rate");
  const avgLatency = $("ops-avg-latency");
  if (!traceCount || !logCount || !successRate || !avgLatency) return;

  const logs = state.logs || [];
  const success = logs.filter((log) => log.status === "success").length;
  const latencies = logs
    .map((log) => Number(log.latency_ms))
    .filter((value) => Number.isFinite(value));
  const average = latencies.length
    ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length)
    : null;

  traceCount.textContent = state.traces.length;
  logCount.textContent = logs.length;
  successRate.textContent = logs.length ? `${Math.round((success / logs.length) * 100)}%` : "--";
  avgLatency.textContent = average === null ? "--" : `${average}ms`;
}

function formatJson(value) {
  if (value === null || value === undefined) return "--";
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    return String(value);
  }
}

function findToolOutput(result) {
  const step = result?.trace?.find((item) => item.type === "tool_result" && item.output);
  return step?.output || null;
}

function renderQueryResult(toolOutput) {
  const isStructuredOnly = renderStructuredResult(toolOutput);
  if (isStructuredOnly) {
    $("result-head").innerHTML = "";
    $("result-body").innerHTML = "";
    $("result-table-card").classList.add("is-hidden");
    return;
  }

  const sql = toolOutput?.sql || "-- no sql";
  const rows = toolOutput?.rows || [];
  const isTableResult = Array.isArray(rows) && rows.length > 0;
  const tableCard = $("result-table-card");
  const generationMode = toolOutput?.generation_mode;

  $("sql-output").textContent = sql;
  $("sql-generation-mode").textContent = generationMode === "llm"
    ? "LLM + SQL Guard"
    : generationMode === "llm_repaired"
      ? "LLM 自修复 + SQL Guard"
    : generationMode === "rules_fallback"
      ? "规则兜底 + SQL Guard"
      : "SQL Guard";
  $("rows-summary").textContent = isTableResult ? `返回 ${rows.length} 行` : "暂无表格结果";

  if (!isTableResult) {
    $("result-head").innerHTML = "";
    $("result-body").innerHTML = "";
    tableCard.classList.add("is-hidden");
    return;
  }

  tableCard.classList.remove("is-hidden");
  const columns = Object.keys(rows[0]);
  $("result-head").innerHTML = `<tr>${columns.map((key) => `<th>${escapeHtml(key)}</th>`).join("")}</tr>`;
  $("result-body").innerHTML = rows
    .map((row) => `<tr>${columns.map((key) => `<td>${escapeHtml(row[key])}</td>`).join("")}</tr>`)
    .join("");
}

function renderStructuredResult(toolOutput) {
  const target = $("structured-result");

  if (!toolOutput) {
    target.innerHTML = renderEmpty("暂无结构化输出。");
    return false;
  }

  if (Array.isArray(toolOutput.plan_items)) {
    target.innerHTML = `
      <div class="structured-card">
        <strong>学习计划</strong>
        <p class="muted">${escapeHtml(toolOutput.message || "")}</p>
        <div class="study-plan-list">
          ${(toolOutput.plan_items || []).map((item) => `
            <div class="study-plan-item compact">
              <div class="study-plan-priority">${escapeHtml(item.priority)}</div>
              <div>
                <strong>${escapeHtml(item.skill_name)}</strong>
                <p>${escapeHtml(item.action)}</p>
              </div>
            </div>
          `).join("") || renderEmpty("暂无明确技能缺口。")}
        </div>
      </div>
    `;
    $("sql-output").textContent = "-- 学习计划不需要生成 SQL";
    $("rows-summary").textContent = `生成 ${toolOutput.plan_items.length} 项学习优先级`;
    return true;
  }

  if (Array.isArray(toolOutput.skills)) {
    target.innerHTML = `
      <div class="structured-card">
        <strong>JD 分析结果</strong>
        <p class="muted">岗位方向：${escapeHtml(formatValue(toolOutput.job_orientation))} · 难度：${escapeHtml(formatValue(toolOutput.difficulty))}</p>
        <div class="tag-list">${renderExtractedSkillTags(toolOutput.skills)}</div>
        <p class="muted">${escapeHtml(toolOutput.summary || "")}</p>
        ${renderRequirementInline(toolOutput.requirement)}
      </div>
    `;
    $("sql-output").textContent = "-- JD 分析不需要生成 SQL";
    $("rows-summary").textContent = `抽取 ${toolOutput.skills.length} 个技能标签`;
    return true;
  }

  if (toolOutput.status && toolOutput.source_url) {
    const parsed = toolOutput.parsed_job || {};
    target.innerHTML = `
      <div class="structured-card">
        <strong>采集结果：${escapeHtml(toolOutput.status)}</strong>
        <p class="muted">job_id=${escapeHtml(formatValue(toolOutput.job_id))} · ${escapeHtml(toolOutput.message || "")}</p>
        <p class="muted">${escapeHtml(parsed.title || "")} ${parsed.company_name ? "· " + escapeHtml(parsed.company_name) : ""}</p>
        <p><a class="link" href="${escapeHtml(toolOutput.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(toolOutput.source_url)}</a></p>
      </div>
    `;
    $("sql-output").textContent = "-- 岗位采集不需要生成 SQL";
    $("rows-summary").textContent = "岗位采集结果";
    return true;
  }

  target.innerHTML = "";
  return false;
}

function renderRequirementInline(requirement) {
  if (!requirement) return "";
  return `
    <div class="match-section">
      <span class="muted">学历 / 专业 / 语言要求</span>
      <div class="tag-list">
        ${renderSkillTagList([
          ...(requirement.education_requirements || []),
          ...(requirement.major_requirements || []),
          ...(requirement.language_requirements || []),
        ], "未明确提到")}
      </div>
    </div>
    <div class="match-section">
      <span class="muted">经验 / 能力 / 加分项</span>
      <div class="tag-list">
        ${renderSkillTagList([
          ...(requirement.experience_requirements || []),
          ...(requirement.soft_skill_requirements || []),
          ...(requirement.bonus_requirements || []),
        ], "未明确提到")}
      </div>
    </div>
  `;
}

async function runAgent() {
  const task = $("task-input").value.trim();
  if (!task) {
    showToast("请输入 Agent 任务");
    return;
  }

  const button = $("run-agent");
  setBusy(button, true, "运行中", "运行 Agent");
  $("final-answer").textContent = "Agent 正在执行...";
  renderCurrentTrace([]);

  try {
    const result = await api("/agent/run", {
      method: "POST",
      body: JSON.stringify({ task }),
    });

    state.lastAgentResult = result;
    $("final-answer").textContent = result.final_answer || "执行完成，但未返回 final_answer。";
    $("trace-id").textContent = `trace_id=${result.trace_id || "--"}`;
    renderCurrentTrace(result.trace || []);
    renderQueryResult(findToolOutput(result));
    await Promise.all([loadJobs(), loadSkills(), loadLogs(), loadTraces()]);
    showToast("Agent 执行完成");
  } catch (error) {
    $("final-answer").textContent = error.message;
    $("sql-output").textContent = "-- request failed";
    renderStructuredResult(null);
    showToast(error.message);
  } finally {
    setBusy(button, false, "运行中", "运行 Agent");
  }
}

async function runBatchExtract() {
  await runObservableExtractionBatch("skills");
}

async function runBatchRequirementExtract() {
  await runObservableExtractionBatch("requirements");
}

async function runObservableExtractionBatch(mode) {
  const isSkillBatch = mode === "skills";
  const activeButton = $(isSkillBatch ? "batch-extract" : "batch-requirements");
  const otherButton = $(isSkillBatch ? "batch-requirements" : "batch-extract");
  const idleText = isSkillBatch ? "批量抽取技能" : "批量补全岗位要求";
  const busyText = isSkillBatch ? "抽取中" : "补全中";

  if (!state.jobs.length) await loadJobs();
  const candidates = state.jobs
    .filter((job) => isSkillBatch
      ? Number(job.skill_count || 0) === 0
      : job.extraction_status !== "completed")
    .slice(0, 20);

  const progress = {
    mode,
    total: candidates.length,
    completed: 0,
    skillSuccess: 0,
    requirementOnly: 0,
    failed: 0,
    currentTitle: "",
    done: candidates.length === 0,
    results: [],
  };

  renderBatchProgress(progress);
  if (!candidates.length) {
    showToast(isSkillBatch ? "当前没有待抽取技能的岗位" : "当前没有待补全要求的岗位");
    return;
  }

  setBusy(activeButton, true, busyText, idleText);
  otherButton.disabled = true;
  try {
    for (const job of candidates) {
      progress.currentTitle = job.title;
      renderBatchProgress(progress);
      try {
        const result = await api(`/jobs/${job.job_id}/extract-skills`, { method: "POST" });
        const skillNames = (result.skills || []).map((skill) => skill.skill_name);
        if (skillNames.length) {
          progress.skillSuccess += 1;
        } else {
          progress.requirementOnly += 1;
        }
        progress.results.unshift({
          status: skillNames.length ? "skills" : "requirements",
          jobId: job.job_id,
          title: job.title,
          detail: skillNames.length ? skillNames.join("、") : "仅识别到学历、专业、语言或职责等岗位要求",
        });
        updateJobExtractionSnapshot(job.job_id, result);
        if (isSkillBatch) updateSkillLibrarySnapshot(result.skills || []);
        renderJobs();
        renderDashboard();
        renderSkills();
      } catch (error) {
        progress.failed += 1;
        progress.results.unshift({
          status: "failed",
          jobId: job.job_id,
          title: job.title,
          detail: error.message,
        });
      }
      progress.completed += 1;
      renderBatchProgress(progress);
    }
  } finally {
    progress.currentTitle = "";
    progress.done = true;
    await Promise.all([loadJobs(), loadSkills(), loadLogs()]).catch(() => undefined);
    renderBatchProgress(progress);
    setBusy(activeButton, false, busyText, idleText);
    otherButton.disabled = false;
  }

  showToast(`批处理完成：技能 ${progress.skillSuccess}，仅岗位要求 ${progress.requirementOnly}，失败 ${progress.failed}`);
}

function updateJobExtractionSnapshot(jobId, result) {
  const job = state.jobs.find((item) => Number(item.job_id) === Number(jobId));
  if (!job) return;

  job.skill_names = (result.skills || []).map((skill) => skill.skill_name);
  job.skill_count = job.skill_names.length;
  job.requirement_highlights = getRequirementHighlights(result.requirement);
  job.extraction_status = result.requirement
    ? "completed"
    : job.skill_count
      ? "skills_only"
      : "pending";
}

function updateSkillLibrarySnapshot(skills) {
  for (const skill of skills) {
    const existing = state.skills.find(
      (item) => item.skill_name.toLowerCase() === skill.skill_name.toLowerCase()
    );
    if (existing) {
      existing.job_count = Number(existing.job_count || 0) + 1;
      continue;
    }
    state.skills.push({
      skill_id: null,
      skill_name: skill.skill_name,
      category: skill.category,
      job_count: 1,
    });
  }
}

function getRequirementHighlights(requirement) {
  if (!requirement) return [];
  const values = [
    ...(requirement.education_requirements || []),
    ...(requirement.language_requirements || []),
    ...(requirement.major_requirements || []),
    ...(requirement.experience_requirements || []),
  ];
  return [...new Set(values)].slice(0, 4);
}

function renderBatchProgress(progress) {
  const target = $("batch-progress");
  target.classList.remove("is-hidden");
  const percent = progress.total ? Math.round(progress.completed / progress.total * 100) : 0;
  const title = progress.done
    ? progress.total ? "批处理完成" : "没有待处理岗位"
    : `正在处理：${progress.currentTitle || "准备任务"}`;

  target.innerHTML = `
    <div class="batch-progress-head">
      <div>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(progress.completed)} / ${escapeHtml(progress.total)}</span>
      </div>
      ${statusPill(progress.done ? "已完成" : "运行中", progress.done ? "success" : "warning")}
    </div>
    <progress max="${escapeHtml(progress.total || 1)}" value="${escapeHtml(progress.completed)}"></progress>
    <div class="batch-counters">
      <span>技能标签 <strong>${escapeHtml(progress.skillSuccess)}</strong></span>
      <span>仅岗位要求 <strong>${escapeHtml(progress.requirementOnly)}</strong></span>
      <span>失败 <strong>${escapeHtml(progress.failed)}</strong></span>
      <span>进度 <strong>${escapeHtml(percent)}%</strong></span>
    </div>
    <div class="batch-result-list">
      ${progress.results.map((item) => `
        <div class="batch-result-item">
          ${statusPill(item.status === "failed" ? "失败" : item.status === "skills" ? "已提取技能" : "仅岗位要求", item.status === "failed" ? "danger" : item.status === "skills" ? "success" : "warning")}
          <div>
            <strong>#${escapeHtml(item.jobId)} ${escapeHtml(item.title)}</strong>
            <p>${escapeHtml(item.detail)}</p>
          </div>
        </div>
      `).join("") || '<span class="muted">等待第一条处理结果。</span>'}
    </div>
  `;
}

function setCrawlerState(type, title, text) {
  const box = $("crawl-state");
  box.className = `request-state ${type ? `is-${type}` : ""}`.trim();
  box.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span>`;
}

function renderCrawlRecords() {
  const target = $("crawl-records");
  if (!target) return;

  if (!state.crawlRecords.length) {
    target.innerHTML = renderEmpty("暂无采集记录。完成一次岗位 URL 采集后会显示在这里。");
    return;
  }

  target.innerHTML = state.crawlRecords.map((record) => {
    const statusType = record.status === "success"
      ? "success"
      : record.status === "failed"
        ? "danger"
        : "warning";
    const parsed = record.parsed_json || {};
    const title = record.title || parsed.title || "未识别岗位标题";

    return `
      <article class="crawl-record">
        <div class="crawl-record-main">
          <div>
            <strong>${escapeHtml(title)}</strong>
            <p>${escapeHtml(formatValue(parsed.company_name, "公司未识别"))} · ${escapeHtml(formatValue(parsed.city, "城市未识别"))} · ${escapeHtml(formatDate(record.crawled_at))}</p>
          </div>
          ${statusPill(record.status, statusType)}
        </div>
        <p class="crawl-record-url">${escapeHtml(record.source_url)}</p>
        ${record.raw_text_preview ? `<p class="crawl-record-preview">${escapeHtml(record.raw_text_preview)}</p>` : ""}
        ${record.error_message ? `<p class="crawl-record-error">${escapeHtml(record.error_message)}</p>` : ""}
        <div class="row-actions">
          ${record.job_id ? `<button class="button button-ghost" data-job-view="${escapeHtml(record.job_id)}" type="button">查看岗位 #${escapeHtml(record.job_id)}</button>` : ""}
          <span class="muted">task_id=${escapeHtml(record.task_id)} · record_id=${escapeHtml(record.record_id)}</span>
        </div>
      </article>
    `;
  }).join("");
}

async function submitCrawler(event) {
  event.preventDefault();
  const url = $("crawl-url").value.trim();
  if (!url) {
    setCrawlerState("error", "表单校验失败", "请输入公开岗位 URL。");
    return;
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch (error) {
    setCrawlerState("error", "URL 格式错误", "请输入以 http:// 或 https:// 开头的有效链接。");
    return;
  }

  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    setCrawlerState("error", "URL 协议不支持", "只支持 http:// 或 https:// 的公开网页。");
    return;
  }

  const payload = {
    url,
    company_name: $("crawl-company").value.trim() || null,
    city: $("crawl-city").value.trim() || null,
    job_type: $("crawl-type").value.trim() || null,
  };

  const button = $("crawl-submit");
  setBusy(button, true, "采集中", "开始采集");
  setCrawlerState("loading", "正在采集", "后端正在请求页面、解析正文并写入 jobs。");

  try {
    const result = await api("/crawler/fetch-url", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.lastCrawlResult = result;
    renderCrawlResult(result);
    setCrawlerState("success", "采集完成", result.message || "岗位已写入数据库。");
    await Promise.all([loadJobs(), loadLogs(), loadCrawlRecords()]);
    showToast("采集完成");
  } catch (error) {
    $("crawl-result").innerHTML = `<div class="result-box empty-box">${escapeHtml(error.message)}</div>`;
    setCrawlerState("error", "采集失败", error.message);
    await loadCrawlRecords().catch(() => undefined);
    showToast(error.message);
  } finally {
    setBusy(button, false, "采集中", "开始采集");
  }
}

async function submitBatchCrawler() {
  const urls = $("batch-crawl-urls").value
    .split(/\r?\n/)
    .map((url) => url.trim())
    .filter(Boolean);

  if (!urls.length) {
    setCrawlerState("error", "表单校验失败", "请至少输入一个公开岗位 URL。");
    return;
  }

  if (urls.length > 50) {
    setCrawlerState("error", "批量数量超限", "一次最多处理 50 个公开岗位 URL。");
    return;
  }

  const invalidUrl = urls.find((url) => {
    try {
      const parsed = new URL(url);
      return !["http:", "https:"].includes(parsed.protocol);
    } catch (error) {
      return true;
    }
  });

  if (invalidUrl) {
    setCrawlerState("error", "URL 格式错误", `存在无效链接：${invalidUrl}`);
    return;
  }

  const button = $("batch-crawl-submit");
  setBusy(button, true, "批量采集中", "批量采集");
  setCrawlerState("loading", "正在批量采集", `正在处理 ${urls.length} 个岗位链接。`);

  try {
    const result = await api("/crawler/fetch-urls", {
      method: "POST",
      body: JSON.stringify({ urls }),
    });

    renderBatchCrawlResult(result);
    setCrawlerState(
      "success",
      "批量采集完成",
      `成功 ${result.success_count}，跳过 ${result.skipped_count}，失败 ${result.failed_count}`
    );
    await Promise.all([loadJobs(), loadLogs(), loadCrawlRecords()]);
    showToast("批量采集完成");
  } catch (error) {
    $("crawl-result").innerHTML = `<div class="result-box empty-box">${escapeHtml(error.message)}</div>`;
    setCrawlerState("error", "批量采集失败", error.message);
    await loadCrawlRecords().catch(() => undefined);
    showToast(error.message);
  } finally {
    setBusy(button, false, "批量采集中", "批量采集");
  }
}

function renderBatchCrawlResult(result) {
  $("crawl-result").innerHTML = `
    <div class="detail-stack">
      <div class="detail-block">
        <h3>批量采集结果</h3>
        <p>总数：${escapeHtml(result.total)}
成功：${escapeHtml(result.success_count)}
跳过：${escapeHtml(result.skipped_count)}
失败：${escapeHtml(result.failed_count)}</p>
      </div>
      ${result.results.map((item) => `
        <div class="detail-block">
          <h3>${escapeHtml(item.status)} ${item.job_id ? `#${escapeHtml(item.job_id)}` : ""}</h3>
          <p>${escapeHtml(item.message || item.error || "")}
${escapeHtml(item.source_url)}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function renderCrawlResult(result) {
  const parsed = result.parsed_job || {};
  $("crawl-result").innerHTML = `
    <div class="detail-stack">
      <div class="detail-block">
        <h3>${escapeHtml(parsed.title || "采集结果")}</h3>
        <p>状态：${escapeHtml(result.status)}
job_id：${escapeHtml(formatValue(result.job_id))}
公司：${escapeHtml(parsed.company_name || parsed.company || "未识别")}
城市：${escapeHtml(parsed.city || "未识别")}</p>
      </div>
      <div class="row-actions">
        ${result.job_id ? `<button class="button button-primary" data-job-view="${escapeHtml(result.job_id)}" type="button">查看岗位</button>` : ""}
        <a class="button button-secondary" href="${escapeHtml(result.source_url)}" target="_blank" rel="noreferrer">打开来源</a>
      </div>
    </div>
  `;
}

function bindEvents() {
  $("auth-login-tab").addEventListener("click", () => setAuthMode("login"));
  $("auth-register-tab").addEventListener("click", () => setAuthMode("register"));
  $("auth-form").addEventListener("submit", submitAuth);
  $("logout").addEventListener("click", () => {
    clearAuthState();
    showToast("已退出登录");
  });

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  document.querySelectorAll("[data-view-jump]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.viewJump));
  });

  $("refresh-all").addEventListener("click", loadAll);
  $("refresh-jobs").addEventListener("click", loadJobs);
  $("refresh-logs").addEventListener("click", loadLogs);
  $("refresh-traces").addEventListener("click", loadTraces);
  $("refresh-console-logs").addEventListener("click", loadLogs);
  $("refresh-console-traces").addEventListener("click", loadTraces);
  $("trace-search").addEventListener("input", renderTraceHistory);
  $("log-status-filter").addEventListener("change", renderLogs);
  $("refresh-crawl-records").addEventListener("click", loadCrawlRecords);
  $("refresh-profiles").addEventListener("click", loadProfiles);
  $("batch-extract").addEventListener("click", runBatchExtract);
  $("batch-requirements").addEventListener("click", runBatchRequirementExtract);
  $("run-agent").addEventListener("click", runAgent);
  $("crawler-form").addEventListener("submit", submitCrawler);
  $("batch-crawl-submit").addEventListener("click", submitBatchCrawler);
  $("profile-form").addEventListener("submit", saveProfile);
  $("load-profile").addEventListener("click", loadProfile);
  $("parse-resume").addEventListener("click", parseResume);
  $("run-match").addEventListener("click", runProfileMatch);
  $("generate-study-plan").addEventListener("click", runStudyPlan);
  $("run-interview").addEventListener("click", runMockInterview);
  $("run-evaluation").addEventListener("click", runAnswerEvaluation);
  $("drawer-close").addEventListener("click", closeJobDrawer);

  ["job-search", "city-filter", "type-filter", "company-filter"].forEach((id) => {
    $(id).addEventListener("input", renderJobs);
    $(id).addEventListener("change", renderJobs);
  });

  document.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-job-view]");
    if (viewButton) {
      openJobDrawer(viewButton.dataset.jobView);
      return;
    }

    const extractButton = event.target.closest("[data-job-extract]");
    if (extractButton) {
      extractJobSkills(extractButton.dataset.jobExtract, extractButton);
      return;
    }

    const drawerExtractButton = event.target.closest("[data-drawer-extract]");
    if (drawerExtractButton) {
      extractJobSkills(drawerExtractButton.dataset.drawerExtract, drawerExtractButton);
      return;
    }

    const evaluateButton = event.target.closest("[data-evaluate-question]");
    if (evaluateButton) {
      $("evaluation-session-id").value = evaluateButton.dataset.evaluateSession || "";
      $("evaluation-question").value = decodeURIComponent(evaluateButton.dataset.evaluateQuestion || "");
      return;
    }

    const profileLoadButton = event.target.closest("[data-profile-load]");
    if (profileLoadButton) {
      $("profile-user-id").value = profileLoadButton.dataset.profileLoad || "";
      loadProfile();
      return;
    }

    const traceButton = event.target.closest("[data-trace-id]");
    if (traceButton) {
      loadTraceDetail(traceButton.dataset.traceId);
      return;
    }

    const logButton = event.target.closest("[data-log-id]");
    if (logButton) {
      loadLogDetail(logButton.dataset.logId);
    }
  });

}

bindEvents();
renderCurrentTrace();
renderTraceDetail();
renderLogDetail();
renderOpsMetrics();
renderStructuredResult(null);
restoreAuth();
