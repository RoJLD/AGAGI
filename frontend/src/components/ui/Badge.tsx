import type { ReactNode } from "react";

type BadgeVariant = "teal" | "success" | "danger" | "warning" | "purple";

export function Badge({ variant = "teal", children }: { variant?: BadgeVariant; children: ReactNode }) {
  return <span className={`badge badge--${variant}`}>{children}</span>;
}
