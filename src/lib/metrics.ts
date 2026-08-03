/**
 * Presentation helpers for the operations dashboard.
 *
 * Model metrics arrive as full-precision floats. Printing `0.7938129002522887`
 * on a page a reviewer is meant to read tells them nothing and looks unfinished,
 * so everything on screen goes through here.
 */

/** Three significant decimals — the resolution these metrics actually carry. */
export function formatMetric(value: number | string | boolean): string {
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "string") return value;
  if (!Number.isFinite(value)) return "—";
  if (Number.isInteger(value)) return value.toLocaleString("en-IN");
  if (Math.abs(value) >= 1000) return value.toLocaleString("en-IN", { maximumFractionDigits: 1 });
  return value.toFixed(3);
}

/** A probability as whole percent, clamped away from unearned certainty. */
export function formatProbability(value: number, digits = 0): string {
  const clamped = Math.min(0.99, Math.max(0.01, value));
  return `${(clamped * 100).toFixed(digits)}%`;
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatMs(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  if (value >= 10) return `${value.toFixed(0)} ms`;
  return `${value.toFixed(2)} ms`;
}

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatRupees(value: number): string {
  return inr.format(value);
}

export function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b[a-z]/g, (character) => character.toUpperCase());
}

export function timeAgo(value: string | null): string {
  if (!value) return "No events yet";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1_000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3_600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3_600)}h ago`;
  return `${Math.floor(seconds / 86_400)}d ago`;
}

/** What each headline model metric means, and which direction is good. */
export const METRIC_GUIDE: Record<string, { label: string; hint: string; higherIsBetter: boolean }> = {
  roc_auc: {
    label: "ROC-AUC",
    hint: "Ranking quality: chance a true abandoner scores above a converter.",
    higherIsBetter: true,
  },
  pr_auc: {
    label: "PR-AUC",
    hint: "Precision/recall balance on the positive class.",
    higherIsBetter: true,
  },
  log_loss: {
    label: "Log loss",
    hint: "Penalty for confident wrong answers. Lower is better.",
    higherIsBetter: false,
  },
  brier: {
    label: "Brier score",
    hint: "Mean squared error of the probability itself. Lower is better.",
    higherIsBetter: false,
  },
  ece_15: {
    label: "ECE (15 bins)",
    hint: "Calibration gap: how far stated probabilities drift from observed rates.",
    higherIsBetter: false,
  },
  micro_f1: {
    label: "Micro-F1",
    hint: "Overall accuracy across all root-cause labels.",
    higherIsBetter: true,
  },
  macro_f1: {
    label: "Macro-F1",
    hint: "Accuracy averaged per label, so rare causes count equally.",
    higherIsBetter: true,
  },
  hamming_loss: {
    label: "Hamming loss",
    hint: "Fraction of label slots predicted wrongly. Lower is better.",
    higherIsBetter: false,
  },
  top2_recall: {
    label: "Top-2 recall",
    hint: "How often the true cause appears in the two highest-ranked causes.",
    higherIsBetter: true,
  },
  unknown_coverage: {
    label: "Unknown coverage",
    hint: "Share of sessions the model declines to diagnose rather than guess.",
    higherIsBetter: true,
  },
  mean_causes_abandoning: {
    label: "Mean causes",
    hint: "Average number of causes predicted per abandoning session.",
    higherIsBetter: true,
  },
};

/** Stage names presented as the agents the case study asks us to orchestrate. */
export const AGENT_STAGES: Record<string, { name: string; role: string }> = {
  features: {
    name: "Feature Agent",
    role: "Rebuilds the canonical 67-signal vector from the event log",
  },
  risk: {
    name: "Risk Agent",
    role: "Scores calibrated abandonment probability with SHAP attribution",
  },
  root_cause: {
    name: "Reasoning Agent",
    role: "Infers which supported causes the evidence actually backs",
  },
  policy_and_rank: {
    name: "Policy & Recommendation Agents",
    role: "Screens every candidate against safety rules, then ranks by utility",
  },
  explain: {
    name: "Explainability Agent",
    role: "Builds the grounded justification trail from the persisted trace",
  },
};
