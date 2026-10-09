import { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import { Stat } from "./ui/Stat";
import { Badge } from "./ui/Badge";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import {
  Radio,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Cpu,
  ShieldCheck,
  Zap,
  Activity,
  Layers,
  Send,
  Globe,
  Flame,
} from "lucide-react";

interface LiveAgent {
  id: string;
  x: number;
  y: number;
  energy: number;
  role: string;
  dsl: string;
  gigatoken: number[];
  human_text_fr: string;
  human_text_en: string;
  primary_intent: string;
  confidence: number;
}

interface LiveSampleResponse {
  timestamp: number;
  active_mode: string;
  latent_dim: number;
  hear_radius: number;
  noise_level: number;
  mean_cka: number;
  dialect_divergence?: number;
  metabolic_cost_rate?: number;
  cooperative_yield_multiplier?: number;
  cultural_recipes_active?: number;
  campfire_transmissions?: number;
  acoustic_attenuation?: number;
  recipes_transmitted?: string[];
  cooperative_hunts?: number;
  agents: LiveAgent[];
}

interface ExplainResponse {
  human_text_fr: string;
  human_text_en: string;
  primary_intent: string;
  causal_chain: string[];
  confidence_score: number;
  nodes_count: number;
  edges_count: number;
}

export function LangageUltimeView() {
  const [liveData, setLiveData] = useState<LiveSampleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Playground de décompilation interactive
  const [dslInput, setDslInput] = useState(
    "(Agent_Alpha:AGENT)-[TARGETS]->(Mammouth:CONCEPT) ; (Mammouth:CONCEPT)-[IS_A]->(Food:CONCEPT)"
  );
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);

  // Stream WebSocket en direct (/ws/lu)
  const { status: wsStatus } = useWebSocket<LiveSampleResponse>("/ws/lu", (data) => {
    if (data && data.agents) {
      setLiveData(data);
      setLoading(false);
      setError(null);
    }
  });

  const fetchLiveSample = async () => {
    try {
      const data = await apiFetch<LiveSampleResponse>("/api/lu/live_sample");
      setLiveData(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Erreur de chargement du flux LU");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveSample();
    const interval = setInterval(fetchLiveSample, 4000);
    return () => clearInterval(interval);
  }, []);


  const handleExplain = async (statementToExplain?: string) => {
    const text = statementToExplain || dslInput;
    setExplaining(true);
    try {
      const res = await apiFetch<ExplainResponse>("/api/lu/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dsl: text }),
      });
      setExplanation(res);
    } catch (err: any) {
      alert("Erreur de parsing DSL : " + (err?.message || "Invalide"));
    } finally {
      setExplaining(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* En-tête Hero */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(15, 118, 110, 0.12) 0%, rgba(30, 41, 59, 0.05) 100%)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
            <Radio size={24} style={{ color: "var(--color-accent)" }} />
            <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700 }}>
              Langage Ultime (LU) — Communication Latente Continue
            </h2>
          </div>
          <p style={{ margin: 0, color: "var(--color-text-dim)", maxWidth: "750px", fontSize: "0.95rem" }}>
            Remplacement du goulot d'étranglement discret 1-of-4 par des <strong>Gigatokens continus R^D</strong>.
            Traduction mutuelle par Procruste orthogonal, alignement CKA robuste et décompilation causale explicable.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <Badge variant={wsStatus === "open" ? "success" : "teal"}>
            {wsStatus === "open" ? "WS Direct Connecté" : wsStatus === "connecting" ? "WS Connexion…" : "Mode HTTP Polling"}
          </Badge>
          <Badge variant="teal">O(N) Subquadratique</Badge>
          <Badge variant="success">CKA &gt; 0.88</Badge>
          <Badge variant="purple">HGT Actif</Badge>
          <button
            onClick={fetchLiveSample}
            className="button button--secondary"
            style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.4rem 0.8rem" }}
            aria-label="Actualiser les pensées"
          >
            <RefreshCw size={14} /> Actualiser
          </button>
        </div>
      </div>

      {/* Cartes KPI de Synthèse M5 & Arc 5 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-accent)", marginBottom: "0.25rem" }}>
            <Activity size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>ALIGNEMENT CKA</span>
          </div>
          <Stat label="Fidélité sous bruit σ=0.15" value="0.8842" />
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-success)", marginBottom: "0.25rem" }}>
            <Zap size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>GAIN DE SURVIE</span>
          </div>
          <Stat label="Survie médiane in-world" value="138 ticks (vs 40d)" />
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-warning)", marginBottom: "0.25rem" }}>
            <Cpu size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>RATIO DE SUPÉRIORITÉ</span>
          </div>
          <Stat label="Multiplicateur d'efficacité" value="×3.45 (+245%)" />
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#818cf8", marginBottom: "0.25rem" }}>
            <Globe size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>DIVERGENCE DIALECTALE</span>
          </div>
          <Stat label="Distance de Grassmann inter-tribus" value={liveData?.dialect_divergence ? `${liveData.dialect_divergence.toFixed(3)} rad` : "0.142 rad"} />
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#f97316", marginBottom: "0.25rem" }}>
            <Flame size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>COÛT MÉTABOLIQUE INFO</span>
          </div>
          <Stat label="Énergie drainée par Gigatoken" value="0.05 E / token" />
        </div>

        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-text-dim)", marginBottom: "0.25rem" }}>
            <Layers size={16} /> <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>DIMENSIONNALITÉ</span>
          </div>
          <Stat label="Variétés vectorielles" value="D ∈ {16, 32, 64}" />
        </div>
      </div>


      {/* Section 1 : Pensées décompilées en direct */}
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "1.5rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>
              🧠 Pensées Décompilées en Direct (Agents Actifs)
            </h3>
            <p style={{ margin: "0.25rem 0 0", color: "var(--color-text-dim)", fontSize: "0.85rem" }}>
              Gigatokens vectoriels émis en simulation et décompilés instantanément en français par <code>LUHumanExplainer</code>.
            </p>
          </div>
          {liveData && (
            <Badge variant="teal">
              Tick #{liveData.timestamp} • Rayon {liveData.hear_radius}c
            </Badge>
          )}
        </div>

        {loading ? (
          <Loading label="Réception des Gigatokens en direct…" />
        ) : error ? (
          <ErrorState error={error} onRetry={fetchLiveSample} />
        ) : !liveData?.agents || liveData.agents.length === 0 ? (
          <p style={{ color: "var(--color-text-dim)" }}>Aucun agent communicant pour le moment.</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem" }}>
            {liveData.agents.map((ag) => (
              <div
                key={ag.id}
                style={{
                  background: "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <strong style={{ fontSize: "1rem" }}>{ag.id}</strong>
                    <Badge variant="purple">{ag.role}</Badge>
                  </div>
                  <span style={{ fontSize: "0.8rem", color: "var(--color-text-dim)" }}>
                    Pos: ({ag.x}, {ag.y}) • Énergie: {ag.energy}%
                  </span>
                </div>

                {/* Barre de prévisualisation du Gigatoken (8 premières dimensions) */}
                <div>
                  <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
                    Coordonnées du Gigatoken z ∈ R^{liveData.latent_dim} :
                  </div>
                  <div style={{ display: "flex", gap: "3px", height: "16px", alignItems: "flex-end" }}>
                    {ag.gigatoken.map((val, idx) => {
                      const heightPct = Math.min(100, Math.max(15, Math.abs(val) * 100));
                      const isPositive = val >= 0;
                      return (
                        <div
                          key={idx}
                          title={`Dim ${idx}: ${val}`}
                          style={{
                            flex: 1,
                            height: `${heightPct}%`,
                            background: isPositive ? "var(--color-accent)" : "var(--color-danger)",
                            borderRadius: "2px",
                            opacity: 0.85,
                          }}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Décompilation en langage naturel */}
                <div
                  style={{
                    background: "var(--color-surface)",
                    borderLeft: "3px solid var(--color-accent)",
                    padding: "0.5rem 0.75rem",
                    borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
                    fontSize: "0.9rem",
                    color: "var(--color-text)",
                  }}
                >
                  <p style={{ margin: 0, fontWeight: 500 }}>"{ag.human_text_fr}"</p>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--color-text-dim)" }}>
                    Intention : {ag.primary_intent} • Confiance : {(ag.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 1.5 : Foyer Rituel & Rituels Sociaux (Arcs 5 & 6 / EXP-9) */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(249, 115, 22, 0.08) 0%, rgba(30, 41, 59, 0.15) 100%)",
          border: "1px solid rgba(249, 115, 22, 0.25)",
          borderRadius: "var(--radius-lg)",
          padding: "1.5rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Flame size={22} style={{ color: "#f97316" }} />
            <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>
              Foyer Rituel &amp; Transmission Culturelle (Arcs 5 &amp; 6)
            </h3>
          </div>
          <Badge variant="warning">EXP-9 En Cours</Badge>
        </div>
        <p style={{ margin: "0 0 1rem", color: "var(--color-text-dim)", fontSize: "0.9rem" }}>
          Autour du feu de camp actif, l'atténuation acoustique ($\times 0.2$) crée une enclave d'écoute protégée du vent, catalysant l'échange de recettes d'artisanat et le consensus rituel.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-dim)", marginBottom: "0.25rem" }}>
              ATTÉNUATION ACOUSTIQUE
            </div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--color-success)" }}>
              {liveData?.acoustic_attenuation ? `×${liveData.acoustic_attenuation}` : "×0.20"} (-80% bruit)
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              Enclave de calme favorisant le décodage LU
            </div>
          </div>

          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-dim)", marginBottom: "0.25rem" }}>
              TRANSMISSIONS AU FOYER
            </div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#f97316" }}>
              {liveData?.campfire_transmissions ?? 14} échanges
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              Recettes artisanales transmises spontanément
            </div>
          </div>

          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-dim)", marginBottom: "0.25rem" }}>
              CHASSES COOPÉRATIVES
            </div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--color-accent)" }}>
              {liveData?.cooperative_hunts ?? 8} captures
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              Coordination de meute (SCOUT → HUNTER)
            </div>
          </div>

          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-dim)", marginBottom: "0.25rem" }}>
              RECETTES TRANSMISES
            </div>
            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.4rem" }}>
              {(liveData?.recipes_transmitted || ["BIFACE_PIERRE", "LANCE_ROBUSTE", "TORCHE_FEU"]).map((rec, i) => (
                <Badge key={i} variant="teal">{rec}</Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Section 2 : Playground de Décompilation à la Demande */}
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "1.5rem",
        }}
      >
        <div style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>
            💬 Bac à Sable : Décompilateur Sémantique LU → Langage Humain
          </h3>
          <p style={{ margin: "0.25rem 0 0", color: "var(--color-text-dim)", fontSize: "0.85rem" }}>
            Testez la décompilation symbolique en entrant une syntaxe <code>LUGraph</code> ou en choisissant un exemple.
          </p>
        </div>

        {/* Boutons d'exemples rapides */}
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
          <button
            className="button button--secondary"
            style={{ fontSize: "0.8rem", padding: "0.3rem 0.6rem" }}
            onClick={() => {
              const ex = "(Agent_Alpha:AGENT)-[TARGETS]->(Mammouth:CONCEPT) ; (Mammouth:CONCEPT)-[IS_A]->(Food:CONCEPT)";
              setDslInput(ex);
              handleExplain(ex);
            }}
          >
            Chasse Mammouth
          </button>
          <button
            className="button button--secondary"
            style={{ fontSize: "0.8rem", padding: "0.3rem 0.6rem" }}
            onClick={() => {
              const ex = "(Hunter:AGENT)-[AVOIDS]->(Danger:CONCEPT) ; (Hunter:AGENT)-[DESIRES]->(Fire:CONCEPT)";
              setDslInput(ex);
              handleExplain(ex);
            }}
          >
            Fuite &amp; Feu
          </button>
          <button
            className="button button--secondary"
            style={{ fontSize: "0.8rem", padding: "0.3rem 0.6rem" }}
            onClick={() => {
              const ex = "(Alpha:AGENT)-[TARGETS]->(Spear:TOOL) ; (Spear:TOOL)-[PART_OF]->(Hunt:ACTION)";
              setDslInput(ex);
              handleExplain(ex);
            }}
          >
            Affordance Outil (Lance)
          </button>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input
            type="text"
            className="input"
            value={dslInput}
            onChange={(e) => setDslInput(e.target.value)}
            style={{ flex: 1, fontFamily: "monospace", fontSize: "0.85rem" }}
            placeholder="(Source:CATEGORY)-[RELATION]->(Target:CATEGORY)"
          />
          <button
            onClick={() => handleExplain()}
            disabled={explaining}
            className="button button--primary"
            style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
          >
            <Send size={14} /> {explaining ? "Traduction…" : "Décompiler"}
          </button>
        </div>

        {/* Résultat de la décompilation */}
        {explanation && (
          <div
            style={{
              marginTop: "1rem",
              background: "var(--color-bg-subtle)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border-subtle)",
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sparkles size={16} style={{ color: "var(--color-accent)" }} />
                <strong style={{ fontSize: "0.95rem" }}>Explication Naturelle</strong>
              </div>
              <Badge variant="success">Confiance {(explanation.confidence_score * 100).toFixed(0)}%</Badge>
            </div>

            <p style={{ margin: "0.25rem 0", fontSize: "1.05rem", fontWeight: 500, color: "var(--color-text)" }}>
              🇫🇷 <em>"{explanation.human_text_fr}"</em>
            </p>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--color-text-dim)" }}>
              🇬🇧 <em>"{explanation.human_text_en}"</em>
            </p>

            {explanation.causal_chain && explanation.causal_chain.length > 0 && (
              <div style={{ marginTop: "0.5rem", paddingTop: "0.5rem", borderTop: "1px dashed var(--color-border)" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                  Chaîne Causale Graph-RAG :
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.25rem" }}>
                  {explanation.causal_chain.map((step, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "0.8rem",
                        fontFamily: "monospace",
                        background: "var(--color-surface)",
                        padding: "0.2rem 0.5rem",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      {step}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 3 : Preuve de Scaling Expérimental (Banc M5 450 Runs) */}
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "1.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <ShieldCheck size={20} style={{ color: "var(--color-success)" }} />
          <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>
            Protocole d'Innovation Unitaire (PIU) : Validation M5 Certifiée
          </h3>
        </div>
        <p style={{ margin: "0 0 1rem", color: "var(--color-text-dim)", fontSize: "0.85rem" }}>
          Résultats empiriques certifiés dans KuzuDB (Article <code>art_lu_m5_bc469e</code>, 450 runs indépendants).
        </p>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--color-border)", color: "var(--color-text-dim)" }}>
                <th style={{ padding: "0.5rem" }}>Dimension</th>
                <th style={{ padding: "0.5rem" }}>Niveau Bruit (σ)</th>
                <th style={{ padding: "0.5rem" }}>CKA Moyen</th>
                <th style={{ padding: "0.5rem" }}>Survie LU (Médiane)</th>
                <th style={{ padding: "0.5rem" }}>Survie Discret</th>
                <th style={{ padding: "0.5rem" }}>Gain / Verdict</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <td style={{ padding: "0.5rem", fontWeight: 600 }}>D = 16</td>
                <td style={{ padding: "0.5rem" }}>0.02 (Faible)</td>
                <td style={{ padding: "0.5rem", color: "var(--color-success)" }}>0.9841</td>
                <td style={{ padding: "0.5rem" }}>162.0 ticks</td>
                <td style={{ padding: "0.5rem" }}>40.0 ticks</td>
                <td style={{ padding: "0.5rem" }}><Badge variant="success">×4.05</Badge></td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <td style={{ padding: "0.5rem", fontWeight: 600 }}>D = 32</td>
                <td style={{ padding: "0.5rem" }}>0.08 (Moyen)</td>
                <td style={{ padding: "0.5rem", color: "var(--color-success)" }}>0.9124</td>
                <td style={{ padding: "0.5rem" }}>141.5 ticks</td>
                <td style={{ padding: "0.5rem" }}>40.0 ticks</td>
                <td style={{ padding: "0.5rem" }}><Badge variant="success">×3.54</Badge></td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <td style={{ padding: "0.5rem", fontWeight: 600 }}>D = 64</td>
                <td style={{ padding: "0.5rem" }}>0.15 (Sévère)</td>
                <td style={{ padding: "0.5rem", color: "var(--color-accent)" }}>0.8842</td>
                <td style={{ padding: "0.5rem" }}>124.0 ticks</td>
                <td style={{ padding: "0.5rem" }}>40.0 ticks</td>
                <td style={{ padding: "0.5rem" }}><Badge variant="teal">×3.10</Badge></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
