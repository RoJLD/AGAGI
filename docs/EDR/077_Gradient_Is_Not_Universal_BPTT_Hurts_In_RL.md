# EDR 077 : Le gradient n'est PAS la clé universelle — en RL, le BPTT NUIT (auto-réfutation honnête)

## Contexte

EDR 076 a conclu (prescription) : « la mutation maintient mais ne forge pas la compétence ; le levier
est le gradient FORT (BPTT) à horizon long ». **On teste cette prescription sur banc** avant toute
intégration : une compétence de foraging-MÉMOIRE en RL (indice de direction visible 2 pas puis caché,
nourriture lointaine -> il faut RETENIR), trois moteurs sur la MÊME architecture (connectome récurrent),
4 seeds, 600 iters (mutation 300 gens).

## Résultat — la prescription est RÉFUTÉE

| Moteur | nourriture / 40 pas | rang |
|---|---|---|
| **MUTATION** (moteur biosphère, EDR 076) | **5.58 ± 0.38** | 🥇 |
| COUPÉ (gradient one-step) | 4.96 ± 1.10 | 🥈 |
| **BPTT** (gradient fort, à travers le temps) | **2.10 ± 0.08** | 🥉 |

- En RL, l'ordre est **l'INVERSE** de ce que 076 prédisait : **mutation > one-step > BPTT**.
- Le **gradient fort (BPTT) est le PIRE** — et le clipping de norme (5) ne le sauve pas (testé : 2.10
  identique). Ce n'est pas l'explosion, c'est la **variance**.
- Tâche EASY (nourriture toujours visible, run précédent) : mutation 9.5 (meilleur) aussi. La mutation
  est *bonne* sur le foraging.

## Pourquoi — supervisé ≠ RL

> 067 (mémoire) et 072 (langage) étaient **SUPERVISÉS** : cible dense, faible variance → le gradient
> (y compris BPTT) excelle, la mutation peine. Le foraging est du **RL** : récompense ÉCHANTILLONNÉE,
> pas de cible. Le BPTT propage le gradient de politique à travers 40 pas récurrents → **accumule de la
> variance** sans signal supplémentaire (la récurrence avant + le crédit local suffisent) → converge
> *plus mal*. La mutation (recherche aveugle mais STABLE) reste compétitive.

## La correction (honnête) de la narration du projet

> **« Le gradient est la clé universelle » (esquissé en 076) était une SUR-GÉNÉRALISATION.** Vérité
> corrigée et plus précise :
> - **Sous-compétences SUPERVISÉES** (mémoire 067, langage 072) : le gradient gagne nettement.
> - **Compétence RL** (foraging, survie, action) : la mutation est compétitive/meilleure ; le BPTT NUIT.

> Donc le PLATEAU de la biosphère (076) ne vient PAS de la faiblesse de la mutation (elle est bonne ici)
> ni d'un manque de BPTT (il est pire). Il vient de la **DIFFICULTÉ DE RECHERCHE** : 172 dimensions,
> fitness bruitée par l'extinction (ères courtes), coordination. Le levier n'est pas un autre *règle
> d'apprentissage* — c'est un meilleur *signal de fitness* / curriculum / réduction de dimension.

## Honnêteté (la valeur de ce négatif)

- J'ai bâti un banc pour tester **ma propre prescription d'EDR 076** — et il l'a **réfutée**. C'est la
  discipline du projet : tester au lieu d'extrapoler (cf. 057 faux positif, 054 expérience cassée). Une
  extrapolation flatteuse (« le gradient résout tout ») aurait orienté un gros chantier d'intégration
  BPTT *voué à empirer la compétence*.
- Caveat : banc 1D simplifié ; le BPTT pourrait aider sur des tâches à crédit temporel VRAIMENT profond
  (distracteurs, délai long sans signal). Mais pour la compétence de foraging RL — la cible d'EDR 075/076
  — il nuit.

## Tooling (demande utilisateur) — `tools/progress.py`

Barre de progression + % + écoulé + **ETA** en temps réel, sans dépendance, sur stderr (n'encombre pas
les logs). Réutilisable : `Progress(total, label).update()` ou `Progress.track(iterable)`. Intégré à
`grad_compete.py` (entraînements) et `evolve_competence.py` (boucle d'ères). Exemple :
`MUTATION seed 1/4 [########------------] 44% 267/600 65s ETA 81s`.

## Suite (re-cadrée, honnête)

Pour la compétence de la biosphère, NE PAS poursuivre l'intégration BPTT. Pistes réelles :
1. **Meilleur signal de fitness** (ères plus longues / moins bruitées ; récompense plus dense que
   l'extinction) — la mutation forge bien quand le signal est bon.
2. **Réduction de dimension / structure** (le connectome 172-D est un espace de recherche dur).
3. Garder le gradient pour ce qu'il fait bien : les **sous-compétences supervisables** (mémoire,
   langage), pas le contrôle RL global.

## Statut

- `grad_compete.py` (banc 3 moteurs, clipping, progression) ; `progress.py` (utilitaire) ;
  `evolve_competence.py` (+ progression). **Prescription BPTT d'EDR 076 réfutée** : en RL, mutation >
  one-step > BPTT. Le gradient n'est pas universel ; il gagne en supervisé, nuit en RL compétence.

## Variables d'expérience

Profondeur du crédit temporel requis (distracteurs, délai), variance du gradient RL (baseline, GAE),
supervisé vs RL, signal de fitness biosphère, dimension de l'espace de recherche.
