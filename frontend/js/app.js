/* Bilim+ — SPA: роутер и экраны */
"use strict";

const $app = document.getElementById("app");
let SUBJECTS_CACHE = null;

/* ---------- utils ---------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function pct(x) { return Math.round((x || 0) * 100); }
function toast(msg) {
  document.querySelectorAll(".toast").forEach(t => t.remove());
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}
function statusBadge(status, bestScore) {
  if (status === "passed") return `<span class="badge passed">✓ Сдано ${pct(bestScore)}%</span>`;
  if (status === "read") return `<span class="badge read">📖 Прочитано</span>`;
  return `<span class="badge new">Новое</span>`;
}
function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }) + " " +
    d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

/* ---------- header ---------- */
function header(active) {
  return `
  <div class="header">
    <div class="logo" onclick="location.hash='#/home'">🎓 Bilim<span>+</span></div>
    <nav>
      <button class="nav-btn ${active === "home" ? "active" : ""}" onclick="location.hash='#/home'">🏠 <span class="label">Главная</span></button>
      <button class="nav-btn ${active === "subjects" ? "active" : ""}" onclick="location.hash='#/subjects'">📚 <span class="label">Предметы</span></button>
      <button class="nav-btn logout" onclick="logout()">Выйти</button>
    </nav>
  </div>`;
}
function logout() {
  API.clearSession();
  SUBJECTS_CACHE = null;
  location.hash = "#/login";
  render();
}

/* ---------- auth screen ---------- */
let authMode = "login";
function screenAuth() {
  $app.innerHTML = `
  <div class="auth-wrap">
    <div class="auth-card">
      <div class="auth-logo">🎓</div>
      <div class="auth-title">Bilim+</div>
      <div class="auth-sub">Школьная база Казахстана: теория и адаптивные тесты по 9 предметам для 5–11 классов</div>
      <div class="auth-tabs">
        <button class="auth-tab ${authMode === "login" ? "active" : ""}" onclick="authMode='login';render()">Вход</button>
        <button class="auth-tab ${authMode === "register" ? "active" : ""}" onclick="authMode='register';render()">Регистрация</button>
      </div>
      <div class="error-msg" id="authError"></div>
      <form id="authForm">
        ${authMode === "register" ? `
        <div class="field"><label>Имя</label><input id="fName" placeholder="Например, Аружан" required></div>` : ""}
        <div class="field"><label>E-mail</label><input id="fEmail" type="email" placeholder="you@mail.kz" required></div>
        <div class="field"><label>Пароль ${authMode === "register" ? "(минимум 6 символов)" : ""}</label><input id="fPass" type="password" placeholder="••••••" required minlength="6"></div>
        <button class="btn" type="submit">${authMode === "login" ? "Войти" : "Создать аккаунт"}</button>
      </form>
    </div>
  </div>`;
  document.getElementById("authForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("fEmail").value.trim();
    const pass = document.getElementById("fPass").value;
    const errEl = document.getElementById("authError");
    errEl.classList.remove("show");
    try {
      let res;
      if (authMode === "register") {
        const name = document.getElementById("fName").value.trim();
        res = await API.register(name, email, pass);
      } else {
        res = await API.login(email, pass);
      }
      API.saveSession(res.token, res.user);
      SUBJECTS_CACHE = null;
      location.hash = "#/home";
      render();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.add("show");
    }
  });
}

/* ---------- dashboard ---------- */
async function screenHome() {
  $app.innerHTML = header("home") + `<div class="container"><div class="spinner">Загрузка…</div></div>`;
  let dash;
  try { dash = await API.progress(); } catch (e) { return handleApiError(e); }

  const subjectRows = (dash.by_subject || []).map(s => {
    const p = s.total ? Math.round(s.passed / s.total * 100) : 0;
    return `
    <div class="subject-progress">
      <div class="sp-icon">${esc(s.icon)}</div>
      <div class="sp-info">
        <div class="sp-title">${esc(s.title)}</div>
        <div class="sp-bar"><div class="sp-fill" style="width:${p}%"></div></div>
      </div>
      <div class="sp-count">${s.passed}/${s.total} · ${p}%</div>
    </div>`;
  }).join("");

  const weakRows = (dash.weak_topics || []).map(w => `
    <div class="weak-item" onclick="location.hash='#/topic/${w.topic_id}'">
      <div class="wi-badge">${pct(w.best_score)}%</div>
      <div class="wi-title">${esc(w.title)}<div class="wi-subject">${esc(w.subject)} · попыток: ${w.attempts_count}</div></div>
      <div>→</div>
    </div>`).join("") || `<div class="empty">Пока нет несданных тестов 🎉</div>`;

  const recentRows = (dash.recent || []).map(r => `
    <div class="recent-item">
      <span class="recent-score ${r.passed ? "pass" : "fail"}">${pct(r.score)}%</span>
      <span style="flex:1">${esc(r.title)}</span>
      <span style="color:var(--muted);font-size:12px">${fmtDate(r.date)}</span>
    </div>`).join("") || `<div class="empty">Пройди первый тест!</div>`;

  $app.innerHTML = header("home") + `
  <div class="container">
    <div class="page-title">Сәлем, ${esc(API.user.name)}! 👋</div>
    <div class="page-sub">Твоя учебная база: читай теорию, сдавай тесты, закрывай слабые темы.</div>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-num">${dash.topics_passed}<span style="font-size:15px;color:var(--muted)">/${dash.topics_total}</span></div><div class="stat-label">тем сдано</div></div>
      <div class="stat-card"><div class="stat-num">${dash.tests_taken}</div><div class="stat-label">тестов пройдено</div></div>
      <div class="stat-card"><div class="stat-num">${pct(dash.avg_score)}%</div><div class="stat-label">средний балл</div></div>
      <div class="stat-card"><div class="stat-num">${dash.topics_read}</div><div class="stat-label">тем изучено</div></div>
    </div>
    <div class="card">
      <h3>🔥 Слабые темы — повтори и пересдай</h3>
      ${weakRows}
    </div>
    <div class="card">
      <h3>📊 Прогресс по предметам</h3>
      ${subjectRows}
    </div>
    <div class="card">
      <h3>🕒 Последние результаты</h3>
      ${recentRows}
    </div>
  </div>`;
}

/* ---------- subjects list ---------- */
async function loadSubjects(force) {
  if (!SUBJECTS_CACHE || force) SUBJECTS_CACHE = await API.subjects();
  return SUBJECTS_CACHE;
}
async function screenSubjects() {
  $app.innerHTML = header("subjects") + `<div class="container"><div class="spinner">Загрузка…</div></div>`;
  let subjects;
  try { subjects = await loadSubjects(); } catch (e) { return handleApiError(e); }

  const cards = subjects.map(s => {
    let total = 0, passed = 0;
    s.sections.forEach(sec => sec.topics.forEach(t => { total++; if (t.status === "passed") passed++; }));
    const p = total ? Math.round(passed / total * 100) : 0;
    return `
    <div class="subject-card" style="border-left-color:${esc(s.color)}" onclick="location.hash='#/subject/${s.id}'">
      <div class="sc-icon">${esc(s.icon)}</div>
      <div class="sc-title">${esc(s.title)}</div>
      <div class="sc-meta">${s.sections.length} раздел(ов) · ${total} тем · сдано ${passed}</div>
      <div class="sc-bar"><div class="sc-fill" style="width:${p}%"></div></div>
    </div>`;
  }).join("");

  $app.innerHTML = header("subjects") + `
  <div class="container">
    <div class="page-title">Предметы</div>
    <div class="page-sub">Школьная программа Казахстана, 5–11 классы. Теория + тесты после каждой темы.</div>
    <div class="subjects-grid">${cards}</div>
  </div>`;
}

/* ---------- subject detail ---------- */
async function screenSubject(id) {
  $app.innerHTML = header("subjects") + `<div class="container"><div class="spinner">Загрузка…</div></div>`;
  let subjects;
  try { subjects = await loadSubjects(true); } catch (e) { return handleApiError(e); }
  const s = subjects.find(x => x.id == id);
  if (!s) { location.hash = "#/subjects"; return; }

  const sections = s.sections.map(sec => {
    const items = sec.topics.map(t => `
      <div class="topic-item" onclick="location.hash='#/topic/${t.id}'">
        <div class="topic-status ${t.status}">${t.status === "passed" ? "✅" : t.status === "read" ? "📖" : "📘"}</div>
        <div class="topic-info">
          <div class="topic-title">${esc(t.title)}</div>
          <div class="topic-meta">${t.grade_min}–${t.grade_max} класс · вопросов в банке: ${t.questions_count}</div>
        </div>
        <div>${statusBadge(t.status, t.best_score)}</div>
      </div>`).join("");
    return `<div class="section-block"><div class="section-title">${esc(sec.title)}</div>${items}</div>`;
  }).join("");

  $app.innerHTML = header("subjects") + `
  <div class="container">
    <div class="breadcrumbs"><a href="#/subjects">Предметы</a> / <span>${esc(s.title)}</span></div>
    <div class="page-title">${esc(s.icon)} ${esc(s.title)}</div>
    <div class="page-sub">Выбери тему: сначала прочитай теорию, затем пройди тест. Не сдашь — соберём новый, с учётом ошибок.</div>
    ${sections}
  </div>`;
}

/* ---------- topic (theory) ---------- */
async function screenTopic(id) {
  $app.innerHTML = header("subjects") + `<div class="container"><div class="spinner">Загрузка…</div></div>`;
  let t;
  try { t = await API.topic(id); } catch (e) { return handleApiError(e); }

  const subjTitle = findSubjectOf(id);
  $app.innerHTML = header("subjects") + `
  <div class="container">
    <div class="breadcrumbs"><a href="#/subjects">Предметы</a> / ${subjTitle} / <span>${esc(t.title)}</span></div>
    <div class="test-info">
      <span style="font-size:20px">📝</span>
      <div>Тест: 10 вопросов, проходной балл — <b>70%</b>. Провалишь — система соберёт <b>новый тест</b> с учётом твоих ошибок. Лучший результат: <b>${pct(t.best_score)}%</b> · попыток: ${t.attempts_count}</div>
    </div>
    <div class="theory-card">
      <h2>${esc(t.title)} <span class="badge grade" style="vertical-align:middle">${t.grade_min}–${t.grade_max} класс</span></h2>
      <div class="theory-content">${t.theory}</div>
    </div>
    <div class="theory-actions">
      <button class="btn green" onclick="startTestFlow(${t.id})">🚀 Пройти тест</button>
    </div>
  </div>`;
  window.scrollTo(0, 0);
}
function findSubjectOf(topicId) {
  if (!SUBJECTS_CACHE) return "";
  for (const s of SUBJECTS_CACHE)
    for (const sec of s.sections)
      for (const t of sec.topics)
        if (t.id == topicId) return `<a href="#/subject/${s.id}">${esc(s.title)}</a>`;
  return "";
}

/* ---------- test ---------- */
let TEST_STATE = null;

async function startTestFlow(topicId) {
  let attempt;
  try { attempt = await API.startTest(topicId); } catch (e) { toast(e.message); return; }
  TEST_STATE = { attempt, answers: {}, submitted: null };
  location.hash = "#/test/" + attempt.attempt_id;
  render();
}

function screenTest() {
  if (!TEST_STATE) { location.hash = "#/home"; return; }
  const { attempt } = TEST_STATE;
  const answered = Object.keys(TEST_STATE.answers).length;

  const qCards = attempt.questions.map((q, i) => {
    const sel = TEST_STATE.answers[q.id];
    const isMulti = q.type === "multiple";
    const opts = q.options.map((opt, oi) => {
      const selected = isMulti ? Array.isArray(sel) && sel.includes(oi) : sel === oi;
      return `
      <div class="option ${isMulti ? "multi" : ""} ${selected ? "selected" : ""}" onclick="pickOption(${q.id}, ${oi}, ${isMulti})">
        <div class="opt-marker">${isMulti ? (selected ? "✓" : "") : String.fromCharCode(65 + oi)}</div>
        <div>${esc(opt)}</div>
      </div>`;
    }).join("");
    return `
    <div class="q-card" id="qcard-${q.id}">
      <div class="q-num">Вопрос ${i + 1} из ${attempt.questions.length} ${isMulti ? "· несколько ответов" : ""}</div>
      <div class="q-text">${esc(q.text)}</div>
      ${isMulti ? `<div class="q-hint">Выбери все правильные варианты</div>` : ""}
      ${opts}
    </div>`;
  }).join("");

  $app.innerHTML = header("") + `
  <div class="container">
    <div class="test-header">
      <div class="test-progress-text">
        <span>Тест · ${esc(attempt.topic_title || "")}</span>
        <span>${answered}/${attempt.questions.length}</span>
      </div>
      <div class="test-progress-bar"><div class="test-progress-fill" style="width:${answered / attempt.questions.length * 100}%"></div></div>
    </div>
    ${attempt.is_retry ? `<div class="retry-banner">🔁 <b>Повторная попытка.</b> ${esc(attempt.retry_reason || "")}</div>` : ""}
    ${qCards}
    <div class="submit-row">
      <button class="btn" onclick="submitTest()" ${answered < attempt.questions.length ? "" : ""}>Проверить ответы${answered < attempt.questions.length ? ` (${answered}/${attempt.questions.length})` : ""}</button>
    </div>
  </div>`;
}

function pickOption(qid, oi, isMulti) {
  if (isMulti) {
    const cur = Array.isArray(TEST_STATE.answers[qid]) ? [...TEST_STATE.answers[qid]] : [];
    const idx = cur.indexOf(oi);
    if (idx >= 0) cur.splice(idx, 1); else cur.push(oi);
    TEST_STATE.answers[qid] = cur;
  } else {
    TEST_STATE.answers[qid] = oi;
  }
  // быстрый ре-рендер без скролла
  const pos = window.scrollY;
  screenTest();
  window.scrollTo(0, pos);
}

async function submitTest() {
  const { attempt } = TEST_STATE;
  const answers = attempt.questions.map(q => ({
    question_id: q.id,
    selected: TEST_STATE.answers[q.id] ?? null,
  }));
  const unanswered = answers.filter(a => a.selected === null || (Array.isArray(a.selected) && !a.selected.length)).length;
  if (unanswered > 0) {
    if (!confirm(`Ты не ответил(а) на ${unanswered} вопрос(ов). Отправить так?`)) return;
  }
  try {
    const res = await API.submit(attempt.attempt_id, answers);
    TEST_STATE.submitted = res;
    SUBJECTS_CACHE = null;
    location.hash = "#/result/" + attempt.attempt_id;
    render();
  } catch (e) { toast(e.message); }
}

/* ---------- result ---------- */
function screenResult() {
  if (!TEST_STATE || !TEST_STATE.submitted) { location.hash = "#/home"; return; }
  const res = TEST_STATE.submitted;
  const topicId = TEST_STATE.attempt.topic_id;

  const review = res.results.map((r, i) => {
    const yourTxt = r.selected === null || (Array.isArray(r.selected) && !r.selected.length)
      ? "нет ответа"
      : (Array.isArray(r.selected) ? r.selected.map(x => esc(r.options[x])).join(", ") : esc(r.options[r.selected]));
    const correctTxt = Array.isArray(r.correct) ? r.correct.map(x => esc(r.options[x])).join(", ") : esc(r.options[r.correct]);
    return `
    <div class="review-item ${r.is_correct ? "ok" : "bad"}">
      <div class="review-q">${i + 1}. ${esc(r.text)}</div>
      <div class="review-answers">Твой ответ: <span class="your ${r.is_correct ? "ok" : ""}">${yourTxt}</span> ${r.is_correct ? "✓" : "✗"}</div>
      ${!r.is_correct ? `<div class="review-answers">Правильный ответ: <span class="correct">${correctTxt}</span></div>` : ""}
      ${r.explanation ? `<div class="review-exp"><b>Пояснение:</b> ${esc(r.explanation)}</div>` : ""}
    </div>`;
  }).join("");

  $app.innerHTML = header("") + `
  <div class="container">
    <div class="card result-hero">
      <div class="result-ring ${res.passed ? "pass" : "fail"}">
        ${pct(res.score)}%
        <small>${res.correct_count} из ${res.total}</small>
      </div>
      <div class="result-title">${res.passed ? "🎉 Тест сдан!" : "😔 Тест не сдан"}</div>
      <div class="result-sub">${res.passed
        ? "Отличная работа! Тема засчитана. Закрепи материал следующими темами."
        : esc(res.retry_hint || "Нужно минимум 70%. Разбери ошибки и попробуй ещё раз — новый тест будет составлен с учётом твоих слабых мест.")}</div>
      <div class="result-actions">
        ${res.passed
          ? `<button class="btn outline" onclick="location.hash='#/topic/${topicId}'">К теории</button>
             <button class="btn green" onclick="location.hash='#/subjects'">Дальше →</button>`
          : `<button class="btn outline" onclick="location.hash='#/topic/${topicId}'">📖 Перечитать теорию</button>
             <button class="btn" onclick="startTestFlow(${topicId})">🔁 Пройти новый тест</button>`}
      </div>
    </div>
    <div class="section-title" style="margin-top:24px">Разбор ответов</div>
    ${review}
    <div class="submit-row">
      ${res.passed
        ? `<button class="btn outline" onclick="location.hash='#/home'">На главную</button>`
        : `<button class="btn outline" onclick="location.hash='#/topic/${topicId}'">📖 Перечитать теорию</button>
           <button class="btn" onclick="startTestFlow(${topicId})">🔁 Пройти новый тест</button>`}
    </div>
  </div>`;
  window.scrollTo(0, 0);
}

/* ---------- errors & router ---------- */
function handleApiError(e) {
  if (e.status === 401) {
    API.clearSession();
    location.hash = "#/login";
    render();
  } else {
    toast(e.message);
  }
}

function render() {
  const hash = location.hash || "#/home";
  if (!API.token && hash !== "#/login") {
    location.hash = "#/login";
    return screenAuth();
  }
  if (API.token && hash === "#/login") {
    location.hash = "#/home";
    return;
  }
  if (hash === "#/login") return screenAuth();
  if (hash === "#/home") return screenHome();
  if (hash === "#/subjects") return screenSubjects();
  if (hash.startsWith("#/subject/")) return screenSubject(hash.split("/")[2]);
  if (hash.startsWith("#/topic/")) return screenTopic(hash.split("/")[2]);
  if (hash.startsWith("#/test/")) return screenTest();
  if (hash.startsWith("#/result/")) return screenResult();
  location.hash = "#/home";
}

window.addEventListener("hashchange", render);
document.addEventListener("DOMContentLoaded", () => {
  if (API.token && !location.hash) location.hash = "#/home";
  render();
});
