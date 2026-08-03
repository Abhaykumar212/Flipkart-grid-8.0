import { useDashboardResource } from "./useDashboardStream";
import type { DecisionOverviewResponse } from "../types/dashboard";

export function useOverview() {
  return useDashboardResource<DecisionOverviewResponse>("/api/v1/dashboard/overview");
}
