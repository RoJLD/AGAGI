# EDR 193 — La fidélité latente n'est PAS un artefact d'encodage : un g BILINÉAIRE prédit le latent caché ~17× mieux que le g linéaire, avec une composante action-conditionnée (LATENT_BILINEAR)

> **Date** : 2026-07-02. **Fil** : G4 / anticipation (re-examine EDR 135). **Bloc** : 190+.
> **Verdict pré-enregistré** (décomposition FULL vs CACHÉS, spec §6) : `ENCODING_ARTIFACT` / `LATENT_BILINEAR` /
> `LATENT_LINEAR` / `PARTIAL`.
> **Résultat** : **LATENT_BILINEAR**. Sur les nœuds CACHÉS, la fidélité NE s'effondre PAS (learned-linéaire 0.358 =
> fidèle) → **pas un artefact de ré-encodage d'entrée** ; et un g **bilinéaire** (état-dépendant, fitté offline par
> ridge) prédit le latent caché **0.021 vs 0.358** pour le g linéaire du modèle (~17× moins d'erreur relative).
> **Contrôle** : per-action 0.021 vs action-agnostique 0.072 (×3.4) → composante **action-conditionnée réelle**.
> **Prédiction opus PRÉ-ENREGISTRÉE** : ENCODING_ARTIFACT — **RÉFUTÉE par le run** (rare miss ; le latent caché EST
> anticipable).
> **Outil** : `tools/g_bilinear_probe.py`. **Run** : seeds 0-7, warmup=300, measure=600, λ=1.0, **2 passes
> byte-identiques**. **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-02-g-bilinear-fidelity*`.

## 0. Correction de prémisse (revue finale opus, vérifiée)

Le design INITIAL supposait « le g linéaire d'EDR 135 était NEUTRE sur env-grille ». **FAUX** (vérifié en relançant le
tool d'EDR 135) : env-grille = **G_FIDELE** (median ~0.75) ; le NEUTRE était le mode **synthétique** (obs gaussiennes,
pas de couplage action→obs). Le chantier a donc PIVOTÉ (spec v2) vers la vraie question : cette fidélité vit-elle dans
le ré-encodage d'ENTRÉE (one-hot position, trivial) ou dans le latent CACHÉ (anticipation réelle) ?

## 1. Question et méthode

Rollout env-grille 1-D déterministe (miroir de `collect_ratios_env`, EDR 135) → triplets latents `(H_prev, move,
H_next, g_learned)`. On fitte offline (ridge, split temporel 70/30 par action, par seed) un g **bilinéaire**
`ΔH = H_prev · W_a` et on compare sa fidélité (`pred_err/base_err`) à celle du g linéaire **appris** (référence 135),
**décomposée** : dims PLEINES (172) vs dims **CACHÉES** `[I, N−O) = [14, 64)` (hors blocs one-hot entrée/sortie ;
layout vérifié `mamba_agent.py:356-376`).

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques ; n=1290 transitions test)

```
            | learned-lineaire | bilineaire
  FULL      |      0.293       |   0.028
  HIDDEN    |      0.358       |   0.021
  VERDICT : LATENT_BILINEAR
```

Diagnostic post-hoc (verdict gelé inchangé) — action-conditionnement sur les CACHÉS :
```
  HIDDEN per-action bilin   = 0.021
  HIDDEN action-agnostique  = 0.072   (un seul W poole sur toutes les actions)
```

## 3. Lecture

1. **ENCODING_ARTIFACT réfuté (opus s'est trompé sur la prédiction).** Sur les nœuds CACHÉS, la fidélité NE s'effondre
   PAS : le g linéaire y reste **fidèle (0.358 < 0.95)**. Donc le G_FIDELE d'EDR 135 sur env-grille **n'est PAS** un pur
   artefact de ré-encodage de position — le latent caché est **génuinement prédictible**. (Corrige/valide EDR 135 : sa
   fidélité env était réelle, pas I/O.)
2. **Un g bilinéaire écrase le g linéaire sur le latent (~17×).** HIDDEN bilinéaire **0.021** vs linéaire-appris
   **0.358** : la forme **état-dépendante** capture le latent caché quasi parfaitement là où le delta-constant-par-action
   du modèle laisse ~36 % d'erreur. **La FORME de g EST un levier réel** pour la fidélité d'anticipation (contrairement
   au cadrage initial, faux, où le linéaire était supposé neutre).
3. **La composante action-conditionnée est réelle mais partielle.** Per-action **0.021** bat l'action-agnostique
   **0.072** (×3.4) → l'action module vraiment la transition cachée (anticipation de conséquence d'action). MAIS
   l'agnostique est déjà **fidèle (0.072)** → une bonne part est une **récurrence quasi-linéaire-en-H** du connectome
   (`H_next ≈ W·H_prev`), trivialement fittable par une carte linéaire, indépendamment de l'action.

## 4. Portée — un levier G4 positif, borné

- **Actionnable** : le planificateur/rêve gagnerait à un g **bilinéaire** (état-dépendant) plutôt que le
  delta-constant-par-action actuel — il prédit le latent (dont les cachés) ~17× mieux, avec un vrai conditionnement
  d'action. **1er levier G4 « forme de g » qui PAIE** dans ce fil (135 n'avait pas de contraste valide).
- **Borné (caveats)** :
  - **(a) Fit offline = ORACLE** (borne haute). Le modèle apprend un g LINÉAIRE en ligne ; qu'il puisse APPRENDRE le
    bilinéaire via sa plasticité est **non testé**. Le résultat prouve que la forme bilinéaire *peut* prédire, pas que
    le moteur *saurait* la fitter en ligne.
  - **(b) Fidélité ≠ comportement** (caveat EDR 135) : mieux prédire le latent n'établit PAS que ça améliore
    survie/planification. La fidélité de g est nécessaire, pas suffisante.
  - **(c) Récurrence quasi-linéaire** : une part du gain bilinéaire = le connectome est ~linéaire-en-H (agnostique déjà
    fidèle 0.072). Le « bilinéaire gagne » signifie d'abord « la transition interne est une carte per-action linéaire
    de H », que le g linéaire-constant du modèle ne capture pas.

## 5. Caveats méthodo

- **(d)** Env-grille seul (obs riche causal) ; substrat synthétique non inclus (backlog). Le masque exclut aussi les
  **sorties** `[N−O, N)` (moteurs) ; on restreint aux cachés purs `[I, N−O)`.
- **(e)** Sous-détermination `W_a` (172×172, ~200 triplets/action, λ=1.0) bornée par le **test-set** (le ratio bas est
  sur held-out → la structure prédite est réelle, pas de l'overfit). **(f)** float64 (fit) vs float32 (135). Verdict au
  comptage/median via `fidelity_verdict` (EDR 135). Hérite des caveats d'EDR 135.

## 6. Provenance / non-périmètre

- `tools/g_bilinear_probe.py` (`main_bilinear_check`, seeds 0-7, w300/m600, λ=1.0) ; **2 passes byte-identiques** ;
  diagnostic action-conditionnement lancé une fois (post-hoc, verdict gelé inchangé). AUCUN test relancé après le run.
- **Tooling ADDITIF** : nouveau fichier + test + spec/plan/EDR uniquement ; `src/` intact (import read-only de
  `mamba_agent`) ; `tools/g_fidelity_probe.py` (EDR-135) **intact** (réutilisé par import). Ne touche NI le substrat
  torch (fil //).
- Subagent-driven : 2 tâches machinerie + 1 rework (SPEC conforme + qualité Approved), revue finale **opus** qui a
  **invalidé la prémisse initiale** (C1 : linéaire FIDELE sur env-grille ; C2 : risque d'artefact d'encodage) → PIVOT
  vers la décomposition FULL/CACHÉS (contrôle décisif I1 d'opus). **Opus a prédit ENCODING_ARTIFACT ; le run l'a
  RÉFUTÉ** (le latent caché est fidèle) — cas où l'instrument tranche contre la prédiction, ce qui renforce la valeur du
  contrôle pré-enregistré. Verdict gelé avant le run.
- **Numérotation** : EDR **193** — bloc **190+**. Re-examen isolé d'EDR 135 (G4/anticipation).
