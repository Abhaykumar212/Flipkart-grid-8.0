export function InterventionWhy({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) return null;
  return (
    <details className="mt-2 text-fk-sm">
      <summary className="min-h-9 cursor-pointer py-2 font-medium text-fk-blue">
        Why this recommendation?
      </summary>
      <ul className="space-y-1 border-l-2 border-blue-200 pl-3 text-fk-muted">
        {reasons.map((reason) => <li key={reason}>{reason}</li>)}
      </ul>
    </details>
  );
}
