import {
  Activity,
  BarChart3,
  FlaskConical,
  Gamepad2,
  GraduationCap,
  History,
  Network,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export const TAB_KEYS = [
  "edr",
  "live",
  "evolution",
  "comparison",
  "topology",
  "academy",
  "laboratoire",
  "timeline",
  "sandbox",
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

/** Onglets regroupés par famille — libellés humains FR + icônes. La clé reste technique. */
export const TAB_FAMILIES: TabFamily[] = [
  {
    family: "Observation",
    tabs: [
      { key: "edr", label: "EDR", icon: ShieldAlert },
      { key: "live", label: "Temps réel", icon: Activity },
    ],
  },
  {
    family: "Analyse",
    tabs: [
      { key: "evolution", label: "Évolution", icon: TrendingUp },
      { key: "comparison", label: "Comparaison", icon: BarChart3 },
      { key: "topology", label: "Topologie", icon: Network },
    ],
  },
  {
    family: "Expérimentation",
    tabs: [
      { key: "laboratoire", label: "Laboratoire", icon: FlaskConical },
      { key: "sandbox", label: "Bac à sable", icon: Gamepad2 },
    ],
  },
  {
    family: "Connaissance",
    tabs: [
      { key: "academy", label: "Academy", icon: GraduationCap },
      { key: "timeline", label: "Chronologie", icon: History },
    ],
  },
];
