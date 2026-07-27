---
id: EDR-164
type: EDR
title: "Le seuil de rétention du craft est une FALAISE NETTE (transition de phase bistable) à c*≈0.04, PAS une non-rentabilité graduelle — CORRIGE EDR-162. Sweep fin (2 seeds) : rétention tient à c≤0.03 (P(consume|craft) HAUT 0.77-0.97, un petit coût RENFORCE = régularise) puis s'effondre catastrophiquement à c≥0.05 (P~0.4). Le seuil (0.04) est très loin de la borne statique r·P≈0.9 → effondrement = INSTABILITÉ DYNAMIQUE de bassin (cercle vicieux = bifurcation nœud-selle), pas E[craft]<0. Correction clé : le binding est FORT (P jusqu'à 0.97), PAS 0.25 (162 citait le comp_rate inconditionnel). Levier in-world affiné : warm-start dans le bon bassin (converge 131/132), pas 'renforcer le binding'"
status: accepted
gate: null
verdict: RETENTION_THRESHOLD_IS_SHARP_BISTABLE_CLIFF_BINDING_ALREADY_STRONG
supersedes_mechanism_of: EDR-162
---

# EDR 164 : le seuil de rétention est une falaise bistable (c*≈0.04) — corrige le mécanisme d'EDR-162

## Contexte

EDR-162 avait conclu `NO_RETENTION_ADVANTAGE` (dès un coût c≥0.3 le craft s'effondre) avec le mécanisme
« la rétention est en aval de la FORCE du binding, faible (P≈0.25) ». Item C : localiser FINEMENT le
seuil de coût c* et vérifier le mécanisme (`E[craft] = −c + r·P(consume|craft)` → tient ssi c < r·P).

## Constat

Sweep fin de c (ON, gate additif task-agnostique + learn_episode, r=1, 800 ép, 2 seeds) ;
P = P(consume|craft) = comp_late / craft_late :

| c | craft_late (s0 / s1) | P (s0 / s1) | état |
|---|---|---|---|
| 0.00 | 0.160 / 0.114 | 0.79 / 0.77 | tient |
| 0.01 | 0.191 / — | 0.91 / — | tient (RENFORCE) |
| 0.02 | 0.199 / — | 0.95 / — | tient (RENFORCE) |
| 0.03 | 0.204 / 0.109 | **0.97 / 0.89** | tient (P max) |
| 0.04 | 0.071 / 0.083 | 0.42 / 0.55 | **transition** |
| 0.05 | 0.060 / 0.070 | 0.33 / 0.42 | effondré |

`VERDICT = RETENTION_THRESHOLD_IS_SHARP_BISTABLE_CLIFF`. Seuil c* ≈ 0.04, robuste sur 2 seeds
(tient ≤0.03, s'effondre ≥0.05, transition à 0.04). Transition NETTE (falaise), pas graduelle.

## Lecture

- **CORRIGE EDR-162** : `P(consume|craft)` est en réalité HAUT (0.77-0.97), PAS 0.25. Le « 0.25 » de 162
  était le comp_rate INCONDITIONNEL (P(craft ∧ consume)), pas le P CONDITIONNEL. **Le binding est FORT**
  quand le craft est soutenu — le verrou de la rétention n'est donc PAS un binding faible.
- **L'effondrement est une INSTABILITÉ DYNAMIQUE de bassin, pas une non-rentabilité statique.** À
  l'équilibre haut (c≤0.03, P≈0.97), `E[craft] = −c + r·P ≈ +0.94` : largement profitable. La borne
  statique prédirait une tolérance jusqu'à c ≈ r·P ≈ 0.9. Or l'effondrement survient à c* ≈ 0.04, **20×
  plus bas**. Le cercle vicieux (craft↓ → consume↓ → P↓ → craft↓) est un feedback positif → deux bassins
  (haut-craft / collapsé) séparés par une bifurcation nœud-selle ; le coût déplace le bassin ATTEIGNABLE.
- **Un petit coût RENFORCE la rétention** (P : 0.79 → 0.97 de c=0 à c=0.03) : le coût agit comme
  RÉGULARISEUR (pénalise le craft-sans-consume → l'agent ne crafte que s'il va consommer → conditionnement
  plus propre). Bénéfique jusqu'à la falaise.
- **La rétention est un problème de BOOTSTRAP/BASSIN, pas de force ni de crédit** : le coût tue le craft
  pendant la phase d'exploration (P encore bas) AVANT que le binding n'atteigne l'équilibre haut →
  converge la path-dependence d'EDR-131/133 (bassin d'optim précoce) et le warm-start d'EDR-132.

## Conséquences

- **Levier in-world (axe 3) AFFINÉ vs 162** : le binding est déjà FORT (P≈0.97) ; l'enjeu de la rétention
  d'un moyen coûteux est la BISTABILITÉ. Leviers = (a) **warm-start** du binding dans le bassin haut
  (converge EDR-131/132), (b) garder c/r < ~0.04 (in-world : coût du craft faible devant la récompense),
  (c) curriculum de coût croissant (rester dans le bassin haut en montant c lentement). PAS « renforcer
  le binding » (déjà fort) comme l'écrivait 162.
- **Corrige/complète le triptyque H-unif** : 162 tenait (rétention à COÛT échoue) mais pour la MAUVAISE
  raison ; la vraie cause est la bistabilité, pas la faiblesse du binding. Le pari H-unif reste : les 3
  phénomènes sont routage/crédit conditionnel ; la rétention y ajoute une couche DYNAMIQUE (bistabilité).
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-164` ; corrige le mécanisme d'EDR-162.

## Caveats

1. c* ≈ 0.04 localisé à 2 seeds (transition à 0.04 : s0 collapsé 0.42, s1 marginal 0.55) ; la valeur
   exacte du seuil est stochastique (bistable near-threshold), mais la FALAISE et sa position ~0.04 sont
   robustes.
2. r=1 fixe ; la prédiction c* ∝ r (le seuil scale avec la récompense) est plausible mais NON testée ici
   (bornage — un sweep r confirmerait la loi c*/r).
3. Substrat 172-nœuds dégénéré, means→ends 2-pas synthétique ; la valeur ABSOLUE de c* est spécifique au
   substrat/barème. Le ROBUSTE = falaise nette + P haut (binding fort) + seuil ≪ borne statique.
4. « Bifurcation nœud-selle » est une lecture mécaniste (feedback positif + bistabilité observée), non
   une preuve analytique.
