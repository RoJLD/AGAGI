# Fil directeur AGI — les 5 portes G0→G4

> Stratégie qui chapeaute SCIENCE/NAS/BACKEND/FRONTEND. Continue (ne remplace pas)
> `../FIL_CONDUCTEUR.md`. État auto-généré : `tools/consolidate_records.py` → `results/records_graph.json`.
> Design : `../superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md`.

## Thèse réconciliée
« Le bon est trouvé si le monde l'EXIGE (010/012) ET si l'agent l'APPREND (067) » — les deux se
mesurent en un point : la **généralisation zéro-shot** (`transfer_ratio`, north-star).

## Moteur (ADR-001, ADR-002)
GA (recherche de substrat) + gradient (apprentissage intra-vie) + Baldwin. Évolution topologique active.

## Les 5 portes (bottom-up par dépendance, capacités stratifiées EDR 075)
| Porte | Question | KPI | Outil | Record |
|---|---|---|---|---|
| **G0** | Le monde exige ? | survival_ratio champion/dummy | à créer | SDR-G0 |
| **G1** | Ça généralise ? ★ | transfer_ratio | `tools/curriculum_transfer.py` | SDR-G1 |
| **G2** | Ça compose ? | émergence chaîne non récompensée | à créer | SDR-G2 |
| **G3** | Le langage paye ? | mammoth_kills ON/OFF | `tools/wire_ref_head.py` | SDR-G3 |
| **G4** | Ça anticipe ? | anticipation_bench | `tools/anticipation_bench.py` | SDR-G4 |

> On ne franchit une porte que si la précédente est mesurée (verdict EDR powered).
> Méthode : Commandement 15 (1 variable, powered, valide-ou-revert). Négatifs = livrables.

## Consolidation (SDR→EDR→ADR)
`docs/{SDR,ADR,EDR}/` + frontmatter `motivates`/`triggers`/`tests`. `tools/consolidate_records.py`
construit le graphe, échoue sur lien cassé (anti-théâtre). Niveau actuel : index statique (pas de LLM).
