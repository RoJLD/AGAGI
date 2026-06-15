import type { ReactNode } from "react";

interface PanelProps {
  as?: "div" | "article" | "section";
  className?: string;
  children: ReactNode;
}

/** Surface standard (fond + rayon + ombre). Remplace .academy-box / .metrics-panel / .panel. */
export function Panel({ as: Tag = "div", className = "", children }: PanelProps) {
  return <Tag className={`panel-base ${className}`.trim()}>{children}</Tag>;
}
