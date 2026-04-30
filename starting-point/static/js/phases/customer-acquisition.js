// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: 7-Day Daily Task Cards renderer

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

  const platform = data.platform || '小红书';
  const tasks = data.tasks || [];

  // Title card
  const titleCard = document.createElement('div');
  titleCard.className = 'output-card fade-in';
  titleCard.innerHTML = `
    <div class="output-card__title">7天行动计划</div>
    <div class="output-card__subtitle">平台: ${esc(platform)} · 每天30分钟内</div>
  `;
  wrapper.appendChild(titleCard);

  // Task cards
  if (tasks.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'output-card fade-in';
    empty.innerHTML = '<div class="output-card__value">任务生成中，请稍后刷新</div>';
    wrapper.appendChild(empty);
    return wrapper;
  }

  tasks.forEach(task => {
    wrapper.appendChild(renderTaskCard(task));
  });

  return wrapper;
}

function renderTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'task-card fade-in';

  const dayLabel = task.day === 1 ? '今天' : `第${task.day}天`;
  const checked = isTaskCompleted(task.day);

  card.innerHTML = `
    <div class="task-card__header">
      <label class="task-card__checkbox">
        <input type="checkbox" data-day="${task.day}" ${checked ? 'checked' : ''} />
        <span class="task-card__day">${esc(dayLabel)}</span>
      </label>
      <span class="task-card__time">${esc(task.estimated_time || '30分钟')}</span>
    </div>
    <div class="task-card__task">${esc(task.task)}</div>
    <div class="task-card__meta">
      <span class="task-card__platform">${esc(task.platform)}</span>
    </div>
    <div class="task-card__why">${esc(task.why)}</div>
    <div class="task-card__signal">成功信号: ${esc(task.success_signal)}</div>
  `;

  const checkbox = card.querySelector('input[type="checkbox"]');
  checkbox.addEventListener('change', () => {
    toggleTaskCompleted(task.day);
    if (checkbox.checked) {
      card.classList.add('task-card--done');
    } else {
      card.classList.remove('task-card--done');
    }
  });

  if (checked) {
    card.classList.add('task-card--done');
  }

  return card;
}

const STORAGE_KEY = 'starting_point_completed_tasks';

function isTaskCompleted(day) {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return !!saved[day];
  } catch { return false; }
}

function toggleTaskCompleted(day) {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch {}
  saved[day] = !saved[day];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}

export function getSummary(data) {
  const tasks = data.tasks || [];
  const done = tasks.filter(t => isTaskCompleted(t.day)).length;
  return `7天行动计划 (${done}/${tasks.length} 完成)`;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
