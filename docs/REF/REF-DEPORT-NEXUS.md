---
id: REF-DEPORT-NEXUS
type: REF
title: "Déport des runs sur le cluster ELYSIUM (nœud nexus) — mode d'emploi et garanties"
status: active
---

## Pourquoi

Décision de robla (2026-09-26) : **les runs AGAGI tournent par défaut sur le cluster ELYSIUM, nœud nexus**
(15 CPU / 64 Gi allouables), et la batcave reste libre — pour les sessions, et pour que l'unité de coût
d'un run ne soit plus mesurée sous la charge des autres (E12 appliqué au coût, payé trois fois le
2026-09-22). Seul un Job témoin existait (2026-09-24, mémoire `nexus-cluster-witness-job`).

## Ce qui existe

| Pièce | Où | Rôle |
|---|---|---|
| namespace (nom configuré) | `deploy/nexus/00-03*.yaml` (GABARITS, rendus par `remote.py namespace`) | normes `elysium-*` : palier LimitRange `ml-heavy` (12 CPU / 32 Gi par conteneur, accordé par ELYSIUM le 2026-09-26 ; il REMPLACE `standard`, retiré dans le même geste), default-deny + egress du seul build, ResourceQuota (requests 8 CPU / 24 Gi, limits 16 CPU / 40 Gi, 16 pods) |
| image runner | `deploy/nexus/runner/` | Python 3.13.12, dépendances ÉPINGLÉES sur la batcave (`constraints.txt`) SAUF torch (2.6.0+cpu dans l'image, 2.6.0+cu124 sur la batcave : même version, autre build), git ; construite par Kaniko DANS le namespace ; référence committée dans `IMAGE.json` (tag + digest) |
| soumission | `tools/jobs/remote.py` | un Job par run : code au sha, attente, rapatriement vérifié |
| point d'entrée | `tools/jobs/remote_entry.py` | stdlib seule ; tourne dans le pod ET en local, à l'identique |
| tests | `tests/sandbox/test_jobs_remote.py` | sans cluster, Windows ET Linux |

## Mode d'emploi

```
python -m tools.jobs.remote executer --sha HEAD -- -m tools.evo_runs.<runner> <args>   # soumettre + attendre + rapatrier
python -m tools.jobs.remote local    --sha HEAD -- -m tools.evo_runs.<runner> <args>   # même chemin, sur la batcave
python -m tools.jobs.remote soumettre ... ; attendre <job> ; rapatrier <job> [--into DIR] ; etat
python -m tools.jobs.remote installer runs/deport/<job>/sortie_non_installee --into DIR   # après un conflit
python -m tools.jobs.remote image [--reconstruire]                                    # (re)construire l'image
python -m tools.jobs.remote namespace [--appliquer]                                   # rendre (et appliquer) les manifestes
python -m tools.jobs.remote config                                                    # configuration résolue, et sa source
python -m tools.jobs.remote surveiller [--duree-s S] [--ignorer=MOTIF]               # sonde LECTURE SEULE du namespace
```

## Configuration — hors du dépôt, sans défaut

Le dépôt est PUBLIC, et ni le cluster ni le nœud ne sont éternels (décision de robla, 2026-09-26) : AUCUNE adresse,
aucun contexte kubectl, aucun nom de nœud n'est écrit dans un fichier suivi. `remote.py` les lit dans les variables
d'environnement, puis dans `~/.agagi/deport.json` (hors dépôt, partagé par tous les worktrees de la machine ; chemin
surchargeable par `AGAGI_DEPORT_CONFIG`) ; l'environnement l'emporte. Une clé requise absente → refus NOMMÉ avant
tout effet, jamais une valeur devinée. Modèle sans valeur réelle (adresses RFC 5737) : `deploy/deport.example.json`.

| clé | variable | rôle |
|---|---|---|
| `contexte` | `AGAGI_KUBE_CONTEXT` | contexte kubectl (requis) |
| `registre` | `AGAGI_REGISTRY` | `hôte:port` du registre ; une IP si on rend la NetworkPolicy (requis) |
| `noeud` | `AGAGI_DEPORT_NOEUD` | nœud où épingler les Jobs (requis) |
| `namespace` | `AGAGI_DEPORT_NAMESPACE` | namespace dédié (requis) |
| `depot_image` | `AGAGI_DEPORT_DEPOT_IMAGE` | chemin de l'image dans le registre, sans hôte (requis) |
| `fenetre` | `AGAGI_DEPORT_FENETRE` | fenêtre d'allumage du nœud, `fuseau,début_h,fin_h,marge_s` ou `aucune` (REQUISE : l'absence se déclare) |
| `allumage` | `AGAGI_DEPORT_ALLUMAGE` | le geste humain qui allume le nœud, cité dans les refus (facultatif) |
| `ca_depuis` | `AGAGI_DEPORT_CA_DEPUIS` | namespace d'où copier la ConfigMap `registry-ca-bundle` au premier build (facultatif) |

Les gabarits suivis (`deploy/nexus/*.yaml`, `runner/build-job.yaml`) portent des `__PLACEHOLDERS__` rendus au moment
de l'application ou du build ; un `kubectl apply -f deploy/nexus/` sur les gabarits BRUTS échoue bruyamment (nom
invalide), c'est voulu. `IMAGE.json` ne porte que le chemin de l'image et son digest, jamais l'hôte. Une garde de test
refuse le retour d'une adresse privée écrite en dur dans le code et les gabarits du déport. L'adresse reste dans
l'historique déjà poussé (commits du 2026-09-26) : la réécrire serait une décision de robla, déconseillée par Master 2
pour une adresse privée non routable.

La commande est toujours `-m <module> [args]` (python implicite). Une commande par Job : un balayage de
seeds se découpe en N Jobs, pas en un pool de processus dans un pod (plafond 2 CPU par conteneur ; quota du
namespace = 8 CPU de requêtes, soit 8 Jobs à `--req-cpu 1` en parallèle — au-delà, la soumission refuse
« quota plein » et ne laisse rien derrière elle). Une variable pour le runner passe par `--env CLE=VALEUR`
(répétable), et SEULEMENT ainsi : le pod n'a que l'environnement de l'image, `local` un environnement système
minimal ; les deux publient les variables déclarées dans le MANIFEST.

## Garanties — et comment chacune peut échouer

1. **Le code qui tourne est celui du sha.** Il arrive comme dépôt git SUPERFICIEL (profondeur 1) poussé par
   `kubectl exec` ; `remote_entry` refuse (code 86 et `REFUS.json`, rien n'a tourné) si HEAD ≠ sha, si
   l'arbre n'est pas propre, ou s'il n'y a pas de `.git`. N'importe quel commit LOCAL est déportable — pas besoin qu'il soit
   poussé. Pourquoi pas `git archive` : sur la batcave, `core.autocrlf=true` vient de la config SYSTÈME de
   Git for Windows et `git archive` l'applique — le pod aurait reçu des sources en CRLF (mesuré). Pourquoi
   un vrai `.git` : les runners tamponnent leur provenance par git (`tools/preregister.provenance`, P2.68 ;
   `src/seed_ai/harness`) — sans lui, un run déporté publierait `git_sha: None`. ⚠️ Seuls les fichiers
   SUIVIS au sha voyagent : une entrée non suivie de la batcave (HoF famine, base kuzu, `agent_states/`)
   n'existe pas dans le pod — et plusieurs chargeurs rendent une liste VIDE sur fichier absent. La soumission
   liste les entrées non suivies de `data/` ; elle ne peut pas savoir si le runner les lit. Une donnée
   d'entrée d'un run se committe (ou se publie par hash).
2. **Aucun secret dans le dépôt.** Le pod n'a besoin ni de GitHub ni d'un jeton ; le seul identifiant est le
   kubeconfig de la batcave (`~/.kube/config`), désigné par la configuration hors dépôt (clé `contexte`).
3. **Les sorties sont déduites, pas déclarées.** Empreinte sha256 et horodatage de l'arbre avant et après :
   tout fichier créé, modifié ou RÉÉCRIT À L'IDENTIQUE est une sortie (hors `.git/`, caches,
   `runs/leases/`) — une reproduction exacte d'un résultat committé est attestée, pas invisible. Une écriture
   HORS de l'arbre (chemin absolu, répertoire temporaire) n'est pas vue : « aucune sortie » est alors crié,
   pas tu. Les racines `AGAGI_*ROOT` (qui déplaceraient les écritures) ne sont jamais transmises au runner.
   Au rapatriement, un MANIFEST absent, de schéma étranger, d'un autre sha/job/point d'entrée, un fichier
   absent, altéré ou non listé fait REFUSER le tout.
4. **Rien n'est écrasé, rien n'est perdu.** Une sortie absente localement est copiée ; identique, laissée ;
   différente d'un fichier SUIVI et PROPRE, elle le remplace (git garde l'ancien) ; différente d'un fichier non
   suivi ou modifié : CONFLIT, rien n'est installé, et la sortie vérifiée est CONSERVÉE sous
   `runs/deport/<job>/sortie_non_installee/` (le pod est alors libéré : la donnée est en sûreté). Journaux
   et MANIFEST vont dans `runs/deport/<job>/` (ignoré par git) ; les `results/*.json` à leur chemin, à
   committer par l'auteur.
5. **La limite CPU est celle du cgroup.** `remote_entry` lit `/sys/fs/cgroup/cpu.max` (v2, repli v1) et pose
   `OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS` et `AGAGI_CPU_LIMIT` dessus. `os.cpu_count()` rend l'HÔTE (16 sur
   nexus pour une limite de 2). Contenu illisible → source `illisible`, jamais « pas de limite ».
6. **Le coût est publié.** MANIFEST : durée murale, CPU user/sys des enfants (`cpu_mesure` dit la méthode :
   Linux compte tous les descendants attendus, Windows le fils direct seul — pas comparables terme à terme
   pour un runner multiprocessus), RSS max (Linux), charge de la MACHINE (`loadavg` de l'hôte sous Linux, %
   CPU système sur 1 s) au début et à la fin, nœud, image, versions.
7. **Un run ne monte AUCUN volume réseau — écart DÉCLARÉ au mandat, accepté par Master 2 le 2026-09-26 (P2.126).** Le pod garde ses sorties (emptyDir) et attend que la batcave les
   tire (`--attente-s`, 1 h, 60 s au moins) ; faute de rapatriement il sort en code 87, jamais en succès. Le mandat prévoyait
   un dépôt par renommage atomique sur le NFS atlas : il est RETIRÉ des pods, pour trois faits apportés par
   les sessions ELYSIUM le 2026-09-26 — (a) un volume `nfs:` déclaré dans un pod est monté `hard` (seul un PV
   peut porter `soft`), et un atlas à terre fige alors le pod puis le kubelet (incident du 01/09 : WAL kine
   8,9 Go, control-plane 3 h 50 à terre) ; (b) atlas est rétrogradé en cible de réplication copy-only
   (SIGIL-1764, crashes RAM, memtest non fait) ; (c) il était éteint ou planté ce jour-là, en pleine fenêtre
   d'éveil. Répliquer vers atlas se fera APRÈS rapatriement, hors du run (le répertoire
   `/elysium-data/agagi` est un geste admin sur le QNAP, à créer quand atlas sera revenu). La fonction de
   dépôt atomique de `remote_entry` (`--depot`, MANIFEST en dernier) reste, testée, pour ce jour-là. kuzu et
   sqlite vivent dans l'arbre de travail du pod.
8. **nexus n'est pas toujours là.** Fenêtre 08:00-00:00 Europe/Paris, extinction IPMI DURE à minuit, sans
   drain (`config/cluster_nodes.yaml` d'ELYSIUM) ; robla l'éteint aussi par intermittence. Toute soumission
   REFUSE si le nœud n'est pas Ready (voie d'allumage nommée : bridge-api « /power nexus on », SIGIL-1611,
   jamais appelée par l'outil) ou si `deadline + attente + marge` ne tient pas avant 23:45 ; le build
   d'image aussi. La fin d'un Job échoué se lit sur ce qui est ARRIVÉ AU POD, jamais sur l'état actuel du
   nœud : `preempte`, `noeud_perdu`, `evince`, `delai_depasse`, `oom`, `refus_entree`, `non_rapatrie`,
   `sources_non_recues`, `pod_disparu`, sinon `inconnu` — preuves brutes rendues avec. Un échec du RUNNER,
   lui, n'y arrive jamais : le pod attend qu'on tire sa sortie, et le code du runner est dans le MANIFEST.
   Rien ne se relance tout seul.
9. **Les pods de run sont préemptibles.** `elysium-disposable` vaut -100 (sous le défaut 1000) : tout pod
   ordinaire peut préempter un run, dont la sortie (emptyDir) est alors perdue — état `preempte`. Accepté
   pour des cellules courtes ; un run de plusieurs heures se découpe, ou demande à ELYSIUM une autre classe.
10. **Refus d'admission muets, rendus bruyants.** Un pod refusé par Kyverno laisse un Job `0/1` sans pod et
   sans événement (ELYSIUM image-ci README, Iron Rule 5) : `remote.py` exige un pod dans les 30 s (quota
   plein compris), RETIRE alors le Job (sinon il démarrerait plus tard sans sources), et refuse AVANT
   soumission des ressources que la LimitRange rejetterait. L'image est gardée sur le CONTEXTE complet du
   sha (Dockerfile, contraintes, requirements, gabarit de build) ; un sha qui ne porte pas encore
   `deploy/nexus/runner/` n'est comparé que sur requirements.txt, et la soumission le dit.

## État mesuré (2026-09-26)

* Namespace appliqué par robla (`kubectl apply -f deploy/nexus/`, avant que les manifestes deviennent des gabarits ;
  leur rendu depuis la configuration est identique à l'état du cluster : `kubectl diff` vide) ; image construite par
  `python -m tools.jobs.remote image --sha 019dc34b` : Kaniko en 80 s sur nexus, sans OOM, tag
  `py3.13.12-39fe2c9bda57`, digest dans `deploy/nexus/runner/IMAGE.json`.
* Premier run déporté : `evo011_preflight --smoke` au sha da09f7a1, 64 s de bout en bout (préparation du dépôt au
  sha, 19,6 Mo envoyés, tirage d'image, run, rapatriement vérifié). Dans le pod : `cpu.max` = 2 CPU lus au cgroup,
  `os.cpu_count()` = 16 (l'hôte), threads posés à 2.
* Image reconstruite après la sortie de l'adresse du dépôt (7481e15e) : digest DIFFÉRENT de la première pour un
  contexte de build identique — une construction Kaniko n'est pas reproductible bit à bit ; un run se désigne par le
  DIGEST d'`IMAGE.json`, jamais par le tag. Témoin relancé sur cette image : identique (EDR-DEPORT-NEXUS-TEMOIN, tour 4).
* La ConfigMap `registry-ca-bundle` du namespace est une COPIE de celle d'elysium-brain : si la CA mkcert du
  registre tourne, la re-copier (sinon build et tirage échouent en TLS) — P2.127.

## Surveillance d'un run

`python -m tools.jobs.remote surveiller` sonde le namespace en LECTURE SEULE (toutes les 60 s) et rend 3 à la première
anomalie : Job échoué, conteneur OOMKilled, pod Pending depuis plus de 10 min ; 4 si le cluster est illisible ; 0 à
l'échéance. Il ne relance, ne supprime ni ne modifie rien — la relance appartient à qui a scellé le run. Une EXCLUSION
se DÉCLARE par motif de nom (`--ignorer=-p2134-` pour des builds d'essai) : ses anomalies ne réveillent personne mais
restent COMPTÉES sur chaque ligne d'état (« anomalies ignorées=N ») — une exclusion commode non comptée serait un angle
mort silencieux (E32). Contrôle positif réel, involontaire : le 2026-09-26 la sonde a attrapé les deux builds d'essai
OOMKilled de P2.134 avant qu'on déclare leur motif. Écrire le motif avec `=` (`--ignorer=-p2134-`) : un motif qui
commence par un tiret serait lu comme une option.

## Ressources d'un Job

* Mémoire : la limite est TOUJOURS un palier déclaré — 4, 8, 16, 20, 24, 28 ou 32 Gi (`--mem`, défaut 4 Gi) — et la
  requête vaut au plus limite / 4 (défaut : exactement limite / 4). Réserve d'ELYSIUM : des pods BURSTABLE, jamais
  Guaranteed ; un pod garanti à 32 Gi ferait évincer les services du nœud à notre place. Paliers 28 et 32 Gi fiables
  seulement quand `nexus-ollama` n'a pas de gros modèle chargé.
* Le plafond se LIT dans les LimitRange du namespace à la soumission (le max le plus restrictif gagne) ; aucun max
  lisible = refus. La limite mémoire MESURÉE dans le cgroup du pod est publiée dans le MANIFEST, à côté du digest.
* CPU : `--cpu` (défaut 2), requête `--req-cpu` (défaut 1). Les threads sont posés depuis le cgroup (`cpu.max`) sauf
  si l'appelant en déclare : la déclaration prend alors TOUT le contrôle. Déclarer plus de threads que la limite CPU
  est SIGNALÉ à la soumission et publié (`sur_souscription` dans `soumission.json`), jamais refusé : c'est parfois
  l'objet de la mesure. Coût mesuré (cellule P4.18, sha afa4dac6, limite 2 CPU) : 16 threads = 499,8 s de CPU et
  253,3 s de mur, contre 87,0 s et 53,9 s à 2 threads — ×5,7 et ×4,7, pour des W appris identiques au bit.
* Issues d'un Job (`attendre`, `lire_fin`) : OOMKilled, Evicted, préemption et perte du nœud sont DISTINCTES et marquées
  `relancable` ; la relance reste un geste déclaré de qui a scellé le run.

## Choisir le lieu : batcave ou nexus

**Un run qui doit répliquer AU BIT des valeurs publiées sous Windows tourne sur la batcave. nexus sert aux mesures
NEUVES, comparées à elles-mêmes. Le nombre de threads est toujours publié** (MANIFEST : `cpu.threads_poses`,
`cpu.threads_source`).

Pourquoi — deux mesures, deux bibliothèques :

* numpy : la cellule du témoin (EDR-DEPORT-NEXUS-TEMOIN) est identique au bit entre les deux lieux, poids gelés comme
  en apprentissage.
* torch float32 : témoin de lieu de agagi-40 (2026-09-26, sha afa4dac6, cellule `b_zero` seed 2026 de P4.18, image
  digest `sha256:7c860b30…`). Les W appris sont identiques au bit entre nexus à 2 threads (cgroup) et nexus à 16 threads
  (déclarés), mais DIFFÈRENT au dernier bit de ceux de la batcave — torch 2.6.0+cpu Linux contre 2.6.0+cu124 Windows,
  même version, autre build. Les 12 âges de survie et toute la dose sont identiques partout. Le chemin cumulé
  `dW_abs_sum` diffère selon le lieu ET selon le nombre de threads : une somme de réductions dépend de leur ordre.
  Conséquence : P4.18, dont la règle exige la réplication au bit, tourne sur la batcave.

Unité de coût de ce témoin — lire avec sa charge, publiée dans chaque MANIFEST :

| lieu | threads | mur | CPU | charge au départ |
|---|---|---|---|---|
| nexus (limite 2 CPU) | 2 (cgroup) | 53,9 s | 87,0 s | loadavg 1,4 |
| nexus (limite 2 CPU) | 16 (déclarés) | 253,3 s | 499,8 s | loadavg 1,7 |
| batcave | défaut de la bibliothèque | 190,1 s | 157,6 s (fils direct seul) | CPU système 87 % |

La ligne batcave n'est PAS une unité libre : la machine était à 87 % de CPU au départ, et son CPU ne compte que le fils
direct (`GetProcessTimes`) quand nexus compte tous les descendants (`RUSAGE_CHILDREN`). Elle ne se compare pas à nexus
pour décider d'un lieu par le coût.

## Ce que le déport ne fait PAS

* Il ne choisit pas le lieu : `executer` va sur nexus, `local` sur la batcave ; aucun repli silencieux.
* Il ne relance rien tout seul (un run relancé change l'unité de coût ; la relance est un geste déclaré).
* Il ne tient pas le bail `kuzu` de la batcave : un pod est sa propre machine (bail local au pod).
* Il ne remplace pas la règle « un seul run lourd à la fois » sur la batcave ; sur nexus, plusieurs Jobs
  coexistent sous la ResourceQuota — publier la charge de début de run (MANIFEST) avec toute unité de coût.

## Écarts assumés aux normes ELYSIUM

* Build Kaniko DANS `elysium-agagi` et non `elysium-brain` (Σ-IMAGE-CI-NAMESPACE-FIXED) : le mandat
  interdit de rien créer hors du namespace dédié. Dette si la norme se durcit (elysium-8d, 2026-09-26).
* Criticité du namespace `standard` alors que les pods sont `disposable` : raison de DIMENSION (le palier
  `disposable` plafonne à 1 CPU / 2 Gi), pas de criticité.
* Le build tire le PyPI PUBLIC et non le miroir PyPI souverain d'ELYSIUM (en RFC1918, que la NetworkPolicy
  du build n'ouvre pas).
* Posé par `kubectl apply` hors du GitOps ELYSIUM : chaque objet porte `elysium.io/managed-by: agagi` et
  `elysium.io/source-repo` pour la carte de propriété (Σ-MANIFEST-MYCORHIZE, SIGIL-1762) ; verser les
  manifestes dans `gitops/` d'ELYSIUM (ou une Application ArgoCD) quand ce sera stable.

## Coordination

Avant toute création sur le cluster : prévenir les sessions ELYSIUM vivantes (règle du mandat). Le
préavis du 2026-09-26 a été relu par elysium-8d et elysium-91 (aucune objection au namespace ; atlas,
nexus, miroir PyPI et labels de propriété : faits repris ci-dessus).
