# EDR 023 : Actor-Critic TD(0) — le crédit temporel pour les chaînes différées

## Contexte — étape 2 de la Vague 0bis

L'EDR 020 a réparé l'apprentissage (crédit d'**action**), mais son critic était **Monte-Carlo
sur le reward immédiat** (`critic ← r`). Or la chaîne moyens→fins est à récompense **différée** :
*crafter* **coûte** 2.0 d'énergie maintenant et ne rapporte que plus tard (tuer le Mammouth, EDR 022).
Sous un critic immédiat, l'avantage du craft est **négatif** → l'actor apprendrait à *ne pas* crafter.
**Aucune chaîne multi-étapes n'est apprenable sans crédit temporel.**

## Décision (V18.10) — TD(0)

`δ = r + γ·V(s') − V(s)` (erreur TD) sert **à la fois** d'avantage pour l'actor et d'erreur de
correction du critic (qui apprend désormais vers `r + γ·V(s')`).

- `policy_gradient.td_error(reward, value, next_value, gamma)` (pur, testé).
- `compute_policy_gradient` : la transition `(s, a, r, V)` est **différée d'un tick** (stockée sur
  le modèle dans `agent._td`, robuste au re-batch) ; au tick suivant `V(s')` est connu → on applique
  l'update à la transition précédente. Actor (avantage δ) + critic (`dW[:,v] += lr·δ·h`). γ = 0.9.
- `_td` réinitialisé dans `reset_state` (pas de fuite inter-vie).

## Résultat — pas de régression, amélioration

Curriculum (collecte item-riche → monde dur pourvu) :

| | MC immédiat (EDR 020) | TD(0) (EDR 023) |
|---|---|---|
| Phase 1 (encodage) | 678 | **784** |
| Phase 2 (transfert monde dur) | 21 | **28** |

> Le gain est **modeste ici** car le curriculum de collecte est surtout à récompense *immédiate*
> (le scaffold paie le grab/craft tout de suite) — le TD a peu à propager. Sa vraie valeur viendra
> sur la chaîne **longue** (craft → chercher → engager → tuer l'apex), récompense différée de
> nombreux ticks, où seul `γ·V(s')` fait remonter le crédit jusqu'au craft initial. Mécanisme posé
> *avant* d'en avoir besoin — au moment où le combat (EDR 022) vient de créer ce payoff différé.

## Limites & suites

- TD(0) (1 pas) ; pour des horizons longs, n-step / TD(λ) propageraient plus vite (futur).
- `γ = 0.9` règle l'horizon (myope ↔ prévoyant) — variable d'expérience à calibrer selon la
  longueur des chaînes ciblées.
- La dernière transition d'une vie n'est pas corrigée (pas de tick suivant) — perte négligeable.

## Variables d'expérience

`gamma` (horizon), `lr_actor`/`lr_critic`, TD(0) vs n-step/TD(λ).
