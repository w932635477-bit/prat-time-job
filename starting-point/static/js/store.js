// starting-point/static/js/store.js
// State management with localStorage persistence

const STORAGE_KEY = 'starting_point_state';

function generateId() {
  return 'u_' + crypto.randomUUID();
}

function createInitialState() {
  return {
    userId: generateId(),
    currentPhase: 0,
    currentStep: 0,
    phaseResults: {},
    contentPlan: null,
    isPaused: false,
    chatHistory: [],
  };
}

export function init() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      // corrupted, start fresh
    }
  }
  const state = createInitialState();
  save(state);
  return state;
}

export function save(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function advanceStep(state) {
  const next = { ...state, currentStep: state.currentStep + 1 };
  save(next);
  return next;
}

export function advancePhase(state) {
  const next = { ...state, currentPhase: state.currentPhase + 1, currentStep: 0 };
  save(next);
  return next;
}

export function recordPhaseResult(state, phaseIndex, summary, data) {
  const next = {
    ...state,
    phaseResults: {
      ...state.phaseResults,
      [phaseIndex]: { summary, data },
    },
  };
  save(next);
  return next;
}

export function goBack(state, phaseIndex, stepIndex) {
  const next = { ...state, currentPhase: phaseIndex, currentStep: stepIndex };
  save(next);
  return next;
}

export function pause(state) {
  const next = { ...state, isPaused: true };
  save(next);
  return next;
}

export function resume(state) {
  const next = { ...state, isPaused: false };
  save(next);
  return next;
}

export function appendHistory(state, role, content) {
  const entry = { role, content, ts: Date.now() };
  const next = {
    ...state,
    chatHistory: [...state.chatHistory, entry],
  };
  save(next);
  return next;
}

export function reset() {
  localStorage.removeItem(STORAGE_KEY);
  const state = createInitialState();
  save(state);
  return state;
}
