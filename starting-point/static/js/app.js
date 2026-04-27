// starting-point/static/js/app.js
// Main controller: init, API calls, shared DOM rendering, event binding

import * as store from './store.js';
import { getToken, fetchWithAuth, getCurrentUser } from './auth.js';
import { getPhase, getPhaseName, getTotalPhases, getRenderer } from './phases/index.js';

const API_BASE = '/api';
let state;

// --- DOM helpers ---

function $(sel) { return document.querySelector(sel); }

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

function renderBubbleAi(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--ai fade-in';
  row.innerHTML = `<div class="bubble-ai">${text}</div>`;
  return row;
}

function renderBubbleUserOption(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--user fade-in';
  row.innerHTML = `<div class="bubble-user-option">${escapeHtml(text)}</div>`;
  return row;
}

function renderBubbleUserText(text) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--user fade-in';
  row.innerHTML = `<div class="bubble-user-text">${escapeHtml(text)}</div>`;
  return row;
}

function renderLoading() {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--loading';
  row.innerHTML = '<div class="bubble-ai loading-dots"><span></span><span></span><span></span></div>';
  return row;
}

function renderOptions(options, onSelect) {
  const row = document.createElement('div');
  row.className = 'chat-row chat-row--options fade-in';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => {
      row.querySelectorAll('.option-btn').forEach(b => b.classList.remove('option-btn--selected'));
      btn.classList.add('option-btn--selected');
      onSelect(opt);
    });
    row.appendChild(btn);
  });
  return row;
}

function getMessagesContainer() {
  return $('#chat-messages');
}

// --- Progress bar ---

function updateProgress(phase, step) {
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

async function apiChat(message, selectedOption) {
  const resp = await fetchWithAuth(`${API_BASE}/chat`, {
    method: 'POST',
    body: JSON.stringify({
      user_id: state.userId,
      message: message || selectedOption || '',
      selected_option: selectedOption || null,
    }),
  });
  if (!resp) throw new Error('Auth required');
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

async function apiGoBack(stepId) {
  const resp = await fetchWithAuth(`${API_BASE}/back/${state.userId}/${stepId}`, {
    method: 'POST',
  });
  if (!resp) throw new Error('Auth required');
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

// --- Send message flow ---

async function sendMessage(text) {
  const messages = getMessagesContainer();
  if (!messages) return;

  messages.appendChild(renderBubbleUserText(text));
  state = store.appendHistory(state, 'user', text);
  scrollToBottom();

  const loadingEl = renderLoading();
  messages.appendChild(loadingEl);
  scrollToBottom();

  try {
    const response = await apiChat(text, null);
    loadingEl.remove();
    handleResponse(response);
  } catch (err) {
    loadingEl.remove();
    messages.appendChild(renderBubbleAi('抱歉，出了点问题。请重试。'));
    console.error('API error:', err);
  }
}

async function handleOptionSelect(opt) {
  const messages = getMessagesContainer();

  messages.appendChild(renderBubbleUserOption(opt.label));
  state = store.appendHistory(state, 'user', opt.label);
  scrollToBottom();

  const loadingEl = renderLoading();
  messages.appendChild(loadingEl);
  scrollToBottom();

  try {
    const response = await apiChat(opt.label, opt.value);
    loadingEl.remove();

    if (response.skill_completed) {
      await handlePhaseComplete(response);
    } else {
      handleResponse(response);
    }
  } catch (err) {
    loadingEl.remove();
    messages.appendChild(renderBubbleAi('抱歉，出了点问题。请重试。'));
    console.error('API error:', err);
  }
}

function handleResponse(response) {
  if (response.paywall) {
    renderPaywall(response.preview_data || {}, response.tiers || []);
    return;
  }

  const messages = getMessagesContainer();

  if (response.message) {
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
}

async function handlePhaseComplete(response) {
  const messages = getMessagesContainer();
  const phaseIndex = state.currentPhase;
  const phaseInfo = getPhase(phaseIndex);

  const renderer = await getRenderer(phaseInfo.id);
  const outputData = response.output || response;
  const card = renderer.renderOutput(outputData);
  messages.appendChild(card);

  state = store.recordPhaseResult(state, phaseIndex, renderer.getSummary(outputData), outputData);
  state = store.advancePhase(state);

  const nextPhase = getPhase(state.currentPhase);
  if (nextPhase) {
    messages.appendChild(renderBubbleAi(
      `"${phaseInfo.name}"完成了。接下来进入"${nextPhase.name}"阶段。`
    ));
  } else {
    messages.appendChild(renderBubbleAi(
      '恭喜！你已经完成了所有阶段。从今天开始，你不再是一个失业的人——你是一个有自己的小生意的人。'
    ));
  }

  updateProgress(state.currentPhase, state.currentStep);
  scrollToBottom();
}

// --- Progress grid toggle ---

function setupProgressGrid() {
  const chip = $('#progress-chip');
  if (!chip) return;

  let gridEl = null;

  chip.addEventListener('click', () => {
    if (gridEl) {
      gridEl.remove();
      gridEl = null;
      return;
    }

    gridEl = document.createElement('div');
    gridEl.className = 'progress-grid';

    const total = getTotalPhases();
    for (let i = 0; i < total; i++) {
      const p = getPhase(i);
      const item = document.createElement('button');
      item.className = 'progress-grid__item';

      if (i < state.currentPhase) {
        item.classList.add('progress-grid__item--completed');
        item.innerHTML = `<span class="progress-grid__icon">✓</span><span class="progress-grid__name">${p.name}</span>`;
        item.addEventListener('click', () => {
          if (confirm(`回到"${p.name}"？当前进度会保留。`)) {
            state = store.goBack(state, i, 0);
            gridEl.remove();
            gridEl = null;
            location.reload();
          }
        });
      } else if (i === state.currentPhase) {
        item.classList.add('progress-grid__item--current');
        item.innerHTML = `<span class="progress-grid__icon">●</span><span class="progress-grid__name">${p.name}</span>`;
      } else {
        item.classList.add('progress-grid__item--future');
        item.innerHTML = `<span class="progress-grid__icon">○</span><span class="progress-grid__name">${p.name}</span>`;
      }

      gridEl.appendChild(item);
    }

    chip.after(gridEl);

    const closeGrid = (e) => {
      if (!gridEl.contains(e.target) && e.target !== chip) {
        gridEl.remove();
        gridEl = null;
        document.removeEventListener('click', closeGrid);
      }
    };
    setTimeout(() => document.addEventListener('click', closeGrid), 0);
  });
}

// --- Paywall rendering ---

function renderPaywall(previewData, tiers) {
  const area = getMessagesContainer();

  if (previewData && Object.keys(previewData).length > 0) {
    const preview = document.createElement('div');
    preview.className = 'chat-row chat-row--ai fade-in';
    preview.innerHTML = `<div class="output-card"><div class="output-card__title">预览方案</div><div class="output-card__field">${formatPreview(previewData)}</div></div>`;
    area.appendChild(preview);
  }

  const wall = document.createElement('div');
  wall.className = 'chat-row chat-row--ai fade-in';
  wall.innerHTML = `
    <div class="paywall">
      <div class="paywall__title">解锁完整方案</div>
      <div class="paywall__subtitle">选择适合你的方案，继续你的旅程</div>
      <div class="pricing-grid">
        ${tiers.map(t => `
          <div class="pricing-card ${t.key === 'standard' ? 'pricing-card--popular' : ''}" data-tier="${t.key}">
            <div class="pricing-card__name">${t.label}</div>
            <div class="pricing-card__price">&yen;${(t.price_fen / 100).toFixed(1)} <span>/${t.duration_days}天</span></div>
            <div class="pricing-card__desc">${t.description}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  area.appendChild(wall);

  wall.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('click', () => handlePurchase(card.dataset.tier));
  });
  scrollToBottom();
}

async function handlePurchase(tier) {
  const resp = await fetchWithAuth(`${API_BASE}/payments/create?tier=${tier}`, { method: 'POST' });
  if (!resp) return;
  const data = await resp.json();
  alert(`订单创建成功: ${data.order_id}\n\n开发模式下请在后台确认支付。`);
  pollPayment(data.order_id);
}

async function pollPayment(orderId) {
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 3000));
    const resp = await fetchWithAuth(`${API_BASE}/payments/status/${orderId}`);
    if (!resp) return;
    const data = await resp.json();
    if (data.status === 'paid') {
      location.reload();
      return;
    }
  }
}

function formatPreview(data) {
  return Object.entries(data).map(([k, v]) =>
    `<div><strong>${escapeHtml(k)}</strong>: ${typeof v === 'object' ? escapeHtml(JSON.stringify(v)) : escapeHtml(String(v))}</div>`
  ).join('');
}

// --- Init ---

async function initApp() {
  // Auth guard
  if (!getToken()) {
    window.location.href = '/login.html';
    return;
  }

  state = store.init();

  const currentUser = await getCurrentUser();
  if (!currentUser) return;
  state = { ...state, userId: currentUser.id };
  store.save(state);

  // Set avatar
  const avatar = document.getElementById('user-avatar');
  if (avatar && currentUser.avatar_url) {
    avatar.src = currentUser.avatar_url;
    avatar.style.display = 'block';
    avatar.onclick = () => { window.location.href = '/account.html'; };
  }

  const messages = getMessagesContainer();
  const input = $('#chatInput');
  const sendBtn = $('#sendBtn');

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

  setupProgressGrid();

  try {
    const response = await apiChat('你好', null);
    handleResponse(response);
  } catch (err) {
    messages.appendChild(renderBubbleAi('连接失败，请刷新页面重试。'));
    console.error('Init error:', err);
  }
}

document.addEventListener('DOMContentLoaded', initApp);
