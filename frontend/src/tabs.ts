import {
  Activity,
  BarChart3,
  CandlestickChart,
  Compass,
  Database,
  FlaskConical,
  Gamepad2,
  Gauge,
  GraduationCap,
  History,
  Network,
  NotebookPen,
  ShieldAlert,
  Spline,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { TabItem } from "./components/ui/Tabs";

export const TAB_KEYS = [
  "edr",
  "live",
  "sante",
  "evolution",
  "comparison",
  "topology",
  "sweeps",
  "cohorte",
  "energie",
  "parcours",
  "laboratoire",
  "sandbox",
  "runs",
  "academy",
  "timeline",
  "provenance",
  "carnet",
] as const;

export type TabKey = (typeof TAB_KEYS)[number];

export interface TabDef {
  key: TabKey;
  label: string;
  icon: LucideIcon;
}

export interface TabFamily {
  family: string;
  tabs: TabDef[];
}

/** Aplatit les familles d'onglets en items pour la primitive TabList (group = nom de famille). */
export function buildNavItems(families: TabFamily[]): TabItem[] {
  return families.flatMap((fam) =>
    fam.tabs.map((t) => ({ id: t.key, label: t.label, icon: t.icon, group: fam.family })),
  );
}

/** Onglets regroupés par famille — libellés humains FR + icônes. La clé reste technique. */
export const TAB_FAMILIES: TabFamily[] = [
  {
    family: "Observation",
    tabs: [
      { key: "edr", label: "EDR", icon: ShieldAlert },
      { key: "live", label: "Temps réel", icon: Activity },
      { key: "sante", label: "Santé", icon: Gauge },
    ],
  },
  {
    family: "Analyse",
    tabs: [
      { key: "evolution", label: "Évolution", icon: TrendingUp },
      { key: "comparison", label: "Comparaison", icon: BarChart3 },
      { key: "topology", label: "Topologie", icon: Network },
      { key: "sweeps", label: "Sweeps", icon: Spline },
      { key: "cohorte", label: "Cohorte", icon: CandlestickChart },
      { key: "energie", label: "Énergie", icon: Zap },
    ],
  },
  {
    family: "Expérimentation",
    tabs: [
      { key: "parcours", label: "Parcours", icon: Compass },
      { key: "laboratoire", label: "Laboratoire", icon: FlaskConical },
      { key: "sandbox", label: "Bac à sable", icon: Gamepad2 },
      { key: "runs", label: "Historique runs", icon: Database },
    ],
  },
  {
    family: "Connaissance",
    tabs: [
      { key: "academy", label: "Academy", icon: GraduationCap },
      { key: "timeline", label: "Chronologie", icon: History },
      { key: "provenance", label: "Provenance", icon: Workflow },
      { key: "carnet", label: "Carnet", icon: NotebookPen },
    ],
  },
];
