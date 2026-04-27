// starting-point/static/js/phases/customer-acquisition.js
// Phase 3: 30-day Content Plan renderer

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('data-phase', '3');

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
    <div class="output-card__subtitle">平台: ${esc(platform)} · 每周持续发布</div>
  `;
  wrapper.appendChild(titleCard);

  // Week 1: open by default with content
  const week1 = renderWeekAccordion(
    1,
    week1Content.theme || '试水期',
    week1Content.content_pieces || [],
    true,
    week1Content.emotional_support || '',
  );
  wrapper.appendChild(week1);

  // Weeks 2-4: collapsed placeholders
  remainingWeeks.forEach(w => {
    wrapper.appendChild(renderWeekPlaceholder(w.week, w.theme, w.pieces));
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

  if (piece.script) {
    const scriptDiv = document.createElement('div');
    scriptDiv.className = 'content-piece__script';
    scriptDiv.textContent = piece.script;
    details.appendChild(scriptDiv);
  }

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

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
