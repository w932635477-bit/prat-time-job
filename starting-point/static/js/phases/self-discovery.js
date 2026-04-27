// starting-point/static/js/phases/self-discovery.js
// Phase 1: Self Discovery output renderer

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '1');

  const assets = data.asset_map || data.assets || [];
  const items = Array.isArray(assets)
    ? assets.map(renderAsset).join('')
    : '<div class="output-card__value">资产已识别</div>';

  card.innerHTML = `
    <div class="output-card__title">发现金矿完成</div>
    <div class="output-card__subtitle">你的可定价资产</div>
    ${items}
  `;
  return card;
}

function renderAsset(asset) {
  if (typeof asset === 'string') {
    return `<div class="output-card__field"><div class="output-card__value">${esc(asset)}</div></div>`;
  }
  const name = asset.name || asset.skill || '资产';
  const price = asset.market_price || asset.price_range || '';
  const evidence = asset.evidence || '';
  return `
    <div class="output-card__field">
      <div class="result-item__name">${esc(name)}</div>
      ${price ? `<div class="result-item__value">${esc(price)}</div>` : ''}
      ${evidence ? `<div class="result-item__evidence">${esc(evidence)}</div>` : ''}
    </div>
  `;
}

export function getSummary(data) {
  const assets = data.asset_map || data.assets || [];
  if (Array.isArray(assets) && assets.length > 0) {
    return `发现 ${assets.length} 项可定价资产`;
  }
  return '资产已识别';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
