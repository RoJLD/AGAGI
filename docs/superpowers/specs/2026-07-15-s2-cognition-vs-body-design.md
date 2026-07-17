# S2 — Cognition ou Corps ? Décomposer le levier de survie du champion (2×2 GÉNOME × POLITIQUE)

## Contexte

Le fil S2 a établi que le champion HoF survit ~4× le random (between-subject EXIGE), mais que **cet avantage n'est PAS
causalement médié par la perception** : l'ablation-perception within-subject ne coûte rien en survie (S2-ablation PR #165,
régime-robuste ; confirmé indépendamment par la session // S2-002 sur les 5 mondes). Le champion UTILISE l'obs (~29 % de
ses actions en dépendent) mais de façon survival-neutre. **Question ouverte, foundational** : si ce n'est pas la
perception, l'edge 4× vient-il de la **COGNITION** (ce que l'agent FAIT — sa politique) ou du **CORPS** (ce que l'agent
EST — traits génome/métabolisme que le monde applique quelles que soient les actions) ? Si c'est le corps, le benchmark
mesure l'endurance, pas l'intelligence.

## Objectif

Décomposer causalement le levier de survie du champion via un **2×2 GÉNOME × POLITIQUE**. `s2_demand` fournit déjà 3 des
4 cellules ; il manque `champion_body` (génome champion + actions aléatoires). Étude standalone, additive (ne modifie PAS
`CONDITIONS` ni le verdict between-subject de `s2_demand`).

## Le 2×2

| | politique Mamba (moteur normal) | politique random (`RandomActionBatchModel`) |
|---|---|---|
| **génome champion** | `champion` = (None, fresh=False) — réel, ~4× | **`champion_body`** = (`RandomActionBatchModel`, fresh=False) ← NOUVEAU |
| **génome random** | `random_genome` = (None, fresh=True) | `random_action` = (`RandomActionBatchModel`, fresh=True) |

`champion_body` isole le CORPS : même génome que le champion (métabolisme, taille de cerveau, organes — traits appliqués
par le monde), mais actions aléatoires → la politique/cognition est détruite, seul reste ce que l'agent EST.

## Architecture (additive)

### `verdict_cognition_body` (CREATE dans `src/seed_ai/s2_stats.py`)
Réutilise `_compare` (Cliff δ + p apparié par ère). Décompose l'edge du champion :

```python
def verdict_cognition_body(champion, champion_body, random_genome, random_action,
                           alpha=ALPHA, cliff_thresh=CLIFF_THRESH):
    policy = _compare(champion, champion_body, "survival")        # C vs B : la POLITIQUE compte-t-elle (génome champ) ?
    body   = _compare(champion_body, random_action, "survival")   # B vs R : le CORPS champ (actions random) bat-il le floor ?
    inter  = _compare(random_genome, random_action, "survival")   # G vs R : effet politique sur génome RANDOM (interaction)
    policy_sig = (policy["p"] < alpha) and (policy["cliff"] >= cliff_thresh)
    body_sig   = (body["p"]   < alpha) and (body["cliff"]   >= cliff_thresh)
    if policy_sig and body_sig:   verdict = "BOTH"
    elif policy_sig:              verdict = "COGNITION"     # la survie vient du FAIRE (politique)
    elif body_sig:                verdict = "BODY"          # la survie vient de l'ÊTRE (corps/génome)
    else:                         verdict = "NEITHER"       # dégénéré (le champion ne bat ni B ni R)
    return {"verdict": verdict, "policy_cmp": policy, "body_cmp": body, "inter_cmp": inter,
            "policy_sig": policy_sig, "body_sig": body_sig}
```
Seuils GELÉS = `ALPHA=0.05`, `CLIFF_THRESH=0.33`. `inter_cmp` (effet politique sur génome random) est un corroborant
d'INTERACTION rapporté : si la politique aide plus avec le génome champion (`policy["cliff"]`) qu'avec un génome random
(`inter["cliff"]`) → synergie génome×politique.

### `tools/s2_cognition_body.py` (CREATE)
`cognition_body_study(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=200) -> report`. Pour chaque monde :
déroule les 4 cellules via `run_condition` (réutilisé de `s2_demand`) — `champion`/`champion_body`/`random_genome`/
`random_action` — puis `verdict_cognition_body`. `_report` imprime le tableau 2×2 (survies médianes) + le verdict par
monde. RAG-off (`_disable_kuzu` par l'appelant), Holm sur la famille des mondes.

## Portée & régime (gelés)
- **5 mondes** (soup/stoneage/agricultural/industrial/famine) — S2-002 a montré le decoy perceptif sur les 5, donc la
  question « cognition ou corps » se pose partout. K=12, max_ticks=200, num_agents=20, RAG-off, seed=2026.
- **Déterminisme** : `seed_at` + `_disable_kuzu` ; 2 runs même seed reproductibles.

## Tests (`tests/`)
- `verdict_cognition_body` sur survies synthétiques : (a) C≫B, B≈R → **COGNITION** ; (b) C≈B, B≫R → **BODY** ;
  (c) C≫B, B≫R → **BOTH** ; (d) C≈B≈R → **NEITHER**. Verdict ∈ ensemble gelé.
- Contrat : `cognition_body_study` (config minuscule, calib stub / K=1) rend un bloc par monde avec les 4 survies + verdict.

## Résultat attendu (non préjugé)
- **BODY** → le biosphère récompense l'endurance/corps, pas la cognition → **le benchmark d'intelligence est
  questionnable** (finding foundational fort). Cohérent avec le régime dur (tout le monde meurt vite, la survie = drain).
- **COGNITION** → la survie vient de la politique obs-indépendante (le champion FAIT quelque chose d'utile sans percevoir)
  → l'intelligence compte, par un canal non-perceptif (réflexe/comportement interne).
- **BOTH / INTERACTION** → corps ET politique, possiblement en synergie (génome champion tuné à sa politique).

## Risques
- Un cerveau plus gros (génome champion) coûte plus d'énergie → `champion_body` (actions random) pourrait survivre PIRE
  que `random_action` (le cerveau champ = poids mort sans sa politique) : ce serait un signal fort de COGNITION (le corps
  seul est un handicap ; c'est la politique qui rentabilise le génome).
- HoF champion à charger via `HOF_PATH` PRÉFIXÉ en env. Compute : 4 cellules × 5 mondes × K=12 ≈ ~1 h → arrière-plan.
