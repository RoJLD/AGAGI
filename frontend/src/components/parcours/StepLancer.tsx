// frontend/src/components/parcours/StepLancer.tsx
import { RunLauncher } from "../RunLauncher";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { NextStepButton } from "./NextStepButton";
import type { RunConfig } from "../../types";

export function StepLancer({ onNext }: { onNext: () => void }) {
  const { setActiveExperiment, activeExperiment } = useActiveExperiment();

  const handleLaunch = (config: RunConfig) => {
    setActiveExperiment({
      condition: config.variable_tested || config.script_name,
      variableTested: config.variable_tested,
      scriptName: config.script_name,
      worldType: config.world_type,
      seeds: Array.from({ length: config.n_seeds }, (_, i) => config.base_seed + i),
      launchedAt: Date.now(),
    });
  };

  return (
    <>
      <RunLauncher onLaunch={handleLaunch} />
      <NextStepButton label="Suivre le run en direct" onClick={onNext} disabled={!activeExperiment} />
    </>
  );
}
