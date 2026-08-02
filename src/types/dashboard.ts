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
  type: "event_ingested" | "decision_made" | "decision_updated";
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
  interventions: Record<string, unknown>;
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
