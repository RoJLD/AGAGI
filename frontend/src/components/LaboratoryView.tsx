import { useEffect, useState } from "react";
import type { Article } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

interface ExperimentSummary {
  gate: string;
  status: string;
  nodes_count: number;
}

export function LaboratoryView() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [baseline, setBaseline] = useState("");
  const [intervention, setIntervention] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchArticles = () => {
    fetch(`${API_BASE}/api/sociologist/articles`)
      .then((res) => res.json())
      .then((data) => {
        setArticles(data);
      })
      .catch((err) => {
        console.error("Failed to fetch sociologist articles:", err);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchArticles();
    // Fetch experiments for dropdowns
    fetch(`${API_BASE}/api/experiments`)
      .then((res) => res.json())
      .then((data: ExperimentSummary[]) => {
        setExperiments(data);
        if (data.length >= 2) {
            setBaseline(data[0].gate);
            setIntervention(data[1].gate);
        }
      })
      .catch((err) => console.error("Failed to fetch experiments:", err));
  }, []);

  const handleAnalyze = async () => {
    if (!baseline || !intervention) {
        setErrorMsg("Veuillez sélectionner une Baseline et une Intervention.");
        return;
    }
    if (baseline === intervention) {
        setErrorMsg("La Baseline et l'Intervention doivent être différentes.");
        return;
    }
    
    setIsAnalyzing(true);
    setErrorMsg("");
    
    try {
        const res = await fetch(`${API_BASE}/api/sociologist/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ baseline, intervention })
        });
        
        const result = await res.json();
        if (result.status === "success") {
            // Re-fetch articles to show the new one
            fetchArticles();
        } else {
            setErrorMsg(result.message || "Erreur lors de l'analyse.");
        }
    } catch (err) {
        console.error(err);
        setErrorMsg("Erreur réseau ou timeout du LLM.");
    } finally {
        setIsAnalyzing(false);
    }
  };

  return (
    <div className="laboratory-view">
      <h2>Laboratoire & Publications (IA Sociologue)</h2>
      <p>
        Cette page consigne les découvertes scientifiques extraites automatiquement de KuzuDB par l'Agent Sociologue
        après chaque comparaison d'évolution.
      </p>

      <div className="academy-box" style={{ marginBottom: "20px" }}>
        <h3>Lancer une nouvelle étude</h3>
        <p style={{ marginBottom: "15px" }}>Sélectionnez deux expériences à comparer par le LLM Sociologue :</p>
        
        <div style={{ display: "flex", gap: "15px", alignItems: "center", marginBottom: "15px" }}>
            <div>
                <label style={{ display: "block", marginBottom: "5px", color: "var(--color-text-dim)" }}>Baseline</label>
                <select 
                    value={baseline} 
                    onChange={e => setBaseline(e.target.value)}
                    style={{ padding: "8px", background: "var(--color-bg)", color: "var(--color-text)", border: "1px solid var(--color-border)", borderRadius: "4px" }}
                >
                    <option value="">Sélectionner...</option>
                    {experiments.map(exp => (
                        <option key={`base-${exp.gate}`} value={exp.gate}>{exp.gate}</option>
                    ))}
                </select>
            </div>
            
            <div style={{ fontSize: "20px", color: "var(--color-text-dim)" }}>VS</div>
            
            <div>
                <label style={{ display: "block", marginBottom: "5px", color: "var(--color-text-dim)" }}>Intervention</label>
                <select 
                    value={intervention} 
                    onChange={e => setIntervention(e.target.value)}
                    style={{ padding: "8px", background: "var(--color-bg)", color: "var(--color-text)", border: "1px solid var(--color-border)", borderRadius: "4px" }}
                >
                    <option value="">Sélectionner...</option>
                    {experiments.map(exp => (
                        <option key={`int-${exp.gate}`} value={exp.gate}>{exp.gate}</option>
                    ))}
                </select>
            </div>
            
            <button 
                onClick={handleAnalyze} 
                disabled={isAnalyzing}
                style={{ 
                    padding: "10px 20px", 
                    background: "var(--color-accent)", 
                    color: "var(--color-bg)", 
                    border: "none", 
                    borderRadius: "6px",
                    cursor: isAnalyzing ? "wait" : "pointer",
                    fontWeight: "bold",
                    marginTop: "22px",
                    opacity: isAnalyzing ? 0.7 : 1
                }}
            >
                {isAnalyzing ? "Analyse en cours (LLM)..." : "Générer l'Article"}
            </button>
        </div>
        
        {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}
      </div>

      {loading ? (
        <p>Chargement des publications...</p>
      ) : articles.length > 0 ? (
        <div className="articles-list">
          {articles.map((article) => {
            const dateStr = new Date(article.timestamp).toLocaleString();
            return (
              <div key={article.id} className="academy-box article-card">
                <h3>{article.title}</h3>
                <p className="article-meta">
                  <small style={{ color: "var(--color-text-dim)" }}>Publié le {dateStr} | ID: {article.id}</small>
                </p>
                <div style={{ whiteSpace: "pre-wrap", marginTop: "15px", lineHeight: "1.5" }}>
                  {article.content}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="academy-box">
          <p>Aucun article publié pour le moment.</p>
        </div>
      )}
    </div>
  );
}