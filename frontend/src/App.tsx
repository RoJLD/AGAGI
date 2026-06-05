import { useEffect, useMemo, useState } from "react";
import type { AcademyPayload, ExperimentDetail, ExperimentHistory, ExperimentSummary, GraphData } from "./types";
import { TopologyViewer } from "./components/TopologyViewer";
import { ComparisonChart } from "./components/ComparisonChart";
import { RadarChart } from "./components/RadarChart";

import { LaboratoryView } from "./components/LaboratoryView";
import { TimelineViewer } from "./components/TimelineViewer";
import { SandboxView } from "./components/SandboxView";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";
const tabs = ["evolution", "comparison", "topology", "academy", "laboratoire", "timeline", "sandbox"] as const;

type TabKey = (typeof tabs)[number];

function formatPercentage(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function createLinePath(values: number[], width: number, height: number) {
  const count = values.length;
  if (!count) return "";
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const scaleY = (v: number) => height - ((v - minValue) / (maxValue - minValue || 1)) * height;
  const step = width / Math.max(count - 1, 1);
  return values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${index * step} ${scaleY(value)}`)
    .join(" ");
}

function createStabilitySeries(values: number[]) {
  if (values.length <= 1) {
    return values.map(() => 1);
  }

  const deltas = values.map((value, index) => (index === 0 ? 0 : Math.abs(value - values[index - 1])));
  const maxDelta = Math.max(...deltas.slice(1), 0.01);
  return deltas.map((delta) => 1 - Math.min(1, delta / maxDelta));
}

function ChartLine({ values, color }: { values: number[]; color: string }) {
  return <path d={createLinePath(values, 700, 260)} fill="none" stroke={color} strokeWidth={3} />;
}

export default function App() {
  const [tab, setTab] = useState<TabKey>("evolution");
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [selectedGate, setSelectedGate] = useState<string>("");
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [academy, setAcademy] = useState<AcademyPayload | null>(null);
  const [wsLog, setWsLog] = useState<string[]>([]);

  const selectedExperiment = useMemo(() => experiments.find((item) => item.gate === selectedGate), [experiments, selectedGate]);

  const summaryMetrics = useMemo(() => {
    if (!experiments.length) return null;

    const fitnessValues = experiments.map((item) => item.latest_fitness);
    const accuracyValues = experiments.map((item) => item.latest_accuracy);
    const sizes = experiments.flatMap((item) => (item.latest_size !== undefined ? [item.latest_size] : []));

    const bestFitness = experiments.reduce((best, current) => (current.latest_fitness > best.latest_fitness ? current : best), experiments[0]);
    const bestAccuracy = experiments.reduce((best, current) => (current.latest_accuracy > best.latest_accuracy ? current : best), experiments[0]);

    const emergentScores = experiments.flatMap((item) => (item.emergent_score !== undefined ? [item.emergent_score] : []));
    const robustnessScores = experiments.flatMap((item) => (item.robustness_score !== undefined ? [item.robustness_score] : []));
    const stabilityScores = experiments.flatMap((item) => (item.performance_stability !== undefined ? [item.performance_stability] : []));
    return {
      count: experiments.length,
      averageFitness: fitnessValues.reduce((sum, value) => sum + value, 0) / fitnessValues.length,
      averageAccuracy: accuracyValues.reduce((sum, value) => sum + value, 0) / accuracyValues.length,
      averageEmergentScore: emergentScores.length
        ? emergentScores.reduce((sum, value) => sum + value, 0) / emergentScores.length
        : 0,
      averageRobustness: robustnessScores.length
        ? robustnessScores.reduce((sum, value) => sum + value, 0) / robustnessScores.length
        : 0,
      averageStability: stabilityScores.length
        ? stabilityScores.reduce((sum, value) => sum + value, 0) / stabilityScores.length
        : 0,
      bestFitnessGate: bestFitness.gate,
      bestAccuracyGate: bestAccuracy.gate,
      bestEmergentGate: experiments.reduce(
        (best, current) =>
          current.emergent_score !== undefined && current.emergent_score > (best.emergent_score ?? -Infinity)
            ? current
            : best,
        experiments[0],
      ).gate,
      bestRobustGate: experiments.reduce(
        (best, current) =>
          current.robustness_score !== undefined && current.robustness_score > (best.robustness_score ?? -Infinity)
            ? current
            : best,
        experiments[0],
      ).gate,
      smallestSize: sizes.length ? Math.min(...sizes) : undefined,
    };
  }, [experiments]);

  useEffect(() => {
    fetch(`${API_BASE}/api/experiments`)
      .then((response) => response.json())
      .then((data) => {
        setExperiments(data);
        if (data.length && !selectedGate) {
          setSelectedGate(data[0].gate);
        }
      });

    fetch(`${API_BASE}/api/academy`)
      .then((response) => response.json())
      .then(setAcademy);
  }, []);

  useEffect(() => {
    if (!selectedGate) return;
    fetch(`${API_BASE}/api/experiments/${selectedGate}`)
      .then((response) => response.json())
      .then(setDetail);
  }, [selectedGate]);

  useEffect(() => {
    const wsUrl = API_BASE.replace(/^http/, window.location.protocol === "https:" ? "wss" : "ws");
    const ws = new WebSocket(`${wsUrl}/ws/evolution`);
    ws.addEventListener("message", (event) => {
      setWsLog((previous) => [event.data, ...previous].slice(0, 12));
    });
    ws.addEventListener("error", () => {
      setWsLog((previous) => ["WebSocket failed à la connexion", ...previous].slice(0, 12));
    });
    return () => ws.close();
  }, []);

  const chartData = detail?.history;
  const sizeSeries = chartData?.size ?? [];
  const stabilitySeries = chartData ? createStabilitySeries(chartData.accuracy) : [];

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <h1>AGIseed Dashboard</h1>
          <p>Phase 0 à 3 : API FastAPI + React + D3 + WebSocket</p>
        </div>
        <nav className="tabs">
          {tabs.map((value) => (
            <button key={value} className={value === tab ? "active" : ""} onClick={() => setTab(value)}>
              {value}
            </button>
          ))}
        </nav>
      </header>

      <main className="content">
        <aside className="sidebar">
          <label htmlFor="gate-select">Sélectionner une porte</label>
          <select id="gate-select" value={selectedGate} onChange={(event) => setSelectedGate(event.target.value)}>
            {experiments.map((experiment) => (
              <option key={experiment.gate} value={experiment.gate}>
                {experiment.gate}
              </option>
            ))}
          </select>

          {summaryMetrics ? (
            <div className="summary-panel">
              <h2>Vue globale</h2>
              <p>Total portes : {summaryMetrics.count}</p>
              <p>Meilleure fitness : {summaryMetrics.bestFitnessGate}</p>
              <p>Meilleure précision : {summaryMetrics.bestAccuracyGate}</p>
              <p>Meilleur score d'intelligence : {summaryMetrics.bestEmergentGate}</p>
              <p>Fitness moyenne : {summaryMetrics.averageFitness.toFixed(4)}</p>
              <p>Précision moyenne : {formatPercentage(summaryMetrics.averageAccuracy)}</p>
              <p>Score d'intelligence moyen : {summaryMetrics.averageEmergentScore.toFixed(3)}</p>
              <p>Robustesse moyenne : {summaryMetrics.averageRobustness.toFixed(3)}</p>
              <p>Stabilité moyenne : {summaryMetrics.averageStability.toFixed(3)}</p>
              {summaryMetrics.smallestSize !== undefined && <p>Plus petite topologie : {summaryMetrics.smallestSize}</p>}
            </div>
          ) : null}

          {selectedExperiment ? (
            <div className="metrics-panel">
              <h2>{selectedExperiment.gate}</h2>
              <p>Fitness finale : {selectedExperiment.latest_fitness.toFixed(4)}</p>
              <p>Précision finale : {formatPercentage(selectedExperiment.latest_accuracy)}</p>
              {selectedExperiment.emergent_score !== undefined && (
                <p>Score d'intelligence : {selectedExperiment.emergent_score.toFixed(3)}</p>
              )}
              {selectedExperiment.robustness_score !== undefined && (
                <p>Robustesse : {selectedExperiment.robustness_score.toFixed(3)}</p>
              )}
              {selectedExperiment.performance_stability !== undefined && (
                <p>Stabilité : {selectedExperiment.performance_stability.toFixed(3)}</p>
              )}
              {selectedExperiment.modularity !== undefined && (
                <p>Modularité : {selectedExperiment.modularity.toFixed(3)}</p>
              )}
              {selectedExperiment.motif_density !== undefined && (
                <p>Densité de motifs : {selectedExperiment.motif_density.toFixed(3)}</p>
              )}
              {selectedExperiment.latest_size !== undefined && <p>Taille finale : {selectedExperiment.latest_size}</p>}
            </div>
          ) : null}

          <div className="ws-panel">
            <h3>Flux évolution</h3>
            <div className="ws-log">
              {wsLog.length ? wsLog.map((line, index) => <div key={index}>{line}</div>) : <div>En attente de données...</div>}
            </div>
          </div>
        </aside>

        <section className="panel">
          {tab === "evolution" && (
            <>
              <h2>Évolution dynamique</h2>
              {chartData ? (
                <>
                  <svg viewBox="0 0 720 300" className="chart-svg" aria-label="Evolution chart">
                    <ChartLine values={chartData.fitness} color="#0f766e" />
                    <ChartLine values={chartData.accuracy} color="#be123c" />
                    {sizeSeries.length ? <ChartLine values={sizeSeries.map((value: number) => value / Math.max(...sizeSeries, 1))} color="#334155" /> : null}
                    {stabilitySeries.length ? <ChartLine values={stabilitySeries} color="#f59e0b" /> : null}
                  </svg>
                  <div className="legend-row">
                    <span className="legend-dot" style={{ background: "#0f766e" }} /> Fitness
                    <span className="legend-dot" style={{ background: "#be123c" }} /> Précision
                    <span className="legend-dot" style={{ background: "#334155" }} /> Taille normalisée
                    <span className="legend-dot" style={{ background: "#f59e0b" }} /> Stabilité
                  </div>
                </>
              ) : (
                <p>Chargement des données...</p>
              )}
            </>
          )}

          {tab === "comparison" && (
            <>
              <h2>Comparaison des portes</h2>
              <ComparisonChart experiments={experiments} />
              <RadarChart experiments={experiments} />
              <div className="comparison-list">
                {experiments.map((item) => (
                  <div key={item.gate} className="comparison-card">
                    <strong>{item.gate}</strong>
                    <span>Fitness: {item.latest_fitness.toFixed(3)}</span>
                    <span>Précision: {formatPercentage(item.latest_accuracy)}</span>
                    {item.robustness_score !== undefined && <span>Robustesse: {item.robustness_score.toFixed(3)}</span>}
                    {item.performance_stability !== undefined && <span>Stabilité: {item.performance_stability.toFixed(3)}</span>}
                  </div>
                ))}
              </div>
            </>
          )}

          {tab === "topology" && (
            <>
              <h2>Topologie du meilleur modèle</h2>
              <div className="topology-grid">
                <div className="topology-visual">
                  {detail?.graph ? <TopologyViewer graph={detail.graph} /> : <p>Topologie indisponible.</p>}
                </div>
                <div className="topology-analysis">
                  <h3>Analyse des motifs</h3>
                  {detail?.metrics ? (
                    <div className="motif-summary">
                      <p>Modularité : {detail.metrics.modularity.toFixed(3)}</p>
                      <p>Densité de motifs : {detail.metrics.motif_density.toFixed(3)}</p>
                      <p>Stabilité : {detail.metrics.performance_stability.toFixed(3)}</p>
                      <p>Robustesse : {detail.metrics.robustness_score.toFixed(3)}</p>
                      <p>Sparsité : {detail.metrics.sparsity.toFixed(3)}</p>
                      <p>Ratio caché : {detail.metrics.hidden_ratio.toFixed(3)}</p>
                    </div>
                  ) : (
                    <p>Chargement de l’analyse...</p>
                  )}
                </div>
              </div>
            </>
          )}

          {tab === "academy" && (
            <>
              <h2>Academy</h2>
              {academy ? (
                <div>
                  <div className="academy-box">
                    <h3>Historique des versions</h3>
                    <ol>
                      {academy.version_history.map((item) => (
                        <li key={item.title}>
                          <strong>{item.title}</strong> — {item.description}
                        </li>
                      ))}
                    </ol>
                  </div>
                  <div className="academy-box">
                    <h3>Timeline</h3>
                    <ol>
                      {academy.timeline.map((event, index) => (
                        <li key={index}>{event}</li>
                      ))}
                    </ol>
                  </div>
                  <div className="academy-box">
                    <h3>Objectifs pédagogiques</h3>
                    <ul>
                      {academy.learning_goals.map((goal, index) => (
                        <li key={index}>{goal}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <p>Chargement des contenus Academy...</p>
              )}
            </>
          )}

          {tab === "laboratoire" && <LaboratoryView />}
          {tab === "timeline" && <TimelineViewer />}
          {tab === "sandbox" && <SandboxView />}
        </section>
      </main>
    </div>
  );
}
