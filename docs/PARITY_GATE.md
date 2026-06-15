# Parity Gate — parité frontend + narration des expériences

> Détecteur de **drift sémantique** : des choses vraies dans le repo (capacités backend, expériences EDR)
> mais pas racontées au frontend. Invisible au build → d'où une gate dédiée.
>
> Outil : [`tools/parity_check.py`](../tools/parity_check.py) (stdlib only, aucune dépendance).

## Problème (drift mesuré au 2026-06-15)

| Source de vérité | Dernier EDR | Anomalie |
|---|---|---|
| `docs/EDR/*.md` (87) | **087** | référence |
| `backend/app/edr_findings.json` (onglet EDR) | contient 87 | titre annonce « 037→083 » (obsolète) ; 79/83/85/86 sans carte |
| `docs/FIL_CONDUCTEUR.md` (récit) | corps = **082** | titre H1 « 010→049 » (faux) ; récit en retard de 5 EDR |
| onglet **Academy** | — | déconnecté des EDR (cause racine) |

## Design — hybride en 3 couches (un seul moteur)

- **Couche 0 — `tools/parity_check.py`** : classe le diff (`EXPERIENCE`/`DEV`/`DOC`) puis lance les checks adaptés, chacun en **WARN** (rappel non bloquant) ou **FAIL** (invariant dur).
- **Couche 1 — hook git `pre-commit`** : `parity_check.py --staged` → feedback rapide, advisory, contournable au `--no-verify` (anti-friction volontaire).
- **Couche 2 — CI (`ci.yml`)** : `parity_check.py --strict` → bloque uniquement les **invariants durs** (JSON cassé / findings vide / schéma non conforme).

### Règle de classification (cartographie)
1. nouveau `docs/EDR/NNN_*.md` **ou** message `^EDR N` → **EXPERIENCE** (prioritaire) ;
2. sinon seuls des `*.md` hors EDR → **DOC** ;
3. sinon `src/|tools/|main_*|tests/` ou préfixe `feat/fix/...` → **DEV**.

### Checks narration (étape 1, livrée)
| Check | Niveau |
|---|---|
| `max(docs/EDR)` couvert par les findings | WARN |
| EDR récents (10 derniers) : carte **ou** mention récit | WARN |
| cohérence titre ↔ contenu (`edr_findings.json`, `FIL_CONDUCTEUR` H1) | WARN |
| `edr_findings.json` : JSON valide, `findings` non vide, schéma conforme | **FAIL** |

## Roadmap d'implémentation

- [x] **Étape 1** — `parity_check.py` checks narration + `--report`/`--staged`/`--strict`. *(livrée, validée sur le drift réel)*
- [ ] **Étape 2** — hook `pre-commit` (WARN-only) + cible `make hooks` (le repo n'a ni husky ni pre-commit).
- [ ] **Étape 3** — checks **parité dev** : route backend ↔ `fetch` frontend ; champ `schemas.py` ↔ `types.ts` ; composants orphelins.
- [ ] **Étape 4** — CI `--strict` sur les invariants durs (étendre `.github/workflows/ci.yml`).
- [ ] **Étape 5** *(cause racine)* — brancher l'onglet **Academy** sur les EDR → réduit les 3 silos manuels.

## Usage
```bash
python tools/parity_check.py                 # rapport de parité (exit 0)
python tools/parity_check.py --staged        # ne checke que si le commit stagé est une EXPERIENCE
python tools/parity_check.py --strict        # exit 1 sur invariant dur (CI)
python tools/parity_check.py --repo /chemin  # cibler un autre checkout (ex: autre worktree)
```

## Limites honnêtes
Une gate vérifie qu'un consommateur/une carte **existe**, pas qu'il est *utile* ni que le récit est *exact*.
La déconnexion d'Academy est un défaut de design (étape 5), pas verrouillable par un check.
Les heuristiques dev ont des faux positifs (route via chemin dynamique) → d'où WARN, pas FAIL.
