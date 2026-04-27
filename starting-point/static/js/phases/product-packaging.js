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
    <div class="output-card__title">${esc(name)}</div>
    ${tagline ? `<div class="output-card__subtitle">${esc(tagline)}</div>` : ''}
    ${target ? `<div class="output-card__field"><div class="output-card__label">目标客户</div><div class="output-card__value">${esc(target)}</div></div>` : ''}
    <div class="output-card__field">
      <div class="output-card__label">定价</div>
      ${pricing.trial_price ? `<div class="output-card__value">体验价: ${esc(pricing.trial_price)}</div>` : ''}
      ${pricing.standard_price ? `<div class="output-card__value">正式价: ${esc(pricing.standard_price)}</div>` : ''}
      ${pricing.package_price ? `<div class="output-card__value">套餐价: ${esc(pricing.package_price)}</div>` : ''}
    </div>
    ${flow.length > 0 ? `<div class="output-card__field"><div class="output-card__label">服务流程</div>${flow.map((s, i) => `<div class="output-card__value">${i + 1}. ${esc(s)}</div>`).join('')}</div>` : ''}
    ${deliverables ? `<div class="output-card__field"><div class="output-card__label">交付物</div><div class="output-card__value">${esc(deliverables)}</div></div>` : ''}
  `;
  return card;
}

export function getSummary(data) {
  const product = data.product_card || data.constraints || {};
  return product.service_name || '服务产品已设计';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
