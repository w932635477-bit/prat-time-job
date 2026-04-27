// starting-point/static/js/phases/first-deal.js
// Phase 4: First Deal output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '4');

  const toolkit = data.toolkit || data.product_card || {};
  const templates = toolkit.communication_templates || {};
  const formula = toolkit.pricing_formula || '';
  const checklist = toolkit.delivery_checklist || [];
  const postDelivery = toolkit.post_delivery || '';

  card.innerHTML = `
    <div class="output-card__title">首单工具包</div>
    ${templates.price_inquiry ? `<div class="output-card__field"><div class="output-card__label">客户问价时</div><div class="output-card__value">${esc(templates.price_inquiry)}</div></div>` : ''}
    ${templates.service_inquiry ? `<div class="output-card__field"><div class="output-card__label">客户问服务时</div><div class="output-card__value">${esc(templates.service_inquiry)}</div></div>` : ''}
    ${templates.hesitant_client ? `<div class="output-card__field"><div class="output-card__label">客户犹豫时</div><div class="output-card__value">${esc(templates.hesitant_client)}</div></div>` : ''}
    ${formula ? `<div class="output-card__field"><div class="output-card__label">报价公式</div><div class="output-card__value">${esc(formula)}</div></div>` : ''}
    ${checklist.length > 0 ? `<div class="output-card__field"><div class="output-card__label">交付清单</div>${checklist.map(s => `<div class="output-card__value">☐ ${esc(s)}</div>`).join('')}</div>` : ''}
    ${postDelivery ? `<div class="output-card__field"><div class="output-card__label">交付后引导反馈</div><div class="output-card__value">${esc(postDelivery)}</div></div>` : ''}
  `;
  return card;
}

export function getSummary(data) {
  return '首单工具包已生成';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
