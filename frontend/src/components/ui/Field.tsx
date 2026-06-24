import { cloneElement, isValidElement, useId, type ReactNode } from "react";

interface FieldProps {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}

/** Libellé + champ (input/select fourni en children) + indice optionnel.
 *  Associe le label au contrôle : si l'appelant ne fournit pas d'id, on en
 *  génère un (useId) et on l'injecte dans l'enfant unique. */
export function Field({ label, hint, htmlFor, children }: FieldProps) {
  const generatedId = useId();
  // id effectif : priorité à htmlFor explicite, puis id de l'enfant, puis généré.
  const childId =
    isValidElement(children) && typeof children.props.id === "string" ? (children.props.id as string) : undefined;
  const controlId = htmlFor ?? childId ?? generatedId;

  // Injecte l'id dans l'enfant unique s'il n'en a pas déjà un.
  const control =
    isValidElement(children) && !childId ? cloneElement(children, { id: controlId }) : children;

  return (
    <div className="field">
      <label className="field-label" htmlFor={controlId}>
        {label}
      </label>
      {control}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  );
}
