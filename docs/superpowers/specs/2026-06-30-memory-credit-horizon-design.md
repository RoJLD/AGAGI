# Banc « horizon de credit » — frontiere (K,D) : BPTT vs mutation x delai

> **Spec de conception** — 2026-06-30. Chantier P1 de l'audit memoire (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`).
> TOOLING pur (`tools/` + `tests/`), zero `src/`, zero `make_population`/torch -> zero collision avec
> la session // moteur torch (qui pilote `substrate_ab*`/`backend*`/FamineWorld).

## 1. Question & contexte

L'audit memoire conclut : la memoire est PORTEE par l'etat recurrent (EDR 120, `did_x` decodable de
H AUC~0.90) mais le substrat ne l'EXPLOITE pas. EDR 119/120 (session //) attribuent le verrou a
l'**assignation de credit** (TD ne franchit pas la frontiere d'un pas), PAS a la capacite. EDR 067
(`tools/grad_mem.py`) a montre que le **BPTT** resout un K-bit recall avec delai (0.78->1.00) la ou la
mutation sature, sur un reseau simplifie — mais a **delai fige (D=3)**.

**Trou jamais comble** : personne ne fait VARIER le delai D pour tracer la FRONTIERE. Question
falsifiable de ce banc : **l'avantage du gradient (BPTT) sur la mutation s'ELARGIT-il quand le delai D
croit ?** Si oui -> le verrou est l'**horizon de credit** (assigner du credit a travers le temps), ce
qui aligne EDR 067 + le diagnostic credit-assignment d'EDR 119/120 et oriente la migration moteur
(substrat differentiable). Si non (la mutation suit BPTT a tout D) -> le delai n'est pas le facteur
separateur (verdict REFUTE, retour a la planche a dessin).

## 2. Architecture (zero-collision)

Tout dans un nouveau `tools/memory_credit_horizon.py` qui **reutilise** (DRY) les primitives de
`tools/grad_mem.py` : reseau simplifie numpy (dynamique LTC `H=(1-dt)*Hc+dt*tanh(Hc@Wnd)`), tache K-bit
recall avec delai, `run_bptt`/`train` (BPTT+Adam). AUCUN fichier `src/`, AUCUN `make_population`/torch/
Biosphere.

**Correction (lecture du code)** : `grad_mem.py` n'a PAS de bras mutation — les « ~0.78 » de son
`main()` renvoient a EDR 064/`mem_nas.py` (qui mute le vrai Genome, pas le reseau simplifie). Le bras
mutation est donc a IMPLEMENTER sur le reseau simplifie, en fonction publique `train_mutation` AJOUTEE
a `grad_mem.py` : (1+1)-ES qui perturbe `W += N(0,sigma)`, compare candidat vs incumbent sur la **MEME
batch** chaque pas (fitness appariee -> robuste au bruit, lecon EDR 078), garde si `acc_cand >=
acc_inc` ; reutilise `run_bptt` pour le forward (dW ignore). Meme budget (`epochs`) que `train` (BPTT)
-> comparaison appariee. Ajout non-regressif (le `main()` existant inchange).

## 3. Tache (existante, reutilisee)

K-bit recall avec delai D : encoder K bits dans les K premiers slots d'obs ; D ticks d'entree nulle
(le delai) ; signal "go" au slot K ; sortie = relire les K bits sur les K derniers noeuds. Loss = MSE,
**accuracy = sign-match** (fraction de bits correctement relus, moyennee sur le batch).

## 4. Composants & interfaces

### 4.1 `train_arm(arm, N, I, O, K, D, epochs, batch, lr, seed) -> float`
- `arm in {"bptt", "mutation"}`. **Meme reseau, meme tache, meme budget** (epochs/batch) pour les deux
  bras -> comparaison appariee. Renvoie l'accuracy finale (sign-match) sur un batch d'eval frais.
- `bptt` delegue a `grad_mem.train` ; `mutation` delegue a `grad_mem.train_mutation` (ajoute).

### 4.2 `frontier(arm, K, Ds, R, epochs, seed) -> dict`
- Balaie `Ds` (defaut `(1, 3, 6, 10, 16, 24)`) a K fixe (defaut `K=4`), `R` seeds APPARIES
  (`seed_boundary`). Renvoie `{D: mean_acc}` (moyenne sur R seeds).
- Memes seeds entre bras (appariement) : `frontier("bptt", ...)` et `frontier("mutation", ...)`
  utilisent la meme grille de seeds.

### 4.3 `_verdict_horizon(front_bptt, front_mut, gap_margin=0.20, hi=0.90, lo=0.65) -> str`
- `D_max(front)` = plus grand D avec `acc >= 0.95` (0 si aucun). `gap(D) = front_bptt[D] - front_mut[D]`.
- **HORIZON CONFIRME** si : `gap(max(Ds)) - gap(min(Ds)) >= gap_margin` (le gap CROIT avec D) **ET** il
  existe un D ou `front_bptt[D] >= hi` ET `front_mut[D] <= lo` (BPTT tient ou la mutation s'effondre).
- **HORIZON REFUTE** si `gap(max(Ds)) - gap(min(Ds)) < gap_margin` (gap plat/non-croissant : le delai
  ne separe pas les deux algos).
- **INDETERMINE** si une des deux frontieres est vide (cellule manquante).

### 4.4 `_report_horizon(h, front_bptt, front_mut, R, _return)`
- Table ASCII (1 ligne/D : D, acc_bptt, acc_mut, gap) + `D_max` par bras + verdict. Sauvegarde JSON
  (`name="memory_credit_horizon"`). Tout ASCII (cp1252).

### 4.5 `main_credit_horizon(K=4, Ds=(1,3,6,10,16,24), R=3, epochs=400, seed=1167, _return=False)`
- `Harness(seed=seed, name="memory_credit_horizon", with_db=False)`. Calcule `front_bptt`/`front_mut`,
  appelle `_report_horizon`. Smoke = `main_credit_horizon(Ds=(1,6), R=1, epochs=40, seed=99167, _return=True)`.

## 5. Verdict gele (pre-enregistre)

| condition | seuil |
|---|---|
| HORIZON CONFIRME | `gap(D_max_grid) - gap(D_min_grid) >= 0.20` ET (exists D : bptt>=0.90 ET mut<=0.65) |
| HORIZON REFUTE | delta gap `< 0.20` |
| INDETERMINE | frontiere vide |

Attendu (d'apres EDR 067 a D=3 : bptt 1.0 vs mut 0.78, gap 0.22) : a D croissant la mutation devrait
chuter plus vite que BPTT -> gap croissant -> CONFIRME. Mais falsifiable : si la mutation tient a grand
D, REFUTE.

## 6. Provenance, determinisme, non-regression

- `Harness(name="memory_credit_horizon")` -> JSON distinct ; seed reel 1167, smoke 99167 distinct.
- Determinisme : 2 runs byte-identiques (seeds appaires via `seed_boundary`). Run reel APRES revue ;
  AUCUN test relance apres (lecon EDR 107).
- Non-regression : `grad_mem.main()` inchange (appelle la fonction `train_mutation` extraite). Refactor
  pur, comportement identique.
- ASCII-only dans tout `print` execute (cp1252).

## 7. Tests (TDD, `tests/sandbox/test_memory_credit_horizon.py`)

1. **Tache recall correcte** : un reseau a poids choisis (ou apres BPTT a D petit) relit les bits ->
   accuracy elevee ; sanity du sign-match.
2. **`train_arm` apparie deterministe** : deux appels `train_arm("bptt", ..., seed=k)` memes args ->
   accuracy identique ; idem `"mutation"`.
3. **`_verdict_horizon` 3 branches** : frontieres synthetiques -> CONFIRME (gap 0.05->0.30) / REFUTE
   (gap 0.05->0.10) / INDETERMINE (frontiere vide).
4. **Smoke** `main_credit_horizon(Ds=(1,6), R=1, epochs=40, seed=99167, _return=True)` : renvoie un
   verdict valide, table a 2 lignes, JSON ecrit. Seed distinct du run reel.

## 8. Cout & repli

Banc numpy, petit reseau (N~19), epochs~400, 6 valeurs de D x 2 bras x R=3 -> **rapide**
(secondes-minutes, pas comme les sims Lewis). Repli : `Ds=(1,6,16)`, R=2, epochs=200. Run reel APRES
revue.

## 9. Doc & memoire

- **Doc** : `docs/EDR/121_*` (numero a confirmer non-contendu ; sinon `docs/EDR/Credit_Horizon_*`).
- **Memoire** : MAJ `memory-architecture-audit` (resultat horizon de credit) + lien
  [[intelligence-typing-flat-connectome]].

## 10. Coordination (sessions paralleles)

Tooling-only (`tools/memory_credit_horizon.py` + refactor `tools/grad_mem.py` + tests). `git diff src/`
VIDE. N'utilise NI `make_population` NI torch NI `substrate_ab*` (fichiers actifs de la session //) ->
zero collision. Commits path-scoped.
