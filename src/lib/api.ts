export interface ProblemDetail {
  type?: string;
  title?: string;
  status: number;
  detail: string;
  errors?: Array<{ loc: Array<string | number>; msg: string; type: string }>;
}

const configuredBase = import.meta.env.VITE_API_BASE?.trim();

export const API_BASE = (configuredBase || "http://localhost:8000").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalized}`;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(problem: ProblemDetail) {
    super(problem.detail || problem.title || `API request failed with ${problem.status}`);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) {
    let problem: ProblemDetail = {
      status: response.status,
      title: "Request failed",
      detail: `API request failed with ${response.status}`,
    };
    try {
      const body = (await response.json()) as Partial<ProblemDetail>;
      problem = {
        ...problem,
        ...body,
        status: response.status,
        detail: body.detail ?? problem.detail,
      };
    } catch {
      // A proxy/network error page is not problem+json; keep the normalized fallback.
    }
    throw new ApiError(problem);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function apiGet<T>(
  path: string,
  signal?: AbortSignal,
  headers?: Record<string, string>,
): Promise<T> {
  return request<T>(path, { method: "GET", signal, headers });
}

export function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}
