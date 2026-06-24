# Design — Disjoindre monoculture vs génome (contrôle EDR 097)

Date : 2026-06-24

EDR 097 : le champion HoF cloné ×40 fait pire que la soupe fraîche diverse sur la compétence apex
vivante (apex 0.162 vs 0.211). Confond non séparé : génome champion apex-pauvre, OU effet monoculture
sur la chasse coopérative. Un bras de contrôle `mono_fresh` tranche.

## Contexte

L'apex-prédation est COOPÉRATIVE (pack, dégâts cumulés, EDR 096). Le bras `champion` de
`tools/target_competence_probe.py` est une **monoculture** (UN génome HoF cloné ×40) ; le bras `tabula`
est une population **diverse** (`init_primordial_soup`). Le déficit apex du champion (EDR 097) peut
venir du génome OU de la monoculture. Aucun des deux bras existants ne sépare les causes.

## Hypothèse & contrôle

Bras de contrôle **`mono_fresh`** : monoculture d'un génome **frais** (cloner `init_primordial_soup()
[0]` ×`num_agents`), exactement comme `champion` clone le HoF mais avec un génome random. Comparaison
3-way appariée par seed (même `SeedManager(i)`, donc comparable aux runs tabula/champion à `CT_K` égal) :

| bras | population | rôle |
|---|---|---|
| tabula | soupe fraîche DIVERSE | référence diversité |
| champion | monoculture HoF #1 | mesuré EDR 097 (apex 0.162) |
| **mono_fresh** | monoculture génome FRAIS | **contrôle** |

**Verdict :**
- `mono_fresh ≈ champion < tabula` → **MONOCULTURE** (la diversité porte l'apex coop) ; le champion
  n'est pas spécifiquement mauvais.
- `champion < mono_fresh` → le **génome champion** est apex-pauvre EN PLUS de l'effet monoculture.
- `mono_fresh ≈ tabula` → la monoculture est inoffensive → le déficit du champion EST le génome.

## Architecture — petit build

`tools/target_competence_probe.py`, fonction `run_probe` (`:55-119`). Ajouter une branche `mode ==
"mono_fresh"` dans le bloc de peuplement (`:72-83`) :

```python
elif mode == "mono_fresh":
    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    mono_g = genomes[0]                      # UN génome frais, cloné -> isole l'effet monoculture
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(mono_g)
        env.add_agent(a, energy=50.0)
```

Le reste (récolte enrichie `mammoth_kills`/`spears_crafted`, métrique vivante réparée, décompo
`frac_apex`/`frac_tool` par ère, verdict PLANCHER/SIGNAL, provenance) est **inchangé et réutilisé**.

## Garde-fous anti-théâtre

- **Apparié** : même `SeedManager(i)` que tabula/champion (CT_K égal) → 3-way comparable.
- **Décomposition rapportée** : `frac_apex`/`frac_tool` par ère (déjà câblés EDR 096), jamais le scalaire
  nu.
- **Tous les agents** (vivants+morts) : déjà le cas.
- **Sweet spot** explicite (0.25/3.0).
- Le contrôle EST la condition de validité de l'interprétation d'EDR 097 (sans lui, génome et
  monoculture restent confondus).

## Tests

- Smoke `slow` : `run_probe("stoneage", k=1, ..., mode="mono_fresh")` → renvoie `per_era` avec la
  décompo (`frac_apex`/`frac_tool`/`total_mammoth`/`total_spears`) et `median_competence ∈ [0,1]`
  (preuve que le mode peuple et tourne). Non-régression : `test_live_harvest.py` (mode tabula) reste
  vert.

## Hors périmètre (YAGNI)

- Pas de bras « champion dilué » (corroboration secondaire ; `mono_fresh` suffit à disjoindre).
- Pas de modif de la métrique ni du verdict.
- Pas de top-K HoF (un seul champion #1, comme EDR 097).

## Suite (selon verdict)

- MONOCULTURE responsable → l'apex coop dépend de la DIVERSITÉ → re-questionner le déploiement HoF
  (cloner un champion détruit la coordination) ; piste : populations mixtes / diversité préservée.
- GÉNOME responsable → le champion est réellement apex-pauvre → le HoF ne capture pas la compétence
  apex (re-questionner le critère de sélection HoF, cf. [[nas-bottleneck-is-substrate-not-search]]).
