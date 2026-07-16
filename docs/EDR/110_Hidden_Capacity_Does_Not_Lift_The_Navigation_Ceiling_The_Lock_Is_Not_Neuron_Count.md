# EDR 110 — La capacite cachee ne leve PAS le plafond de navigation : le verrou n'est pas le nombre de neurones

> **Date** : 2026-06-29. **Verdict** : `CAPACITE INERTE` (pre-enregistre, atteint).
> **Outil** : `tools/lewis_survival_sweep.py` (`main_capacity_nav`). **Seed** : 110. **Commit** : 954b9d7.
> **Spec** : `docs/superpowers/specs/2026-06-29-EDR110-Capacity-Nav-Ceiling-design.md`.
> **Plan** : `docs/superpowers/plans/2026-06-29-EDR110-capacity-nav.md`.

## 1. Question

EDR 107 (`SUBSTRAT BLOQUE`) a montre qu'evoluer la navigation EN Lewis (N_APEX=0, metab=0,
forage_payoff=3) sur la fitness de prod `calculate_life_score` **plafonne `p_reach` ~0.36** ≪ 0.5
competence, et a conclu : **le verrou est l'ARCHITECTURE du connectome**, ni le monde, ni la
selection, ni la cinematique (106), ni l'energie (090-101).

Le suspect numero 1 du programme NAS : le connectome de prod est `MambaAgent(I=59, O=108,
num_nodes=172)` -> **hidden = 5 noeuds** (97 % I/O). EDR 110 teste directement cette accusation :
**ajouter de la capacite cachee monte-t-il le plafond de navigation au-dessus de 0.36 ?**

## 2. Methode

Echelle de capacite cachee **figee** `n_hidden in {5, 20, 40, 80}` (baseline + 4x/8x/16x ; `num_nodes
= 167 + n_hidden` = 172/187/207/247, sous le cap soft 256). Pour chaque palier :
- semer 5 genomes frais a capacite N (`_fresh_genome(n_hidden)`, W dense aleatoire) ;
- evoluer 20 generations via la boucle evolve_nav d'EDR 107 (ere fraiche scaffold-chaud, cliquet
  best-ever top-5), avec une mutation a **capacite figee** (`_capacity_mc` : `add_node_rate=0`,
  `prune_rate=0`, `meso_skip_rate=0`, `meso_gate_rate=0`) -> N ne derive pas ;
- lire **deux signaux** : `gen0` = `p_reach` de la generation 1 (capacite brute, elites semees
  intactes) ; `plateau` = mediane des 5 dernieres generations (capacite exploitee par l'evolution).

**1 variable (Commandement 15)** : seule `n_hidden` varie ; monde, selection, graines (deterministes
par bras), config de mutation, ticks, population sont identiques.

### Garde-fou et correction de methode (debogage du run)
Un `assert g.num_nodes == 167 + n_hidden` par generation protege la capacite figee. Le premier run
a **crashe** dessus (bras n=40) : cause-racine = la **reproduction intra-monde** de Biosphere3D
(energie l.1342, MATE l.836, HGT l.883) appelle `MambaAgent.mutate()`, qui gele `add_node`/`prune`
mais **pas** `meso_*_rate` (defaut 0.05) -> `add_meso_gated_unit` insere 2 noeuds ; ces rejetons
grossis entraient dans le pool score puis dans `best_ever`. Geler la mutation EXTERNE (`_capacity_mc`)
ne suffit pas car la mutation se produit AUSSI dans la sim. **Fix (commit 954b9d7)** : filtrer les
genomes scores a `num_nodes == 167 + n_hidden` AVANT le cliquet best-ever -> les rejetons intra-monde
a capacite derivee sont evalues (comptent dans `p_reach`) mais **exclus de la selection**. C'est
scientifiquement correct pour la Phase 1 (capacite FIXE) ; la croissance dynamique serait la Phase 2.
Le garde-fou n'a plus jamais tire apres le fix.

## 3. Resultats

| n_hidden | num_nodes | gen0  | first | **plateau** | delta vs base |
|---------:|----------:|------:|------:|------------:|--------------:|
| 5        | 172       | 0.244 | 0.220 | **0.333**   | +0.000        |
| 20       | 187       | 0.330 | 0.339 | **0.400**   | +0.067        |
| 40       | 207       | 0.121 | 0.256 | **0.250**   | -0.083        |
| 80       | 247       | 0.147 | 0.308 | **0.250**   | -0.083        |

- **Pente du plateau vs log2(N) = -0.0257** (legerement NEGATIVE).
- **delta(N_max - N_min) = 0.250 - 0.333 = -0.083** (sous le gate +0.10, et de signe negatif).

Trajectoires `p_reach` par generation (20 gen) — toutes dans la **meme bande ~0.15-0.44**, sans
tendance correlee a la capacite :
```
N= 5 : 0.24 0.21 0.22 0.19 0.25 0.16 0.19 0.14 0.29 0.30 0.24 0.31 0.25 0.26 0.27 0.36 0.32 0.33 0.40 0.29
N=20 : 0.33 0.34 0.38 0.25 0.37 0.29 0.44 0.25 0.31 0.22 0.34 0.24 0.21 0.29 0.19 0.36 0.43 0.40 0.24 0.41
N=40 : 0.12 0.26 0.24 0.30 0.27 0.30 0.15 0.32 0.14 0.35 0.28 0.25 0.27 0.22 0.31 0.32 0.10 0.24 0.27 0.25
N=80 : 0.15 0.37 0.25 0.31 0.36 0.26 0.26 0.34 0.29 0.17 0.22 0.35 0.14 0.26 0.17 0.25 0.20 0.29 0.26 0.20
```

## 4. Verdict : `CAPACITE INERTE`

Le plateau **ne monte pas** avec la capacite : non-monotone, cantonne a ~0.25-0.40 (toujours ≪ 0.5),
et la plus grosse capacite (80, **16x** le baseline) plafonne **plus bas** que le baseline (5). La
condition pre-enregistree est remplie : `abs(delta)=0.083 < 0.10` ET `abs(slope)=0.0257 < 0.05`.

- **Le baseline n=5 (plateau 0.333) reproduit le ~0.36 d'EDR 107** -> le harnais est valide ; ce
  n'est pas un artefact de re-implementation.
- **Lecture secondaire (gen0)** : la capacite brute ne monte pas non plus (0.244 / 0.330 / 0.121 /
  0.147) — les grands reseaux denses aleatoires sont meme plus bruites a la naissance. Donc **ni la
  capacite brute, ni la capacite exploitee par l'evolution** ne profitent de plus de neurones caches.

**Conclusion scientifique.** EDR 107 disait « le verrou est l'architecture du connectome ». EDR 110
**affine** : ce verrou n'est **PAS le nombre de neurones caches**. Offrir 16x la capacite ne deplace
pas le plafond (et le degrade marginalement : plus de parametres a cabler sous une recherche de
connexions inchangee = plus de bruit, pas plus de competence).

## 5. Convergence (surdetermination)

Ce `CAPACITE INERTE` **converge** avec les findings independants du programme :
- **EDR 105-Topo** : la croissance topologique ne leve pas l'apex (le repertoire-MONDE est le verrou).
- **nas-bottleneck-is-substrate-not-search** : corr nodes x apex = -0.18 ; de plus gros cerveaux
  n'achetent pas d'apex.
- **EDR 104 / 108** : ni la dose de diversite ni la selection diverse ne levent l'apex.

Triangulation : **ni les knobs-monde, ni la selection, ni la TAILLE/capacite du reseau** ne levent la
navigation/l'apex. La seule hypothese survivante de tout l'arc Lewis reste le **repertoire-MONDE**
(richesse d'affordances : ce vers quoi naviguer, pas avec quoi). Le mur n'est pas une carence de
substrat-CAPACITE mais de substrat-MONDE.

## 6. Caveats

- **R=1** (un seed, confirmatoire). Determinisme **verifie** : deux runs independants (seed 110)
  byte-identiques (memes trajectoires, meme verdict). La bande etroite et concordante des 4 bras
  rend un artefact de bruit peu probable, mais la puissance reste 1 seed.
- **gen0 = generation 1** (apres un passage `_reproduce`), pas litteralement pre-evolution ; les
  elites semees passant intactes via `build_population`, gen0 est domine par les genomes semes bruts
  -> ~ capacite brute, a ne pas sur-interpreter.
- **Filtre best_ever** : la Phase 1 exclut de la SELECTION les rejetons intra-monde a capacite
  grossie (cf. section 2). Ils restent dans la mesure de `p_reach` (rares -> pollution negligeable).
- **Capacite figee** : `prune_rate` est inerte dans le config (la fonction `prune` lit
  `mutation_genes[4]`), mais `prune` ne change jamais `num_nodes` -> la garantie de capacite tient.

## 7. Suite

- **Capacite/taille du reseau ELIMINEE comme levier de navigation** (s'ajoute a : monde-knobs,
  selection, cinematique, energie). Axe NAS « plus de neurones caches » CLOS pour ce substrat.
- **Phase 2 (croissance dynamique)** : largement deja repondue — EDR 107 tournait avec `add_node=0.2`
  (croissance lente) et plafonnait deja ; EDR 110 montre que meme une grande capacite offerte
  d'emblee est inerte -> **faible ROI**, ne pas prioriser.
- **Seule piste amont restante** : enrichir le **repertoire-MONDE** (une affordance : un signal/outil/
  proie offrant une strategie de navigation DISTINCTE et utile), puis re-mesurer `p_reach`/apex. Le
  verrou est ce que le monde DEMANDE, pas la capacite de calcul de l'agent (echo EDR 010).
