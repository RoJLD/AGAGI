---
id: REF-DEPORT-NEXUS
type: REF
title: "Déport des runs sur le cluster ELYSIUM (nœud nexus) — mode d'emploi et garanties"
status: active
---

## Pourquoi

Décision de robla (2026-09-26) : **les runs AGAGI tournent par défaut sur le cluster ELYSIUM, nœud nexus**
(15 CPU / 61,66 Gi allouables, relu le 2026-09-28), et la batcave reste libre — pour les sessions, et pour que l'unité de coût
d'un run ne soit plus mesurée sous la charge des autres (E12 appliqué au coût, payé trois fois le
2026-09-22). Seul un Job témoin existait (2026-09-24, mémoire `nexus-cluster-witness-job`).

## Ce qui existe

| Pièce | Où | Rôle |
|---|---|---|
| namespace (nom configuré) | `deploy/nexus/00-03*.yaml` (GABARITS, rendus par `remote.py namespace`) | normes `elysium-*` : palier LimitRange `ml-heavy` (12 CPU / 32 Gi par conteneur, accordé par ELYSIUM le 2026-09-26 ; il REMPLACE `standard`, retiré dans le même geste), default-deny (DNS vers kube-dns seul, P2.127) + egress du seul build, ResourceQuota (requests 8 CPU / 24 Gi, limits 16 CPU / 40 Gi, 16 pods, 100 Jobs, 20 ConfigMaps) |
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
| `namespace` | `AGAGI_DEPORT_NAMESPACE` | namespace dédié (requis). ⚠️ Nom NON libre vis-à-vis d'ELYSIUM : le palier ml-heavy ne tient que parce que la boucle manuelle du README des LimitRange ELYSIUM saute ce namespace par son NOM (`ML_HEAVY_NS`, PR ELYSIUM #1301) — le label `limitrange-tier` n'y joue aucun rôle. Sous un autre nom, faire d'abord ajouter ce nom côté ELYSIUM ; sinon la boucle y repose `standard` (4 Gi) et la soumission REFUSE bruyamment tout palier > 4 Gi |
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
seeds se découpe en N Jobs, pas en un pool de processus dans un pod. Parallélisme, borné par TOUS les postes du quota :
aux défauts (`--cpu 2`, `--req-cpu 1`, `--mem 4Gi`), 8 Jobs (requests.cpu 8) ; dès `--mem 8Gi`, limits.memory 40 Gi lie
— 5 Jobs à 8 Gi, 2 à 16 ou 20 Gi, UN seul à 24-32 Gi (sérialisation voulue par ELYSIUM) ; au-delà de `--cpu 2`,
limits.cpu 16 lie ; count/jobs.batch 100 compte aussi les Jobs terminés pendant leur TTL de 24 h ; un build Kaniko
consomme le même quota. Un pod qui dépasse À LUI SEUL un `hard` (ex. `--req-cpu 10 --cpu 10` sous requests.cpu 8) est REFUSÉ
avant création : il ne serait jamais admis. Au-delà du quota LIBRE, la soumission refuse « quota plein » et ne laisse
rien derrière elle. Une variable pour le runner passe par `--env CLE=VALEUR`
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
   soumission des ressources que le `max` de la LimitRange rejetterait ou qu'aucun quota vide n'admettrait (plafonds
   et `hard` LUS sur le cluster, jamais supposés). L'image est gardée sur le CONTEXTE complet du
   sha (Dockerfile, contraintes, requirements, gabarit de build, script d'empreinte) ; un sha qui ne porte pas TOUS
   ces fichiers n'est comparé que sur requirements.txt, et la soumission le dit. ⚠️ Le tag hache les OCTETS
   bruts de ces cinq fichiers : toute retouche, COMMENTAIRE COMPRIS, change le tag, et la garde refuse ensuite toute
   soumission à un sha ultérieur jusqu'à une reconstruction. Un commentaire à corriger dans l'un d'eux attend donc la
   prochaine reconstruction PLANIFIÉE de l'image.

## État mesuré (chaque puce porte sa date)

* 2026-09-26 : namespace appliqué par robla (`kubectl apply -f deploy/nexus/`, avant que les manifestes deviennent des
  gabarits ; leur rendu depuis la configuration était alors identique à l'état du cluster : `kubectl diff` vide) ; image construite par
  `python -m tools.jobs.remote image --sha 019dc34b` : Kaniko en 80 s sur nexus, sans OOM, tag
  `py3.13.12-39fe2c9bda57`, digest dans `deploy/nexus/runner/IMAGE.json`.
* 2026-09-26 : premier run déporté, `evo011_preflight --smoke` au sha da09f7a1, 64 s de bout en bout (préparation du dépôt au
  sha, 19,6 Mo envoyés, tirage d'image, run, rapatriement vérifié). Dans le pod : `cpu.max` = 2 CPU lus au cgroup,
  `os.cpu_count()` = 16 (l'hôte), threads posés à 2.
* 2026-09-26 : image reconstruite après la sortie de l'adresse du dépôt (7481e15e) : digest DIFFÉRENT de la première pour un
  contexte de build identique — une construction Kaniko n'est pas reproductible bit à bit ; un run se désigne par le
  DIGEST d'`IMAGE.json`, jamais par le tag. Témoin relancé sur cette image : identique (EDR-DEPORT-NEXUS-TEMOIN, tour 4).
* 2026-09-26 : la ConfigMap `registry-ca-bundle` du namespace est une COPIE de celle d'elysium-brain : si la CA mkcert du
  registre tourne, la re-copier (sinon build et tirage échouent en TLS) — P2.127.
* 2026-09-26, 19:16 UTC : palier ml-heavy APPLIQUÉ par robla (`python -m tools.jobs.remote namespace --appliquer`,
  après `kubectl diff` et un dry-run serveur) ; `elysium-limitrange-standard` supprimée dans le même geste ; une seule
  LimitRange dans le namespace, quota 24 / 40 Gi, `kubectl diff` vide ensuite.
* 2026-09-28 : gabarits de P2.127 (labels de propriété AGAGI sur les cinq objets, annotation derived-from, DNS restreint
  à kube-dns) écrits dans le dépôt et NON appliqués : `kubectl diff` non vide jusqu'au prochain `namespace --appliquer`
  par robla (appliqués le 2026-10-13, ci-dessous).
* 2026-09-28 (P2.134, `results/deport_p2134_reproductibilite.json`, heures lues au statut des Jobs, UTC) : un build
  Kaniko devient REPRODUCTIBLE au bit avec le Dockerfile NETTOYÉ (journaux apt/dpkg et cache ldconfig retirés ; pip
  `--no-compile` puis `.pyc` à empreinte de hash) ET `--reproducible` — 4 builds sur 4 au même digest, à deux paliers
  (16 et 8 Gi) et 8 min 09 s d'écart. Ablation : `--reproducible` seul, Dockerfile publié → deux digests (couches apt et
  pip) ; le nettoyage seul (2026-09-26) → même contenu, couches différentes. 8 Gi suffisent (2 sur 2) ; le pic réel
  n'est PAS mesuré (échantillon toutes les 15 s = minorant). Non testé : un autre jour — git vient d'apt sans version
  épinglée. Adoption décidée par Master 2 (message du 2026-09-28, consigné dans P2.134), APRÈS P4.18 (elle change le
  contexte haché donc l'image) : le digest devient l'IDENTITÉ citée par un record, une empreinte de contenu publiée à
  côté comme DIAGNOSTIC — ce qui RÉVISE la proposition validée le 2026-09-26, où l'empreinte valait équivalence.
* 2026-09-28, après P4.18 : P2.134 ADOPTÉE dans le dépôt — Dockerfile nettoyé, `--reproducible` et `--cache=false`
  dans le gabarit (le cache resservirait des couches d'un autre jour : c'est la RECETTE qui doit garantir le digest),
  kaniko à 8 Gi pour 2 Gi, et une dernière étape qui écrit l'empreinte de contenu dans l'image
  (`deploy/nexus/runner/empreinte_contenu.py` : zones `python` = /usr/local et `systeme`, chemins injectés par le
  runtime du build exclus), IMPRIMÉE dans le journal du build et reportée par `remote.py` dans `IMAGE.json` (source
  « journal du build <Job> » : deux images se comparent AVANT tout run) ; `remote_entry` la publie aussi dans chaque
  MANIFEST (`image_empreinte`, `absente` hors image).
  La nouvelle image, son digest et la vérification de sa reproductibilité par le chemin de PRODUCTION sont au commit
  qui écrit `IMAGE.json`.
* 2026-09-28 au soir (`results/deport_p2134_adoption.json`, heures lues au statut des Jobs) : nouvelle image construite
  par le chemin de PRODUCTION (`image --sha ea09dbb9`, 19:46:48Z → 19:48:58Z), puis RECONSTRUITE (`--reconstruire`,
  19:49:37Z → 19:51:36Z) : MÊME digest `sha256:d5341acf…` et MÊMES empreintes (python : 39 411 entrées ; systeme : 7 194).
  Le digest diffère de celui des essais du matin parce que le Dockerfile adopté ajoute l'étape d'empreinte — autre image.
  Témoin `evo011_preflight --smoke` sur cette image : contre les trois côtés du tour 4 d'EDR-DEPORT-NEXUS-TEMOIN (batcave,
  nexus ×2, ancienne image), un SEUL écart hors `elapsed_s` — `git_sha`, la provenance, qui diffère par construction ;
  aucun nombre ne change. Le MANIFEST porte l'empreinte (`image_empreinte`). Reste : une reconstruction un AUTRE jour.
* 2026-10-13 (P2.127, `results/deport_p2127_validation.json`, heures lues au statut des Jobs) : gabarits APPLIQUÉS par
  robla entre 17:00 et 17:28 (heure de Paris), `kubectl diff` vide à 17:28:13. Sonde : deux Jobs de l'image runner, A sans
  le label de build, B avec. AVANT (12:20Z) : A — DNS OK, 443 en échec, DNS DIRECT vers un résolveur public OK ; B — 443 OK,
  DNS direct OK : le DNS sortait de partout. APRÈS, en régime établi (20 s d'attente dans le pod avant de sonder) : A —
  kube-dns OK, 443, 80, 22 et DNS direct en ÉCHEC ; B — 443 OK, 80, 22 et DNS direct en ÉCHEC. ⚠️ **Course au
  démarrage** : sans attente, les PREMIÈRES sondes d'un pod passent parfois (A a ouvert 443 et 80 à 17:34), jamais les
  dernières — kube-router pose ses règles après le démarrage du pod ; s'y ajoutent ~1-2 min de propagation après un
  apply. Conséquences : une validation de NetworkPolicy attend dans le pod avant de sonder, et la restriction ne garantit
  rien pendant les premières secondes d'un pod.
* 2026-10-13 : build de contrôle SOUS DNS restreint (`image --sha HEAD --reconstruire`, Job 15:39:18Z → 15:41:28Z) :
  réussi (PyPI, apt en https, push) — mais AUTRE digest, `sha256:cd8b9f34…`, pour le MÊME contexte que d5341acf :
  **P2.134 (ii) ÉCHOUE à 15 jours**. L'empreinte localise les deux zones (python : 39 411 → 39 488 entrées ; systeme :
  7 194 entrées, hash différent) ; 15 dépendances Python TRANSITIVES non épinglées ont bougé, et perl-base côté apt ;
  numpy, scipy, torch, kuzu et psutil sont identiques (épinglés). `IMAGE.json` RESTE sur d5341acf : τ de P4.19 y a été
  mesuré, R3 et le retest de P4.18 y tournent. L'image cd8b9f34 n'est référencée par aucun run (tag `-r1c7f`, cf.
  Registre d'images). Un constraints COMPLET (les 82 versions du freeze de d5341acf) est préparé hors suivi ; la bascule
  — un seul build — vient APRÈS R3 et le retest de P4.18.
* 2026-10-13 : le `python` des sessions est un 3.14 SANS tzdata : `executer`, `soumettre` et `image` REFUSENT (« fuseau
  illisible »). Les lancer avec Python 3.13. Depuis P2.173 (2026-10-14), le refus nomme l'interpréteur fautif et le
  remède, et distingue les deux causes par la base de fuseaux de CET interpréteur : vide → installer tzdata ou changer
  d'interpréteur ; pleine → corriger le `tz` de la fenêtre.

## Surveillance d'un run

`python -m tools.jobs.remote surveiller` sonde le namespace en LECTURE SEULE (toutes les 60 s) et rend 3 à la première
anomalie : Job échoué, conteneur OOMKilled, pod Pending depuis plus de 10 min ; 4 après 3 lectures ratées
CONSÉCUTIVES (`--echecs-max`) ; 0 à l'échéance. Une lecture ratée isolée ne l'arrête pas — le 2026-09-26 à 20:25, un
seul délai de connexion à l'API avait mis fin à la surveillance, le cluster répondait 40 s plus tard — mais elle est
imprimée sur-le-champ et le total figure sur chaque ligne (« lectures ratées=N »). La ligne d'état publie aussi la
mémoire du quota (`req.mem`, `lim.mem`) et `lim.cpu` : aux défauts, requests.cpu et limits.cpu lient à 8 Jobs ; dès
`--mem 8Gi`, c'est limits.memory (40 Gi). Il ne relance, ne supprime ni ne modifie rien — la relance appartient à qui a scellé le run. Une EXCLUSION
se DÉCLARE par motif de nom (`--ignorer=-p2134-` pour des builds d'essai) : ses anomalies ne réveillent personne mais
restent COMPTÉES sur chaque ligne d'état (« anomalies ignorées=N ») — une exclusion commode non comptée serait un angle
mort silencieux (E32). Contrôle positif réel, involontaire : le 2026-09-26 la sonde a attrapé les deux builds d'essai
OOMKilled de P2.134 avant qu'on déclare leur motif. Écrire le motif avec `=` (`--ignorer=-p2134-`) : un motif qui
commence par un tiret serait lu comme une option.

**Accrocs de l'API pendant un run (P2.167, 2026-10-13).** L'envoi des sources, `attendre` et `rapatrier` rejouent un appel
idempotent tant que l'API du cluster est coupée, au plus 3 fois DE SUITE (le plafond de la sonde), chaque accroc imprimé et
compté dans `runs/deport/<job>/accrocs_api.json`. Au-delà, ils abandonnent en disant jusqu'à quand le pod garde la sortie
(`--attente-s` après la fin du runner) et quelle commande relancer : `python -m tools.jobs.remote rapatrier <job>`. À
l'état `pret`, `attendre` imprime l'heure LIMITE du rapatriement. Un pod resté en Running après la fin du runner n'est
PAS une sortie perdue : si le rapatriement a eu lieu mais que le marqueur de libération n'a pas pu être posé, la sortie est
en sûreté et le pod sortira en 87 à l'échéance.

**Codes de sortie d'`executer` (P2.168, 2026-10-14).** Le code du RUNNER passe tel quel quand le run a tourné et que sa
sortie est installée ; tout autre dénouement a SON code, hors des codes d'un runner usuel (0, 1, 2 d'argparse), et le
journal le dit sur une ligne `[remote] <libellé> (<code>)` :

| code | libellé | ce qui s'est passé | quoi faire |
|---|---|---|---|
| 85 | `REFUS` | refusé AVANT la soumission (fenêtre, garde d'image, quota, nœud éteint, configuration, arguments du CLI) : rien n'a tourné, aucun Job ne reste | corriger, relancer |
| 86 | `POD : remote_entry a refusé avant exécution` | refus DANS le pod (sha, archive, commande) : rien n'a tourné | lire `REFUS.json` |
| 87 | `SORTIE PERDUE` | fenêtre de rapatriement passée ou pod disparu | relancer le run |
| 88 | `FIN SANS SORTIE` | le Job a fini sans sortie prête — l'état (`oom`, `evince`, `preempte`, `noeud_perdu`, `delai_depasse`…) et `relancable` sont imprimés | selon l'état |
| 89 | `ABANDON après la soumission` | API injoignable au-delà du plafond, sortie corrompue ou en conflit, attente échue : le run a PU tourner | `rapatrier <job>` ou `installer`, jamais relancer à l'aveugle |

Seul le 85 commence par « [remote] REFUS » : un script de vague qui cherche ce texte continue d'y lire le refus local.
`image` suit la même table : 88 pour un build en échec (OOMKilled nommé) ou encore actif après son échéance, 89 pour un
digest illisible (le build a tourné, l'image a pu être poussée sans qu'`IMAGE.json` la nomme).
Un runner qui rend LUI-MÊME un code de 85 à 89 est SIGNALÉ (« le RUNNER a rendu … ») et jamais réécrit — le MANIFEST
tranche. Avant P2.168, un refus local rendait 2, comme un argparse de runner en échec, et une fin d'infrastructure rendait
1, comme un runner en échec : le code seul ne les distinguait pas.

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
* Le Job de BUILD (`remote.py image`) ne passe ni par les paliers ni par la réserve limite / 4 : ses ressources viennent
  du gabarit HACHÉ `runner/build-job.yaml` (kaniko : requête 2 Gi pour une limite de 8 Gi, soit limite / 4, depuis
  l'adoption de P2.134 ; 2 Gi pour 4 Gi avant). Un build échoué dit sa cause LUE dans ses statuts (OOMKilled
  NOMMÉ, délai du Job, init de contexte). L'attente locale se lit dans le gabarit (son échéance + 120 s) : un build
  encore actif au-delà est RETIRÉ, après lecture de sa cause et de ses logs, et c'est dit. À chaque (re)construction,
  `IMAGE.json` publie les heures du build lues sur le Job, avec leur source, à côté de l'heure de la machine qui soumet
  (l'IMAGE.json du 2026-09-26 n'en porte pas encore).

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
  Conséquence : P4.18, dont la règle exige la réplication au bit, tourne sur la batcave. Évidence suivie :
  `results/s2_bassin_fragility_temoin_lieu.json` (depuis 838446e6, le commit du record P4.18, 2026-09-28) — les trois
  lieux et leurs Jobs, l'image, la plateforme, les W comparés au bit (`W_entre_lieux_au_bit`) et leur écart max
  (2,4e-7), les empreintes ; aucune adresse. La phrase « évidence NON publiée » qui vivait ici était PÉRIMÉE dès son
  écriture (P2.150, close).

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
* Criticité du namespace `standard` alors que les pods sont `disposable` : label gardé, comme le README ELYSIUM le
  prescrit pour elysium-ml (qui porte en fait `vital` sur le cluster, relu le 2026-09-28), pour les politiques CNCE de
  priorityClass. La DIMENSION ne vient pas de ce label : la LimitRange effective est ml-heavy, posée
  hors de la boucle manuelle d'ELYSIUM, qui saute ce namespace par son NOM (cf. la clé `namespace`).
* Le build tire le PyPI PUBLIC et non le miroir PyPI souverain d'ELYSIUM (en RFC1918, que la NetworkPolicy
  du build n'ouvre pas).
* Posé par `kubectl apply` hors du GitOps ELYSIUM : les gabarits portent les quatre labels de propriété de
  `LABELS_PROPRIETE` (`elysium.io/managed-by`, `elysium.io/source-repo`, `elysium.io/owner`, `app.kubernetes.io/part-of`)
  pour la carte de propriété (Σ-MANIFEST-MYCORHIZE, SIGIL-1762) — la copie de LimitRange comprise, qui ne se déclare
  plus `elysium-core` et dit sa source par l'annotation `elysium.io/derived-from: SIGIL-1627` (P2.127, accord
  d'elysium-91 et d'elysium-8d le 2026-09-28 : aucun lecteur ELYSIUM de ces labels sur une LimitRange ; posés sur le
  cluster par robla le 2026-10-13) ; verser les
  manifestes dans `gitops/` d'ELYSIUM (ou une Application ArgoCD) quand ce sera stable.
* DNS restreint à kube-dns (P2.127, même accord) : bloc repris d'opa-ingress, UN élément `to:` qui porte
  namespaceSelector ET podSelector. VALIDÉ le 2026-10-13 en régime établi (cf. État mesuré) : un pod de l'image runner
  SANS le label de build résout `pypi.org` et `kubernetes.default` par kube-dns et ÉCHOUE à ouvrir `pypi.org:443` comme à
  joindre un résolveur public (contrôle négatif du default-deny) ; AVEC le label de build, le 443 passe et le DNS direct
  reste fermé — sauf pendant les premières secondes d'un pod (course au démarrage). kube-dns : relu le 2026-10-13, TROIS endpoints prêts (coredns sur
  orbit-01, coredns-elysium sur orbit-03 et sur nexus), tous `k8s-app=kube-dns`, donc tous couverts par la règle ; la
  « réplique unique » du 2026-09-28 n'est plus vraie.

## Registre d'images : conservation et journal de suppression

**Le registre** (réponse d'elysium-f8, 2026-10-13) : un conteneur `registry:2` sur l'HÔTE orbit-01, hors de k8s ; ni
garbage-collect ni rétention (`storage.delete` désactivé) ; AUCUNE sauvegarde ; stockage sur le disque RACINE d'orbit-01
(serveur k3s, 89-90 % plein). Chaque build au contenu neuf y ajoute ~0,5 Go : reconstruire au strict nécessaire. ELYSIUM
a pris la durabilité du registre dans son chantier P3 (copie hors site, restauration prouvée). L'image de production
`sha256:d5341acf…` est ARCHIVÉE hors registre sur la batcave (disposition OCI, 11 blobs vérifiés par leur sha256, manifest
relu = d5341acf ; `repousser.py` livré avec l'archive, NON exercé contre un registre) — c'est l'archive, pas le registre,
qui fait référence.

**Règle de protection** (Master 2, 2026-10-13, amendée le soir même) : une image est PROTÉGÉE si un run cité par un
résultat suivi ou par un record a tourné DESSUS, ou si elle porte une mesure consignée nulle part ailleurs. Une image qui
n'est qu'une preuve de BUILD — digest, couches et freeze déjà consignés dans un JSON suivi — est SUPPRIMABLE. Le journal
ci-dessous ne protège rien : y citer un digest au statut « SUPPRIMÉ » ne fait pas de l'image une dépendance (la première
forme de la règle, « tout digest cité par un JSON suivi », protégeait ce qu'on consignait au moment de le supprimer).
Toute suppression exige la phrase d'accord de robla dans la session qui la fait ; elle se fait PAR DIGEST, sans retrait
de tag sur une image protégée ni `--delete-untagged`.

**Inventaire du 2026-10-13** (lecture seule : catalogue, tags, manifests ; dépôts dont le nom contient « agagi » —
aucun dépôt de cache Kaniko AGAGI ; citations cherchées dans tous les fichiers suivis de d1 `0af0fa49`, de toutes les
branches et sur le disque de tous les worktrees). Octets « propres » = blobs qu'aucune autre image AGAGI ne porte, un
MAJORANT de ce que libère une suppression (le partage avec les dépôts non-AGAGI n'est pas vu) ; total AGAGI 3,67 Gi.

| digest | tags | statut | pourquoi | propres |
|---|---|---|---|---|
| `d5341acf…` | runner `py3.13.12-1c77aaaf3cf1`, `-r3bdf` | PROTÉGÉE | production : τ de P4.19, R3, retest de P4.18 | 0 Mi |
| `7c860b30…` | runner `py3.13.12-2bf24b9ccf41` | PROTÉGÉE | témoin de lieu de P4.18, témoin du déport tour 4 | 459 Mi |
| `a1d6e4eb…` | runner `py3.13.12-39fe2c9bda57` | PROTÉGÉE | témoin du déport tours 1-3, premiers runs du 26/09 | 459 Mi |
| `cf08cef4…` | essais `p2134-r1-*` (4) | à laisser | preuve de build ; ne libère RIEN (blobs tous partagés) | 0 Mi |
| `cd8b9f34…` | runner `py3.13.12-1c77aaaf3cf1-r1c7f` | supprimable si manque d'espace | preuve de build de P2.134 (ii), consignée dans `results/deport_p2127_validation.json` (digest, empreintes, freeze complet, couches) | 461 Mi |
| `9f6e2d24…`, `5caa5ff0…` | essais `p2134-r3-0-a787`, `-r3-1-26fa` | supprimable si manque d'espace, APRÈS consignation du freeze | ablation C de P2.134 : digest et couches dans `results/deport_p2134_reproductibilite.json`, freeze PAS encore consigné | 456 Mi chacune |
| `536dbfcd…`, `d5d96dec…` | essais `p2134-r2-0-d281`, `-r2-1-efcf` | SUPPRIMÉES le 2026-10-13 (journal) | builds d'essai du 2026-09-26 (17:01 UTC), cités nulle part ; résultat écrit dans P2.134 (3) | ≤ 920 Mi à deux |

**Journal de suppression** (une ligne par geste d'ELYSIUM : date et heure, digest, tags, session qui l'a fait, accord de
robla) :

* 2026-10-13T20:12:27Z — DELETE par digest via l'API du registre, HTTP 202, par la session Arboreal (ELYSIUM), accord de
  l'Architecte (robla) rapporté par Arboreal : `elysium/agagi-runner-essais@sha256:536dbfcdd161be6e991655fe16f47149fe3fa4cafa882a11d8050a4f906d6b54`
  (tag `p2134-r2-0-d281`) et `elysium/agagi-runner-essais@sha256:d5d96decc0b3b2d703b405df2249fb2fd5727905312f510ca6d20bbcdafb7e41`
  (tag `p2134-r2-1-efcf`). `registry garbage-collect` SANS `--delete-untagged` à 20:13:05–20:13:06Z. Arboreal : pull réel de
  `d5341acf…` depuis nexus à 20:13:40Z, complet ; une copie du registre faite AVANT le GC (20:10:54Z) est gardée sur nexus,
  donc une restauration reste possible. Vérifié ensuite par INFRA-NEXUS (lecture seule, 20:14Z et après) : les deux
  manifests rendent 404, comme un digest inventé (contrôle positif du 404) ; 7 images AGAGI restantes, 11 tags, et leurs 65
  blobs (configs et couches) répondent tous avec la taille attendue — le GC n'a ramassé aucun blob partagé.

## Coordination

Avant toute création sur le cluster : prévenir les sessions ELYSIUM vivantes (règle du mandat). Le
préavis du 2026-09-26 a été relu par elysium-8d et elysium-91 (aucune objection au namespace ; atlas,
nexus, miroir PyPI et labels de propriété : faits repris ci-dessus).
