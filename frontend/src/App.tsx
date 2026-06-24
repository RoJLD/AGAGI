import { lazy, Suspense } from "react";
import { useTheme } from "./hooks/useTheme";
import { useHashRoute } from "./hooks/useHashRoute";
import { TabList, tabId, panelId } from "./components/ui/Tabs";
import { TAB_KEYS, TAB_FAMILIES, buildNavItems } from "./tabs";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { GateSidebar } from "./components/GateSidebar";
import { EDRDashboard } from "./components/EDRDashboard";
import { Loading } from "./components/ui/Loading";
import { Sun, Moon } from "lucide-react";

const LiveMetrics = lazy(() => import("./components/LiveMetrics").then((m) => ({ default: m.LiveMetrics })));
const FlatlandViewer = lazy(() => import("./components/FlatlandViewer").then((m) => ({ default: m.FlatlandViewer })));
const EvolutionView = lazy(() => import("./components/EvolutionView").then((m) => ({ default: m.EvolutionView })));
const ComparisonView = lazy(() => import("./components/ComparisonView").then((m) => ({ default: m.ComparisonView })));
const TopologyView = lazy(() => import("./components/TopologyView").then((m) => ({ default: m.TopologyView })));
const AcademyView = lazy(() => import("./components/AcademyView").then((m) => ({ default: m.AcademyView })));
const LaboratoryView = lazy(() => import("./components/LaboratoryView").then((m) => ({ default: m.LaboratoryView })));
const TimelineViewer = lazy(() => import("./components/TimelineViewer").then((m) => ({ default: m.TimelineViewer })));
const SandboxView = lazy(() => import("./components/SandboxView").then((m) => ({ default: m.SandboxView })));
const RunLauncher = lazy(() => import("./components/RunLauncher").then((m) => ({ default: m.RunLauncher })));
const RunsHistoryView = lazy(() => import("./components/RunsHistoryView").then((m) => ({ default: m.RunsHistoryView })));
const HealthView = lazy(() => import("./components/HealthView").then((m) => ({ default: m.HealthView })));
const ParcoursView = lazy(() => import("./components/parcours/ParcoursView").then((m) => ({ default: m.ParcoursView })));
const SweepView = lazy(() => import("./components/SweepView").then((m) => ({ default: m.SweepView })));

export default function App() {
  const { theme, toggle } = useTheme();
  const { tab, setTab, navigate } = useHashRoute(TAB_KEYS, "parcours");
  const showSidebar = tab === "evolution" || tab === "comparison" || tab === "topology";

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <h1>AGIseed Dashboard</h1>
          <p>Instrument d'expérimentation — biosphère évolutive, runs multi-seed &amp; A/B rigoureux</p>
        </div>
        <div className="topbar-right">
          <button className="theme-toggle" onClick={toggle} aria-label="Basculer le thème">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Clair" : "Sombre"}
          </button>
          <nav className="topbar-nav">
            <TabList
              items={buildNavItems(TAB_FAMILIES)}
              activeId={tab}
              onSelect={(id) => setTab(id as (typeof TAB_KEYS)[number])}
              ariaLabel="Sections du dashboard"
              className="tabs"
            />
          </nav>
        </div>
      </header>

      <main className={showSidebar ? "content" : "content content--full"}>
        {showSidebar && <GateSidebar />}

        <section
          className="panel"
          role="tabpanel"
          id={panelId(tab)}
          aria-labelledby={tabId(tab)}
          tabIndex={0}
        >
          <ErrorBoundary key={tab}>
          <Suspense fallback={<Loading label="Chargement de la vue…" />}>
          {tab === "parcours" && <ParcoursView />}
          {tab === "edr" && <EDRDashboard />}
          {tab === "live" && (
            <>
              <LiveMetrics />
              <FlatlandViewer />
            </>
          )}
          {tab === "evolution" && <EvolutionView />}
          {tab === "comparison" && <ComparisonView />}
          {tab === "topology" && <TopologyView />}
          {tab === "sweeps" && <SweepView />}
          {tab === "academy" && <AcademyView />}
          {tab === "laboratoire" && <LaboratoryView />}
          {tab === "timeline" && <TimelineViewer />}
          {tab === "sandbox" && (
            <>
              <RunLauncher />
              <SandboxView />
            </>
          )}
          {tab === "runs" && <RunsHistoryView onCompare={(cond) => navigate("comparison", { ab: cond })} />}
          {tab === "sante" && <HealthView />}
          </Suspense>
          </ErrorBoundary>
        </section>
      </main>
    </div>
  );
}
