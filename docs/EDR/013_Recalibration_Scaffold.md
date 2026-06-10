# EDR 013 : Recalibrage (C) + Scaffold d'Approche (A) — et le déplacement du goulot

## Contexte

Suite au verdict de l'EDR 012 (monde exigeant OK, mais émergence du craft réfutée : crash malthusien + chaîne trop profonde), on a appliqué « C puis A » : recalibrer l'écologie pour une population persistante, puis scaffolder le comportement profond.

## Décision (V18.1)

### C — Recalibrage écologique (3 itérations guidées par micro-mesure)

Le micro-test (30 agents, 200-300 ticks) a **éliminé** les fausses pistes :
- *Manque de nourriture* → ❌ (proies toujours pleines).
- *Reward-par-kill trop bas* → ❌ (survivants à 43 énergie).
- *Mort en HP / riposte* → ❌ après le fix ci-dessous (meanHP 96).
- **Compétence de chasse** → ✅ **LE goulot** : les agents faibles ne chassent pas assez, et le respawn instantané retiré au Step 2 était une *béquille* qui masquait ça.

Acquis conservés (vraies améliorations) :
- **Riposte juste** (`world_1`) : le gibier ne blesse que l'agent **sur sa case** (qui l'attaque), plus par simple proximité. Un agent prudent survit ; tuer un Mammouth exige de l'attaquer → prendre 50 → donc une lance. *Gradient moyens→fins préservé.*
- **Économie de camp de base** : `prey_reward` base 9→25 (Lapin ~26, viable ; Mammouth ~105, gradient préservé), `target_prey_count` 9→15, régénération en rafale (`prey_regen_burst=3`), `num_agents` 100→30.

### A — Scaffold d'approche (annelé)

Bonus d'énergie **annelé** qui enseigne le comportement de chasse manquant (`stone_economy.anneal`, `approach_reward`, câblés dans `_resolve_biology`) :
- `+ε·λ(ère)` si l'agent **réduit sa distance** au gibier le plus proche.
- `λ(ère) = max(0, 1 − ère/N)` : fort tôt, s'efface (le « cheatcode » de l'axe 5, à tester contre le pur intrinsèque).
- Variables d'expérience : `scaffold_eps=0.5`, `scaffold_eras=30`.

## Résultats — Run V18_V0_C_A (30 ères, 30 agents)

| Signal | Run EDR 012 (base 9) | Run C+A |
|---|---|---|
| Énergie moyenne | ~25, plate | **~35** (28-43) |
| Survie / ère | 50-60 ticks | **70-90 ticks** |
| Chasse (kills) | 900 | **~1500** (×1.7) |
| Craft (lances) | 1 | **1** (aucune nouvelle) |
| Tendance inter-ères | plate | **plate** (ère 1 ≈ ère 30) |

Micro-test (ère 1, λ~0.97) : survie précoce **×2.6** (13 vs 5 agents vivants à t30, meanE 51 vs 28).

## Diagnostic — le goulot se déplace

1. **Le scaffold d'approche fait sa cible** : plus de chasse, plus d'énergie, survie plus longue. ✅
2. **Le craft n'émerge pas** (0 nouvelle lance) — attendu : le scaffold d'approche n'enseigne pas la chaîne `grab→grab→rub`. Il lui faut **son propre scaffold**.
3. **Pas d'adaptation inter-ères** — le plus profond. En fin de run (ères 25-30), l'annelage a ramené le scaffold ~0, et survie/énergie restent comme au début (scaffold plein). **La population fait aussi bien sans le scaffold** : le subside aide la survie sur l'instant mais **ne s'encode pas dans le génome**.

> Le monde n'est plus le goulot (il est survivable et enseigne la chasse). Le nouveau goulot est le **moteur évolutif** qui ne grimpe pas — droit sur les leviers **Vague 1** de l'EDR 010 : gènes fantômes diluant la sélection, HoF passif (jamais recombiné/réinjecté), pas de crossover inter-ères.

## Conséquences — prochains leviers

- **(A-suite) Scaffold de craft** : récompenses intermédiaires annelées sur `grab d'ingrédient` + `craft de lance` + `coup sur gros gibier`. Complète l'échelle de compétence.
- **(Vague 1) Réparer le moteur évolutif** : tuer/câbler les gènes fantômes (restaure la pression de sélection), activer le HoF (crossover/réinjection inter-ères). C'est probablement la cause de la platitude inter-ères.

## Variables d'expérience

`PREY_REWARD_BASE`, `target_prey_count`, `prey_regen_burst`, `scaffold_eps`, `scaffold_eras`, fix riposte (même case vs proximité), `num_agents`. Toutes en ablation.
