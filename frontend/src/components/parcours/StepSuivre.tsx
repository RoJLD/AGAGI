// frontend/src/components/parcours/StepSuivre.tsx
import { LiveDashboard } from "./LiveDashboard";
import { Empty } from "../ui/Empty";
import { NextStepButton } from "./NextStepButton";

export function StepSuivre({
  running,
  hasActive,
  onNext,
}: {
  running: boolean;
  hasActive: boolean;
  onNext: () => void;
}) {
  if (!hasActive && !running) {
    return (
      <Empty message="Aucune expérience active — commence par l'étape Lancer, ou choisis une condition existante dans l'Historique des runs." />
    );
  }
  return (
    <>
      <LiveDashboard />
      <NextStepButton label="Comparer les résultats" onClick={onNext} />
    </>
  );
}
