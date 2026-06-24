import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export interface ActiveExperiment {
  condition: string;
  variableTested: string;
  scriptName: string;
  worldType: string;
  seeds: number[];
  launchedAt: number;
  baseline?: string;
}

interface ActiveExperimentApi {
  activeExperiment: ActiveExperiment | null;
  setActiveExperiment: (exp: ActiveExperiment) => void;
  updateActiveExperiment: (patch: Partial<ActiveExperiment>) => void;
  clearActiveExperiment: () => void;
}

const STORAGE_KEY = "agiseed.activeExperiment";

function readStored(): ActiveExperiment | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ActiveExperiment) : null;
  } catch {
    return null;
  }
}

function writeStored(exp: ActiveExperiment | null): void {
  try {
    if (exp) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(exp));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* localStorage indisponible (navigation privée) : on reste en mémoire. */
  }
}

const ActiveExperimentContext = createContext<ActiveExperimentApi | null>(null);

export function ActiveExperimentProvider({ children }: { children: ReactNode }) {
  const [activeExperiment, setState] = useState<ActiveExperiment | null>(readStored);

  const setActiveExperiment = useCallback((exp: ActiveExperiment) => {
    setState(exp);
    writeStored(exp);
  }, []);

  const updateActiveExperiment = useCallback((patch: Partial<ActiveExperiment>) => {
    setState((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...patch };
      writeStored(next);
      return next;
    });
  }, []);

  const clearActiveExperiment = useCallback(() => {
    setState(null);
    writeStored(null);
  }, []);

  return (
    <ActiveExperimentContext.Provider
      value={{ activeExperiment, setActiveExperiment, updateActiveExperiment, clearActiveExperiment }}
    >
      {children}
    </ActiveExperimentContext.Provider>
  );
}

export function useActiveExperiment(): ActiveExperimentApi {
  const ctx = useContext(ActiveExperimentContext);
  if (!ctx) throw new Error("useActiveExperiment doit être utilisé dans <ActiveExperimentProvider>");
  return ctx;
}
