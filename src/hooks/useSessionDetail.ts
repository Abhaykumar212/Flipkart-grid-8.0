import { useDashboardResource } from "./useDashboardStream";
import type { SessionDetailResponse } from "../types/dashboard";

export function useSessionDetail(sessionId: string) {
  return useDashboardResource<SessionDetailResponse>(
    `/api/v1/dashboard/sessions/${encodeURIComponent(sessionId)}`,
  );
}
