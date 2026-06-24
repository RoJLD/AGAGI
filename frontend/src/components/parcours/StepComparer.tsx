// frontend/src/components/parcours/StepComparer.tsx
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { ComparisonView } from "../ComparisonView";
import { Empty } from "../ui/Empty";
import { NextStepButton } from "./NextStepButton";

export function StepComparer({ hasActive, onNext }: { hasActive: boolean; onNext: () => void }) {
  const { updateActiveExperiment } = useActiveExperiment();
  return (
    <>
      {!hasActive && (
        <Empty message="Astuce : lance une expérience pour pré-remplir l'A/B avec sa condition. Tu peux comparer librement ci-dessous." />
      )}
      <ComparisonView onBaselineChange={(baseline) => updateActiveExperiment({ baseline })} />
      <NextStepButton label="Conclure & publier" onClick={onNext} />
    </>
  );
}
