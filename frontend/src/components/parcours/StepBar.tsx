import { STEP_ORDER, type ParcoursStep } from "./steps";

const LABELS: Record<ParcoursStep, string> = {
  lancer: "Lancer",
  suivre: "Suivre",
  comparer: "Comparer",
  conclure: "Conclure",
};

/** Barre d'étapes du parcours — souple : toutes cliquables. role=tablist + aria-selected. */
export function StepBar({
  current,
  reached,
  onSelect,
}: {
  current: ParcoursStep;
  reached: Record<ParcoursStep, boolean>;
  onSelect: (s: ParcoursStep) => void;
}) {
  return (
    <div className="step-bar" role="tablist" aria-label="Étapes du parcours">
      {STEP_ORDER.map((s, i) => {
        const state = s === current ? "active" : reached[s] ? "done" : "todo";
        return (
          <button
            key={s}
            role="tab"
            aria-selected={s === current}
            aria-current={s === current ? "step" : undefined}
            data-testid={`step-${s}`}
            className={`step-pill step-pill--${state}`}
            onClick={() => onSelect(s)}
          >
            <span className="step-pill__index">{i + 1}</span>
            {LABELS[s]}
          </button>
        );
      })}
    </div>
  );
}
