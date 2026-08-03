export interface DecisionSummary {
  decision_id: string;
  decision_time: string;
  decision: string;
  probability: number;
  risk_band: string;
  selected_intervention: string | null;
  confidence: number;
  trigger: string;
}

export interface ActiveSession {
  session_id: string;
  user_id: string | null;
  started_at: string;
  last_event_at: string | null;
  device_type: string | null;
  referral_source: string | null;
  current_route: string | null;
  cart_value: number;
  item_count: number;
  event_count: number;
  latest_decision: DecisionSummary | null;
}

export interface ActiveSessionsResponse {
  sessions: ActiveSession[];
  count: number;
  generated_at: string;
}

export interface DashboardEvent {
  id: string;
  type: "event_ingested" | "decision_made" | "decision_updated" | "intervention_shown" | "outcome_recorded";
  data: Record<string, unknown>;
}

export type DashboardStreamStatus = "connecting" | "connected" | "reconnecting";

export interface SessionEvent {
  event_id: string;
  event_type: string;
  sequence_no: number;
  product_id: string | null;
  client_timestamp: string;
  server_timestamp: string;
  metadata: Record<string, unknown>;
  is_late: boolean;
}

export interface FeatureSnapshot {
  snapshot_id: string | null;
  computed_at: string;
  feature_schema_version: string;
  features: Record<string, number>;
  source?: "LIVE" | "PERSISTED";
  trigger_event_id?: string | null;
}

export interface CartContext {
  value: number;
  mrp_total: number;
  item_count: number;
  delivery_fee: number;
  promo_code: string | null;
  first_add_at: string | null;
  items: Array<{
    product_id: string;
    title: string | null;
    brand: string | null;
    quantity: number;
    unit_price: number;
    variant: string | null;
  }>;
}

export interface SessionDetailResponse {
  session: {
    session_id: string;
    user_id: string | null;
    started_at: string;
    ended_at: string | null;
    last_event_at: string | null;
    device_type: string | null;
    referral_source: string | null;
    current_route: string | null;
    outcome: string;
  };
  timeline: SessionEvent[];
  cart: CartContext;
  counters: Record<string, number>;
  feature_snapshot: FeatureSnapshot;
  decisions: DecisionSummary[];
  outcomes: Record<string, DecisionOutcome | null>;
  interventions: Record<string, unknown>;
}

export interface DecisionOutcome {
  intervention_shown: boolean;
  clicked: boolean;
  dismissed: boolean;
  order_completed: boolean;
  time_to_purchase_seconds: number | null;
  discount_cost: number;
  estimated_margin: number | null;
  recorded_at: string;
  impression: { shown_at: string; surface: string; channel: string } | null;
}

export interface RootCauseResult {
  cause: string;
  probability: number;
  evidence_keys: string[];
}

export interface DashboardCandidate {
  intervention: string;
  display_name: string;
  generated: boolean;
  cost_level: string | null;
  intrusiveness: number | null;
  policy_status: string;
  policy_reasons: string[];
  stopped_at_rule: string | null;
  replacement: string | null;
  utility_score: number | null;
  utility_breakdown: Record<string, number>;
  confidence: number | null;
  channel: string | null;
  selected: boolean;
  explanation: string | null;
}

export interface ExplanationTrailData {
  observations: Array<{
    feature: string;
    value: number;
    shap: number;
    statement: string;
  }>;
  risk: { statement: string };
  inference: { root_cause: string; probability: number; statement: string };
  action: {
    decision: string;
    intervention: string;
    channel: string | null;
    confidence: number;
    statement: string;
  };
  rejected: Array<{
    intervention: string;
    status: string;
    reasons: string[];
    statement: string;
  }>;
  uncertainty: { cause_margin: number; statement: string };
  versions: Record<string, string>;
  rendered_by: string;
  rendered_text?: string;
}

export interface DecisionTraceResponse {
  decision_id: string;
  session_id: string;
  trace_id: string;
  decision_time: string;
  trigger: string;
  risk: {
    probability: number;
    band: string;
    model_version: string;
    statement: string;
  };
  root_causes: RootCauseResult[];
  candidates: DashboardCandidate[];
  policy_results: Array<Record<string, unknown>>;
  utility_scores: Array<{
    intervention: string;
    score: number;
    confidence: number;
    score_breakdown: Record<string, number>;
    channel: string | null;
  }>;
  final: {
    decision: string;
    selected_intervention: string | null;
    channel: string | null;
    confidence: number;
  };
  explanation: ExplanationTrailData;
  feature_snapshot: FeatureSnapshot | null;
  model_versions: Record<string, string>;
  latency_ms: Record<string, number>;
  outcome: DecisionOutcome | null;
  audit_answers: {
    elevated_risk: string;
    root_cause: string;
    selected_intervention: string;
    rejected_interventions: string[];
    discount_not_offered: string;
    uncertainty: string;
    versions: Record<string, string>;
  };
}

export interface ModelMetricsResponse {
  models: Array<{
    model_id: string;
    model_name: string;
    model_version: string;
    model_type: string;
    status: string;
    feature_schema_version: string;
    training_data_version: string;
    trained_at: string;
    promoted_at: string | null;
    metrics: Record<string, number | string | boolean>;
    notes: string | null;
  }>;
  count: number;
  generated_at: string;
}

export interface RuntimeMetricsResponse {
  counters: Record<string, {
    total: number;
    by_label: Record<string, number>;
  }>;
  latency_ms: Record<string, {
    count: number;
    p50: number;
    p95: number;
    p99: number;
    max: number;
  }>;
  gauges: Record<string, number>;
  drift: {
    observations: number;
    mean_predicted_probability: number | null;
    feature_psi: Record<string, number>;
    drift_suspected: boolean;
    warning_features: string[];
    baseline_available: boolean;
    automated_action: false;
  };
}

export interface LatencyPercentiles {
  count: number;
  p50: number;
  p95: number;
  p99: number;
  max: number;
}

export interface DecisionOverviewResponse {
  decisions: number;
  sessions: number;
  by_decision: Record<string, number>;
  by_intervention: Record<string, number>;
  by_cause: Record<string, number>;
  by_risk_band: Record<string, number>;
  intervention_rate: number;
  restraint_rate: number;
  mean_probability: number | null;
  mean_confidence: number | null;
  outcomes: {
    shown: number;
    clicked: number;
    dismissed: number;
    converted: number;
    ctr: number;
    dismissal_rate: number;
  };
  discount_spend: number;
  latency_ms: Record<string, LatencyPercentiles>;
  generated_at: string;
}

export interface ScenarioExpectation {
  session_id: string;
  expected: Record<string, string>;
}

export interface DemoScenario {
  scenario: string;
  title: string;
  proves: string;
  detail: string;
  session_count: number;
  event_count: number;
  expectations: ScenarioExpectation[];
}

export interface ScenarioStep {
  session_id: string;
  trigger: string;
  decision_id: string | null;
  decision: string | null;
  intervention: string | null;
  dominant_cause: string | null;
  probability: number | null;
  confidence: number | null;
  experiment_group: string | null;
  channel: string | null;
  rendered_text: string | null;
  expected: Record<string, string>;
  mismatches: Record<string, { expected: string; actual: string }>;
  passed: boolean;
}

export interface ScenarioRunResponse {
  scenario: string;
  title: string;
  proves: string;
  detail: string;
  run_key: string;
  passed: boolean;
  duration_ms: number;
  steps: ScenarioStep[];
}

export interface SimulateResponse {
  requested_sessions: number;
  totals: Record<string, number>;
  by_scenario: Record<string, number>;
  response_model: Record<string, number | string>;
  disclaimer: string;
}

export interface ExperimentMetricsResponse {
  experiment: {
    experiment_id: string;
    name: string;
    status: string;
    traffic_split: number;
    control_group: string;
    treatment_group: string;
  };
  arms: Record<string, {
    group: string;
    sessions: number;
    decisions: number;
    interventions_shown: number;
    intervention_rate: number;
    ctr: number;
    dismissal_rate: number;
    conversion_rate: number;
    mean_time_to_purchase_seconds: number | null;
    total_discount_cost: number;
    total_revenue: number;
    estimated_margin: number;
    margin_per_session: number;
    interventions_per_session: number;
  }>;
  uplift: {
    absolute: number;
    relative: number | null;
    ci95: number | null;
    label: string;
  };
}
