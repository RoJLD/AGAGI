import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Field } from "./ui/Field";
import { Loading } from "./ui/Loading";
import { useToast } from "../contexts/ToastContext";
import { Play, RotateCw, GitFork, ShieldAlert, Award } from "lucide-react";

export interface PhylogeneticRun {
  id: string;
  transfer_ratio: number;
  stone_score: number;
  agri_score: number;
  indus_score: number;
  status: string;
  timestamp: string;
}

export function TriWorldCurriculumView() {
  const queryClient = useQueryClient();
  const { notify } = useToast();

  const [popSize, setPopSize] = useState(4);
  const [eras, setEras] = useState(1);
  const [ticks, setTicks] = useState(10);
  const [mutationRate, setMutationRate] = useState(0.02);

  const historyQuery = useQuery({
    queryKey: ["curriculum", "history"],
    queryFn: () => apiFetch<PhylogeneticRun[]>("/api/curriculum/history"),
    refetchInterval: 15_000,
  });

  const runMutation = useMutation({
    mutationFn: () =>
      apiFetch("/api/curriculum/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pop_size: popSize,
          eras: eras,
          ticks: ticks,
          mutation_rate: mutationRate,
        }),
      }),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["curriculum", "history"] });
      notify(`Curriculum ${data.run_id || "achevé"} exécuté avec succès ! Ratio: ${data.transfer_ratio?.toFixed(2)}`, "success");
    },
    onError: (err: any) => {
      notify(`Erreur lors du run : ${err.message || err}`, "error");
    },
  });

  const runs = historyQuery.data || [];

  return (
    <div className="curriculum-container" style={{ marginBottom: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            <GitFork size={20} color="var(--color-accent, #38bdf8)" />
            Curriculum Phylogénétique Tri-Mondes (Arc 5)
          </h3>
          <p className="text-dim" style={{ margin: "4px 0 0 0", fontSize: "0.88rem" }}>
            Évolution continue à travers 3 mondes : 🪨 Pierre (Survie) &rarr; 🌾 Agricole (Grenier) &rarr; ⚙️ Industriel (Forge). Persisté dans KuzuDB.
          </p>
        </div>
        <Button
          variant="primary"
          disabled={runMutation.isPending}
          onClick={() => runMutation.mutate()}
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          {runMutation.isPending ? <RotateCw className="spin" size={16} /> : <Play size={16} />}
          {runMutation.isPending ? "Exécution en cours..." : "Lancer le Curriculum"}
        </Button>
      </div>

      <Panel className="mb-4">
        <div style={{ padding: "1rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "12px", alignItems: "flex-end" }}>
          <Field label="Population">
            <input
              type="number"
              min={2}
              max={20}
              value={popSize}
              onChange={(e) => setPopSize(parseInt(e.target.value) || 4)}
              disabled={runMutation.isPending}
            />
          </Field>
          <Field label="Ères par monde">
            <input
              type="number"
              min={1}
              max={10}
              value={eras}
              onChange={(e) => setEras(parseInt(e.target.value) || 1)}
              disabled={runMutation.isPending}
            />
          </Field>
          <Field label="Ticks max / ère">
            <input
              type="number"
              min={5}
              max={50}
              value={ticks}
              onChange={(e) => setTicks(parseInt(e.target.value) || 10)}
              disabled={runMutation.isPending}
            />
          </Field>
          <Field label="Taux mutation">
            <input
              type="number"
              step={0.01}
              min={0.001}
              max={0.2}
              value={mutationRate}
              onChange={(e) => setMutationRate(parseFloat(e.target.value) || 0.02)}
              disabled={runMutation.isPending}
            />
          </Field>
        </div>
      </Panel>

      <Panel>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem" }}>
          <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Historique des Runs Phylogénétiques (KuzuDB)</h4>
          <span className="text-dim" style={{ fontSize: "0.82rem" }}>
            {runs.length} run(s) enregistrés
          </span>
        </div>

        {historyQuery.isLoading ? (
          <Loading label="Chargement des runs KuzuDB..." />
        ) : runs.length === 0 ? (
          <div className="text-dim" style={{ padding: "1.5rem", textAlign: "center", fontStyle: "italic" }}>
            Aucun run de curriculum enregistré. Cliquez sur &laquo; Lancer le Curriculum &raquo; pour démarrer une lignée tri-mondes.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="runs-table" style={{ width: "100%", fontSize: "0.88rem" }}>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Date</th>
                  <th>Transfert (W3/W1)</th>
                  <th>🪨 W1 Pierre</th>
                  <th>🌾 W2 Agricole</th>
                  <th>⚙️ W3 Forge</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => {
                  const isPositiveTransfer = r.transfer_ratio >= 1.0;
                  return (
                    <tr key={r.id}>
                      <td>
                        <code>{r.id}</code>
                      </td>
                      <td className="text-dim" style={{ whiteSpace: "nowrap" }}>
                        {r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : "—"}
                      </td>
                      <td>
                        <Badge variant={isPositiveTransfer ? "success" : "warning"}>
                          &times;{r.transfer_ratio.toFixed(2)}
                        </Badge>
                      </td>
                      <td>
                        <span style={{ color: "#f59e0b", fontWeight: 600 }}>{r.stone_score.toFixed(1)}</span>
                      </td>
                      <td>
                        <span style={{ color: "#22c55e", fontWeight: 600 }}>{r.agri_score.toFixed(1)}</span>
                      </td>
                      <td>
                        <span style={{ color: "#06b6d4", fontWeight: 600 }}>{r.indus_score.toFixed(1)}</span>
                      </td>
                      <td>
                        <Badge variant="teal">{r.status}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
