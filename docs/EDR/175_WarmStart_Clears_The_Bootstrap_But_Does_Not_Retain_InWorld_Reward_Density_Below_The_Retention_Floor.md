---
id: EDR-175
type: EDR
title: Le warm-start FRANCHIT le bootstrap du throw-gate mais ne le RETIENT pas in-world — la densité de récompense est sous le plancher de rétention (r·P)
status: accepted
gate: G1
verdict: WARMSTART_CLEARS_BOOTSTRAP_NOT_RETENTION_REWARD_BELOW_FLOOR
---

# EDR-175 : warm-start ⇒ bootstrap franchi (frozen +0.40) mais binding NON retenu sous REINFORCE

> Territoire BIND/torch (fin de l'arc 172→175). Banc `tools/torch_throw_gate_inworld_ab.py`
> (`compare_warmstart` + `_collect_warm_direction`, additif). Levier désigné par EDR-174 + [[warm-start-transversal-law]].

## Contexte

Arc throw-gate in-world : **172** (câblage → NEUTRE), **173** (débias NAV-005 → nécessaire-pas-suffisant),
**174** (densité → BACKFIRE). Méta-verdict 174 : les fixes côté SIGNAL sont épuisés → pivot **warm-start**
(la loi transversale : le binding émerge d'un bassin pré-formé, établie sur 4 fils proxy). Cet EDR teste le
warm-start in-world.

**Question** : un `_throw_w` pré-formé « spear-aware » produit-il / retient-il le binding là où le cold-start
(zéros, EDR-173) échoue ?

## Méthode

- **Warm direction** (`_collect_warm_direction`) : rollout court (gate cold, juste pour collecter `H`) +
  **régression logistique `H → has_spear`** (le vrai discriminant ; la différence-de-moyennes ÉCHOUE — testé,
  transfert négatif). Injectée comme `_throw_w = scale·ŵ`. Le bassin part spear-aware.
- **Deux mesures** : (1) **FROZEN** (`lr=0`, gate gelé) = warm-start PUR, isole si la représentation supporte
  le binding ; (2) **REINFORCE** (`lr>0`) = test de RÉTENTION, gap mesuré en fenêtre post-warmup. **cold** (zéros)
  vs **warm**, chacun ON+shuffle. Couche 1 levée (energy/spear/métab), antisat=0.3 (mesurabilité). Verdict
  primaire = warm_on vs cold_on. K=6.

## Résultat

**FROZEN (gate gelé)** : le warm crée un `binding_gap` **positif** = +0.19 (scale 3) / +0.40 (scale 8) / +0.61
(scale 15). → **le bootstrap est FRANCHISSABLE** : la représentation `H` supporte un throw spear-conditionnel,
le bassin bindé est atteignable.

**REINFORCE (K=6, scale 8, fenêtre post-warmup)** :

| bras | gap médian | trajectoire | vs shuffle |
|---|---|---|---|
| cold (zéros) | **−0.222** | 0 → anti-bind | HEBBIEN (anti-bind) |
| warm (spear-aware) | **−0.044** | +0.40 → ÉRODE vers ~0 | HEBBIEN (anti-bind) |

`warm > cold` sur **5/6 seeds** (median_diff +0.17) mais **sign_p 0.22 = NON significatif**, et le warm médian
reste **légèrement négatif** (n'a PAS retenu le +0.40 injecté). Les deux bras anti-bindent (HEBBIEN).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : frozen ⇒ warm gap +0.40 (binding représentable). Sous REINFORCE ⇒ warm érode de +0.40 à ≈0/−0.04 ;
  cold anti-binde à −0.22 ; warm moins négatif que cold (5/6, n.s.).
- **INTERPRÉTATION (la séparation décisive)** : le warm-start **FRANCHIT le bootstrap** (frozen le prouve — la
  représentation est décodable ET utilisable) — c'est la **moitié** de la loi transversale, confirmée. MAIS il
  **ne RETIENT pas** sous les dynamiques in-world. Loi de **rétention-167** (`c_warm = r·P`) : un moyen coûteux
  n'est retenu que si `récompense·P(succès) > coût` ; in-world le kill/hit-avec-outil est ~0.001 (EDR-173) → `r·P`
  **sous le plancher de rétention** → le gap injecté érode. L'avantage warm résiduel (+0.17, hystérésis faible)
  est la décroissance plus lente du warm, insuffisante et n.s.
- **EXPLICATION UNIFIÉE de l'arc 172-175** : le throw-gate échoue au **bootstrap** (cold : 172/173) ET à la
  **rétention** (warm : 175) pour la **MÊME raison sous-jacente** — la densité de récompense in-world est sous le
  seuil `r·P`. Aucun des 4 leviers (câblage/débias/densité/warm-start) ne relève le payoff RÉEL du
  throw-avec-spear au-dessus du plancher. Le throw-gate est le cas qui **SÉPARE les deux moitiés** de la loi
  transversale : franchir-le-bootstrap (warm-start ✓) ≠ retenir (r·P ✗). Dans les 4 fils proxy, le warm-start
  marchait car les sous-problèmes avaient un `r·P` adéquat ; ici non.

## Portée / Bornage (honnêteté)

1. **`warm > cold` est NON significatif** (sign_p 0.22, K=6) : l'hystérésis partielle est réelle mais faible ; le
   claim ROBUSTE est « warm N'a PAS retenu le binding » (médiane négative), pas « warm bat cold ».
2. Warm direction = logistique sur `H` de collecte ; `H` dérive dans le temps → le transfert n'est pas parfait
   (mais le frozen +0.40 prouve qu'il transfère assez).
3. Confond anti-sat/fenêtre (3ᵉ récurrent) : à fenêtre tardive le throw collapse (throw_rate→0) → mesuré en
   fenêtre médiane où le throw persiste. antisat=0.3 pour la mesurabilité, pas la prod (6.0).
4. Un `r·P` RÉELLEMENT au-dessus du plancher (proies denses + kill fiable) n'a pas été construit — c'est
   justement ce que la biosphère (throw balistique à payoff rare) ne fournit pas.

## Suite

- **CLÔT l'arc throw-gate in-world (172→175) côté gate/récompense/warm.** Le binding in-world de cette action
  requiert une TÂCHE où l'outil PAIE de façon fiable et dense (kill fréquent), PAS un réglage du gate/du signal/de
  l'init sur la balistique actuelle. Le throw balistique de la biosphère est structurellement sous le plancher.
- **Leçon générale actionnable** : avant de tenter un binding in-world sur une action, **vérifier `r·P` vs le
  plancher de rétention** (récompense fiable × probabilité de succès). Les actions à payoff rare (throw-outil,
  craft, autel) ne bindent pas — ni à froid ni warm — sans densifier le PAYOFF (pas le signal).
- Le banc (`compare_warmstart`, knobs warm/lr/antisat) est réutilisable pour tester le warm-start sur une action à
  `r·P` élevé quand une telle tâche existera.

Lignée : clôt l'arc 172/173/174/175 et RAFFINE [[warm-start-transversal-law]] (sépare bootstrap-clearing de
retention ; le throw-gate est le cas in-world qui dissocie les deux moitiés). Converge [[coop-competence-is-population-property]]
(crédit means→ends) + la thèse CRÉDIT de COS Phase B (crédit ATTRIBUABLE ET RETENABLE = densité, pas signe/init).
Instancie la loi de rétention c_warm=r·P in-world.
