import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { SessionDetailResponse } from "../../types/dashboard";
import SessionReplay from "./SessionReplay";


const detail: SessionDetailResponse = {
  session: {
    session_id: "session-1",
    user_id: null,
    started_at: "2026-08-03T08:00:00Z",
    ended_at: null,
    last_event_at: "2026-08-03T08:01:00Z",
    device_type: "DESKTOP",
    referral_source: "DIRECT",
    current_route: "/cart",
    outcome: "OPEN",
  },
  timeline: [{
    event_id: "event-1",
    event_type: "ITEM_ADDED_TO_CART",
    sequence_no: 1,
    product_id: "p-1006",
    client_timestamp: "2026-08-03T08:00:00Z",
    server_timestamp: "2026-08-03T08:00:01Z",
    metadata: {},
    is_late: false,
  }],
  cart: {
    value: 8499,
    mrp_total: 8999,
    item_count: 1,
    delivery_fee: 0,
    promo_code: null,
    first_add_at: "2026-08-03T08:00:00Z",
    items: [],
  },
  counters: {},
  feature_snapshot: {
    snapshot_id: "snapshot-1",
    computed_at: "2026-08-03T08:01:00Z",
    feature_schema_version: "fs-v1",
    features: {},
  },
  decisions: [{
    decision_id: "decision-1",
    decision_time: "2026-08-03T08:01:00Z",
    decision: "INTERVENE",
    probability: 0.88,
    risk_band: "HIGH",
    selected_intervention: "REVIEW_SUMMARY",
    confidence: 0.82,
    trigger: "REVIEW_OPENED",
  }],
  outcomes: {
    "decision-1": {
      intervention_shown: true,
      clicked: false,
      dismissed: false,
      order_completed: true,
      time_to_purchase_seconds: 45,
      discount_cost: 0,
      estimated_margin: 1527.82,
      recorded_at: "2026-08-03T08:02:00Z",
      impression: null,
    },
  },
  interventions: {},
};

vi.mock("../../hooks/useSessionDetail", () => ({
  useSessionDetail: () => ({ data: detail, loading: false, error: null }),
}));

describe("SessionReplay", () => {
  it("renders the event trail, decision, and resolved outcome", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard/sessions/session-1/replay"]}>
        <Routes>
          <Route path="/dashboard/sessions/:sessionId/replay" element={<SessionReplay />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Session replay" })).toBeInTheDocument();
    expect(screen.getByText("ITEM ADDED TO CART")).toBeInTheDocument();
    expect(screen.getByText("INTERVENE · REVIEW_SUMMARY")).toBeInTheDocument();
    expect(screen.getByText("Converted")).toBeInTheDocument();
  });
});
