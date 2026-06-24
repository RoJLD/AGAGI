import { useQuery } from "@tanstack/react-query";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { useHashRoute } from "../../hooks/useHashRoute";
import { TAB_KEYS } from "../../tabs";
import { apiFetch } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { StepBar } from "./StepBar";
import { STEP_ORDER, type ParcoursStep } from "./steps";
import { StepLancer } from "./StepLancer";
import { StepSuivre } from "./StepSuivre";
import { StepComparer } from "./StepComparer";
import { StepConclure } from "./StepConclure";

const STEP_SET = new Set<string>(STEP_ORDER);
const isStep = (v: string): v is ParcoursStep => STEP_SET.has(v);

export function ParcoursView() {
  const { query, navigate } = useHashRoute(TAB_KEYS, "parcours");
  const { activeExperiment } = useActiveExperiment();
  const step: ParcoursStep = isStep(query.step ?? "") ? (query.step as ParcoursStep) : "lancer";

  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<{ running: boolean }>("/api/sandbox/status"),
    refetchInterval: 3000,
    staleTime: 0,
  });
  const running = statusQuery.data?.running ?? false;

  const reached: Record<ParcoursStep, boolean> = {
    lancer: true,
    suivre: !!activeExperiment || running,
    comparer: !!activeExperiment,
    conclure: !!activeExperiment,
  };

  const go = (s: ParcoursStep) => {
    const q: Record<string, string> = { step: s };
    if (s === "comparer" && activeExperiment) q.ab = activeExperiment.condition;
    navigate("parcours", q);
  };

  return (
    <div className="parcours-view">
      <h2>Parcours d'expérimentation</h2>
      <p className="text-dim mb-4">
        Lancer → Suivre en direct → Comparer → Conclure. Le run que tu lances reste le fil
        conducteur d'étape en étape.
      </p>
      <StepBar current={step} reached={reached} onSelect={go} />

      <div className="parcours-step mt-5">
        {step === "lancer" && <StepLancer onNext={() => go("suivre")} />}
        {step === "suivre" && <StepSuivre running={running} hasActive={!!activeExperiment} onNext={() => go("comparer")} />}
        {step === "comparer" && <StepComparer hasActive={!!activeExperiment} onNext={() => go("conclure")} />}
        {step === "conclure" && <StepConclure hasActive={!!activeExperiment} />}
      </div>
    </div>
  );
}
