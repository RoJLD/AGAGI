import { useEffect, useState } from "react";

interface ParsedHash {
  path: string;
  query: Record<string, string>;
}

function parseHash(): ParsedHash {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [path, queryStr] = raw.split("?");
  const params = new URLSearchParams(queryStr || "");
  const query: Record<string, string> = {};
  params.forEach((value, key) => {
    query[key] = value;
  });
  return { path: path || "", query };
}

function buildHash(tab: string, query: Record<string, string>): string {
  const params = new URLSearchParams(Object.entries(query).filter(([, v]) => Boolean(v)));
  const qs = params.toString();
  return `#/${tab}${qs ? `?${qs}` : ""}`;
}

/**
 * Routing minimal par hash : `#/onglet?gate=XXX&ab=YYY`.
 * - URL partageable/bookmarkable, sans dépendance ni réécriture serveur.
 * - `gate` : query transverse (sidebar). `query` expose tous les paramètres (ex: `ab` pour le deep-link A/B).
 * - `navigate(tab, query)` : navigation avec paramètres arbitraires.
 */
export function useHashRoute<T extends string>(validTabs: readonly T[], defaultTab: T) {
  const [parsed, setParsed] = useState<ParsedHash>(parseHash);

  useEffect(() => {
    const onChange = () => setParsed(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const tab = (validTabs as readonly string[]).includes(parsed.path) ? (parsed.path as T) : defaultTab;
  const gate = parsed.query.gate || "";

  const write = (nextTab: T, query: Record<string, string>) => {
    const next = buildHash(nextTab, query);
    if (window.location.hash !== next) window.location.hash = next;
  };

  return {
    tab,
    gate,
    query: parsed.query,
    setTab: (t: T) => write(t, gate ? { gate } : {}),
    setGate: (g: string) => write(tab, g ? { gate: g } : {}),
    navigate: (t: T, query: Record<string, string> = {}) => write(t, query),
  };
}
