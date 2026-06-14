import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}

/** Libellé + champ (input/select fourni en children) + indice optionnel. */
export function Field({ label, hint, htmlFor, children }: FieldProps) {
  return (
    <div className="field">
      <label className="field-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  );
}
