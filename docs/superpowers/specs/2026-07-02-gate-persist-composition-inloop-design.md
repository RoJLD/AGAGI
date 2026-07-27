# Design — Persistance du gate à travers le rebuild + binding in-loop (cran 2, prérequis)

> Session 2026-07-02 (suite d'EDR-163). Débloque le cran 2 (gate in-world) identifié comme bloqué par
> le review final : le rebuild du pop sur mortalité réinitialise `w_gate`/`b_gate` → érode le binding
> appris. Backlog : `../../BACKLOG.md` §Axe 1. Méthode : Commandement 15 (1 variable, powered).

## Problème

L'infra torch in-loop (crans 0-1, EDR-163) reconstruit le pop torch quand la population change
(mortalité). Le rebuild crée un `w_gate`/`b_gate` NEUFS. Or le gate porte le binding means→ends appris
(EDR-158/159). Au cran 2 (allumer le gate in-world), chaque décès effacerait donc le binding accumulé.
Le probe compositionnel d'EDR-161 (CAPABILITY_PAYS) n'a jamais rencontré ce régime : son pop est fixe,
jetable, sans rebuild. **Question : le CAPABILITY_PAYS d'EDR-161 survit-il quand le pop est reconstruit,
et la persistance du gate est-elle le levier ?**

## Asymétrie du rebuild (fait structurant)

Au rebuild réel in-world :
- **W (substrat)** SURVIT — écrit dans le génome par Baldwin (`_write_back`), relu par le nouveau pop.
- **gate (`w_gate`/`b_gate`)** PERDU — population-partagé, PAS dans le génome (MVP non-hérité).

Le binding appris vit dans le gate → il s'évapore au rebuild alors que le substrat persiste. Le harnais
reproduit fidèlement cette asymétrie : rebuild = `TorchPopulationModel(mêmes_agents)` (W via génome) +
gate neuf ; `inherit_gate` porte le gate en plus.

## Architecture — deux unités

### Unité A — `TorchPopulationModel.inherit_gate(old_pop)` (additif)
Copie `w_gate.data`/`b_gate.data` de `old_pop` vers `self` si les dimensions sont compatibles (même N).
Skip propre (log, no-op) si incompatible (N changé) ou si l'un des gates est None. ADDITIF : ne touche
NI forward NI learn NI learn_episode. Réutilisable par l'intégration biosphère réelle (cran 2 réel).

### Unité B — `tools/torch_gate_persist_ab.py` (harnais in-loop)
Réutilise le monde 2-pas craft→USE d'EDR-161 (`compositional_world_probe`, non modifié). Fait tourner un
pop torch PERSISTANT sur des cycles ; tous les R épisodes, déclenche un REBUILD (nouveau
`TorchPopulationModel` depuis les mêmes agents → W survit via génome). A/B sur le rebuild :

| Bras | Au rebuild | Isole |
|---|---|---|
| PERSIST | `inherit_gate(old_pop)` (gate survit) | le fix |
| RESET | gate réinitialisé (bug actuel) | le bloqueur |

KPI = `comp_rate` (instrument EDR-161) mesuré après plusieurs cycles de rebuild. Verdict via
`compute_ab_verdict` (substrate_ab). Hypothèse falsifiable : **PERSIST maintient le binding à travers la
mortalité, RESET le perd.** Si les deux tiennent → la persistance du gate n'était pas le bloqueur
(informatif aussi).

## Data flow
1. Init : pop torch persistant (gate ON, GATE_TARGET=USE), agents à génomes homogènes (N stable).
2. Boucle d'épisodes : forward S1/S2 → `learn_episode` (gate + crédit épisodique), Baldwin write-back W.
3. Tous les R épisodes : rebuild = `TorchPopulationModel(agents)` (W relu du génome) ; bras PERSIST
   appelle `new.inherit_gate(old)`, bras RESET ne fait rien.
4. Fin : `comp_rate` du dernier quart, apparié par seed, verdict PERSIST vs RESET.

## Error handling
- `inherit_gate` : dims incompatibles / gate None → no-op loggé, jamais de crash.
- Rebuild : si le gate source est absent (gate OFF), `inherit_gate` est un no-op.
- Le harnais tourne gate ON des deux côtés (seul le comportement au rebuild varie).

## Testing
- `inherit_gate` copie les valeurs (dims compatibles) : `new.w_gate == old.w_gate` après appel.
- `inherit_gate` skip propre sur dims incompatibles (N différent) : no-op, pas d'exception.
- `inherit_gate` no-op si un gate est None.
- Harnais : `run_arm(persist=...)` renvoie `comp_rate` ; `compare` produit un verdict PERSIST vs RESET.
- Smoke léger (peu d'épisodes/agents/rebuilds) pour la structure ; le verdict scientifique = run powered.

## Bornes (caveats)
- N stable requis (cohorte fixe ; `add_node` casserait le transfert de `w_gate` taille N).
- Monde synthétique 2-pas (proxy EDR-161), pas la biosphère — indicatif, pas conclusif in-world réel.
- Optimiseur Adam réinitialisé au rebuild (perte des moments accumulés → impact négligeable, cf. review final EDR-163).
- Gate reste population-partagé non-hérité (MVP) — c'est justement ce qui rend le carry-over explicite
  nécessaire ; un gate hérité (dans le génome) serait une autre conception (hors scope).

## Contraintes projet
- Commits PATH-SCOPED : `backend_torch.py` porte du travail EDR-160 en vol (session //) → committer
  UNIQUEMENT l'ajout `inherit_gate` de façon isolée. Harnais/tests = fichiers neufs.
- Non-régression : `inherit_gate` additif, gate OFF par défaut → chemins existants intacts.

## Hors scope
Intégration du gate dans `world_1_stoneage.py` (cran 2 réel), gate hérité dans le génome, N variable
(add_node) au rebuild, biosphère réelle. Ce chantier valide le PRÉREQUIS et l'hypothèse en harnais.
