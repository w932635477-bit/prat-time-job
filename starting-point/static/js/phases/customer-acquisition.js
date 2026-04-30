// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: Adaptive Task Plan with daily check-in

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

  const platform = data.platform || '小红书';
  const tasks = data.tasks || [];
  const suggestedDays = data.suggested_days || 14;

  const titleCard = document.createElement('div');
  titleCard.className = 'output-card fade-in';
  titleCard.innerHTML = `
    <div class="output-card__title">${suggestedDays}天行动计划</div>
    <div class="output-card__subtitle">平台: ${esc(platform)} · 每天30分钟内</div>
  `;
  wrapper.appendChild(titleCard);

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
  const suggestedDays = data.suggested_days || 14;
  const done = tasks.filter(t => isTaskCompleted(t.day)).length;
  return `${suggestedDays}天行动计划 (${done}/${tasks.length} 完成)`;
}

export function renderCheckinCard(taskDay, currentDay, totalDays) {
  const card = document.createElement('div');
  card.className = 'checkin-card fade-in';

  const progressPct = Math.round((currentDay / totalDays) * 100);

  card.innerHTML = `
    <div class="checkin-card__progress">
      <div class="checkin-card__progress-bar">
        <div class="checkin-card__progress-fill" style="width:${progressPct}%"></div>
      </div>
      <span class="checkin-card__progress-text">第${currentDay}/${totalDays}天</span>
    </div>
    <div class="checkin-card__task-title">${esc(taskDay.task)}</div>
    <div class="checkin-card__meta">
      <span class="checkin-card__platform">${esc(taskDay.platform)}</span>
      <span class="checkin-card__time">${esc(taskDay.estimated_time || '30分钟')}</span>
    </div>
    <div class="checkin-card__why">${esc(taskDay.why)}</div>
    <div class="checkin-card__signal">成功信号: ${esc(taskDay.success_signal)}</div>
  `;

  return card;
}

export function renderRescueAdvice(advice) {
  const card = document.createElement('div');
  card.className = 'rescue-card fade-in';
  card.innerHTML = `
    <div class="rescue-card__title">帮你分析一下</div>
    <div class="rescue-card__advice">${esc(advice)}</div>
  `;
  return card;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
