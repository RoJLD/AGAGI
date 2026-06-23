interface StatProps {
  label: string;
  value: string | number;
}

/** Bloc métrique compact (libellé + valeur). */
export function Stat({ label, value }: StatProps) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
