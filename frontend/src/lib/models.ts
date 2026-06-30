// Single canonical model surfaced in the UI. Other models still live in the
// database and the backend exposes them via /v1/accuracy/summary?model=..., but
// the dashboard intentionally pins one to keep the experience focused.
export const CANONICAL_MODEL = "ensemble-v1";
