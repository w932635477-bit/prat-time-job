// starting-point/static/js/phases/growth.js
// Phase 5: Growth output renderer (enhanced)

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.className = 'output-card fade-in';
  wrapper.setAttribute('data-phase', '5');

  const plan = data.growth_plan || {};

  if (plan.deal_review) {
    wrapper.appendChild(makeField('首单复盘', plan.deal_review));
  }

  if (plan.next_action_today) {
    wrapper.appendChild(makeField('今天做什么', plan.next_action_today));
  }

  const testimonial = plan.testimonial_to_content;
  if (testimonial) {
    const items = [];
    if (typeof testimonial === 'object') {
      if (testimonial.approach) items.push(makeField('方法', testimonial.approach));
      if (testimonial.content_template) items.push(makeCopyField('内容模板', testimonial.content_template));
      if (testimonial.when_to_post) items.push(makeField('发布时机', testimonial.when_to_post));
    } else {
      items.push(makeField('口碑变内容', String(testimonial)));
    }
    wrapper.appendChild(makeSection('好评变内容', items));
  }

  const pricingAdj = plan.pricing_adjustment;
  if (pricingAdj) {
    const items = [];
    if (typeof pricingAdj === 'object') {
      if (pricingAdj.current_price) items.push(makeField('当前价格', pricingAdj.current_price));
      if (pricingAdj.suggested_price) items.push(makeField('建议新价格', pricingAdj.suggested_price));
      if (pricingAdj.when_to_raise) items.push(makeField('涨价时机', pricingAdj.when_to_raise));
      if (pricingAdj.how_to_communicate) items.push(makeCopyField('涨价话术', pricingAdj.how_to_communicate));
    } else {
      items.push(makeField('定价调整', String(pricingAdj)));
    }
    wrapper.appendChild(makeSection('定价调整', items));
  }

  const referral = plan.referral_mechanism;
  if (referral) {
    const items = [];
    if (typeof referral === 'object') {
      if (referral.script) items.push(makeCopyField('推荐话术', referral.script));
      if (referral.incentive) items.push(makeField('推荐人好处', referral.incentive));
      if (referral.timing) items.push(makeField('开口时机', referral.timing));
    } else {
      items.push(makeField('转介绍', String(referral)));
    }
    wrapper.appendChild(makeSection('转介绍', items));
  }

  const repeat = plan.repeat_purchase;
  if (repeat) {
    const items = [];
    if (typeof repeat === 'object') {
      if (repeat.product_idea) items.push(makeField('复购产品', repeat.product_idea));
      if (repeat.pitch) items.push(makeCopyField('推销话术', repeat.pitch));
      if (repeat.pricing) items.push(makeField('复购价格', repeat.pricing));
    } else {
      items.push(makeField('复购设计', String(repeat)));
    }
    wrapper.appendChild(makeSection('复购设计', items));
  }

  return wrapper;
}

export function getSummary(data) {
  return '增长计划已生成';
}

function makeSection(title, children) {
  const section = document.createElement('div');
  section.className = 'output-card__section';
  const heading = document.createElement('div');
  heading.className = 'output-card__title';
  heading.textContent = title;
  section.appendChild(heading);
  children.forEach(c => section.appendChild(c));
  return section;
}

function makeField(label, value) {
  const field = document.createElement('div');
  field.className = 'output-card__field';
  if (label) {
    const lbl = document.createElement('div');
    lbl.className = 'output-card__label';
    lbl.textContent = label;
    field.appendChild(lbl);
  }
  const val = document.createElement('div');
  val.className = 'output-card__value';
  val.textContent = value;
  field.appendChild(val);
  return field;
}

function makeCopyField(label, text) {
  const field = document.createElement('div');
  field.className = 'output-card__field';
  if (label) {
    const lbl = document.createElement('div');
    lbl.className = 'output-card__label';
    lbl.textContent = label;
    field.appendChild(lbl);
  }
  const row = document.createElement('div');
  row.className = 'output-card__value-row';
  const val = document.createElement('div');
  val.className = 'output-card__value';
  val.textContent = text;
  row.appendChild(val);
  const btn = document.createElement('button');
  btn.className = 'copy-btn';
  btn.textContent = '复制';
  btn.addEventListener('click', () => copyToClipboard(text, btn));
  row.appendChild(btn);
  field.appendChild(row);
  return field;
}

function copyToClipboard(text, btn) {
  const doCopy = (str) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(str);
    }
    const ta = document.createElement('textarea');
    ta.value = str;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    return Promise.resolve();
  };
  doCopy(text).then(() => {
    btn.textContent = '已复制';
    setTimeout(() => { btn.textContent = '复制'; }, 1500);
  });
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
