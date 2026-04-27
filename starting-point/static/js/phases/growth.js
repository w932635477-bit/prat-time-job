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
    ${testimonial ? `<div class="output-card__field"><div class="output-card__label">口碑变内容</div><div class="output-card__value">${esc(testimonial)}</div></div>` : ''}
    ${pricingAdj ? `<div class="output-card__field"><div class="output-card__label">定价调整</div><div class="output-card__value">${esc(pricingAdj)}</div></div>` : ''}
    ${referral ? `<div class="output-card__field"><div class="output-card__label">转介绍机制</div><div class="output-card__value">${esc(referral)}</div></div>` : ''}
    ${repeat ? `<div class="output-card__field"><div class="output-card__label">复购设计</div><div class="output-card__value">${esc(repeat)}</div></div>` : ''}
  `;
  return card;
}

export function getSummary(data) {
  return '增长计划已生成';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
