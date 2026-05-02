// starting-point/static/js/phases/index.js
// Phase definitions and ordering

export const PHASES = [
  { id: 'assessment',           name: '起跑评估', steps: 4 },
  { id: 'self_discovery',       name: '发现金矿', steps: 11 },
  { id: 'product_packaging',    name: '包装产品', steps: 4 },
  { id: 'customer_acquisition', name: '找到客户', steps: 4 },
  { id: 'first_deal',           name: '完成首单', steps: 5 },
  { id: 'growth',               name: '转起来',   steps: 5 },
];

export function getPhase(index) {
  return PHASES[index] || null;
}

export function getPhaseName(index) {
  return PHASES[index]?.name ?? '未知阶段';
}

export function getTotalPhases() {
  return PHASES.length;
}

// Lazy-load phase renderer modules
const rendererCache = {};

export async function getRenderer(phaseId) {
  if (rendererCache[phaseId]) return rendererCache[phaseId];
  const mod = await import(`./${phaseId}.js`);
  rendererCache[phaseId] = mod;
  return mod;
}
