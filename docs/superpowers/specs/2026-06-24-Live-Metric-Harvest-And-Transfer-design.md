# Design — Câbler la récolte de la métrique vivante + re-mesurer le transfert

Date : 2026-06-24

Compléter la réparation de `stoneage_competence` (EDR 096) en alimentant les champs vivants qu'elle lit,
puis re-mesurer le transfert (champion-vs-frais, puis curriculum) sur cette dimension enfin vivante.

## Contexte

EDR 096 + réparation (PR #50) : `stoneage_competence` agrège désormais des **fractions de
participation** à des signaux VIVANTS — `mammoth_kills` (apex coop) et `spears_crafted` (lance) — au lieu
de l'autel mort. Mais les deux sites de récolte d'`agent_stats` ne fournissent PAS ces champs :

- `make_run_era_fn` (`main_curriculum.py:108-114`) — utilisé par le `CurriculumRunner` (curriculum réel
  ET expérience A) — récolte `age/energy/preys_eaten/altars_solved/total_dreams`.
- `target_competence_probe.run_probe` (`tools/target_competence_probe.py:92-94`) — expérience B — idem.

**Conséquence** : `_frac_reaching(stats, "mammoth_kills")` lit un champ absent → `frac_apex = frac_tool =
0` → la compétence retombe à `0.4·frac_hunt`, un faux plancher. **La réparation de métrique est donc
INERTE** (dans le curriculum réel comme dans les sondes) tant que la récolte n'alimente pas ces champs.

## Périmètre

1. **Câbler la récolte** (complète la réparation) : ajouter `mammoth_kills`/`spears_crafted` aux deux
   dicts `agent_stats`.
2. **Run B** (champion-vs-frais) puis **Run A** (transfert curriculum), sur la métrique vivante, + EDR.

Hors périmètre (YAGNI) : pas de modif des métriques ; pas de 3ᵉ site de récolte (`base_world.run_era`
n'est pas le chemin de A/B) ; pas de nouveau verdict (les tools en ont déjà).

## Architecture

### Unité 1 — câblage de la récolte (build)

Ajouter deux clés aux dicts `agent_stats`, aux deux sites, via `a.get(..., 0)` (additif, sûr ; champs
présents sur stoneage `world_1_stoneage.py:337,339`, 0 ailleurs ; les métriques non-réparées ne les
lisent pas) :

```python
"mammoth_kills": a.get("mammoth_kills", 0),
"spears_crafted": a.get("spears_crafted", 0),
```

- `main_curriculum.py:108-114` (`make_run_era_fn`).
- `tools/target_competence_probe.py:92-94` (`run_probe`).

**Test (garde-fou régression)** : smoke `slow` — une mini-ère stoneage via `make_run_era_fn` →
asserter que `agent_stats[0]` contient les clés `mammoth_kills` ET `spears_crafted` (preuve que la
récolte alimente la métrique réparée). C'est le seul test : le reste est pure exécution.

### Unité 2 — Run B (champion-vs-frais)

`tools/target_competence_probe.py`, cible **stoneage**, sweet spot (`CT_METAB=0.25 CT_PAYOFF=3.0`),
K ères, plusieurs seeds (via re-run par `CT_K`). Lancer `CT_MODE=tabula` puis `CT_MODE=champion`.
**Verdict** : le champion PORTE la compétence apex/outil si `competence(champion) > competence(tabula)`
ET la décomposition (la sonde sort déjà `med_*`/`max_*` par ère + signaux bruts) montre un avantage apex
(et/ou lance) chez le champion. Rapporter la décomposition, jamais le scalaire nu.

### Unité 3 — Run A (transfert curriculum)

`tools/curriculum_transfer.py`, `CT_METRIC=world` (→ `competence_for("stoneage")` = métrique réparée),
cible **stoneage**, ladder développementale (ex. `CT_LADDER` menant à stoneage), sweet spot, ≥5 seeds.
Ratio `C_curr/C_tabula` apparié → `compute_transfer_verdict` (TRANSFERE/NEUTRE/NUIT, `sign_p`). Rapport
par seed.

## Garde-fous anti-théâtre

- **Le câblage est la condition de validité** : sans lui, B et A mesureraient un faux plancher (apex
  invisible). C'est précisément le piège qu'une exécution à l'aveugle aurait raté.
- **Décomposition rapportée** : B sort les signaux bruts par ère ; A le ratio par seed. Jamais le label
  nu.
- **Tous les agents** (vivants+morts) : déjà le cas aux deux sites (`env.agents + env.dead_agents`).
- **Sweet spot** explicite (sinon plancher létal, EDR 085).
- **Champ vivant confirmé** : `mammoth_kills`/`spears_crafted` incrémentés (`world_1_stoneage.py:717-723,
  1210`).

## Tests

- Unité 1 : smoke `slow` (clés présentes dans `agent_stats` après une ère stoneage). Non-régression :
  `tests/sandbox/test_competence_repair.py` + `test_curriculum_transfer.py` restent verts (signatures
  inchangées ; les dicts gagnent 2 clés, lues seulement par la métrique réparée).
- Unités 2/3 : exécution + EDR (pas de test ; la validité repose sur le câblage + la décomposition).

## Suite (selon verdicts)

- B `champion > tabula` sur apex/lance → les champions PORTENT une compétence vivante transférable →
  A pertinent (le curriculum la construit-il ?).
- B `champion ≈ tabula` → la compétence vivante n'est pas portée par les champions (re-questionner le
  HoF / la sélection).
- A `TRANSFERE` → l'échafaudage développemental construit la compétence vivante (déblocage majeur,
  contredit le NEUTRE d'EDR 091 qui mesurait le plancher mort).
