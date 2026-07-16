# EDR 106 — POLITIQUE : le mur d'approche est la NAVIGATION de l'agent, pas la cinématique des proies

## Contexte

EDR 105 a localisé le mur d'acquisition à l'**APPROCHE** (`GOULOT=APPROCHE`) : à `N_APEX=0`/`metab=0`,
seuls 18% des agents atteignent une cellule-proie (`p_reach`), mais capturent à 100% quand ils y
arrivent. Le `min_dist` plafonne à ~1.24 — les agents s'approchent à ~1 case sans franchir la
dernière.

L'exploration du code a révélé une **hypothèse cinématique forte** : les proies régulières fuient
(Lapin `moves_per_tick=2`, Cerf `=1`) ou approchent (Sanglier `=0.5`), l'agent se déplaçant à 1/tick.
Le **Lapin fuit deux fois plus vite** que l'agent → kinématiquement increatchable par poursuite naïve.
Le plateau `min_dist≈1.24` semblait expliqué : l'agent colle une proie qui court plus vite que lui.

EDR 106 teste cette hypothèse en **annulant la vitesse des proies**. Pré-enregistrement :
`docs/superpowers/specs/2026-06-25-EDR106-Approach-Kinematics-design.md`. Variable :
`prey_speed_scale ∈ {1.0, 0.5, 0.25, 0.0}` à `N_APEX=0`/`metab=0`, reste gelé. Métrique : `p_reach`
(entonnoir `trace_forage` d'EDR 105, réemploi DRY). **Verdict porté par le niveau figé** (`scale=0`).
Lignée : 090→…→101→105→**106**.

## Le verdict : POLITIQUE

| `prey_speed_scale` | p_reach | p_cap | cap_tot | cap_lapin | cap_cerf | cap_sanglier | min_dist | n |
|---|---|---|---|---|---|---|---|---|
| 1.0 (baseline) | 0.16 | 1.00 | 0.32 | 0.12 | 0.11 | 0.06 | 1.32 | 1795 |
| 0.5 | 0.19 | 1.00 | 0.42 | 0.17 | 0.12 | 0.10 | 1.27 | 1026 |
| 0.25 | 0.19 | 1.00 | 0.37 | 0.16 | 0.11 | 0.08 | 1.43 | 1061 |
| **0.0 (figé)** | **0.21** | 1.00 | 0.37 | 0.15 | 0.12 | 0.07 | 1.37 | 467 |

`p_reach(figé) = 0.21 < 0.5` → **POLITIQUE**. Figer entièrement les proies fait passer `p_reach` de
0.16 à seulement **0.21** : même des proies **totalement immobiles** ne sont atteintes que par 21% des
agents. Le mur N'EST PAS la cinématique.

## Le mécanisme : l'hypothèse cinématique est RÉFUTÉE

Trois faits convergent :

1. **Figer ne débloque presque rien.** `p_reach` : 0.16 → 0.21 entre pleine vitesse et figé — un gain
   dérisoire, **très loin** du seuil 0.5. Si la fuite était le mur, figer aurait fait sauter `p_reach`.
   Il ne bouge quasiment pas.
2. **Le plateau `min_dist` persiste figé.** Même contre des proies **immobiles**, `min_dist` reste
   ~1.37 : les agents s'approchent à ~1 case d'une cible **statique** et ne franchissent toujours pas
   la dernière case. Ce n'est donc pas « la proie s'enfuit » — c'est **l'agent qui ne fait pas le pas
   final**.
3. **L'effet cinématique existe mais est marginal.** Jonckheere-Terpstra z=1.91, p=0.028 : `p_reach`
   croît *faiblement* quand la vitesse baisse. La cinématique a un effet **réel mais négligeable**
   (~0.05 de `p_reach`), incapable de débloquer le mur.

**La répartition par espèce réfute aussi la prédiction secondaire.** J'avais prédit des captures
dominées par le Sanglier (seul qui approche) ; en réalité elles sont dominées par le **Lapin**
(0.12-0.17, le fuyard le plus rapide) et figer ne débloque **aucune** espèce (Lapin 0.12→0.15,
Sanglier 0.06→0.07). Même la proie la plus rapide est attrapée à peu près autant figée que mobile →
la vitesse n'est pas le facteur limitant.

## Ce que cela signifie : le mur est la POLITIQUE de navigation (substrat)

Le mur d'approche est la **politique de navigation évoluée du champion** : sa trajectoire l'amène à
~1 case des proies mais ne s'engage pas sur leur cellule, même quand elles sont immobiles. Pour des
**réplicas** (pas d'évolution, pas d'apprentissage en ligne ici), cette politique est **figée** — le
scaffold d'approche (qui récompense la réduction de distance) ne joue qu'à l'évolution, pas pour des
réplicas. Donc le déficit vit dans le **substrat évolué** : les champions forgés en *stoneage* ne
naviguent pas vers les proies de Lewis.

Cela **re-confirme la méta-leçon NAS/090** : le goulot est le **substrat / répertoire comportemental**,
pas un paramètre de monde (ni la cinématique, ni l'énergie). Aucun knob de vitesse ne répare ce qui
est un déficit de **compétence de navigation** dans le génome.

| Hypothèse sur l'APPROCHE | Test (EDR 106) | Verdict |
|---|---|---|
| CINÉMATIQUE (proies fuient trop vite) | figer les proies → `p_reach` 0.16→0.21 | **RÉFUTÉE** (effet marginal) |
| POLITIQUE (navigation de l'agent) | proies figées toujours non atteintes (`p_reach=0.21≪0.5`) | **RETENUE** |

## Le vrai levier suivant (re-pointé) : la compétence de navigation du substrat

EDR 106 ferme la question cinématique et re-pointe vers le **substrat** :

- **Ré-évoluer la navigation EN Lewis (prioritaire)** : sélectionner sur l'atteinte de proies en Lewis
  (pas en stoneage), pour forger une politique qui s'engage sur la cellule-proie. C'est l'écho direct
  d'EDR 090 (« adapter le substrat AVANT de durcir ») et de la méta-leçon NAS.
- **EDR 107 = décomposer le déficit de politique** : pourquoi la trajectoire stoppe à ~1 case d'une
  cible statique ? Pistes (non mesurées) : décalage de distribution d'observations stoneage→Lewis (la
  politique « voit » Lewis différemment), une action de pas-final que le réseau n'émet pas, ou
  l'absence d'apprentissage en ligne pour corriger. C'est une décomposition du substrat, pas du monde.

## Honnêteté & méthode

- **Intuition réfutée (4ᵉ fois).** Mon hypothèse cinématique était *forte* (Lapin fuit à 2×) et
  **fausse**. Comme heal (EDR 094), brain_cost (098) et throw (099), la mesure a battu l'intuition.
  L'expérience était conçue pour falsifier dans les deux sens — et elle a falsifié *mon* hypothèse.
  C'est le cœur de la méthode : pré-enregistrer un verdict que les données peuvent renverser.
- **Verdict surdéterminé, puissance réduite.** Run gelé impraticablement lent à `metab=0`/`scale=0`
  (agents mieux nourris survivent plus ; précédent EDR 101/105) → run **réduit fidèle** (`R=1,
  n_eval=3, max_ticks=150`). `p_reach(figé)=0.21` est estimé sur **n=467 agents** ; le seuil 0.5 est
  très loin. Provenance `results/lewis_approach_kinematics_106.json` (régénérable, `seed=106`, commit
  `dfeb888`).
- **Caveat `n` variable.** `n` décroît avec la vitesse (1795→467) — dynamiques de
  reproduction/survie différentes selon le niveau. Le verdict porte sur la **fraction** `p_reach`
  (bien estimée à chaque niveau), pas sur `n` ; la monotonie marginale (JT) est cohérente malgré la
  variation de `n`.
- **Invariant RNG (verrou non-régression).** Le knob `prey_speed_scale=1.0` (défaut) est
  **byte-identique** à l'origine (multiplication par 1.0 = identité IEEE 754, même consommation de
  `np.random.rand()`) — vérifié par test (trajectoires identiques sur 8 steps) et par la revue finale
  (PRÊT À MERGER). Protège les sessions parallèles.
- **Freeze réellement immobile.** À `scale=0` : fuite-au-feu désactivée + `moves_per_tick=0` → aucune
  voie de mouvement. Le verdict repose sur un niveau authentiquement figé.

## Variables d'expérience

`prey_speed_scale` (balayé : POLITIQUE — figer ne débloque pas), et — prochain levier — la **compétence
de navigation du substrat** (ré-évoluer en Lewis / décomposer le déficit de politique, EDR 107). Outils :
`tools/lewis_survival_sweep.py` (`main_approach`, `_verdict_approach`, `_report_approach`, param
`_cfg(prey_speed_scale=…)`), knob + compteur espèce dans `src/worlds/world_1_stoneage.py`,
`src/seed_ai/exp_stats.py`. Provenance : `results/lewis_approach_kinematics_106.json` (puissance
réduite, surdéterminé). Lignée : 090→093→094→098→099→100→101→105→**106**.
