# Design — Territoires de recherche AGAGI + Cartographe automatique

**Date** : 2026-07-01. **Statut** : design validé (brainstorming), prêt pour plan d'implémentation.

## Objectif

Diviser la recherche scientifique AGAGI en **territoires spécialisés** pour (a) permettre à plusieurs
sessions parallèles de se partager la recherche sans collision, et (b) approfondir par spécialisation.
Les territoires sont **vivants** (naissent, se scindent, fusionnent, se retirent) et **collaboratifs**
(deux territoires peuvent converger). Un **cartographe automatique** détecte les gaps, les bottlenecks et
l'émergence de nouveaux territoires à partir du corpus existant.

Problème concret motivant : les sessions parallèles partagent un working tree et se collisionnent —
3 collisions de numéros d'EDR rien que dans la session du 2026-07-01 (132, 140, 141), résolues au coup
par coup par renumérotation. Le spectre de recherche s'agrandit (151+ EDR) sans carte partagée.

## Décisions (brainstorming)

1. **Axe de découpe** : HYBRIDE couche×question — chaque territoire = une couche (isolation fichiers) +
   une/deux questions phares end-to-end (profondeur).
2. **Granularité** : ~10 territoires fins.
3. **Schéma d'ID** : IDs PRÉFIXÉS par territoire, append-only (`EDR-SUB-012`). Collision structurellement
   impossible ; le legacy `EDR-nnn` (1-151) cohabite intact.
4. **consolidate_records.py** : parser ÉTENDU pour accepter les DEUX formats (legacy + préfixé), une passe.
5. **Moteur du cartographe** : HYBRIDE — script déterministe (moisson de signaux structurés) + pass agent
   (couche sémantique : clustering, sévérité, propositions).
6. **Autonomie** : le cartographe DÉTECTE et PROPOSE automatiquement ; la CRÉATION d'un territoire (écriture
   au registre) est APPROUVÉE par une session lead / l'humain.

## Non-objectifs (YAGNI)

- Ne PAS renuméroter les 151 EDR legacy (cohabitation).
- Ne PAS auto-committer la création de territoires (faux positif = pollution de la carte partagée).
- Ne PAS refactorer les benches existants ni imposer une réorganisation des `tools/` déjà en place —
  l'ownership se DÉCLARE dans le registre, on ne déplace pas les fichiers.
- Pas de préfixe « partagé » pour la collaboration (ambigu) — un pilote + co-signataires.

---

# PARTIE 1 — Territoires & coordination

## 1.1 Carte initiale des territoires (~10)

Dérivée de la carte mémoire actuelle. La carte est un POINT DE DÉPART, pas une structure figée.

| Préfixe | Couche | Territoire | Question phare | Statut initial |
|---------|--------|------------|----------------|----------------|
| **SUB** | Substrat/Moteur | Moteur d'apprentissage : torch, gradient/BPTT/Baldwin, connectome, NAS | Moteur torch ≥ legacy + exploiter le gradient (BPTT in-world) | actif (fil 134-145) |
| **BIND** | Substrat/Cognition | Crédit compositionnel : gate de conditionnement, anti-saturation, means→ends | Cracker le means→ends conditionnel | résolu-proxy → portage |
| **MEM** | Substrat | Mémoire : épisodique vs câblée, NTM, long-terme, BPTT-mémoire | La mémoire paie-t-elle, et quand | Partie A close |
| **WLD** | Monde | Demande d'intelligence & plancher : S2, life_score, survie | Le monde exige-t-il l'intelligence (métrique) | verdict VOID à réparer |
| **CRAFT** | Monde | Craft, rétention, tool-gate | Pourquoi le craft n'est pas retenu | verrou = rétention |
| **NAV** | Monde | Navigation & énergie : Lewis, forage, p_reach | Le mur de navigation | mur = politique/substrat |
| **FAM** | Monde | Famine, stockage, spécialisation, cross-world | Émergence de spécialisation world-spécifique | durcir réfuté |
| **COG** | Cognition | Types d'intelligence & organes : ToM, referential, dreaming, planning | Quels types émergent / sont dissociables | ToM clos, dreaming réfuté |
| **INFRA** | Instruments | Méthodo, repro, consolidate, parity gate, hazards mp/biosphère | Garder les bancs sains et repro | continu |
| **PROD** | Prod | Migration prod, backend, frontend | Porter les recettes validées | roadmap BACKEND/FRONTEND |

**Commons partagés** (possédés par personne, intendant désigné) : le sim de monde (WLD/CRAFT/NAV/FAM le
lisent), `tools/consolidate_records.py` (intendant INFRA), le core substrat (intendant SUB), les benches
transverses (ex. `tools/substrate_ab_compositional.py` — intendant BIND).

## 1.2 Règles d'évolution des territoires

- **Naissance** : nouveau préfixe + ligne au registre, EDR démarre à `-001`.
- **Scission** (ex. WLD → WLD + META) : nouveau préfixe à neuf ; les EDR de l'ancien gardent leur préfixe ;
  le registre note la filiation (`META ← scindé de WLD, 2026-…`).
- **Fusion** (ex. NAV replié dans WLD) : le registre marque `NAV → mergé dans WLD` ; les `EDR-NAV-*`
  existants restent valides tels quels.
- **Dormance / retrait** : statut `dormant` (frontière sans travail récent) ou `clos` (question résolue).
- **Invariant** : un préfixe n'est JAMAIS réutilisé ni renuméroté. C'est ce qui rend collisions impossibles
  ET évolution gratuite.

## 1.3 Le registre vivant — `docs/roadmap/SPECIALITES.md`

Source de vérité unique. Une section par territoire :

```
## SUB — Substrat & Moteur d'apprentissage
- statut: actif
- couche: Substrat/Moteur
- question_phare: Moteur torch ≥ legacy + exploiter le gradient (BPTT in-world)
- fichiers_possedes: tools/substrate_world_ab.py, tools/torch_*_probe.py
- commons_intendant: [core substrat]
- memoire: sota-gap-substrate.md
- frontiere_courante: BPTT fenêtré in-world (persister le graphe K ticks)
- ponts_actifs: [BIND (portage means→ends), MEM (BPTT-mémoire)]
- filiation: —
- dernier_EDR: EDR-SUB-… (auto-rempli par le cartographe)
```

Éditer la carte = éditer ce fichier (path-scoped, append/edit ligne-à-ligne, peu conflictuel).
En-tête du fichier : la **convention d'IDs**, la table des **commons + intendants**, et le lien vers le
rapport cartographe le plus récent.

## 1.4 IDs préfixés

- Format : `EDR-<PREFIX>-<nnn>` (nnn zéro-paddé à 3, séquence propre au préfixe). Idem `SDR-`/`ADR-` si
  besoin plus tard (hors scope initial).
- Frontmatter EDR inchangé sauf `id` ; nouveau champ optionnel `also: [PREFIX, …]` pour la collaboration.
- Nom de fichier : `docs/EDR/<PREFIX>-<nnn>_Titre.md` (miroir de l'`id`), ex. `SUB-012_...md`. Il cohabite
  dans le même dossier que les legacy `140_...md` (tri séparé, aucun conflit de glob).
- Legacy `EDR-nnn` / `140_...md` : inchangé, cohabite.

## 1.5 Collaboration cross-territoire

- Un record conjoint a **un seul pilote** (préfixe propriétaire) + `also: [co-territoires]`.
- Le registre a un champ `ponts_actifs` par territoire, listant les convergences en cours
  (ex. BIND×SUB = portage prod ; SUB×MEM = BPTT-mémoire). Le cartographe peut proposer des ponts
  (deux territoires dont les EDR récents se citent mutuellement).

## 1.6 consolidate_records.py — parser étendu

- Accepter `id: EDR-nnn` (legacy) ET `id: EDR-<PREFIX>-<nnn>` (préfixé).
- Le graphe de records indexe par `id` complet (le préfixe fait partie de la clé → jamais de collision).
- Edges (liens entre records) : résoudre les deux formats dans les références.
- Ajouter au rapport consolidate : un **compte par préfixe** (matière première du cartographe).
- TDD : cas legacy seul, préfixé seul, mixte ; un doublon d'id (même préfixe+num) doit être signalé
  (`problemes>0`).

---

# PARTIE 2 — Cartographe automatique

Bâti SUR la Partie 1 (a besoin du registre + des préfixes pour dire « orphelin vs territoire connu »).
Moteur HYBRIDE : script déterministe (signal) + pass agent (interprétation). Détection auto, création
approuvée.

## 2.1 Signaux (déterministes, `tools/cartography.py`)

Parse le corpus (EDR frontmatter, `MEMORY.md` + notes mémoire, `SPECIALITES.md`, sortie consolidate) et
extrait :

- **Leads pendants (gaps)** : occurrences de « piste suivante / actionnable / prochain build / prochaine
  sonde » dans un EDR/mémoire, cross-référencées contre les EDR aval — un lead sans EDR aval qui le
  reprend = gap ouvert. (Heuristique texte + proximité de préfixe.)
- **Verdicts abandonnés** : records `status`/verdict ∈ {INCONCLUSIF, VOID, INDÉTERMINÉ} sans record aval
  qui les tranche.
- **Territoires dormants** : préfixe sans EDR depuis N jours / K records d'écart (via `dernier_EDR`).
- **Termes-verrou récurrents (bottlenecks)** : fréquence des marqueurs « verrou / mur / RÉFUTÉ / bassin »
  et du terme cause-racine associé, agrégée par territoire ET transverse (un terme qui revient dans ≥3
  territoires = bottleneck systémique candidat).
- **Comptes par préfixe** : volume et récence (santé du territoire).
- **Orphelins** : EDR récents dont les mots-clés ne matchent le `question_phare`/`fichiers` d'aucun
  territoire (signal brut, affiné par l'agent).

Sortie : `docs/roadmap/cartographie/signals-<date>.json` (données brutes reproductibles).

## 2.2 Interprétation (pass agent, à la demande / hebdo)

Consomme le JSON de signaux + relit les clusters ambigus et produit un **rapport cartographe** :

- **Gaps classés** : les leads pendants + verdicts abandonnés, priorisés (impact × facilité), avec le
  territoire propriétaire et une amorce de question.
- **Bottlenecks** : les termes-verrou systémiques, avec les territoires touchés → candidat à un territoire
  transverse ou à un pont.
- **Émergence** : clusters d'orphelins sémantiquement cohérents → **territoires candidats** (préfixe
  proposé, territoire, question phare, EDR-preuve qui le motivent). Aussi : territoires à SCINDER (deux
  sous-questions distinctes) ou à FUSIONNER (deux territoires qui convergent).
- **Ponts proposés** : paires de territoires dont les EDR récents se citent.

Le rapport est écrit dans `docs/roadmap/cartographie/rapport-<date>.md`. Chaque proposition de création/
scission/fusion inclut sa PREUVE (les records qui la motivent) pour l'approbation.

## 2.3 Boucle d'approbation

- Détection = automatique (script + agent). Le rapport est advisory.
- **Création/scission/fusion** = une session lead (ou l'humain) approuve → édite `SPECIALITES.md`
  (naissance officielle). Le cartographe ne touche JAMAIS le registre lui-même.
- Un lead approuvé peut être « adopté » : le rapport marque le lead comme repris quand un EDR aval le cite.

## 2.4 Cadence

- Le script : à la demande, et idéalement en fin de `consolidate_records.py` (les comptes/préfixe y sont
  déjà) — pas de cron obligatoire.
- Le pass agent : à la demande (une session lead lance « cartographie ») ou hebdomadaire. Pas d'automatisme
  de fond imposé (coût token).

---

## Fichiers créés / modifiés

**Partie 1**
- CRÉÉ `docs/roadmap/SPECIALITES.md` (le registre + convention IDs + commons/intendants).
- MODIFIÉ `tools/consolidate_records.py` (parser 2 formats, compte/préfixe, détection doublon d'id).
- MODIFIÉ `docs/FIL_CONDUCTEUR.md` / `docs/roadmap/SCIENCE.md` : pointeur vers le registre.
- Convention documentée ; les EDR futurs utilisent `EDR-<PREFIX>-nnn`.

**Partie 2**
- CRÉÉ `tools/cartography.py` (moisson déterministe → signals JSON).
- CRÉÉ `docs/roadmap/cartographie/` (signals + rapports).
- Sous-agent / prompt de cartographie (couche sémantique) — invoqué à la demande.

## Découpage en plans

- **Plan 1 (fondation, near-term)** : Partie 1 — registre + IDs préfixés + parser consolidate étendu (TDD).
  Autonome et immédiatement utile (stoppe les collisions).
- **Plan 2 (cartographe)** : Partie 2 — script de signaux (TDD) puis pass agent + rapport. Dépend de la
  Partie 1 (registre + comptes/préfixe).

Ce document EST le design des deux parties. On écrit d'abord le **plan d'implémentation de la Partie 1**
(fondation) via writing-plans, on l'implémente et on la merge ; la **Partie 2** obtiendra SON plan quand la
fondation est en place (elle en dépend). Pas de re-brainstorming : ce spec suffit pour les deux plans.

## Bornage / risques

- **Heuristiques texte** du script (leads/verdicts/termes-verrou) : imparfaites (faux positifs/négatifs) ;
  c'est pourquoi l'agent affine et l'humain approuve. Le script ne DÉCIDE rien.
- **Migration douce** : les 151 EDR legacy restent en `EDR-nnn` ; on n'impose le préfixe qu'aux nouveaux.
  Le registre initial mappe rétroactivement chaque territoire à ses EDR legacy (référence, pas renommage).
- **Contention du registre** : `SPECIALITES.md` édité par plusieurs sessions → édition ligne-à-ligne +
  commits path-scoped (convention [[parallel-sessions-shared-tree]]).
