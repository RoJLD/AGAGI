import { useState } from "react";
import type { RunConfig, RunPreset } from "../types";

const KEY = "agiseed.run_presets";

function load(): RunPreset[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as RunPreset[]) : [];
  } catch {
    return [];
  }
}

/** Presets de configuration de runs, persistés en localStorage (id = label, upsert). */
export function useRunPresets() {
  const [presets, setPresets] = useState<RunPreset[]>(load);

  const persist = (next: RunPreset[]) => {
    setPresets(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* localStorage indisponible */
    }
  };

  const savePreset = (label: string, config: RunConfig) => {
    const id = label.trim();
    if (!id) return;
    persist([...presets.filter((p) => p.id !== id), { id, label: id, config }]);
  };

  const deletePreset = (id: string) => persist(presets.filter((p) => p.id !== id));

  return { presets, savePreset, deletePreset };
}
