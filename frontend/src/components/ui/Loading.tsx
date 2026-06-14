export function Loading({ label }: { label?: string }) {
  return (
    <div className="state-block" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label ?? "Chargement…"}</span>
    </div>
  );
}
