// starting-point/static/js/phases/first-deal.js
// Phase 4: First Deal output renderer (enhanced)

export function renderOutput(data) {
  const wrapper = document.createElement('div');
  wrapper.className = 'output-card fade-in';
  wrapper.setAttribute('data-phase', '4');

  const toolkit = data.toolkit || data.product_card || {};

  if (toolkit.scenario) {
    wrapper.appendChild(makeField('当前场景', toolkit.scenario));
  }

  const templates = toolkit.communication_templates || {};
  if (Object.keys(templates).length > 0) {
    wrapper.appendChild(makeSection('沟通话术', [
      templates.first_response && makeCopyField('客户第一次私信', templates.first_response),
      templates.price_inquiry && makeCopyField('客户问价', templates.price_inquiry),
      templates.service_inquiry && makeCopyField('客户问服务', templates.service_inquiry),
      templates.hesitant_client && makeCopyField('客户犹豫', templates.hesitant_client),
      templates.closing_line && makeCopyField('引导下单', templates.closing_line),
    ].filter(Boolean)));
  }

  const pf = toolkit.pricing_formula;
  if (pf) {
    const items = [];
    if (typeof pf === 'object') {
      if (pf.formula) items.push(makeField('报价公式', pf.formula));
      if (pf.example) items.push(makeField('举例', pf.example));
      if (pf.floor_price) items.push(makeField('最低价', pf.floor_price));
      if (pf.psychological_anchor) items.push(makeField('心理锚定技巧', pf.psychological_anchor));
    } else {
      items.push(makeField('报价公式', String(pf)));
    }
    wrapper.appendChild(makeSection('定价策略', items));
  }

  const methods = toolkit.payment_methods || [];
  if (methods.length > 0) {
    wrapper.appendChild(makeSection('收款方式', methods.map(m => {
      const parts = [m.method || ''];
      if (m.how) parts.push(`操作：${m.how}`);
      if (m.when_to_collect) parts.push(`收款时机：${m.when_to_collect}`);
      if (m.tip) parts.push(`注意：${m.tip}`);
      return makeField(m.method || '收款', parts.join(' | '));
    })));
  }

  const checklist = toolkit.delivery_checklist || [];
  if (checklist.length > 0) {
    wrapper.appendChild(makeSection('交付清单', checklist.map(item => {
      if (typeof item === 'string') {
        return makeField('', `☐ ${esc(item)}`);
      }
      const label = item.step || '';
      const time = item.estimated_time ? `（${esc(item.estimated_time)}）` : '';
      const tip = item.tip ? ` — ${esc(item.tip)}` : '';
      return makeField('', `☐ ${esc(label)}${time}${tip}`);
    })));
  }

  const post = toolkit.post_delivery;
  if (post) {
    const items = [];
    if (typeof post === 'object') {
      if (post.thank_you_message) items.push(makeCopyField('感谢话术', post.thank_you_message));
      if (post.review_request) items.push(makeCopyField('请客户好评', post.review_request));
      if (post.next_step_hint) items.push(makeCopyField('引导复购', post.next_step_hint));
    } else {
      items.push(makeField('交付后', String(post)));
    }
    wrapper.appendChild(makeSection('交付后', items));
  }

  return wrapper;
}

export function getSummary(data) {
  return '首单工具包已生成';
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
