# EDR 110 — La capacite cachee monte-t-elle le plafond de navigation Lewis ? (Phase 1 : echelle statique)

> **Spec de conception** — 2026-06-29. Suite directe d'EDR 107 (SUBSTRAT BLOQUE).
> Outil : `tools/lewis_survival_sweep.py` (extension DRY, comme 105/106/107).
> Discipline : Commandement 15 (1 variable = la capacite cachee semee).

## 1. Contexte & question

**EDR 107** a re-evolue la navigation EN Lewis (N_APEX=0, metab=0, forage_payoff=3) sur la fitness de
prod `calculate_life_score`, cliquet best-ever, 20 generations. Resultat : `p_reach` (fraction
d'agents atteignant une cellule-proie) **plafonne ~0.36** — un doublement one-shot du baseline 0.18
puis **saturation** (first-5 median 0.365 vs last-5 0.373, pente +0.0038 plate) ≪ competence 0.5.
Verdict : **le verrou est l'ARCHITECTURE du connectome**, ni le monde, ni la selection, ni la
cinematique (EDR 106), ni l'energie (090-101).

**Le suspect numero 1.** Le connectome de prod est `MambaAgent(num_inputs=59, num_outputs=108,
num_nodes=172)` -> **hidden = 172 - 59 - 108 = 5 noeuds caches** (97 % I/O). Tout le programme NAS
converge sur ce fait structurel (nas-d1 : hidden=5/172 ; from_genome keystone). C'est le candidat
naturel pour expliquer la saturation a 0.36.

**La question d'EDR 110.** Si l'on **ajoute de la capacite cachee** au connectome, le plafond de
navigation `p_reach` monte-t-il au-dessus de 0.36 ? C'est le test *direct* de la conclusion d'EDR 107 :
manipuler l'architecture qu'on accuse.

**Hypothese concurrente a respecter.** Le verrou pourrait etre le **repertoire-MONDE**, pas la
capacite reseau (EDR 105-Topo : la croissance topologique ne leve pas l'apex ; nas-bottleneck :
corr nodes x apex = -0.18, plus gros cerveaux n'achetent pas d'apex). MAIS cela concernait
l'**apex/coop** ; EDR 110 teste la **navigation** (`p_reach`), metrique plus en amont, localisee par
EDR 107. Donc non-redondant et **decisif des deux cotes**.

## 2. Raffinement-cle (decouvert au cadrage) : EDR 107 avait deja la croissance lente

`MutationConfig` (defaut) porte `add_node_rate=0.2` et `prune_rate=0.1`. Le `mc =
MutationConfig(weight_init_std=2.0)` d'EDR 107 **avait donc la croissance topologique ACTIVE** —
et a quand meme plafonne. EDR 107 a ainsi *implicitement* teste « laisse la capacite grandir
lentement (de 5, quelques noeuds en 20 gen) » -> plafond.

Consequences :
- **Phase 2 (croissance dynamique) est en grande partie deja repondue** par EDR 107. Elle ne sera
  rouverte que si la Phase 1 le justifie (EDR 111 eventuel).
- **EDR 110 = Phase 1 = capacite STATIQUE large d'emblee** : la manipulation vraiment nouvelle et
  plus forte. On seme directement N caches (jusqu'a 16x le baseline) et on **fige la capacite**
  (`add_node_rate=0.0, prune_rate=0.0`) pour que N soit la seule variable entre bras.
- Question aiguisee : *la lenteur de la croissance* est-elle le frein, ou la *capacite elle-meme*
  est-elle inerte pour la navigation ? Semer 80 caches gratuitement tranche.

## 3. Architecture

Etendre `tools/lewis_survival_sweep.py`. Pour chaque palier de capacite cachee N d'une echelle
`hidden_levels=(5, 20, 40, 80)` :
1. **Semer** des genomes frais a N caches (`num_nodes = 167 + N`, I=59, O=108, W dense aleatoire x0.1).
2. **Evoluer** via la boucle evolve_nav d'EDR 107 (ere fraiche scaffold-chaud, metab=0, Lewis vide
   d'apex, cliquet best-ever) MAIS avec un `MutationConfig` a **capacite figee** (`add_node_rate=0.0,
   prune_rate=0.0` ; mutation de poids + add_connection conservees pour cabler les caches semes).
3. **Lire deux signaux gratuits** dans la meme trajectoire :
   - `p_reach` a la **generation 0** = effet capacite BRUTE (caches denses fonctionnels des le depart).
   - **plateau evolue** = mediane des k dernieres generations (k=5 si gen>=10), comme EDR 107.

Verdict : le plateau monte-t-il **monotonement** avec N (CAPACITE LEVE) ou reste-t-il plat
(CAPACITE INERTE -> convergence surdeterminee avec le verrou repertoire-MONDE) ?

## 4. Composants & interfaces

Tout dans `tools/lewis_survival_sweep.py` (reutilise au maximum l'existant 105/106/107).

### 4.1 `_fresh_genome(n_hidden)`
- **Produit** : un `Genome` frais a capacite cachee `n_hidden` (`num_nodes = 167 + n_hidden`, I=59,
  O=108, W dense aleatoire). Implementation : `MambaAgent(num_inputs=59, num_outputs=108,
  num_nodes=167 + n_hidden).genome`. Reutilise la construction dense par defaut ; seule la bande
  mediane `[59, 59 + n_hidden)` grossit.
- **Contrat** : `g.num_nodes == 167 + n_hidden`, `g.num_inputs == 59`, `g.num_outputs == 108`.
  La graine RNG doit etre posee par l'appelant (`seed_at`) pour le determinisme.

### 4.2 `_capacity_mc()`
- **Produit** : un `MutationConfig` a **capacite figee** : `add_node_rate=0.0, prune_rate=0.0,
  weight_init_std=2.0` (le reste aux defauts : weight mutation + add_connection actives). C'est le
  seul ecart vs le `mc` d'EDR 107, et il est **necessaire** pour figer N (sinon les bras derivent).

### 4.3 `_capacity_arm(cfg, mc, n_hidden, generations, num_agents, max_ticks, base_seed)`
- **Consomme** : `_fresh_genome`, `_reproduce` (capacite figee via `mc`), `_evolve_nav_gen`,
  `_p_reach_of_pool` (tous existants).
- **Produit** : un dict `{"n_hidden", "num_nodes", "traj" (liste p_reach par gen), "gen0" (p_reach
  gen 1 = capacite brute), "plateau" (mediane last-k), "first" (mediane first-k), "stats" (liste)}`.
- **Logique** : calque `main_evolve_nav` mais (a) seme `best_ever` depuis `_fresh_genome(n_hidden)`
  repete (au lieu de `_load_champions`), (b) utilise `_capacity_mc()`, (c) **assert** a chaque
  generation que tous les genomes reproduits ont `num_nodes == 167 + n_hidden` (garde-fou anti-derive
  de capacite ; echoue fort si add_node/prune fuit).

### 4.4 `_verdict_capacity(arms)`
- **Consomme** : liste de dicts `_capacity_arm` triee par `n_hidden` croissant.
- **Produit** : verdict (str). Logique **deterministe** (pre-enregistree, cf. section 5) :
  - `plateaus = [a["plateau"] for a in arms]` (arms tries par `n_hidden` croissant).
  - `delta = plateaus[-1] - plateaus[0]` (effet end-to-end, du baseline au max).
  - `slope = float(np.polyfit([log2(a["n_hidden"]) for a in arms], plateaus, 1)[0])` (pente vs
    `log2(N)` pour lisser l'echelle geometrique 5->80).
  - **CAPACITE LEVE** si `delta >= 0.10` ET `slope > 0`.
  - **CAPACITE INERTE** si `abs(delta) < 0.10` ET `abs(slope) < 0.05` (plateau immobile end-to-end
    ET pente quasi nulle).
  - **CAPACITE AMBIGUE** sinon (signal partiel/non-monotone : p.ex. `delta >= 0.10` mais
    `slope <= 0` (saut non-monotone), ou pente non nulle mais `delta` sous le seuil).

### 4.5 `_report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return)`
- Table ASCII : 1 ligne/bras (`n_hidden`, `num_nodes`, `gen0`, `first`, `plateau`, `delta vs
  baseline`). Pente plateau vs log2(N). Verdict pre-enregistre. Provenance (seed, commit).
- Sauvegarde JSON via `h.save` (cle par bras). Tout ASCII (cp1252 ; pas de fleche/x/accent dans les
  `print` executes).

### 4.6 `main_capacity_nav(hidden_levels=(5, 20, 40, 80), generations=20, num_agents=24, max_ticks=80, seed=110, _return=False)`
- Orchestration : `Harness(seed, name="lewis_capacity_nav", with_db=False)`, `_disable_kuzu()`,
  `mc = _capacity_mc()`, `cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)`. Pour chaque N :
  `seed_at(base + N, 0)` (graine deterministe par bras), `_capacity_arm(...)`. Puis
  `_report_capacity_nav`.

## 5. Verdict pre-enregistre (fige AVANT les donnees, falsifiable des deux cotes)

| Branche | Condition | Lecture scientifique |
|---|---|---|
| **CAPACITE LEVE** | plateau monte avec N : `delta(N_max - N_min) >= +0.10` ET tendance monotone croissante | La capacite cachee EST le levier de navigation. **Percee** : rouvre le programme NAS substrat (vraie couche cachee). Contredit le verrou repertoire-MONDE pour la navigation. |
| **CAPACITE INERTE** | plateau plat : `abs(delta) < +0.10` ET pas de tendance | Ajouter de la capacite n'achete pas de navigation. **Convergence surdeterminee** avec EDR 105-Topo + nas-bottleneck : le mur n'est ni le monde-seul ni la capacite-seule. La capacite n'est pas actionnable seule -> reste le repertoire-MONDE (enrichir une affordance). |
| **CAPACITE AMBIGUE** | non-monotone, OU gen0 monte mais plateau non, OU signal partiel | Sous-determine. Noter le sens du signal partiel, elargir l'echelle ou la puissance (R>1) dans un suivi. |

**Seuil delta = +0.10** : choisi > la moitie du saut one-shot d'EDR 107 (0.18 -> 0.36, soit +0.18) et
>> la pente plate d'EDR 107 (+0.0038/gen). Un effet capacite reel devrait deplacer le plafond d'au
moins ~0.10 sur une echelle 16x ; en deca, c'est du bruit de la meme famille que la saturation 107.

**Lecture secondaire (gen0).** Si `gen0` monte avec N mais le plateau non -> la capacite aide la
navigation BRUTE mais l'evolution ne la consolide pas (verrou de selection/fitness, pas de capacite).
Si ni gen0 ni plateau ne montent -> capacite franchement inerte. Documente dans tous les cas.

## 6. Tests (TDD, banc `tests/sandbox/test_edr110_capacity_nav.py`)

1. **`_fresh_genome` dims** : `_fresh_genome(80).num_nodes == 247`, `.num_inputs == 59`,
   `.num_outputs == 108` ; `_fresh_genome(5).num_nodes == 172`.
2. **Materialisation capacite (de-risk go/no-go)** : construire un agent via `from_genome(
   _fresh_genome(80))`, assert `agent.genome.num_nodes == 247`, assert la bande cachee `W[59:139,
   :]` n'est pas tout-zero (caches non-inertes), assert `agent.forward(obs59)` renvoie des logits de
   forme attendue sans exception. **Si ce test echoue -> STOP (substrat ne supporte pas la capacite
   semee, comme le bug keystone).**
3. **`_capacity_mc` fige la capacite** : `_capacity_mc().add_node_rate == 0.0` et `.prune_rate ==
   0.0` ; appliquer `apply_mutations(_fresh_genome(40), _capacity_mc())` N fois preserve
   `num_nodes == 207`.
4. **`_verdict_capacity` branches** : bras synthetiques montant -> `CAPACITE LEVE` ; plats ->
   `CAPACITE INERTE` ; non-monotone -> `CAPACITE AMBIGUE`.
5. **Determinisme** : `main_capacity_nav(hidden_levels=(5,), generations=2, seed=110, _return=True)`
   appele deux fois -> trajectoires identiques (meme seed -> meme `p_reach`).
6. **Smoke** : `main_capacity_nav(hidden_levels=(5, 20), generations=2, num_agents=6, max_ticks=40,
   seed=12345, _return=True)` tourne, renvoie un verdict valide, JSON ecrit. **Seed distinct de 110**
   pour eviter la collision de provenance d'EDR 107 (le smoke ne doit pas ecraser le run reel).

## 7. Cout & repli puissance

4 bras x 20 gen x 24 agents x 80 ticks a metab=0 (~4x EDR 107, qui etait deja lent). Confirmatoire
**R=1, seed fixe (110)**. Repli si trop lent : reduire `generations` a 15, ou tomber a 3 bras
`(5, 40, 80)`. Le run reel est lance APRES la revue de code (jamais de test apres le run reel : il
ecraserait le JSON de provenance — lecon EDR 107).

## 8. Provenance, determinisme, non-regression

- `results/` gitignore ; provenance citee par seed (110) + commit dans le doc EDR.
- Determinisme verifie (test 5) ; le run reel sera reproduit une fois pour confirmer la trajectoire.
- **Non-regression** : `main_capacity_nav` est une fonction NOUVELLE ; aucun chemin existant
  (`main_evolve_nav` etc.) n'est modifie. `_fresh_genome` / `_capacity_mc` sont additifs.
- ASCII-only dans tout `print` execute (Windows cp1252) : pas de `->`/accents (utiliser `->` ASCII OK,
  pas de fleche unicode).

## 9. Commandement 15 — 1 variable

La **seule** variable manipulee entre bras est `n_hidden` (capacite cachee semee). Tout le reste est
identique : monde (Lewis vide d'apex, metab=0, forage_payoff=3), selection (`calculate_life_score`,
cliquet best-ever), graines (deterministes par bras), config de mutation (capacite figee identique),
ticks, population. La capacite figee (`add_node=0, prune=0`) garantit que N ne derive pas en cours
d'evolution -> le contraste inter-bras est pur.
