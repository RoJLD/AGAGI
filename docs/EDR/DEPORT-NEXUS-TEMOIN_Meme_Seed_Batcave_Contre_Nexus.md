---
id: EDR-DEPORT-NEXUS-TEMOIN
type: EDR
title: Même sha, même seed, batcave contre nexus — identiques sous la règle déclarée pour UNE cellule numpy, poids gelés ET appris ; unité de coût des deux côtés, sous charge côté batcave
status: accepted
gate: foundational
adopts: [REF-DEPORT-NEXUS]
verdict: IDENTIQUE_HORS_DUREE_UNE_CELLULE_NUMPY
review: docs/reviews/2026-09-26-DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md
---

# EDR-DEPORT-NEXUS-TEMOIN : le déport rend la même sortie que la batcave — pour une cellule numpy, et pas au-delà

> Livrable (4) de la session INFRA-NEXUS (P2.126). Instrument : `tools/jobs/remote.py` — `executer` pour nexus,
> `local` pour la batcave, qui partagent la préparation du dépôt au sha et le point d'entrée
> `tools/jobs/remote_entry.py` — et le comparateur `ecarts_hors_volatils`. Évidence :
> `results/deport_temoin_nexus.json`, produite par `agreger_temoin` ; toutes les sorties y sont embarquées en OCTETS
> BRUTS (base64) et chaque compte ci-dessous se rejoue par `python -m tools.jobs.remote temoin
> results/deport_temoin_nexus.json` (« tout se rejoue »). Revue /refutateur avant publication : 42 critiques,
> 19 confirmées, toutes traitées ici (la revue note que son témoin cru sain a rendu autant de critiques recevables que
> les défectueux : ses critiques valent par leurs sondes, pas par leur nombre).

## Question

Un run déporté sur nexus (Linux, pod limité à 2 CPU par le cgroup) rend-il, au même sha et à la même seed, la MÊME
sortie que sur la batcave (Windows) ? Et combien coûte la même cellule de chaque côté ?

**Règle** : les sorties du runner sont identiques OCTET POUR OCTET, fins de ligne comprises, une fois masquée la seule
VALEUR des clés déclarées volatiles — ici `elapsed_s` (durée murale). Son antériorité : le comparateur et la liste
des volatils sont committés à 7f639e35 (11:32 UTC), AVANT le premier run nexus (12:15 UTC) — mais APRÈS la paire
batcave du tour 1 (11:04 et 11:05 UTC), qui montrait déjà deux lignes de durée différentes. La règle n'est PAS scellée
par `tools/preregister` : son antériorité est attestée par l'historique git, pas par un sceau (E11 résiduel).
Runner : le moins cher du dépôt, `python -m tools.evo_runs.evo011_preflight --smoke` — numpy, kuzu neutralisé, aucune
donnée d'entrée, UNE seed, trois bras.

## Histoire : le tour 1 (sha da09f7a1) n'était pas comparable

Sous la règle, batcave~nexus rendait 574 écarts : les sorties ont 575 segments (574 sauts de ligne, puis l'accolade
finale sans saut) et TOUS ceux qui se terminent par un saut de ligne différaient par le seul retour chariot. Le runner
écrivait son JSON en mode texte (`open(out, "w", encoding="utf-8")`), donc CRLF sous Windows et LF sous Linux.
Surtout, les deux côtés n'avaient PAS tourné le même instrument : la batcave avait exécuté une version de
`remote_entry.py` qui n'est dans aucun commit (empreinte c136aeff), nexus celle de 7f639e35 (09ca2e91). Ce tour est
gardé comme histoire ; il n'établit rien, dans un sens ou dans l'autre.

## Tour 2 (sha def16adc) : identiques, poids gelés

Remède : `evo011_preflight.py` écrit son JSON avec `newline="\n"` (commit def16adc). Même règle, même point d'entrée des
quatre côtés (empreinte 28aaf8d1), deux réplicats par machine : les **6 paires** rendent **0 écart**. Contrôle sans
volatils déclarés : 2 écarts par paire, les deux lignes de durée.

**Dose de ce tour : NULLE.** Le runner gèle les poids (`freeze`) : aucune mise à jour de W, dérive max|W−W0| = 0,0
dans les trois bras ; les cohortes s'éteignent aux ticks 43, 49 et 27 sur 200 (1 291 agents-ticks, 9 % du budget).

## Tour 3 (sha def16adc, `--no-freeze`) : identiques, poids appris

Même cellule, apprenant ACTIF : dérive max|W−W0| = 15,0 / 10,99 / 15,0 selon le bras, 998 agents-ticks. Batcave~nexus :
**0 écart** sous la règle, 2 sans volatils. La mise à jour de W pendant la vie — le chemin numérique le plus sensible
aux arrondis de ce runner — rend donc les mêmes octets sur les deux machines, pour cette cellule.

## Tour 4 (sha 7481e15e) : identiques sur l'image reconstruite

La sortie de l'adresse du cluster hors du dépôt (7481e15e) a changé le gabarit de build, donc le contexte haché :
l'image a été reconstruite (digest 7c860b30…). **Elle diffère de la précédente (a1d6e4eb…) pour un Dockerfile, des
contraintes et des requirements identiques** — une construction n'est pas reproductible bit à bit (dépendances
transitives non épinglées, ou horodatages de couches) ; c'est le digest d'`IMAGE.json` qui désigne l'image, jamais le
tag. Même cellule qu'au tour 2 (poids gelés), un côté batcave et deux nexus : **0 écart** sous la règle sur les 3
paires, contrôle 2 par paire. Le record reste donc vrai sur l'image que cite `IMAGE.json`. Coût : nexus 1,397 et
1,396 s (runner) ; batcave 2,514 s, à 30,2 % de CPU au départ.

## Le comparateur et le runner peuvent-ils dire « différent » ?

Oui, mais grossièrement. Trois sorties nexus du même sha (W gelé, W appris, 23 agents au lieu de 24) diffèrent deux à
deux ; le comparateur ne rend alors que sa sentinelle de longueur (les nombres de lignes diffèrent), pas un compte de
lignes. Aucune perturbation à structure constante n'a été mesurée : **la sensibilité au dernier ULP n'est pas
éprouvée**. Elle repose sur peu de valeurs : la revue compte, dans la sortie du tour 2, 7 flottants continus en pleine
précision, le reste étant entiers, constantes, NaN et rapports d'entiers.

## Unité de coût (tour 2), des deux côtés

| côté | runner (`elapsed_s`) | mur (entrée) | CPU user + sys | limite CPU lue | charge de la machine au départ |
|---|---|---|---|---|---|
| nexus ×2 | 1,395 et 1,392 s | 1,697 et 1,688 s | 1,70 + 0,08 et 1,69 + 0,08 s | cgroup `cpu.max` → 2 CPU ; `os.cpu_count()` = 16 | loadavg hôte 1,10 et 1,17 ; 2,1 et 2,3 % CPU |
| batcave ×2 | 2,213 et 2,576 s | 2,644 et 3,208 s | 1,89 + 0,59 et 2,22 + 0,73 s | aucune (Windows) ; 22 cœurs logiques | 23,8 et 89,3 % CPU |

**Bande de bruit** (rapport entre réplicats de la même machine) : nexus 1,002 (runner) et 1,005 (mur) ; batcave 1,16
et 1,21 (1,19 et 1,27 au tour 1). **Contraste** batcave/nexus : 1,59 à 1,85 (runner), 1,56 à 1,90 (mur) — hors des deux
bandes, mais ce n'est PAS une unité machine libre contre machine libre : aucune cellule batcave au repos n'existe, et la
bande batcave mesure surtout l'effet de charge (1,16 entre un réplicat à 23,8 % et un à 89,3 %). Le contraste confond
aussi machine, système, charge et fils BLAS (2 posés par le cgroup côté pod, défaut de la bibliothèque sur 22 cœurs côté
batcave). Les colonnes CPU ne se comparent pas terme à terme : Linux compte tous les descendants attendus
(`RUSAGE_CHILDREN`), Windows le fils direct (`GetProcessTimes`) — et le runner n'est pas mono-processus, il lance trois
`git` (bail, provenance) ; l'écart est probablement petit (~0,08 s), il n'est pas nul. Vie des Jobs côté cluster, lue
dans leurs statuts : 27 à 39 s ; source envoyée : 19,6 à 19,7 Mo par Job.

## Ce que ce record établit, et ce qu'il n'établit pas

* **Établi, pour UNE cellule** (evo011_preflight, seed 0, trois bras, numpy, poids gelés puis appris) : au même sha, le
  déport rend octet pour octet la sortie de la batcave hors durée, **à condition que le runner écrive ses fichiers en
  LF**. Deux réplicats par machine et deux régimes de poids ne font pas une famille : la portée ne s'étend pas à « tout
  runner numpy ».
* **Non établi** : l'identité d'un calcul **torch float32** entre plateformes. Les bibliothèques diffèrent (batcave :
  torch 2.6.0+cu124, MKL 2025.0.1, 16 threads par défaut ; pod : torch 2.6.0+cpu Linux, threads posés à 2 par le cgroup,
  déclarables par `--env` depuis def16adc — valeurs batcave mesurées et publiées dans l'évidence, bloc
  `mesures_annexes`). **Le témoin suivant est nommé** : la cellule P4.18 (monde + torch) que la session SCIENCE lance
  sur nexus et compare aux valeurs publiées sous Windows.
* **Défaut hors de ce runner** : tout runner qui écrit ses résultats en mode texte sans `newline="\n"` rend des octets
  dépendants de la plateforme. git les normalise au commit (`core.autocrlf`), donc le dépôt ne le voit pas ; une
  comparaison d'octets bruts entre deux machines, si.
