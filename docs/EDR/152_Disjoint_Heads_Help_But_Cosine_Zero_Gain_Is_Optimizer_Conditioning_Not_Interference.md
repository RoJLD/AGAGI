# EDR 152 — Têtes disjointes : DISJOINT_HELPS formel (5/5, +43 %) MAIS cosinus≈0 → le gain n'est PAS l'isolation d'interférence, c'est le conditionnement d'optimiseur par-tête

> **Date** : 2026-07-01. **Verdict pré-enregistré** : `DISJOINT_HELPS` si l'amélioration relative moyenne (par
> tête) de la perte held-out FLAT→DISJOINT est **≥ 10 %** sur **≥ 3/5 seeds** ; `DISJOINT_HURTS` si pire de
> ≥ 10 % sur ≥ 3/5 ; sinon `DISJOINT_NEUTRAL`. Readout secondaire (hors verdict) : cosinus des gradients
> inter-têtes w.r.t. le trunc partagé FLAT (< 0 = conflit d'interférence).
> **Résultat** : **DISJOINT_HELPS** (5/5 seeds, improv moyen **+0.431**) — MAIS **cosinus = +0.000** (aucune
> interférence) → le mécanisme « interférence de gradient » est **RÉFUTÉ** ; le gain vient du **conditionnement
> Adam par-tête** (confond I1), concentré sur les têtes MSE, la tête action (CE) inchangée.
> **Outil** : `tools/disjoint_heads_ab.py`. **Run** : K=5, base=2200, STEPS=2000, `set_num_threads(1)`, **2 passes
> byte-identiques**. **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-ab*`.

## 1. Question

Hypothèse #5 de l'audit mémoire/typologie (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`) : le substrat est un connectome
PLAT où toutes les têtes (action / value / world-model) partagent le trunc et une loss combinée — d'où une
**interférence de gradient** supposée. L'**isolation de gradient** (têtes disjointes + losses séparées) aide-t-elle
l'apprentissage multi-facultés ? Banc A/B torch auto-contenu, proxy **supervisé** teacher-student (le RL confondrait
par la variance de crédit ; cf. `mem_nas` EDR 064). Le fil torch // fait la migration FIDÈLE du connectome plat
(EDR 134-143) — les têtes disjointes en sont l'opposé, non commencées.

**Bras** (parité de trunc `D·H`, seule variable = couplage inter-têtes) :
- **FLAT** : trunc `D→H=48` partagé → 3 têtes lisant tout H, **une loss combinée**, un Adam.
- **DISJOINT** : 3 sous-réseaux indépendants `D→16→tête`, **3 losses séparées, 3 Adam** (isolation).

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  seed | headloss FLAT (a/v/p)      | DISJOINT (a/v/p)          | improv | interf
  2200 | 0.255 0.027 0.027 | 0.256 0.010 0.011 | +0.402 | +0.006
  2201 | 0.257 0.025 0.027 | 0.264 0.006 0.010 | +0.452 | +0.005
  2202 | 0.281 0.016 0.031 | 0.278 0.006 0.014 | +0.397 | +0.007
  2203 | 0.235 0.028 0.036 | 0.239 0.010 0.011 | +0.443 | -0.003
  2204 | 0.262 0.025 0.030 | 0.267 0.008 0.008 | +0.461 | -0.013
  MOYEN improv=+0.431   conflit-gradient FLAT (cos)=+0.000
  VERDICT : DISJOINT_HELPS
```

## 3. Lecture — le verdict positif cache une RÉFUTATION du mécanisme visé

1. **DISJOINT_HELPS formel** : les 5 seeds dépassent le seuil (+0.40 à +0.46), improv moyen +0.431. Le banc dit :
   sur ce proxy, le bras disjoint apprend mieux.
2. **MAIS le cosinus ≈ +0.000** (−0.013 à +0.007). **Il n'y a AUCUNE interférence de gradient inter-têtes.** C'est
   exactement le cas « aide MAIS cos≈0 » anticipé par la revue finale opus (réserve I2) : les 3 profs partagent
   l'input mais ont des poids indépendants → sur un trunc de rang 48 leurs gradients sont quasi-orthogonaux, pas
   conflictuels. **Le mécanisme « l'isolation réduit l'interférence » est donc RÉFUTÉ comme explication du gain.**
3. **Décomposition par tête — décisive** : le gain est **entièrement sur les têtes MSE** (value 0.026→0.008,
   pred 0.030→0.011, ~−60 %) ; la tête **action (cross-entropy) est INCHANGÉE** (0.258→0.261, voire marginalement
   pire). Un gain qui épargne exactement la tête à grande échelle de loss (CE ~O(1)) et se concentre sur les têtes
   à petite échelle (MSE) est la **signature du conditionnement d'optimiseur**, pas de l'isolation architecturale.
4. **Le vrai levier = le conditionnement Adam par-tête (confond I1, revue opus).** « Disjoint » bundle *trois*
   changements : (a) masque de poids du trunc, (b) séparation de loss, (c) **3 optimiseurs Adam avec moments
   propres**. Or Adam normalise le pas par la variance par-paramètre. En FLAT, le trunc partagé reçoit la SOMME de
   3 gradients d'échelles très différentes ; l'Adam global est dominé par la variance de la tête action (CE) →
   **le lr effectif des têtes MSE est écrasé**. En DISJOINT, chaque tête MSE a son propre `v` → **lr auto-adapté**
   → apprend mieux. cos≈0 + gain MSE-only + action inchangée ⇒ c'est (c), pas (a)/(b).

## 4. Conséquence pour la migration (#5)

**La refonte architecturale « têtes disjointes » n'est PAS le levier — et l'aurait faussement paru sans le readout
cosinus.** Le gain observé est capturable dans le substrat **plat** par un simple **conditionnement d'optimiseur /
d'échelle de loss** — normalisation de loss, GradNorm, ou lr par-tête — **bien moins cher** qu'un split
architectural + isolation de gradient. Autrement dit : ce qui manque au substrat plat n'est pas l'isolation
structurelle mais l'**équilibrage du crédit d'apprentissage entre facultés d'échelles différentes**. Cohérent avec
l'arc substrat (le verrou est le régime d'apprentissage/crédit, cf. EDR 130/133/136 côté binding, EDR 123 côté
mémoire) plutôt que la topologie.

## 5. Caveats (revue finale opus — PRÊT À INTÉGRER OUI, 0 Critical)

- **I1 (confirmé causalement ici)** : « disjoint » = isolation + **conditionnement Adam par-tête**. Ce dernier est
  le facteur porteur (§3.4). Le verdict binaire (DISJOINT bat FLAT) est valide ; l'attribution à l'isolation
  *architecturale* ne l'est pas.
- **I2 (confirmé : cos≈0)** : profs quasi-orthogonaux → pas d'interférence à isoler ; le banc ne pouvait pas
  observer un gain d'isolation, seulement le confond d'optimiseur. Un banc PRO-interférence exigerait des profs
  corrélés/antagonistes (cibles en tension) — piste V2.
- **I3** : parité limitée au **trunc** (`D·H` apparié) ; les têtes ne sont PAS appariées (FLAT lit H=48, DISJOINT
  H/3=16) — second axe de capacité non contrôlé, de signe non garanti.
- **M1** : le cosinus est mesuré **à convergence** (borne inférieure de l'interférence) ; un cos≈0 final ne réfute
  pas un conflit transitoire précoce. Ici cohérent avec I2 (profs orthogonaux → pas de conflit à aucun stade
  attendu), mais une V2 échantillonnerait le cosinus tôt.
- **Proxy supervisé** : teacher-student, pas le réglage RL in-world. Un verdict positif motiverait la migration ;
  ce verdict NUANCÉ dit que même le gain apparent n'est pas architectural.

## 6. Suite — contrôle décisif

**EDR 153 (proposé)** : ajouter un bras **FLAT + normalisation de loss (GradNorm / lr par-tête)**. Si ce bras
capture le gain de DISJOINT (têtes MSE remontées à ~0.010 sans split architectural), le confond I1 est **prouvé** et
la migration #5 (têtes disjointes) est réfutée comme levier au profit d'un simple équilibrage de crédit. Second
axe V2 : profs **corrélés/antagonistes** pour créer une vraie interférence (cos<0) et re-tester l'isolation dans le
régime où elle DEVRAIT payer.

## 7. Provenance / non-périmètre

- `tools/disjoint_heads_ab.py` (`main_disjoint_heads`, K=5, base=2200, STEPS=2000, `set_num_threads(1)`) ; **2 passes
  byte-identiques** (gel EDR) ; AUCUN test relancé après le run.
- **Tooling-only READ-ONLY** : `git diff src/` VIDE sur toute la branche (zéro collision fil torch //). Ne touche
  NI `torch_batch_model.py`/`backend_torch.py`/`substrate_*`.
- Subagent-driven : 3 tâches (SPEC conforme + qualité Approved chacune), revue finale **opus** (validité
  expérimentale) qui a levé I1-I3/M1-M2 et anticipé le cas « aide + cos≈0 » observé au run. Fix M2
  (`set_num_threads(1)`) appliqué avant le run gelé.
- **Numérotation** : EDR 152 — bloc **150+** (instruments per-type/ToM/facultés), convention gravée
  `parallel-sessions-shared-tree` (fils // compositional/torch/famine en 120-149) pour éviter les collisions
  cross-session. 5e instrument per-type après 125/127/150/151.
