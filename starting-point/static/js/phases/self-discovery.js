// starting-point/static/js/phases/self-discovery.js
// Phase 1: Self Discovery output renderer (with Market Radar)

export function renderOutput(data) {
  const card = document.createElement('div');
  card.className = 'output-card fade-in';
  card.setAttribute('data-phase', '1');

  const assets = data.asset_map || data.assets || [];
  const radar = data.market_radar || {};

  // Assets section
  const items = Array.isArray(assets)
    ? assets.map(renderAsset).join('')
    : '<div class="output-card__value">资产已识别</div>';

  // Market radar section
  let radarHtml = '';
  if (radar && Object.keys(radar).length > 0) {
    radarHtml = renderMarketRadar(radar);
  }

  card.innerHTML = `
    <div class="output-card__title">发现金矿完成</div>
    <div class="output-card__subtitle">你的可定价资产</div>
    ${items}
    ${radarHtml}
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

function renderMarketRadar(radar) {
  const sellers = radar.existing_sellers || [];
  const topics = radar.hot_topics || [];
  const priceRange = radar.price_range || '';
  const uniqueEdge = radar.unique_edge || '';
  const demandLevel = radar.demand_level || 'medium';
  const summary = radar.summary || '';

  const demandLabel = { high: '高', medium: '中', low: '低' }[demandLevel] || '中';
  const demandClass = `radar__badge--${demandLevel}`;

  return `
    <div class="radar-section">
      <div class="radar__title">行业雷达</div>
      ${summary ? `<div class="radar__summary">${esc(summary)}</div>` : ''}
      <div class="radar__demand-row">
        <span class="radar__label">市场需求</span>
        <span class="radar__badge ${demandClass}">${esc(demandLabel)}</span>
      </div>
      ${priceRange ? `
        <div class="radar__row">
          <span class="radar__label">市场定价</span>
          <span class="radar__value">${esc(priceRange)}</span>
        </div>
      ` : ''}
      ${uniqueEdge ? `
        <div class="radar__row">
          <span class="radar__label">你的优势</span>
          <span class="radar__value radar__value--highlight">${esc(uniqueEdge)}</span>
        </div>
      ` : ''}
      ${sellers.length > 0 ? `
        <div class="radar__block">
          <div class="radar__label">谁在卖类似服务</div>
          ${sellers.map(s => `<div class="radar__seller">${esc(s)}</div>`).join('')}
        </div>
      ` : ''}
      ${topics.length > 0 ? `
        <div class="radar__block">
          <div class="radar__label">热门话题</div>
          <div class="radar__tags">
            ${topics.map(t => `<span class="radar__tag">${esc(t)}</span>`).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

export function getSummary(data) {
  const assets = data.asset_map || data.assets || [];
  const radar = data.market_radar || {};
  const parts = [];
  if (Array.isArray(assets) && assets.length > 0) {
    parts.push(`发现 ${assets.length} 项可定价资产`);
  }
  if (radar && radar.demand_level) {
    const label = { high: '高', medium: '中', low: '低' }[radar.demand_level] || '中';
    parts.push(`市场需求${label}`);
  }
  return parts.join('，') || '资产已识别';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
