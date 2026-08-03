import { useDashboardResource } from "./useDashboardStream";
import type { DecisionTraceResponse } from "../types/dashboard";

export function useDecisionTrace(decisionId: string, language = "en") {
  return useDashboardResource<DecisionTraceResponse>(
    `/api/v1/dashboard/decisions/${encodeURIComponent(decisionId)}`,
    language,
  );
}
