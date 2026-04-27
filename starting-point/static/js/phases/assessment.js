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
      <div class="output-card__value">${esc(tag)}</div>
    </div>
    <div class="output-card__field">
      <div class="output-card__label">内容节奏</div>
      <div class="output-card__value">${esc(pace)}</div>
    </div>
    <div class="output-card__field">
      <div class="output-card__label">第一个小目标</div>
      <div class="output-card__value">${esc(milestone)}</div>
    </div>
    ${tone ? `<div class="emotional-support">${esc(tone)}</div>` : ''}
  `;
  return card;
}

export function getSummary(data) {
  const strategy = data.strategy || data.answers || {};
  return strategy.profile_tag || '评估完成';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
