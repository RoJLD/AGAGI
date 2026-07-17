# Banc A/B têtes disjointes vs plat — design (EDR 152)

> **Date** : 2026-07-01. **Type** : instrument [M]-flavored, staged additivement (zéro collision fil torch //).
> **Question de l'audit** (#5 / P2) : l'**isolation de gradient** (têtes disjointes + losses séparées) aide-t-elle
> l'apprentissage multi-facultés vs le substrat PLAT à connectome partagé (état actuel : `torch_batch_model.py`
> une loss combinée sur un W partagé, têtes = tranches positionnelles) ?

## 1. But & falsifiabilité

**Hypothèse** : sur une tâche qui stresse plusieurs facultés simultanément, un substrat où chaque tête a son
propre bloc de paramètres et sa propre loss (isolation de gradient) apprend MIEUX que le substrat plat où toutes
les têtes partagent le trunc et une loss combinée — parce que le plat souffre d'**interférence de gradient**
inter-têtes.

**Verdict pré-enregistré** (gelé) :
- `DISJOINT_HELPS` si l'amélioration relative moyenne (par tête) de la perte held-out FLAT→DISJOINT est
  **≥ 10 %** sur **≥ majorité des K seeds** (≥ 3/5).
- `DISJOINT_HURTS` si DISJOINT est PIRE de ≥ 10 % (perte held-out) sur ≥ 3/5 seeds.
- `DISJOINT_NEUTRAL` sinon.

**Readout secondaire (mécanisme, n'entre pas dans le verdict)** : sur le bras FLAT, le **conflit de gradient
inter-têtes** = cosinus moyen des gradients par tête w.r.t. les params du trunc partagé (cosinus < 0 = conflit).
Explique POURQUOI : si FLAT montre un cosinus négatif ET DISJOINT aide, le mécanisme (interférence) est confirmé.

## 2. Tâche : multi-facultés SUPERVISÉE teacher-student

Proxy supervisé PROPRE du réglage RL multi-têtes (le RL confondrait le signal par la variance de crédit ; cf.
`mem_nas` EDR 064 qui a sorti la mémoire du forage). **Caveat gravé dans l'EDR** : proxy supervisé, pas le
réglage RL in-world ; un verdict POSITIF motive la migration, un NEUTRE dit « l'isolation seule ne suffit pas ».

- Input `x` ∈ R^D (D=32), échantillonné N(0,1).
- **3 profs FIXES** (MLP aléatoires 2 couches tanh, graine fixe indépendante du seed d'entraînement) produisent
  3 cibles de structures DIFFÉRENTES depuis le même `x` (→ interférence sur un trunc partagé) :
  - `y_action` : logits de classification, **K_a = 4** classes → cible = argmax du prof action.
  - `y_value`  : scalaire (régression) — « critic ».
  - `y_pred`   : vecteur R^P (P=8, régression) — « world-model / prédiction obs suivante ».
- Pertes par tête : action = cross-entropy, value = MSE, pred = MSE.

Données : batch de 64 échantillons `x` frais par pas d'optim (profs déterministes → cibles reproductibles) ;
held-out = 512 échantillons fixes (graine séparée). Entraînement = 2000 pas, Adam lr=1e-3.

## 3. Les deux bras (seule variable = couplage inter-têtes)

Largeur cachée totale **H = 48** (divisible par 3), trunc `D×H`, activation tanh.

- **FLAT** : UN trunc dense `D→H` partagé → 3 têtes linéaires lisant **tout H** ; **une loss combinée**
  `L = L_action + L_value + L_pred` ; UN optimiseur. Gradients de toutes les têtes mêlés dans le trunc.
- **DISJOINT** : **3 sous-réseaux indépendants**, chacun `D→(H/3=16)→sa tête` ; **3 losses séparées**, **3
  optimiseurs** (chaque loss ne met à jour que son sous-réseau). Aucun couplage inter-têtes.

**Parité de capacité** : trunc `D×H` identique (FLAT = D·H ; DISJOINT = 3·(D·H/3) = D·H). Les têtes FLAT lisent
H et DISJOINT lisent H/3 → **FLAT a ~3× plus de params de tête** (surtout la tête pred, P=8). C'est **conservateur
pour l'hypothèse** : FLAT a MARGINALEMENT PLUS de capacité, donc un DISJOINT_HELPS malgré moins de params = preuve
plus forte. Les comptes de params des deux bras sont AFFICHÉS (transparence).

## 4. Métrique & agrégation

Comme c'est un A/B sur les **mêmes profs / mêmes données / même seed**, on compare la perte held-out **par tête**
DISJOINT vs FLAT directement (évite les problèmes d'échelle inter-têtes) :
- Par seed : `improv_k = (loss_flat_k - loss_disjoint_k) / loss_flat_k` pour k ∈ {action, value, pred}.
- Agrégat seed = moyenne des 3 `improv_k`.
- Verdict (§1) sur cet agrégat, majorité des seeds.

Table de sortie (ASCII) : par seed, `loss_flat` / `loss_disjoint` par tête + improv moyen ; ligne moyenne ;
readout cosinus-conflit FLAT ; verdict.

## 5. Déterminisme, structure, coordination

- **Déterminisme** : `torch.manual_seed` + `np.random.seed` par seed ; `torch.use_deterministic_algorithms(True)`
  best-effort ; **2 passes byte-identiques** exigées (gel EDR). Profs graine fixe (indépendante du seed d'entraînement).
- **Auto-contenu** : PyTorch pur, PAS de Biosphere / MambaAgent / KuzuDB. Nouveau fichier **`tools/disjoint_heads_ab.py`**
  (n'importe ni ne modifie `torch_batch_model.py`/`backend_torch.py` — zéro collision fil torch //). Repli propre si
  torch absent (skip + message, comme les tests substrate).
- **Prints exécutés = ASCII-only** (cp1252). Accents seulement en docstrings/commentaires.
- **K = 5 seeds** (base 2200, seeds 2200..2204).
- **EDR 152** (bloc 150+ per-type/instrument, convention gravée `parallel-sessions-shared-tree`).
- Test smoke `tests/sandbox/test_disjoint_heads_ab.py` : run réduit (K=1, pas=50, H=6) → verdict ∈ ensemble valide,
  structure du retour.

## 6. Ce que ça tranche

- `DISJOINT_HELPS` → l'isolation de gradient est un levier réel ; motive la migration #5 (têtes disjointes + losses
  séparées dans le substrat torch de prod). Le readout cosinus confirme le mécanisme (interférence).
- `DISJOINT_NEUTRAL` → l'interférence n'est pas le verrou sur ce type de tâche ; l'isolation seule ne paiera pas ;
  cohérent avec l'arc substrat (le levier serait ailleurs : capacité, tâche, crédit).
- `DISJOINT_HURTS` → le partage AIDE (transfert inter-têtes > interférence) ; contre-indique la migration #5.

Toutes les issues sont interprétables → falsifiable des deux côtés.

## 7. Provenance / non-périmètre

- Ne touche AUCUN fichier `src/` ni les fichiers du fil torch // (`torch_batch_model.py`, `backend_torch.py`,
  `substrate_*`). Nouveau tool + test uniquement + EDR + spec/plan.
- Proxy supervisé (caveat §2). Ne prétend pas mesurer l'effet in-world ; c'est le banc cognitif pur de l'isolation.
- 1 variable (Commandement 15) = couplage inter-têtes (le bundle architecture+loss = la DÉFINITION de « disjoint » ;
  une ablation future pourrait séparer masque-de-poids vs séparation-de-loss).
