function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? value as Record<string, unknown>
    : null;
}

function statement(value: unknown): string | null {
  const candidate = record(value)?.statement;
  return typeof candidate === "string" && candidate.trim() ? candidate.trim() : null;
}

/**
 * Selects only customer-ready prose from Tavish's structured explanation.
 * Raw feature names, SHAP values, policy codes, and model metadata never cross
 * this presentation boundary.
 */
export function customerExplanation(
  explanation: Record<string, unknown> | null,
  fallback: string,
): string[] {
  if (!explanation) return fallback.trim() ? [fallback.trim()] : [];
  const observations = Array.isArray(explanation.observations)
    ? explanation.observations.map(statement).filter((item): item is string => Boolean(item))
    : [];
  const inference = statement(explanation.inference);
  const safe = [...observations, ...(inference ? [inference] : [])];
  return [...new Set(safe)].slice(0, 4).length > 0
    ? [...new Set(safe)].slice(0, 4)
    : fallback.trim() ? [fallback.trim()] : [];
}
