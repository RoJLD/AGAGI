import { useEffect, useState } from "react";

interface ParsedHash {
  path: string;
  gate: string;
}

function parseHash(): ParsedHash {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const params = new URLSearchParams(query || "");
  return { path: path || "", gate: params.get("gate") || "" };
}

/**
 * Routing minimal par hash : `#/onglet?gate=XXX`.
 * - URL partageable/bookmarkable, sans dépendance ni réécriture serveur.
 * - `gate` est porté comme query transverse (sidebar partagée entre onglets).
 */
export function useHashRoute<T extends string>(validTabs: readonly T[], defaultTab: T) {
  const [parsed, setParsed] = useState<ParsedHash>(parseHash);

  useEffect(() => {
    const onChange = () => setParsed(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const tab = (validTabs as readonly string[]).includes(parsed.path) ? (parsed.path as T) : defaultTab;
  const gate = parsed.gate;

  const writeHash = (nextTab: T, nextGate: string) => {
    const q = nextGate ? `?gate=${encodeURIComponent(nextGate)}` : "";
    const next = `#/${nextTab}${q}`;
    if (window.location.hash !== next) {
      window.location.hash = next;
    }
  };

  return {
    tab,
    gate,
    setTab: (t: T) => writeHash(t, gate),
    setGate: (g: string) => writeHash(tab, g),
  };
}
