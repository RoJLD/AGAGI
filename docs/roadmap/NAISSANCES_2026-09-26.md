# Prompts de naissance — flotte du 2026-09-26

Décisions de robla (2026-09-26, matin) : **gel de la méthodologie** à ce qui bloque un run, un seul worker Dette
(agagi-32) ; **science** dans l'ordre P4.18 → P4.19 → Task 2 du harnais ; **runs sur le cluster nexus par défaut**,
batcave seulement si aucun cluster ou machine n'est disponible ; **AGAGI-front clos** (ses deux fichiers étaient déjà
dans d1), le front vit dans `frontend/` de d1 ; les sessions sont ouvertes **par robla dans VS Code** (tmux absent),
Master 2 fournit les prompts et coordonne par messages inter-sessions ; **agagi-88 est l'intégrateur** (push au sha
exact, sur ordre de robla). Chaque bloc ci-dessous se colle tel quel comme premier message d'une session neuve.

## Normes communes (reprises dans chaque prompt)

```
NORMES COMMUNES (arbre PARTAGÉ, feat/d1-prod-pairing) :
- Fetch d'abord ; travailler dans un worktree TEMPORAIRE : git worktree add .worktrees/<nom> -b tmp/<nom> feat/d1-prod-pairing.
- Un commit = un run lourd : un seul à la fois sur la machine ; python -m tools.jobs.doctor avant tout run ; toute simulation
  de monde tient le bail kuzu (tools.jobs.run.hold).
- Commits path-scoped (git commit -F msg -- <chemins>), jamais nu, jamais --no-verify ; message SANS backticks.
- Avant d'éditer un fichier partagé : check_staged_authorship.snapshot(...) ; juste AVANT le commit : verify(...) ET
  disque == contenu que TON script a produit (octet pour octet) ; lire le diff stat contre le delta attendu (P2.122).
- Un numéro de backlog s'alloue à l'ÉCRITURE (refus s'il existe sur disque OU dans l'index) ; jamais citer une balise
  <!-- count:… --> littéralement dans un .md (la porte 8 la compte).
- Tests des DEUX côtés (torch / sans torch, Windows / POSIX) ; le run CI qui suit un push est LU et son compte écrit.
- Fusion : merge feat/d1 DANS tmp/<nom> (worktree), tests, puis ff ; jamais de MERGE_HEAD dans l'arbre principal.
- Push : par agagi-88 (intégrateur), au sha EXACT, sur ordre de robla — lui envoyer le sha, jamais un accord relayé.
- Aucun sous-agent opus avant le 28/09 14h. Rendre compte à « Master 2 » par SendMessage : sha, comptes, verdicts.
```

## 1. SCIENCE-HARNAIS

```
Tu es la session SCIENCE-HARNAIS d'AGAGI. Fetch feat/d1-prod-pairing (≥ 79b24af6) et travaille dans .worktrees/science
(branche tmp/science). Lis dans l'ordre : CLAUDE.md ; docs/roadmap/PRIORITES_ET_DETTES.md entrées P4.18, P4.19, P3.7 ;
docs/superpowers/specs/2026-09-16-harness-contracts-design.md ; docs/EDR/EDR-HARNESS-R1*.md ; mémoires
etat-strategique-2026-09-08.md, p1-6-apprenant-inworld-apprend.md, adr-004-fourche-strategique-proposee.md.
Mandat, dans l'ordre, un run lourd à la fois :
(1) P4.18 — contrôle de FRAGILITÉ du bassin : pré-inscription S2-BASSIN-FRAGILITY scellée par tools/preregister.py
    (reviewed_by obligatoire), pré-vol tools/experiment_preflight.py (no-op exact à bruit nul = S_a au bit près,
    appariement Σ|ΔW| vérifié à 1 %, rng dédié publié, declare_design unité = seed), coût projeté depuis UNE cellule
    mesurée machine LIBRE (charge notée), run ~15 min sous bail kuzu. LIEU : nexus par défaut si la session
    INFRA-NEXUS a livré tools/jobs/remote.py ; sinon batcave, en le disant dans le record. Génomes persistés,
    results/*.json SUIVI et cité. Record EDR avec frontmatter (gate/tests/adopts, review: vers un chemin suivi),
    revue par le skill /refutateur AVANT entrée au graphe.
(2) P4.19 — les deux contrôles manquants de la pièce eligibility_trace_credit : sham « δ PERMUTÉ dans le temps » et
    dose appariée en Σ|ΔW| ; même discipline (sceau, pré-vol, Réfutateur).
(3) Task 2 du harnais (ADR-004, critère à trois conditions avant ~16 décembre) : une tâche GÉNÉRÉE (jeu de logique
    vérifiable proposé par claude -p, revue humaine par robla), et la mesure d'acquisition à dose publiée au-dessus de
    lr=0 apparié ET du plafond de l'incapable, n ≥ 12, avec l'ablation d'UNE pièce qui annule l'acquisition.
Ce que tu ne fais PAS : aucune entrée méthodo au backlog hors dette vue en passant (règle « consigner en passant »
maintenue, avec preuve fichier:ligne) ; aucun run sans sceau ; aucun record sans Réfutateur.
Rends compte à Master 2 : hash du sceau, unité mesurée et charge, verdict, sha.
+ NORMES COMMUNES.
```

## 2. FRONT — lot 2 du dashboard Pilotage

```
Tu es la session FRONT d'AGAGI. Le front vivant est frontend/ dans feat/d1-prod-pairing (Vite + react-query ;
dashboard Pilotage lots 0 et 1 livrés par le chantier fusionné e6e2c8e1 ; backend backend/app/routes/pm.py +
services/pilotage_service.py, GET /api/pm/pilotage lu du BOARD.json avec son âge). AGAGI-front (worktree main) est
CLOS : rien d'unique. Worktree .worktrees/front (tmp/front).
Lis : CLAUDE.md ; docs/roadmap/FRONTEND.md ; docs/superpowers/specs/2026-09-22-*pilotage*.md ; mémoire
pilotage-dashboard-spec-2026-09-22.md ; backlog P2.114, P2.87, P2.84 ; tests/test_backend.py,
tests/sandbox/test_pm_pilotage.py ; .github/workflows/ci.yml (pas de smoke docker : /health, /api/pm/pilotage sans DEGRADE).
Mandat, dans l'ordre : (1) P2.114 — ?frais=1 lancé depuis un WORKTREE recalcule la flotte : petit, mesurable, un
commit ; (2) P2.87 — le dashboard s'INDEXE tout seul à mesure que le projet grandit (index dérivé des artefacts
publiés, jamais d'un recalcul) ; (3) P2.84 — lot 2 « Science » : AVANT de coder, un brainstorm court remis à Master 2
(3 vues maximum, chacune adossée à une source DÉJÀ publiée par le dépôt : results/*.json, docs/EDR, data/pm ;
jamais une vue qui recalcule un verdict), puis implémentation vue par vue.
Règles front : aucun fetch brut hors couche données (react-query), zéro setInterval ; npm --prefix frontend test et les
tests backend des DEUX côtés ; jamais un test qui ÉCRIT dans l'arbre (P2.113 a : package-lock, records_graph) ; le
smoke docker de la CI doit rester VERT (lire son run). Rends compte à Master 2 : sha par lot, run CI.
+ NORMES COMMUNES.
```

## 3. INFRA-NEXUS — déport des runs sur le cluster

```
Tu es la session INFRA-NEXUS. But : que les runs AGAGI tournent PAR DÉFAUT sur le cluster ELYSIUM (nœud nexus,
allumé par robla), batcave restant libre. Aujourd'hui RIEN n'existe côté AGAGI : un job témoin a réussi le 24/09
(mémoire nexus-cluster-witness-job.md : manifeste conforme aux 11 normes Kyverno, premier log 3,4 s), c'est tout.
Lis : cette mémoire ; CLAUDE.md § Jobs & ressources ; tools/jobs/run.py, lease.py, doctor.py ; requirements.txt,
requirements-torch.txt ; côté ELYSIUM gitops/jobs/image-ci/_template.yaml (Kaniko, fetch-installation-token).
Coordination OBLIGATOIRE : envoyer un message aux sessions ELYSIUM vivantes (elysium-2d, elysium-8d, elysium-91)
avant tout kubectl create ; rien ne se crée hors du namespace dédié.
Livrables, dans l'ordre : (1) namespace elysium-agagi sous les normes elysium-* (NetworkPolicy, LimitRange,
priorityClass disposable, criticité explicite) ; (2) image runner buildée par Kaniko in-cluster (python 3.12/3.13,
numpy, torch-cpu, psutil, pyyaml, kuzu, jsonschema, pydantic — depuis requirements.txt) ; (3) tools/jobs/remote.py :
soumettre un Job pour une commande « python -m tools.evo_runs.<runner> --seed N » avec le dépôt à un SHA donné
(deploy key dédiée ou GitHub App, jamais de secret dans le dépôt), résultats écrits en LOCAL dans le pod puis déposés
par rename ATOMIQUE sur le NFS atlas, rapatriés dans results/ (suivi git) — JAMAIS kuzu/sqlite ouvert sur NFS ;
limite CPU lue dans /sys/fs/cgroup/cpu.max (os.cpu_count() ment : hôte, pas cgroup) ; (4) TÉMOIN : le runner le moins
cher du dépôt, même seed, batcave vs nexus → JSON bit-identique, publié dans un record court avec l'unité de coût
mesurée des deux côtés ; (5) docs/REF/REF-DEPORT-NEXUS.md et l'entrée backlog qui ferme « exécution locale par défaut ».
Rends compte à Master 2 à chaque livrable ; la session SCIENCE-HARNAIS attend (3) pour déporter P4.19.
+ NORMES COMMUNES.
```

## 4. DETTE — agagi-32 (déjà vivante, périmètre envoyé par message)

Périmètre unique, dans l'ordre : P2.121 famille 6 (git env sur Linux, seul rouge pouvant cacher un défaut réel, à
reproduire sous POSIX avant tout correctif) → famille 1 (torch par test ; `test_instrument_calibration.py` importable
sans torch, E22 `1be5330a`) → famille 5 (fixtures PM sur POSIX) → P2.107 (b) → P2.122. Rien d'autre. Teneur du
registre. Dissolution : moins de 10 rouges hors P2.113 sur un run.

## Ce que Master 2 tient

Gardien de d1 : fusions par worktree puis ff, arbitrage, lecture des runs CI, mise à jour de ce fichier à chaque
naissance ou dissolution. Le tick PM reste à la main (`python -m tools.pm.board`) tant que moins de quatre sessions
partagent l'arbre.
