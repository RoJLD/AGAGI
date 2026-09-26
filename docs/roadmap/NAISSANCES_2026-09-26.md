# Prompts de naissance — flotte du 2026-09-26

Décisions de robla (2026-09-26, matin) : **gel de la méthodologie** à ce qui bloque un run, un seul worker Dette
(agagi-32) ; **science** dans l'ordre P4.18 → P4.19 → Task 2 du harnais ; **runs sur le cluster nexus par défaut**,
batcave seulement si aucun cluster ou machine n'est disponible ; **AGAGI-front clos** (ses deux fichiers étaient déjà
dans d1), le front vit dans `frontend/` de d1 ; les sessions sont ouvertes **par robla dans VS Code** (tmux absent),
Master 2 fournit les prompts et coordonne par messages inter-sessions ; **Master 2 est l'intégrateur** depuis
afeb54c0 (agagi-88 l'a tenu jusque-là, seize pushes, puis s'est fermé ; push au sha exact, chaîne mesurée avant, run lu
après). Chaque bloc ci-dessous se colle tel quel comme premier message d'une session neuve.

## Normes communes (reprises dans chaque prompt)

```
NORMES COMMUNES (arbre PARTAGÉ, feat/d1-prod-pairing) :
- Fetch d'abord ; travailler dans un worktree TEMPORAIRE : git worktree add .worktrees/<nom> -b tmp/<nom> feat/d1-prod-pairing.
- Un commit = un run lourd : un seul à la fois sur la machine ; python -m tools.jobs.doctor avant tout run ; toute simulation
  de monde tient le bail kuzu (tools.jobs.run.hold).
- Commits path-scoped, jamais nus, jamais --no-verify ; message SANS backticks. Forme recommandée (P2.122 CLOSE) :
  python -m tools.check_staged_authorship commit-exact --attendu CHEMIN=FICHIER [...] -F msg — vérification et commit
  dans le MÊME appel, sur le contenu que TON script a produit (jamais relu sur le disque partagé). ⚠️ « git commit --
  chemins » emporte le fichier ENTIER du DISQUE, pas l'index : un hunk d'une autre session écrit après ton empreinte
  part avec toi (9bf30520, E12) ; lire le diff stat contre le delta attendu.
- Un numéro de backlog s'alloue à l'ÉCRITURE (refus s'il existe sur disque OU dans l'index) ; jamais citer une balise
  <!-- count:… --> littéralement dans un .md (la porte 8 la compte).
- Tests des DEUX côtés (torch / sans torch, Windows / POSIX) ; le run CI qui suit un push est LU par
  python -m tools.ci_diff_failed <run> <run_ref> (rouges nouveaux / disparus nommés) et son compte écrit.
- Fusion : merge feat/d1 DANS tmp/<nom> (worktree), tests, puis ff ; jamais de MERGE_HEAD dans l'arbre principal.
- Push : par Master 2 (intégrateur), au sha EXACT — lui envoyer la chaîne mesurée (git log origin..tmp/<nom>) ; aucun
  accord relayé ne vaut, seul robla peut ordonner un push directement.
- Sous-agents opus AUTORISÉS (crédits réinitialisés, décision de robla du 2026-09-26 — la ligne « aucun opus avant le
  28/09 14h » est levée) ; emploi recommandé : revues adversariales, juges, relectures de sceau, pas les tâches mécaniques.
- ⚠️ Mesuré le 2026-09-26 (P2.121 famille 6) : un commit ou un git init lancé DEPUIS un worktree peut passer le dépôt
  PRINCIPAL en bare si GIT_DIR est hérité — la fixture de tests/conftest.py et tools/_git_env.py restent obligatoires ;
  tout sous-processus git qui vise un AUTRE dépôt (jetable, clone, cluster) isole la famille GIT_*.
- Rendre compte à « Master 2 » par SendMessage : sha, comptes, verdicts.
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
Tu es la session FRONT d'AGAGI. Le front vivant est frontend/ dans feat/d1-prod-pairing (Vite + react-query).
⚠️ ÉTAT RÉEL du dashboard Pilotage (mesuré par agagi-88 contre afeb54c0 ; une première version de ce prompt disait
« lots 0 et 1 livrés », c'était FAUX) : le chantier fusionné e6e2c8e1 a livré les PAS 1 et 2 de la spec §7 —
tools/pm/pilotage.py, backend/app/routes/pm.py + services/pilotage_service.py (GET /api/pm/pilotage lu du
BOARD.json avec son âge), schémas, types générés ; grep « pilotage » dans frontend/src ne trouve que schema.ts. Les
PAS 3 (famille « Pilotage » : vues Flotte / Roadmap / Portes, spec §3.3), 4 (patch tick.py + artefact, §3.4) et 5
(« Vague K » dans FRONTEND.md) ne sont PAS faits. AGAGI-front (worktree main) est CLOS : rien d'unique.
Worktree .worktrees/front (tmp/front).
Lis : CLAUDE.md ; docs/roadmap/FRONTEND.md ; docs/superpowers/specs/2026-09-22-*pilotage*.md ; mémoire
pilotage-dashboard-spec-2026-09-22.md ; backlog P2.114, P2.87, P2.84 ; tests/test_backend.py,
tests/sandbox/test_pm_pilotage.py ; .github/workflows/ci.yml (pas de smoke docker : /health, /api/pm/pilotage sans DEGRADE).
Mandat, dans l'ordre : (1) P2.114 — ?frais=1 lancé depuis un WORKTREE recalcule la flotte : petit, mesurable, un
commit ; (2) PAS 3 de la spec — la famille Pilotage (Flotte / Roadmap / Portes) ; (3) PAS 4 et 5 ; (4) P2.87 — le
dashboard s'INDEXE tout seul à mesure que le projet grandit (index dérivé des artefacts publiés, jamais d'un
recalcul) ; (5) P2.84 — lot 2 « Science » : AVANT de coder, un brainstorm court remis à Master 2
(3 vues maximum, chacune adossée à une source DÉJÀ publiée par le dépôt : results/*.json, docs/EDR, data/pm ;
jamais une vue qui recalcule un verdict), puis implémentation vue par vue.
Règles front : aucun fetch brut hors couche données (react-query), zéro setInterval ; npm --prefix frontend test et les
tests backend des DEUX côtés ; jamais un test qui ÉCRIT dans l'arbre (P2.113 a : package-lock, records_graph) ; le
smoke docker de la CI doit rester VERT (lire son run). Leçons du chantier, à tenir : tout import backend vers tools/
doit marcher DANS L'IMAGE docker (tools/ et docs/ montés en volumes :ro, backend/requirements.txt est la seule liste
de dépendances — b7a06d87 : le backend mourait à l'import) ; tout changement de schemas.py passe par make api-types
dans le MÊME commit, et dump_openapi.py écrit du CRLF sous Windows, à normaliser en LF ; le service valide chaque
bloc contre PilotageV1 dans son filet. Rends compte à Master 2 : sha par lot, run CI.
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
→ **Critère ATTEINT** (mesuré sur c676f200 puis 3c9414f6 et afeb54c0) : 5 rouges, tous P2.113 (c) grab et (d)
flatland, 0 hors P2.113 ; tout le périmètre ci-dessus est CLOS, plus P2.128 (portes 19/20 refusent un --only vide) et
E34 au registre. Restent à agagi-32 : P2.129 (extracteur à backtick) et P2.133 (« aucun » lu comme refus par le
Réfutateur), chacune après l'entrée de SCIENCE qui la porte dans d1 ; P2.113 (c)(d) attend la décision de robla.

## Ce que Master 2 tient

Gardien de d1 : fusions par worktree puis ff, arbitrage, lecture des runs CI, mise à jour de ce fichier à chaque
naissance ou dissolution. Le tick PM reste à la main (`python -m tools.pm.board`) tant que moins de quatre sessions
partagent l'arbre.
