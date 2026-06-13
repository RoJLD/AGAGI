# Roadmap AGIseed — Ce qui reste

> **Vision** : un *« algorithme de la vie »* où la bonne chose à faire n'est **pas dite mais trouvée** —
> l'intelligence *trouvée* (connectomes évolués, bottom-up), pas *donnée*.
>
> **Cette page = ce qui reste à faire + où on en est.** L'**historique** scientifique :
> `docs/FIL_CONDUCTEUR.md` (récit) + `docs/EDR/*` (détail, 87 décisions). Les **idées futures /
> aspirationnel** : `docs/BACKLOG.md`. Méthode : **Commandement 15** (1 variable, ≥... mesures, valide ou
> revert — *powerer avant de conclure*).

---

## Architecture (V15/V16)
- **59 entrées / 108 sorties** ; moteur **Liquid Mamba BatchModel** vectorisé + TTC adaptatif ; écologie 9 proies + apex + feu + crafting ; **World Model** (RND), **Actor-Critic TD** intra-vie, **HoF robuste** inter-ère.

## Les 7 Arcs (phylogénèse)

| Arc | Thème | Statut |
|---|---|---|
| 1 | L'Animal (Survie) | ✅ TERMINÉ |
| 2 | Le Primate (Outils) | ✅ TERMINÉ (V14) |
| 3 | L'Homo Habilis (Crafting) | ✅ chaîne moyens→fins émergente+robuste (`027-030`) |
| **4** | **L'Homo Sapiens (Langage)** | 🔵 **EN COURS** — code référentiel fiable câblé (`072-074`) ; bénéfice fonctionnel en cours de test rigoureux (`087`) |
| 5 | La Tribu (Culture) | ⚪ après clôture Arc 4 |
| 6-7 | Penseur, Conscience | ⚪ gelé (`docs/BACKLOG.md`) |

## Diagnostic — 3 causes-racines (orientation)

> De l'audit `EDR 010` (causes A, B) + la trouvaille de session (cause C).

| # | Cause | État |
|---|---|---|
| **A** | Le cerveau ne prédit pas | ✅ World Model RND (`011`) |
| **B** | Le monde n'exige pas l'intelligence | ✅/🔵 monde exigeant (`012`) **+ sweet spot d'énergie** (`085` : il était *trop dur* pour la survie soutenue → réglé : ×5 compétents/frais) |
| **C** | *(nouveau)* Le moteur de SÉLECTION limité par le bruit de fitness | ✅ **HoF robuste en prod** (`078-081`, gated) → +50 % compétence qui *compose* |

---

## Où on en est (037→087)

> Grand arc de session : **langage → gradient → compétence → survie**. Récit complet : `FIL_CONDUCTEUR.md`.

- **Langage (037-074)** : de « bruit » à un **code référentiel fiable câblé dans l'agent** (gradient → convergence 100 % `072` → tête dédiée `074`, MI live +0.22, gated).
- **Gradient (067-071)** *(hors plan)* : la mutation est un **chercheur faible** en supervisé (mémoire `067`, langage `072`) ; mais le **BPTT NUIT en RL** (`077`, auto-réfutation).
- **Compétence (075-081)** : plateau = **bruit de fitness** (`078`) → remède robuste en prod, qui **compose** (`081`).
- **Survie (082-087)** : le langage ne payait pas car les agents mouraient ~45 ticks (`082`). Cause = **économie d'énergie** (`084` : 79 % starvent) → **sweet spot** (`085`, survie ×4) → débloquer la survie a *révélé et corrigé* une **instabilité du connectome** sur les longs épisodes (`086`) → **re-test rigoureux du bénéfice du langage en cours** (`087`, design audité contre 12 confounds).

> **Discipline** : 5 fois un signal à peu de seeds s'est évaporé sous puissance (`057/075/077/082/083`). *Powerer + auditer le design avant de conclure.*

---

## 🔬 Frontière scientifique — prochains leviers

1. **Clore le bénéfice fonctionnel du langage (Arc 4)** — le re-test `087` (FIABLE vs BROUILLÉ, isole le *contenu* du téléguidage) : à survie longue, le contenu référentiel paye-t-il ? Si oui → Arc 4 clos. Si non → sélectionner l'usage du signal + survie encore plus longue.
2. **Régler le sweet spot d'énergie** (`085`) comme variable d'expérience (métab/payoff/densité) — activer par défaut si robuste.
3. **Co-évoluer l'usage du langage** (`083`, tendance +0.29 sous 2 SE) — pression de sélection explicite sur l'écoute du signal.
4. **Vraie RSI** (le #8 est armé `065-069`, sandbox sûre `035`) — différée jusqu'à un bottleneck, à armer en conteneur.
5. **Arc 5 (Tribu)** — *seulement* après clôture de l'Arc 4.

## 🛠️ Outillage / Dev

**Livré (session)** :
- **Dashboard EDR** (`frontend`, onglet `edr`) : visualise les vraies expériences (compétence, bruit de fitness, langage…) via `/api/edr`. **Biosphère live** (onglet `live`) : run évolutive réelle depuis le HoF, sparklines temps-réel.
- **HoF robuste en production** (`config.robust_hof_K`, gated) ; **knobs d'économie d'énergie** (`base_metabolism`, `forage_payoff`, gated) ; **stabilité du connectome** sur longs épisodes (`086`).

**Reste** :
- Stubs frontend à brancher : `sandbox_service` (backend manquant), academy/strategy en mock.
- **Unifier le moteur** : `world_0_soup` duplique `Biosphere3D` (devrait en hériter) ; `world_2/3` inachevés.
- **Ontologie Hypothesis/Fact** (schéma déclaré, vide) : chaque EDR = `Hypothesis`, chaque mesure = `Fact`.
- **Ablation** (levier 5) : Ratio de Transfert sur les mécanismes (curiosité/scaffold/World Model/seuils/router).

---

## Statut des Vagues (pointeurs)

| Vague | Statut |
|---|---|
| **0 — Fondations** | ✅ LIVRÉE (`010-030`) : moteur évolutif réparé (`016`), Actor-Critic (`020`), chaîne moyens→fins auto-suffisante (`030`) |
| **1 — Honnêteté/hygiène** | 🟠 gènes câblés ✅ (`031`) ; ablation + unify-engine + ontologie ⏳ (cf. Dev) |
| **2 — RSI (graine d'AGI)** | ✅ sandbox isolée (`035`) + supervisor réflexif (`036`) + **#8 armé** (`065-069`) ; vraie RSI ⏳ (différée) |
| **3 — Émergence avancée** | 🔵 **langage émergent EN COURS** (`037-087`, Arc 4) ; protoconcepts/économie cognitive → `BACKLOG.md` |
| **4 — Différé/gelé** | ⚪ NAS Macro, Arcs 6-7 → `BACKLOG.md`. À ne pas toucher tant que V0-V3 ne livrent pas. |

> **Règle** : on ne passe à la vague N+1 que si N est *livrée ET mesurée*.

## Méthode & Outils
- **Commandement 15** : 1 variable, mesures suffisantes (≥ ce que la puissance exige), Sociologue, valide ou revert.
- Outils : `tools/sociologist.py` (rapport KuzuDB), `tools/skinner_box.py` (audit neuronal), `tools/progress.py` (barres+ETA), `migrate_v10.py` (chirurgie génétique).
