// frontend/src/components/parcours/StepConclure.tsx
import { LaboratoryView } from "../LaboratoryView";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { Empty } from "../ui/Empty";

export function StepConclure({ hasActive }: { hasActive: boolean }) {
  const { activeExperiment } = useActiveExperiment();
  return (
    <>
      {!hasActive && (
        <Empty message="Aucune expérience active — l'étape Conclure interprète et archive une comparaison. Lance d'abord un run." />
      )}
      <LaboratoryView
        initialBaseline={activeExperiment?.baseline}
        initialIntervention={activeExperiment?.condition}
      />
    </>
  );
}
