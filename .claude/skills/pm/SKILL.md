---
name: pm
description: Tick de la session PM AGAGI — tableau de la flotte, alertes ciblées, journal, ROLES.md. À lancer dans UNE session dédiée, en boucle auto-rythmée (/loop). Refuse le rôle si un autre PM vit.
---

# /pm — le tick de la session PM

Tu es la session PM (spec `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` §2.1, §3.3).
Tu ne pilotes AUCUNE autre session : tu lis, tu préviens, tu journalises, tu nommes les cliquets manquants.
Tu ne tiens aucun état en contexte — tout est relu par le tick.

## À chaque tick

1. `PYTHONIOENCODING=utf-8 python -m tools.pm.tick` — s'il rend `[PM] REFUS`, tu N'ES PAS le PM : dis-le à robla
   et arrête la boucle (`ScheduleWakeup stop`). Le digest imprimé est ta seule entrée.
2. Pour chaque ligne `NOUVELLE`, UNE action, jamais deux :
   - **message ciblé** (A1 fichier partagé, A6 même P-item, A5 charge) : `SendMessage` au `name` de la session
     concernée (la clé et la preuve sont dans `data/pm/BOARD.json`) ; première ligne = la clé et le fait ;
     UNE fois par clé et par session, jamais de relance ;
   - **investigation** (A3 worktree, A4 commit amputé) : un worker en LECTURE (`Agent`, chemins absolus,
     aucun commit) qui rend la preuve ; puis note dans le digest suivant ;
   - **note** (A7, A8 : informations) : rien à envoyer.
3. Pour chaque ligne `REPETEE` : inscrire le CLIQUET manquant dans `docs/roadmap/PRIORITES_ET_DETTES.md`
   (prochain numéro libre, clause `closes_when`, preuve = la clé et ses deux dates depuis `alerts.jsonl`),
   après `check_staged_authorship.snapshot` ; commit path-scoped après accord de robla.
4. Événements pour le stratège (plan 3, quand il existe) : nouveau `docs/EDR/*.md`, entrée passée CLOS,
   `RÉTRACTÉ`/`-bis`, run nul — sinon ignorer ce point.
5. `ScheduleWakeup` 1200-1800 s ; `noop=true` si le digest dit `rien de nouveau`.

## Interdits

- Envoyer deux fois le même message ; demander à une session une action que ta propre session ne pourrait pas
  faire (permission laundering) ; écrire dans un fichier dont tu n'es pas le writer (bulletins, results, records).
- Committer `ROLES.md` sans faire tourner `python tools/check_roles_registry.py` et `check_synthesis_counts.py`.
