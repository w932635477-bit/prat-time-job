# Starting Point V2 UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace V1's 3-page multi-page chat UI with a unified single-page chat app supporting 6-phase journey, collapsible progress bar, phase output cards, and 30-day content plan viewer.

**Architecture:** One `app.html` shell + module-split vanilla JS (ES modules). `store.js` manages state + localStorage persistence. `app.js` is the main controller calling APIs and delegating to phase renderers. Each phase has its own `phases/*.js` module exporting `renderOutput()` and `getSummary()`. V1 HTML files retained for backward compatibility.

**Tech Stack:** Vanilla HTML/CSS/JS (ES modules), existing FastAPI `StaticFiles` serves `static/` dir. No build step. No framework.

**Design Doc:** `docs/plans/2026-04-27-starting-point-v2-ui-design.md`

---

## Task 1: store.js — State Management Module

**Files:**
- Create: `starting-point/static/js/store.js`

**Step 1: Create the directory structure**

```bash
mkdir -p "starting-point/static/js/phases"
```

**Step 2: Write store.js**

```javascript
// starting-point/static/js/store.js
// State management with localStorage persistence

const STORAGE_KEY = 'starting_point_state';

function generateId() {
  return 'u_' + crypto.randomUUID();
}

function createInitialState() {
  return {
    userId: generateId(),
    currentPhase: 0,
    currentStep: 0,
    phaseResults: {},
    contentPlan: null,
    isPaused: false,
    chatHistory: [],
  };
}

export function init() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      // corrupted, start fresh
    }
  }
  const state = createInitialState();
  save(state);
  return state;
}

export function save(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function advanceStep(state) {
  const next = { ...state, currentStep: state.currentStep + 1 };
  save(next);
  return next;
}

export function advancePhase(state) {
  const next = { ...state, currentPhase: state.currentPhase + 1, currentStep: 0 };
  save(next);
  return next;
}

export function recordPhaseResult(state, phaseIndex, summary, data) {
  const next = {
    ...state,
    phaseResults: {
      ...state.phaseResults,
      [phaseIndex]: { summary, data },
    },
  };
  save(next);
  return next;
}

export function goBack(state, phaseIndex, stepIndex) {
  const next = { ...state, currentPhase: phaseIndex, currentStep: stepIndex };
  save(next);
  return next;
}

export function pause(state) {
  const next = { ...state, isPaused: true };
  save(next);
  return next;
}

export function resume(state) {
  const next = { ...state, isPaused: false };
  save(next);
  return next;
}

export function appendHistory(state, role, content) {
  const entry = { role, content, ts: Date.now() };
  const next = {
    ...state,
    chatHistory: [...state.chatHistory, entry],
  };
  save(next);
  return next;
}

export function reset() {
  localStorage.removeItem(STORAGE_KEY);
  const state = createInitialState();
  save(state);
  return state;
}
```

**Step 3: Verify file loads without errors**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node -e "import('./static/js/store.js').then(m => console.log(Object.keys(m)))"`
Expected: `[ 'init', 'save', 'advanceStep', 'advancePhase', 'recordPhaseResult', 'goBack', 'pause', 'resume', 'appendHistory', 'reset' ]`

**Step 4: Commit**

```bash
git add starting-point/static/js/store.js
git commit -m "feat(ui): add store.js state management module"
```

---

## Task 2: phases/index.js — Phase Registry

**Files:**
- Create: `starting-point/static/js/phases/index.js`

**Step 1: Write phases/index.js**

```javascript
// starting-point/static/js/phases/index.js
// Phase definitions and ordering

export const PHASES = [
  { id: 'assessment',           name: '起跑评估', steps: 4 },
  { id: 'self_discovery',       name: '发现金矿', steps: 8 },
  { id: 'product_packaging',    name: '包装产品', steps: 4 },
  { id: 'customer_acquisition', name: '找到客户', steps: 3 },
  { id: 'first_deal',           name: '完成首单', steps: 2 },
  { id: 'growth',               name: '转起来',   steps: 2 },
];

export function getPhase(index) {
  return PHASES[index] || null;
}

export function getPhaseName(index) {
  return PHASES[index]?.name ?? '未知阶段';
}

export function getTotalPhases() {
  return PHASES.length;
}

// Lazy-load phase renderer modules
const rendererCache = {};

export async function getRenderer(phaseId) {
  if (rendererCache[phaseId]) return rendererCache[phaseId];
  const mod = await import(`./${phaseId}.js`);
  rendererCache[phaseId] = mod;
  return mod;
}
```

**Step 2: Verify file loads**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node -e "import('./static/js/phases/index.js').then(m => console.log(m.PHASES.length, m.getTotalPhases()))"`
Expected: `6 6`

**Step 3: Commit**

```bash
git add starting-point/static/js/phases/index.js
git commit -m "feat(ui): add phases/index.js registry"
```

---

## Task 3: app.js — Main Controller + Shared DOM Helpers

**Files:**
- Create: `starting-point/static/js/app.js`

**Step 1: Write app.js**

```javascript
// starting-point/static/js/app.js
// Main controller: init, API calls, shared DOM rendering, event binding

import * as store from './store.js';
import { getPhase, getPhaseName, getTotalPhases, getRenderer } from './phases/index.js';

const API_BASE = '/api';
let state;

// --- DOM helpers ---

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

export function renderBubbleAi(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--ai fade-in';
  row.innerHTML = `<div class="bubble-ai">${text}</div>`;
  return row;
}

export function renderBubbleUserOption(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--user fade-in';
  row.innerHTML = `<div class="bubble-user-option">${escapeHtml(text)}</div>`;
  return row;
}

export function renderBubbleUserText(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--user fade-in';
  row.innerHTML = `<div class="bubble-user-text">${escapeHtml(text)}</div>`;
  return row;
}

export function renderConfidenceBoost(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--confidence fade-in';
  row.innerHTML = `<div class="confidence-boost">${text}</div>`;
  return row;
}

export function renderLoading() {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--loading';
  row.innerHTML = '<div class="bubble-ai loading-dots"><span></span><span></span><span></span></div>';
  return row;
}

export function renderOptions(options, onSelect) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--options fade-in';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => {
      // Mark selected
      row.querySelectorAll('.option-btn').forEach(b => b.classList.remove('option-btn--selected'));
      btn.classList.add('option-btn--selected');
      onSelect(opt);
    });
    row.appendChild(btn);
  });
  return row;
}

export function getMessagesContainer() {
  return $('#chat-messages');
}

// --- Progress bar ---

export function updateProgress(phase, step) {
  const phaseInfo = getPhase(phase);
  if (!phaseInfo) return;

  const chip = $('#progress-chip');
  if (chip) {
    chip.textContent = `第 ${phase + 1}/${getTotalPhases()} 阶段 · ${phaseInfo.name}`;
  }

  const fill = $('.progress-bar__fill');
  if (fill) {
    const total = getTotalPhases();
    const pct = ((phase + step / phaseInfo.steps) / total) * 100;
    fill.style.width = `${Math.min(pct, 100)}%`;
  }
}

// --- API calls ---

export async function apiChat(message, selectedOption) {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: state.userId,
      message: message || selectedOption || '',
      selected_option: selectedOption || null,
    }),
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

export async function apiGoBack(stepId) {
  const resp = await fetch(`${API_BASE}/back/${state.userId}/${stepId}`, {
    method: 'POST',
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

export async function apiGetState() {
  const resp = await fetch(`${API_BASE}/state/${state.userId}`);
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

// --- Phase collapsing ---

export function collapsePhase(phaseIndex) {
  const container = getMessagesContainer();
  const phaseEl = container.querySelector(`[data-phase="${phaseIndex}"]`);
  if (!phaseEl) return;

  const renderer = getRenderer(getPhase(phaseIndex).id);
  // Will be awaited where needed
  return renderer;
}

// --- Send message flow ---

async function sendMessage(text) {
  const messages = getMessagesContainer();
  if (!messages) return;

  // Show user message
  messages.appendChild(renderBubbleUserText(text));
  state = store.appendHistory(state, 'user', text);
  scrollToBottom();

  // Show loading
  const loadingEl = renderLoading();
  messages.appendChild(loadingEl);
  scrollToBottom();

  try {
    const response = await apiChat(text, null);
    loadingEl.remove();

    // Render AI response
    if (response.message) {
      const content = response.message.content || response.message.question || '';
      messages.appendChild(renderBubbleAi(content));
      state = store.appendHistory(state, 'ai', content);

      // Render options if present
      if (response.message.options && response.message.options.length > 0) {
        const opts = response.message.options.map(o => ({ label: o.label, value: o.value }));
        messages.appendChild(renderOptions(opts, async (opt) => {
          await handleOptionSelect(opt);
        }));
      }
    }

    // Update progress
    if (response.current_step !== undefined) {
      state = { ...state, currentStep: response.current_step };
      store.save(state);
    }
    updateProgress(state.currentPhase, state.currentStep);

    scrollToBottom();
  } catch (err) {
    loadingEl.remove();
    messages.appendChild(renderBubbleAi('抱歉，出了点问题。请重试。'));
    console.error('API error:', err);
  }
}

async function handleOptionSelect(opt) {
  const messages = getMessagesContainer();

  // Show user selection
  messages.appendChild(renderBubbleUserOption(opt.label));
  state = store.appendHistory(state, 'user', opt.label);
  scrollToBottom();

  // Loading
  const loadingEl = renderLoading();
  messages.appendChild(loadingEl);
  scrollToBottom();

  try {
    const response = await apiChat(opt.label, opt.value);
    loadingEl.remove();

    if (response.skill_completed) {
      // Phase completed — render output card and advance
      await handlePhaseComplete(response);
    } else if (response.message) {
      const content = response.message.content || response.message.question || '';
      messages.appendChild(renderBubbleAi(content));
      state = store.appendHistory(state, 'ai', content);

      if (response.message.options && response.message.options.length > 0) {
        const opts = response.message.options.map(o => ({ label: o.label, value: o.value }));
        messages.appendChild(renderOptions(opts, async (o) => {
          await handleOptionSelect(o);
        }));
      }
    }

    if (response.current_step !== undefined) {
      state = { ...state, currentStep: response.current_step };
      store.save(state);
    }
    updateProgress(state.currentPhase, state.currentStep);

    scrollToBottom();
  } catch (err) {
    loadingEl.remove();
    messages.appendChild(renderBubbleAi('抱歉，出了点问题。请重试。'));
    console.error('API error:', err);
  }
}

async function handlePhaseComplete(response) {
  const messages = getMessagesContainer();
  const phaseIndex = state.currentPhase;
  const phaseInfo = getPhase(phaseIndex);

  // Render phase output card via phase renderer
  const renderer = await getRenderer(phaseInfo.id);
  const outputData = response.output || response;
  const card = renderer.renderOutput(outputData);
  messages.appendChild(card);

  state = store.recordPhaseResult(state, phaseIndex, renderer.getSummary(outputData), outputData);
  state = store.advancePhase(state);

  // Show transition message
  const nextPhase = getPhase(state.currentPhase);
  if (nextPhase) {
    messages.appendChild(renderBubbleAi(
      `太好了！"${phaseInfo.name}"完成了。接下来是"${nextPhase.name}"阶段。`
    ));
  } else {
    messages.appendChild(renderBubbleAi(
      '恭喜！你已经完成了所有阶段。记住：从今天开始，你不再是一个失业的人——你是一个有自己的小生意的人。'
    ));
  }

  scrollToBottom();
}

// --- Init ---

export async function initApp() {
  state = store.init();

  const messages = getMessagesContainer();
  const input = $('#chatInput');
  const sendBtn = $('#sendBtn');

  // Input handlers
  input.addEventListener('input', () => {
    sendBtn.classList.toggle('input-bar__send--active', input.value.trim().length > 0);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && input.value.trim()) {
      sendMessage(input.value.trim());
      input.value = '';
      sendBtn.classList.remove('input-bar__send--active');
    }
  });

  sendBtn.addEventListener('click', () => {
    if (input.value.trim()) {
      sendMessage(input.value.trim());
      input.value = '';
      sendBtn.classList.remove('input-bar__send--active');
    }
  });

  // Start conversation
  try {
    const response = await apiChat('你好', null);
    if (response.message) {
      const content = response.message.content || response.message.question || '';
      messages.appendChild(renderBubbleAi(content));

      if (response.message.options && response.message.options.length > 0) {
        const opts = response.message.options.map(o => ({ label: o.label, value: o.value }));
        messages.appendChild(renderOptions(opts, async (opt) => {
          await handleOptionSelect(opt);
        }));
      }
    }
    updateProgress(state.currentPhase, state.currentStep);
    scrollToBottom();
  } catch (err) {
    messages.appendChild(renderBubbleAi('连接失败，请刷新页面重试。'));
    console.error('Init error:', err);
  }
}

// Boot
document.addEventListener('DOMContentLoaded', initApp);
```

**Step 2: Verify file parses**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node --check static/js/app.js 2>&1 || echo "Note: dynamic imports may cause node warnings, check for syntax errors only"`
Expected: No syntax errors (may have warnings about browser APIs like `document`)

**Step 3: Commit**

```bash
git add starting-point/static/js/app.js
git commit -m "feat(ui): add app.js main controller with shared DOM helpers"
```

---

## Task 4: app.html Shell + design-system.css Additions

**Files:**
- Create: `starting-point/static/app.html`
- Modify: `starting-point/static/design-system.css`

**Step 1: Add new component styles to design-system.css**

Append after the `@media (min-width: 640px)` block:

```css
/* === V2 Components === */

/* Phase Summary (collapsed completed phase) */
.phase-summary {
  background: var(--bg-secondary);
  border-radius: var(--r-md);
  padding: var(--sp-3) var(--sp-4);
  margin-bottom: var(--sp-4);
}

.phase-summary__label {
  font: var(--t-caption);
  color: var(--text-tertiary);
  margin-bottom: var(--sp-1);
}

.phase-summary__text {
  font: var(--t-body-sm);
  color: var(--text-secondary);
}

/* Progress Chip */
.progress-chip {
  position: fixed;
  top: calc(var(--header-height) + 2px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font: var(--t-caption);
  padding: var(--sp-1) var(--sp-4);
  border-radius: var(--r-pill);
  border: 1px solid var(--divider);
  z-index: 100;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.progress-chip:hover {
  border-color: var(--gold-border);
}

/* Progress Grid (expanded) */
.progress-grid {
  position: fixed;
  top: calc(var(--header-height) + 2px + 32px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--sp-4);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-3);
  z-index: 101;
  min-width: 240px;
}

.progress-grid__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-3);
  border-radius: var(--r-md);
  cursor: default;
  border: none;
  background: none;
  font-family: var(--font-main);
}

.progress-grid__item--completed {
  color: var(--gold);
  cursor: pointer;
}

.progress-grid__item--completed:hover {
  background: var(--gold-subtle);
}

.progress-grid__item--current {
  background: var(--gold-subtle);
  color: var(--gold);
}

.progress-grid__item--future {
  color: var(--text-tertiary);
}

.progress-grid__icon {
  font-size: 20px;
  line-height: 1;
}

.progress-grid__name {
  font: var(--t-micro);
  text-align: center;
}

/* Output Card (shared base) */
.output-card {
  background: var(--bg-secondary);
  border-radius: var(--r-lg);
  padding: var(--sp-5);
  margin: var(--sp-4) 0;
  border-left: 3px solid var(--gold);
}

.output-card__title {
  font: var(--t-title);
  color: var(--gold);
  margin-bottom: var(--sp-4);
}

.output-card__subtitle {
  font: var(--t-caption);
  color: var(--text-tertiary);
  margin-bottom: var(--sp-4);
}

.output-card__field {
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--divider);
}

.output-card__field:last-child {
  border-bottom: none;
}

.output-card__label {
  font: var(--t-caption);
  color: var(--text-tertiary);
  margin-bottom: var(--sp-1);
}

.output-card__value {
  font: var(--t-body-sm);
  color: var(--text-primary);
}

/* Content Plan Accordion */
.content-week {
  background: var(--bg-secondary);
  border-radius: var(--r-md);
  margin-bottom: var(--sp-3);
  border: 1px solid var(--divider);
}

.content-week summary {
  padding: var(--sp-4);
  font: var(--t-body-sm);
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-week summary::-webkit-details-marker {
  display: none;
}

.content-week summary::after {
  content: '▶';
  font-size: 12px;
  color: var(--text-tertiary);
  transition: transform var(--transition-fast);
}

.content-week[open] summary::after {
  transform: rotate(90deg);
}

.content-week__body {
  padding: 0 var(--sp-4) var(--sp-4);
}

/* Content Piece */
.content-piece {
  background: var(--bg-primary);
  border-radius: var(--r-sm);
  margin-bottom: var(--sp-2);
}

.content-piece summary {
  padding: var(--sp-3) var(--sp-4);
  font: var(--t-caption);
  color: var(--text-secondary);
  cursor: pointer;
  list-style: none;
  display: flex;
  gap: var(--sp-2);
  align-items: center;
}

.content-piece summary::-webkit-details-marker {
  display: none;
}

.content-piece summary::after {
  content: '▼';
  font-size: 10px;
  color: var(--text-tertiary);
  margin-left: auto;
}

.content-piece[open] summary::after {
  content: '▲';
}

.content-piece__script {
  padding: var(--sp-3) var(--sp-4);
  font: var(--t-body-sm);
  color: var(--text-primary);
  border-top: 1px solid var(--divider);
  white-space: pre-wrap;
}

.content-piece__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
  padding: 0 var(--sp-4) var(--sp-3);
}

.content-piece__tag {
  background: var(--gold-subtle);
  color: var(--gold);
  font: var(--t-micro);
  padding: 2px var(--sp-2);
  border-radius: var(--r-pill);
}

/* Emotional Support */
.emotional-support {
  background: var(--gold-subtle);
  border-left: 3px solid var(--gold);
  padding: var(--sp-3) var(--sp-4);
  border-radius: 0 var(--r-md) var(--r-md) 0;
  margin: var(--sp-3) 0;
  font: var(--t-body-sm);
  color: var(--gold);
}

/* Back button in progress grid */
.progress-grid__backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
}
```

**Step 2: Create app.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>启点 — 陪你赚到第一块钱</title>
  <link rel="stylesheet" href="design-system.css">
  <style>
    .chat-area {
      padding-top: calc(var(--header-height) + 2px + 32px + var(--sp-4));
      padding-bottom: calc(var(--input-height) + var(--sp-3) + var(--safe-bottom) + var(--sp-3));
      padding-left: var(--page-padding);
      padding-right: var(--page-padding);
      max-width: var(--max-width);
      margin: 0 auto;
    }

    .chat-area__messages {
      display: flex;
      flex-direction: column;
    }

    .chat-row {
      margin-bottom: var(--sp-3);
    }

    .chat-row--ai {
      display: flex;
      justify-content: flex-start;
    }

    .chat-row--user {
      display: flex;
      justify-content: flex-end;
    }

    .chat-row--confidence {
      display: flex;
      justify-content: flex-start;
    }

    .chat-row--loading {
      display: flex;
      justify-content: flex-start;
    }

    .chat-row--options {
      display: flex;
      flex-wrap: wrap;
      gap: var(--sp-3);
      padding-top: var(--sp-1);
    }
  </style>
</head>
<body>
  <!-- Header -->
  <header class="app-header">
    <button class="app-header__back" onclick="location.href='index.html'" aria-label="返回首页">←</button>
    <span class="app-header__title">启点</span>
  </header>

  <!-- Progress Chip -->
  <div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" aria-label="旅程进度">
    <div class="progress-bar__fill" style="width: 0%"></div>
  </div>
  <div id="progress-chip" class="progress-chip" aria-label="阶段进度">第 1/6 阶段 · 起跑评估</div>

  <!-- Chat Area -->
  <div class="chat-area">
    <div id="chat-messages" class="chat-area__messages" role="log" aria-live="polite" aria-label="对话内容">
    </div>
  </div>

  <!-- Input Bar -->
  <div class="input-bar">
    <div class="input-bar__inner">
      <input class="input-bar__field" type="text" placeholder="说点什么..." id="chatInput" aria-label="输入消息">
      <button class="input-bar__send" id="sendBtn" aria-label="发送消息">↑</button>
    </div>
  </div>

  <script type="module" src="js/app.js"></script>
</body>
</html>
```

**Step 3: Verify files exist and HTML is valid**

Run: `ls -la "starting-point/static/app.html" "starting-point/static/js/app.js" "starting-point/static/js/store.js" "starting-point/static/js/phases/index.js"`
Expected: All 4 files exist

**Step 4: Commit**

```bash
git add starting-point/static/app.html starting-point/static/design-system.css
git commit -m "feat(ui): add app.html shell and V2 component styles"
```

---

## Task 5: Phase Renderers (assessment + self-discovery)

**Files:**
- Create: `starting-point/static/js/phases/assessment.js`
- Create: `starting-point/static/js/phases/self-discovery.js`

**Step 1: Write assessment.js**

```javascript
// starting-point/static/js/phases/assessment.js
// Phase 0: Assessment output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '0');

  const strategy = data.strategy || data.answers || {};
  const tag = strategy.profile_tag || '评估完成';
  const pace = strategy.content_pace || 'normal';
  const milestone = strategy.first_milestone || '开始第一步';
  const tone = strategy.expectation_tone || '';

  card.innerHTML = `
    <div class="output-card__title">起跑评估完成</div>
    <div class="output-card__field">
      <div class="output-card__label">你的画像</div>
      <div class="output-card__value">${escapeHtml(tag)}</div>
    </div>
    <div class="output-card__field">
      <div class="output-card__label">内容节奏</div>
      <div class="output-card__value">${escapeHtml(pace)}</div>
    </div>
    <div class="output-card__field">
      <div class="output-card__label">第一个小目标</div>
      <div class="output-card__value">${escapeHtml(milestone)}</div>
    </div>
    ${tone ? `<div class="emotional-support">${escapeHtml(tone)}</div>` : ''}
  `;
  return card;
}

export function getSummary(data) {
  const strategy = data.strategy || data.answers || {};
  return strategy.profile_tag || '评估完成';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 2: Write self-discovery.js**

```javascript
// starting-point/static/js/phases/self-discovery.js
// Phase 1: Self Discovery output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '1');

  const assets = data.asset_map || data.assets || [];
  const assetItems = Array.isArray(assets)
    ? assets.map(a => renderAsset(a)).join('')
    : '<div class="output-card__value">资产已识别</div>';

  card.innerHTML = `
    <div class="output-card__title">发现金矿完成</div>
    <div class="output-card__subtitle">你的可定价资产</div>
    ${assetItems}
  `;
  return card;
}

function renderAsset(asset) {
  if (typeof asset === 'string') {
    return `<div class="output-card__field"><div class="output-card__value">${escapeHtml(asset)}</div></div>`;
  }
  const name = asset.name || asset.skill || '资产';
  const price = asset.market_price || asset.price_range || '';
  const evidence = asset.evidence || '';
  return `
    <div class="output-card__field">
      <div class="result-item__name">${escapeHtml(name)}</div>
      ${price ? `<div class="result-item__value">${escapeHtml(price)}</div>` : ''}
      ${evidence ? `<div class="result-item__evidence">${escapeHtml(evidence)}</div>` : ''}
    </div>
  `;
}

export function getSummary(data) {
  const assets = data.asset_map || data.assets || [];
  if (Array.isArray(assets) && assets.length > 0) {
    return `发现 ${assets.length} 项可定价资产`;
  }
  return '资产已识别';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 3: Verify both files parse**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node --check static/js/phases/assessment.js && node --check static/js/phases/self-discovery.js && echo "OK"`
Expected: `OK`

**Step 4: Commit**

```bash
git add starting-point/static/js/phases/assessment.js starting-point/static/js/phases/self-discovery.js
git commit -m "feat(ui): add assessment and self-discovery phase renderers"
```

---

## Task 6: Phase Renderers (product-packaging + first-deal + growth)

**Files:**
- Create: `starting-point/static/js/phases/product-packaging.js`
- Create: `starting-point/static/js/phases/first-deal.js`
- Create: `starting-point/static/js/phases/growth.js`

**Step 1: Write product-packaging.js**

```javascript
// starting-point/static/js/phases/product-packaging.js
// Phase 2: Product Packaging output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '2');

  const product = data.product_card || data.constraints || {};
  const name = product.service_name || '你的服务';
  const tagline = product.tagline || '';
  const target = product.target_customer || '';
  const pricing = product.pricing || {};
  const flow = product.service_flow || [];
  const deliverables = product.deliverables || '';

  card.innerHTML = `
    <div class="output-card__title">${escapeHtml(name)}</div>
    ${tagline ? `<div class="output-card__subtitle">${escapeHtml(tagline)}</div>` : ''}
    ${target ? `
      <div class="output-card__field">
        <div class="output-card__label">目标客户</div>
        <div class="output-card__value">${escapeHtml(target)}</div>
      </div>
    ` : ''}
    <div class="output-card__field">
      <div class="output-card__label">定价</div>
      ${pricing.trial_price ? `<div class="output-card__value">体验价: ${escapeHtml(pricing.trial_price)}</div>` : ''}
      ${pricing.standard_price ? `<div class="output-card__value">正式价: ${escapeHtml(pricing.standard_price)}</div>` : ''}
      ${pricing.package_price ? `<div class="output-card__value">套餐价: ${escapeHtml(pricing.package_price)}</div>` : ''}
    </div>
    ${flow.length > 0 ? `
      <div class="output-card__field">
        <div class="output-card__label">服务流程</div>
        ${flow.map((s, i) => `<div class="output-card__value">${i + 1}. ${escapeHtml(s)}</div>`).join('')}
      </div>
    ` : ''}
    ${deliverables ? `
      <div class="output-card__field">
        <div class="output-card__label">交付物</div>
        <div class="output-card__value">${escapeHtml(deliverables)}</div>
      </div>
    ` : ''}
  `;
  return card;
}

export function getSummary(data) {
  const product = data.product_card || data.constraints || {};
  return product.service_name || '服务产品已设计';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 2: Write first-deal.js**

```javascript
// starting-point/static/js/phases/first-deal.js
// Phase 4: First Deal output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '4');

  const toolkit = data.toolkit || data.product_card || {};
  const templates = toolkit.communication_templates || {};
  const formula = toolkit.pricing_formula || '';
  const methods = toolkit.payment_methods || [];
  const checklist = toolkit.delivery_checklist || [];
  const postDelivery = toolkit.post_delivery || '';

  card.innerHTML = `
    <div class="output-card__title">首单工具包</div>
    ${templates.price_inquiry ? `
      <div class="output-card__field">
        <div class="output-card__label">客户问价时</div>
        <div class="output-card__value">${escapeHtml(templates.price_inquiry)}</div>
      </div>
    ` : ''}
    ${templates.service_inquiry ? `
      <div class="output-card__field">
        <div class="output-card__label">客户问服务时</div>
        <div class="output-card__value">${escapeHtml(templates.service_inquiry)}</div>
      </div>
    ` : ''}
    ${templates.hesitant_client ? `
      <div class="output-card__field">
        <div class="output-card__label">客户犹豫时</div>
        <div class="output-card__value">${escapeHtml(templates.hesitant_client)}</div>
      </div>
    ` : ''}
    ${formula ? `
      <div class="output-card__field">
        <div class="output-card__label">报价公式</div>
        <div class="output-card__value">${escapeHtml(formula)}</div>
      </div>
    ` : ''}
    ${checklist.length > 0 ? `
      <div class="output-card__field">
        <div class="output-card__label">交付清单</div>
        ${checklist.map(s => `<div class="output-card__value">☐ ${escapeHtml(s)}</div>`).join('')}
      </div>
    ` : ''}
    ${postDelivery ? `
      <div class="output-card__field">
        <div class="output-card__label">交付后引导反馈</div>
        <div class="output-card__value">${escapeHtml(postDelivery)}</div>
      </div>
    ` : ''}
  `;
  return card;
}

export function getSummary(data) {
  return '首单工具包已生成';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 3: Write growth.js**

```javascript
// starting-point/static/js/phases/growth.js
// Phase 5: Growth output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '5');

  const plan = data.growth_plan || {};
  const testimonial = plan.testimonial_to_content || '';
  const pricingAdj = plan.pricing_adjustment || '';
  const referral = plan.referral_mechanism || '';
  const repeat = plan.repeat_purchase || '';

  card.innerHTML = `
    <div class="output-card__title">增长计划</div>
    ${testimonial ? `
      <div class="output-card__field">
        <div class="output-card__label">口碑变内容</div>
        <div class="output-card__value">${escapeHtml(testimonial)}</div>
      </div>
    ` : ''}
    ${pricingAdj ? `
      <div class="output-card__field">
        <div class="output-card__label">定价调整</div>
        <div class="output-card__value">${escapeHtml(pricingAdj)}</div>
      </div>
    ` : ''}
    ${referral ? `
      <div class="output-card__field">
        <div class="output-card__label">转介绍机制</div>
        <div class="output-card__value">${escapeHtml(referral)}</div>
      </div>
    ` : ''}
    ${repeat ? `
      <div class="output-card__field">
        <div class="output-card__label">复购设计</div>
        <div class="output-card__value">${escapeHtml(repeat)}</div>
      </div>
    ` : ''}
  `;
  return card;
}

export function getSummary(data) {
  return '增长计划已生成';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 4: Verify all parse**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node --check static/js/phases/product-packaging.js && node --check static/js/phases/first-deal.js && node --check static/js/phases/growth.js && echo "OK"`
Expected: `OK`

**Step 5: Commit**

```bash
git add starting-point/static/js/phases/product-packaging.js starting-point/static/js/phases/first-deal.js starting-point/static/js/phases/growth.js
git commit -m "feat(ui): add product-packaging, first-deal, growth phase renderers"
```

---

## Task 7: Phase Renderer (customer-acquisition) — 30-day Content Plan

This is the most complex renderer. It uses `<details>/<summary>` for week accordion and per-piece expandable cards.

**Files:**
- Create: `starting-point/static/js/phases/customer-acquisition.js`

**Step 1: Write customer-acquisition.js**

```javascript
// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: 30-day Content Plan renderer

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

  // Week 1 content from LLM response
  const week1Content = data.week1_content || {};
  const remainingWeeks = data.remaining_weeks || [
    { week: 2, theme: '找感觉期', pieces: 7 },
    { week: 3, theme: '突破期', pieces: 8 },
    { week: 4, theme: '收获期', pieces: 8 },
  ];
  const platform = data.platform || '小红书';

  // Title card
  const titleCard = document.createElement('div');
  titleCard.className = 'output-card fade-in';
  titleCard.innerHTML = `
    <div class="output-card__title">30天内容计划</div>
    <div class="output-card__subtitle">平台: ${escapeHtml(platform)} · 每周持续发布</div>
  `;
  wrapper.appendChild(titleCard);

  // Week 1: open by default with content
  const week1Details = renderWeekAccordion(1, week1Content.theme || '试水期', week1Content.content_pieces || [], true, week1Content.emotional_support || '');
  wrapper.appendChild(week1Details);

  // Weeks 2-4: collapsed, placeholder
  remainingWeeks.forEach(w => {
    const details = renderWeekPlaceholder(w.week, w.theme, w.pieces);
    wrapper.appendChild(details);
  });

  return wrapper;
}

function renderWeekAccordion(weekNum, theme, pieces, isOpen, emotionalSupport) {
  const details = document.createElement('details');
  details.className = 'content-week fade-in';
  if (isOpen) details.open = true;

  const summary = document.createElement('summary');
  summary.textContent = `第${weekNum}周: ${theme} (${pieces.length}条)`;
  details.appendChild(summary);

  const body = document.createElement('div');
  body.className = 'content-week__body';

  if (emotionalSupport) {
    const support = document.createElement('div');
    support.className = 'emotional-support';
    support.textContent = emotionalSupport;
    body.appendChild(support);
  }

  pieces.forEach(piece => {
    body.appendChild(renderContentPiece(piece));
  });

  details.appendChild(body);
  return details;
}

function renderWeekPlaceholder(weekNum, theme, piecesCount) {
  const details = document.createElement('details');
  details.className = 'content-week fade-in';

  const summary = document.createElement('summary');
  summary.textContent = `第${weekNum}周: ${theme} (${piecesCount}条) — 点击生成`;
  details.appendChild(summary);

  const body = document.createElement('div');
  body.className = 'content-week__body';
  body.innerHTML = `<div class="output-card__value" style="text-align:center;padding:var(--sp-6);color:var(--text-tertiary)">完成第${weekNum - 1}周后自动生成</div>`;
  details.appendChild(body);

  return details;
}

function renderContentPiece(piece) {
  const details = document.createElement('details');
  details.className = 'content-piece';

  const day = piece.day || '';
  const type = piece.type || '';
  const title = piece.title || '内容';

  const summary = document.createElement('summary');
  summary.textContent = `Day ${day} · ${type} · ${title}`;
  details.appendChild(summary);

  // Script body
  if (piece.script) {
    const scriptDiv = document.createElement('div');
    scriptDiv.className = 'content-piece__script';
    scriptDiv.textContent = piece.script;
    details.appendChild(scriptDiv);
  }

  // Tags
  if (piece.tags && piece.tags.length > 0) {
    const tagsDiv = document.createElement('div');
    tagsDiv.className = 'content-piece__tags';
    piece.tags.forEach(tag => {
      const span = document.createElement('span');
      span.className = 'content-piece__tag';
      span.textContent = `#${tag}`;
      tagsDiv.appendChild(span);
    });
    details.appendChild(tagsDiv);
  }

  return details;
}

export function getSummary(data) {
  const platform = data.platform || '';
  return `30天${platform}内容计划已生成`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
```

**Step 2: Verify parses**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && node --check static/js/phases/customer-acquisition.js && echo "OK"`
Expected: `OK`

**Step 3: Commit**

```bash
git add starting-point/static/js/phases/customer-acquisition.js
git commit -m "feat(ui): add customer-acquisition renderer with 30-day content cards"
```

---

## Task 8: Redesign Landing Page (index.html)

**Files:**
- Modify: `starting-point/static/index.html`

**Step 1: Rewrite index.html for 6-phase journey**

Replace entire file content:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>启点</title>
  <link rel="stylesheet" href="design-system.css">
  <style>
    .landing {
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: var(--sp-10) var(--page-padding);
      padding-bottom: calc(var(--sp-10) + var(--safe-bottom));
    }

    .landing__icon {
      width: 48px;
      height: 48px;
      margin-bottom: var(--sp-10);
      opacity: 0;
      animation: fadeIn 600ms ease-out 100ms forwards;
    }

    .landing__icon svg {
      width: 100%;
      height: 100%;
    }

    .landing__headline {
      margin-bottom: var(--sp-4);
      opacity: 0;
      animation: fadeIn 400ms ease-out 200ms forwards;
    }

    .landing__headline-main {
      font: var(--t-hero);
      letter-spacing: var(--tracking-hero);
      color: var(--text-primary);
      display: block;
    }

    .landing__headline-gold {
      font: var(--t-hero);
      letter-spacing: var(--tracking-hero);
      color: var(--gold);
      display: block;
    }

    .landing__subtitle {
      font: var(--t-body-sm);
      color: var(--text-secondary);
      margin-bottom: var(--sp-12);
      opacity: 0;
      animation: fadeIn 300ms ease-out 400ms forwards;
    }

    .landing__cta {
      width: 100%;
      max-width: 320px;
      margin-bottom: var(--sp-3);
      opacity: 0;
      animation: fadeIn 300ms ease-out 500ms forwards;
    }

    .landing__phases {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: var(--sp-3);
      width: 100%;
      max-width: 360px;
      margin-top: var(--sp-10);
      opacity: 0;
      animation: fadeIn 300ms ease-out 600ms forwards;
    }

    .landing__phase {
      display: flex;
      align-items: center;
      gap: var(--sp-2);
      padding: var(--sp-3);
      background: var(--bg-secondary);
      border-radius: var(--r-md);
      text-align: left;
    }

    .landing__phase-num {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--gold-subtle);
      color: var(--gold);
      font: var(--t-micro);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .landing__phase-text {
      font: var(--t-caption);
      color: var(--text-secondary);
    }

    .landing__phase-name {
      font-weight: 500;
      color: var(--text-primary);
      display: block;
    }

    .landing__phase-desc {
      display: block;
    }
  </style>
</head>
<body>
  <div class="landing">
    <div class="landing__icon" role="img" aria-label="启点指南针">
      <svg viewBox="0 0 48 48" fill="none" stroke="#C9A96E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="24" cy="24" r="20"/>
        <polygon points="24,8 28,24 24,40 20,24" fill="rgba(201,169,110,0.15)" stroke="#C9A96E"/>
        <line x1="24" y1="4" x2="24" y2="10"/>
        <line x1="24" y1="38" x2="24" y2="44"/>
        <line x1="4" y1="24" x2="10" y2="24"/>
        <line x1="38" y1="24" x2="44" y2="24"/>
      </svg>
    </div>

    <div class="landing__headline">
      <span class="landing__headline-main">启点</span>
      <span class="landing__headline-gold">陪你赚到第一块钱</span>
    </div>

    <p class="landing__subtitle">从"我什么都不会"到"赚到第一笔钱"</p>

    <div class="landing__cta">
      <button class="btn-primary" onclick="location.href='app.html'" aria-label="开始旅程">开始你的旅程</button>
    </div>

    <div class="landing__phases">
      <div class="landing__phase">
        <div class="landing__phase-num">0</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">起跑评估</span>
          <span class="landing__phase-desc">了解你的起点</span>
        </div>
      </div>
      <div class="landing__phase">
        <div class="landing__phase-num">1</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">发现金矿</span>
          <span class="landing__phase-desc">发现你能卖什么</span>
        </div>
      </div>
      <div class="landing__phase">
        <div class="landing__phase-num">2</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">包装产品</span>
          <span class="landing__phase-desc">把经验变成服务</span>
        </div>
      </div>
      <div class="landing__phase">
        <div class="landing__phase-num">3</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">找到客户</span>
          <span class="landing__phase-desc">30天内容计划</span>
        </div>
      </div>
      <div class="landing__phase">
        <div class="landing__phase-num">4</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">完成首单</span>
          <span class="landing__phase-desc">搞定第一单</span>
        </div>
      </div>
      <div class="landing__phase">
        <div class="landing__phase-num">5</div>
        <div class="landing__phase-text">
          <span class="landing__phase-name">转起来</span>
          <span class="landing__phase-desc">持续赚钱</span>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
```

**Step 2: Verify HTML structure**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python3 -c "
from html.parser import HTMLParser
class V(HTMLParser):
    def __init__(self): super().__init__(); self.ok = True
    def handle_starttag(self, tag, attrs): pass
    def error(self, msg): self.ok = False
v = V()
v.feed(open('static/index.html').read())
print('VALID' if v.ok else 'INVALID')
"`
Expected: `VALID`

**Step 3: Commit**

```bash
git add starting-point/static/index.html
git commit -m "feat(ui): redesign landing page for 6-phase journey"
```

---

## Task 9: Update main.py to Serve JS Modules Correctly

**Files:**
- Modify: `starting-point/src/starting_point/main.py`

FastAPI's StaticFiles serves files from `static/` as-is. ES modules need correct MIME type (`application/javascript`). StaticFiles should handle this, but we need to verify and ensure the route order doesn't catch `js/` paths before the static mount.

**Step 1: Check current main.py route order**

Read `src/starting_point/main.py`. The `app.mount("/", StaticFiles(...))` at the bottom catches all unhandled routes. This means `GET /js/app.js` → serves `static/js/app.js`. No change needed unless MIME type is wrong.

**Step 2: Verify MIME type by starting server and testing**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && python -m starting_point.main &`
Then: `NO_PROXY="127.0.0.1,localhost" curl -sI http://127.0.0.1:8768/js/app.js | head -5`
Expected: `Content-Type: application/javascript`

**Step 3: If MIME type is wrong, add explicit MIME configuration**

If Step 2 shows wrong MIME type, add this before the static mount:

```python
# In main.py, before app.mount
from starlette.staticfiles import StaticFiles
app.mount("/js", StaticFiles(directory=str(STATIC_DIR / "js")), name="js")
```

Then kill the server and restart to verify.

**Step 4: Kill test server**

Run: `pkill -f "python -m starting_point.main"`

**Step 5: Commit (only if changes were needed)**

```bash
git add src/starting_point/main.py
git commit -m "fix(ui): ensure correct MIME type for JS modules"
```

---

## Task 10: Browser Integration Test

**Prerequisites:** Backend server running with V2 skills (from backend implementation plan Tasks 1-7 completed).

**Step 1: Start the server**

```bash
cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point"
NO_PROXY="127.0.0.1,localhost" python -m starting_point.main
```

**Step 2: Test landing page**

Run: `NO_PROXY="127.0.0.1,localhost" curl -s http://127.0.0.1:8768/ | head -20`
Expected: HTML with "启点" and "陪你赚到第一块钱"

**Step 3: Test app.html loads**

Run: `NO_PROXY="127.0.0.1,localhost" curl -s http://127.0.0.1:8768/app.html | head -5`
Expected: `<!DOCTYPE html>` with "启点"

**Step 4: Test JS modules load**

Run: `NO_PROXY="127.0.0.1,localhost" curl -s http://127.0.0.1:8768/js/app.js | head -3`
Expected: First lines of app.js

**Step 5: Test API from app.html context**

Run: `NO_PROXY="127.0.0.1,localhost" curl -s -X POST http://127.0.0.1:8768/api/chat -H "Content-Type: application/json" -d '{"user_id":"ui-test","message":"hello","selected_option":null}' | python3 -m json.tool | head -20`
Expected: JSON response with `message` containing step question and options

**Step 6: Manual browser test**

Open `http://127.0.0.1:8768/` in browser:
- Verify landing page shows 6 phases
- Click "开始你的旅程" → navigates to app.html
- Verify first question appears (assessment phase)
- Verify options are clickable
- Verify progress chip updates
- Verify back button works
- Open browser console → check for JS errors

**Step 7: Commit final state**

```bash
git add -A
git commit -m "feat(ui): V2 unified single-page chat UI complete"
```

---

## Implementation Order Summary

| Task | Description | Dependencies | Est. Time |
|------|-------------|-------------|-----------|
| 1 | store.js state management | None | 10min |
| 2 | phases/index.js registry | None | 5min |
| 3 | app.js main controller | Task 1, 2 | 20min |
| 4 | app.html + CSS additions | Task 3 | 15min |
| 5 | assessment + self-discovery renderers | Task 2 | 10min |
| 6 | product-packaging + first-deal + growth renderers | Task 2 | 15min |
| 7 | customer-acquisition renderer (30-day) | Task 2 | 15min |
| 8 | Redesign index.html landing | None | 10min |
| 9 | Verify MIME types | Task 4 | 5min |
| 10 | Browser integration test | Task 1-9 + backend | 15min |

**Total: ~2 hours**

Tasks 1+2 can run in parallel. Tasks 5+6+7 can run in parallel. Task 8 is independent.
