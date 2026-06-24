import { useRef, type KeyboardEvent, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  group?: string;
  state?: "active" | "done" | "todo";
}

export const tabId = (id: string): string => `tab-${id}`;
export const panelId = (id: string): string => `panel-${id}`;

interface TabListProps {
  items: TabItem[];
  activeId: string;
  onSelect: (id: string) => void;
  ariaLabel: string;
  orientation?: "horizontal" | "vertical";
  renderLabel?: (item: TabItem, index: number) => ReactNode;
  testIdPrefix?: string;
  className?: string;
}

/** Liste d'onglets accessible (WAI-ARIA tablist) : roving tabindex, navigation
 *  aux flèches/Home/End, activation MANUELLE (Entrée/Espace/clic). Partagée par
 *  la nav globale et le StepBar du Parcours. Le panneau (role=tabpanel) est câblé
 *  par le consommateur via panelId(activeId)/tabId(activeId). */
export function TabList({
  items,
  activeId,
  onSelect,
  ariaLabel,
  orientation = "horizontal",
  renderLabel,
  testIdPrefix = "tab",
  className,
}: TabListProps) {
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);

  btnRefs.current.length = items.length;

  const focusAt = (i: number) => {
    const n = items.length;
    if (!n) return;
    const idx = ((i % n) + n) % n; // wrap circulaire
    btnRefs.current[idx]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const nextKey = orientation === "horizontal" ? "ArrowRight" : "ArrowDown";
    const prevKey = orientation === "horizontal" ? "ArrowLeft" : "ArrowUp";
    if (e.key === nextKey) {
      e.preventDefault();
      focusAt(index + 1);
    } else if (e.key === prevKey) {
      e.preventDefault();
      focusAt(index - 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusAt(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusAt(items.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(items[index].id);
    }
  };

  return (
    <div
      className={`tab-list${className ? ` ${className}` : ""}`}
      role="tablist"
      aria-label={ariaLabel}
      aria-orientation={orientation}
    >
      {items.map((item, index) => {
        const isActive = item.id === activeId;
        const prevGroup = index > 0 ? items[index - 1].group : undefined;
        const startsGroup = item.group !== undefined && index > 0 && item.group !== prevGroup;
        const Icon = item.icon;
        return (
          <button
            key={item.id}
            ref={(el) => {
              btnRefs.current[index] = el;
            }}
            role="tab"
            id={tabId(item.id)}
            aria-selected={isActive}
            aria-controls={panelId(item.id)}
            tabIndex={isActive ? 0 : -1}
            data-testid={`${testIdPrefix}-${item.id}`}
            data-group-start={startsGroup || undefined}
            className={`tab${isActive ? " active" : ""}${item.state ? ` is-${item.state}` : ""}`}
            onClick={() => onSelect(item.id)}
            onKeyDown={(e) => onKeyDown(e, index)}
          >
            {renderLabel ? (
              renderLabel(item, index)
            ) : (
              <>
                {Icon ? <Icon size={16} /> : null}
                {item.label}
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}
