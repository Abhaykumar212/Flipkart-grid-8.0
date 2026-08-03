/**
 * Observable store of pipeline runs, for the /pipeline console.
 *
 * A "run" is one pass of the system: client telemetry -> feature engineering ->
 * model -> SHAP -> risk gate -> root cause agent. The backend returns its own
 * spans; the frontend prepends the client-side telemetry span and stores the
 * merged timeline.
 *
 * Adding a future stage (e.g. the Phase 3 intervention agent) means adding one
 * member to PipelineStage and having that agent emit spans — the console
 * renders whatever it receives without modification.
 */

export type PipelineStage =
  | "telemetry"
  | "feature_engineering"
  | "model_inference"
  | "shap_attribution"
  | "risk_gate"
  | "root_cause_agent"
  | "intervention_ranking"
  | "critic_verdict"
  | "explanation_scored"
  | "delivery_decision";

export type SpanStatus = "ok" | "running" | "skipped" | "error" | "rate_limited";

export interface TraceSpan {
  id: string;
  stage: PipelineStage | string;
  label: string;
  status: SpanStatus;
  /** Epoch milliseconds. */
  started_at: number;
  duration_ms: number;
  source: "frontend" | "backend";
  detail: Record<string, unknown>;
}

export type RunStatus =
  | "success"
  | "gate_not_met"
  | "critic_blocked"
  | "rate_limited"
  | "not_configured"
  | "error"
  | "running";

/** Mirrors backend/schemas.py RootCauseAnalysis. */
export interface RootCauseAnalysis {
  primary_root_cause: {
    category: string;
    headline: string;
    explanation: string;
    supporting_evidence: Array<{
      signal: string;
      observed_value: string;
      shap_contribution: number;
      why_it_matters: string;
    }>;
  };
  contributing_factors: Array<{ category: string; headline: string; signal: string }>;
  shopper_narrative: string;
  confidence: "high" | "medium" | "low";
  confidence_reasoning: string;
  recommended_levers: Array<{
    lever_id: string;
    rationale: string;
    expected_effect: string;
    priority: number;
  }>;
  levers_to_avoid: Array<{ lever_id: string; reason: string }>;
}

export interface GateDecision {
  fired: boolean;
  threshold: number;
  reason: string;
  checks: Record<string, unknown>;
}

/** Mirrors backend/schemas.py ExplanationFactor. */
export interface ExplanationFactor {
  factor: string;
  observation: string;
  contribution: number;
}

/** Mirrors backend/schemas.py RecommendedIntervention. */
export interface RecommendedIntervention {
  lever_id: string;
  headline: string;
  rationale: string;
  score: number;
  confidence: "high" | "medium" | "low";
  expected_conversion_gain: number;
  business_cost: "low" | "medium" | "high";
  llm_endorsed: boolean;
  explanation: ExplanationFactor[];
}

/** Mirrors backend/schemas.py InterventionPlan — the Phase 3 handoff. */
export interface InterventionPlan {
  top_interventions: RecommendedIntervention[];
  fallback_intervention: RecommendedIntervention | null;
  excluded_lever_ids: string[];
}

/**
 * Every reason `selectSurface` (src/lib/interventionPolicy.ts) can hold back an
 * intervention, plus `gate_held` for the case where the RCA gate never even
 * ran the diagnosis. Kept here rather than in interventionPolicy.ts so both
 * that module and the ledger store can depend on it without a cycle.
 */
export type NoInterventionReason =
  | "gate_held"
  | "low_confidence"
  | "margin_approval_required"
  | "fatigue_cap"
  | "cooldown"
  | "no_lever_above_threshold";

/**
 * The delivery layer's outcome for one pipeline run — "nothing shown" is
 * recorded exactly like "something shown", never left as an absence. Attached
 * after the fact via `attachDecision` once the client-side policy has run, so
 * it renders as a span in the waterfall and a panel in the RCA report just
 * like any backend-produced stage.
 */
export interface DeliveryDecision {
  outcome: "delivered" | "held";
  /** Demo-facing summary line, e.g. "Decision: no intervention — user likely to convert unaided (p=0.019)". */
  headline: string;
  /** Supporting detail — the specific check or gate reason behind the headline. */
  detail: string;
  reason?: NoInterventionReason;
  rootCause: string | null;
  leverId?: string;
  intensity?: number;
  surface?: string;
}

export interface PipelineRun {
  id: string;
  startedAt: number;
  status: RunStatus;
  trigger: "auto" | "manual";
  scenarioLabel?: string;
  probability: number | null;
  riskTier: string | null;
  gate: GateDecision | null;
  analysis: RootCauseAnalysis | null;
  interventionPlan: InterventionPlan | null;
  deliveryDecision: DeliveryDecision | null;
  modelUsed: string | null;
  llmLatencyMs: number;
  message: string | null;
  spans: TraceSpan[];
}

export interface RootCauseResponse {
  pipeline_run_id: string;
  status: Exclude<RunStatus, "running">;
  prediction: {
    abandonment_probability: number;
    risk_tier: string;
    confidence_score: number;
    feature_impacts: Record<string, number>;
    top_contributing_features: Array<{ feature: string; shap_value: number }>;
  };
  gate: GateDecision;
  analysis: RootCauseAnalysis | null;
  intervention_plan: InterventionPlan | null;
  model_used: string | null;
  latency_ms: number;
  message: string | null;
  trace: TraceSpan[];
}

/** Keep memory bounded during a long demo. */
const MAX_RUNS = 25;

class PipelineTraceStore {
  private runs: PipelineRun[] = [];
  private listeners = new Set<() => void>();
  /** Cached immutable snapshot so useSyncExternalStore doesn't loop. */
  private snapshot: PipelineRun[] = [];

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): PipelineRun[] => this.snapshot;

  private emit(): void {
    this.snapshot = [...this.runs];
    this.listeners.forEach((listener) => listener());
  }

  /** Open a run as soon as the request leaves the browser, so the UI can show it in flight. */
  startRun(trigger: "auto" | "manual", scenarioLabel?: string): string {
    const id = `local_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
    const run: PipelineRun = {
      id,
      startedAt: Date.now(),
      status: "running",
      trigger,
      scenarioLabel,
      probability: null,
      riskTier: null,
      gate: null,
      analysis: null,
      interventionPlan: null,
      deliveryDecision: null,
      modelUsed: null,
      llmLatencyMs: 0,
      message: null,
      spans: [
        {
          id: `${id}_telemetry`,
          stage: "telemetry",
          label: "Collect session telemetry",
          status: "ok",
          started_at: Date.now(),
          duration_ms: 0,
          source: "frontend",
          detail: {},
        },
      ],
    };
    this.runs = [run, ...this.runs].slice(0, MAX_RUNS);
    this.emit();
    return id;
  }

  /** Attach the client-side feature vector to the telemetry span. */
  attachTelemetry(runId: string, detail: Record<string, unknown>, durationMs: number): void {
    const run = this.runs.find((r) => r.id === runId);
    if (!run) return;
    const span = run.spans.find((s) => s.stage === "telemetry");
    if (span) {
      span.detail = detail;
      span.duration_ms = durationMs;
    }
    this.emit();
  }

  /** Merge the backend's spans and result into an in-flight run. */
  completeRun(runId: string, response: RootCauseResponse): void {
    const index = this.runs.findIndex((r) => r.id === runId);
    if (index === -1) return;
    const run = this.runs[index];
    this.runs[index] = {
      ...run,
      status: response.status,
      probability: response.prediction?.abandonment_probability ?? null,
      riskTier: response.prediction?.risk_tier ?? null,
      gate: response.gate,
      analysis: response.analysis,
      interventionPlan: response.intervention_plan,
      modelUsed: response.model_used,
      llmLatencyMs: response.latency_ms,
      message: response.message,
      // Client telemetry span first, then the backend timeline in order.
      spans: [...run.spans, ...response.trace],
    };
    this.emit();
  }

  /**
   * Attach the delivery layer's outcome once the client-side policy has run.
   * Appends a `delivery_decision` span so it renders in the waterfall exactly
   * like a backend-produced stage, alongside the structured `deliveryDecision`
   * field the RCA report and ledger read directly.
   */
  attachDecision(runId: string, decision: DeliveryDecision): void {
    const index = this.runs.findIndex((r) => r.id === runId);
    if (index === -1) return;
    const run = this.runs[index];
    const span: TraceSpan = {
      id: `${runId}_delivery_decision`,
      stage: "delivery_decision",
      label: decision.headline,
      status: "ok",
      started_at: Date.now(),
      duration_ms: 0,
      source: "frontend",
      detail: { ...decision },
    };
    const spans = run.spans.some((s) => s.stage === "delivery_decision")
      ? run.spans.map((s) => (s.stage === "delivery_decision" ? span : s))
      : [...run.spans, span];
    this.runs[index] = { ...run, deliveryDecision: decision, spans };
    this.emit();
  }

  failRun(runId: string, message: string): void {
    const index = this.runs.findIndex((r) => r.id === runId);
    if (index === -1) return;
    this.runs[index] = { ...this.runs[index], status: "error", message };
    this.emit();
  }

  /** A run superseded by a newer request. Dropped rather than shown as failed. */
  abortRun(runId: string): void {
    this.runs = this.runs.filter((run) => run.id !== runId);
    this.emit();
  }

  clear(): void {
    this.runs = [];
    this.emit();
  }
}

export const pipelineTrace = new PipelineTraceStore();

/** Total wall time of a run, taken from span durations. */
export function runDurationMs(run: PipelineRun): number {
  return run.spans.reduce((total, span) => total + span.duration_ms, 0);
}

export const STAGE_LABELS: Record<string, string> = {
  telemetry: "Session telemetry",
  feature_engineering: "Feature engineering",
  model_inference: "XGBoost inference",
  shap_attribution: "SHAP attribution",
  risk_gate: "Risk gate",
  root_cause_agent: "Root cause agent",
  intervention_ranking: "Intervention ranking",
  critic_verdict: "Critic review",
  explanation_scored: "Explanation grounding",
  delivery_decision: "Delivery decision",
};
