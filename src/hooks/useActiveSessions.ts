import { useDashboardResource } from "./useDashboardStream";
import type { ActiveSessionsResponse } from "../types/dashboard";

export function useActiveSessions() {
  return useDashboardResource<ActiveSessionsResponse>("/api/v1/dashboard/sessions");
}
