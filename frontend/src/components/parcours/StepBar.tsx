import { TabList, type TabItem } from "../ui/Tabs";
import { STEP_ORDER, type ParcoursStep } from "./steps";

const LABELS: Record<ParcoursStep, string> = {
  lancer: "Lancer",
  suivre: "Suivre",
  comparer: "Comparer",
  conclure: "Conclure",
};

/** Barre d'étapes du parcours — souple : toutes cliquables. Construite sur la
 *  primitive TabList (roles tablist/tab, roving tabindex, flèches, activation
 *  manuelle). Conserve les data-testid `step-<id>` et le visuel pastille. */
export function StepBar({
  current,
  reached,
  onSelect,
}: {
  current: ParcoursStep;
  reached: Record<ParcoursStep, boolean>;
  onSelect: (s: ParcoursStep) => void;
}) {
  const items: TabItem[] = STEP_ORDER.map((s) => ({
    id: s,
    label: LABELS[s],
    state: s === current ? "active" : reached[s] ? "done" : "todo",
  }));

  return (
    <TabList
      items={items}
      activeId={current}
      onSelect={(id) => onSelect(id as ParcoursStep)}
      ariaLabel="Étapes du parcours"
      className="step-bar"
      testIdPrefix="step"
      renderLabel={(item, index) => (
        <>
          <span className="step-pill__index">{index + 1}</span>
          {item.label}
        </>
      )}
    />
  );
}
