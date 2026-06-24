# Documentation AGIseed — carte & convention

> **Où trouver quoi.** La doc s'organise sur **deux axes orthogonaux** : le *domaine* (de quoi on
> parle) et l'*horizon* (court-terme / someday / passé). Avant, `roadmap.md` mélangeait les deux
> (science + backend dans un seul fichier) → d'où l'impression de désordre. Désormais chaque doc
> déclare son couple **(domaine, horizon)** sans ambiguïté.

## Les deux axes

| Horizon \ Domaine | 🔬 Scientifique | ⚙️ Backend | 🖥️ Frontend |
|---|---|---|---|
| **Court-terme** (ce qui reste) | `roadmap/SCIENCE.md` · `roadmap/NAS.md` | `roadmap/BACKEND.md` | `roadmap/FRONTEND.md` |
| **Someday** (aspirationnel) | `BACKLOG.md` (§Science, §NAS) | `BACKLOG.md` (§Backend) | `BACKLOG.md` (§Frontend) |
| **Passé** (preuves, immuable) | `EDR/*` · `FIL_CONDUCTEUR.md` | — | — |

## Index des documents

### `roadmap/` — court-terme, par domaine
- **`SCIENCE.md`** — frontière scientifique : les 7 Arcs (phylogénèse), diagnostic, vagues, méthode.
- **`NAS.md`** — Neural Architecture Search : moteur évolutif, table de vérité génotype→phénotype,
  backlog A/B/C, Phase 0. *(sous-axe de la science)*
- **`BACKEND.md`** — serveur FastAPI, observabilité/provenance, A/B multi-run, sécurité/sandbox, CI.
- **`FRONTEND.md`** — dashboard React : passer de *visualiseur* à *instrument de méthode*.

### Racine `docs/`
- **`BACKLOG.md`** — le « someday » : visions et axes futurs non encore planifiés, sectionné par domaine.
- **`SCAN_GLOBAL.md`** — audit de juin 2026. ⚠️ *Générateur d'hypothèses, partiellement périmé* :
  ses claims « gènes morts » sont **corrigés par `roadmap/NAS.md` §1** (re-audit 2026-06-24).
- **`PARITY_GATE.md`** — outil anti-drift (frontend ↔ EDR). *(dette/qualité)*
- **`Metier.md`** — profils de sous-agents experts mobilisables.

### Historique (immuable — **ne pas déplacer** : `tools/parity_check.py` en dépend)
- **`EDR/`** — 93 décisions expérimentales (`NNN_*.md`). La preuve granulaire.
- **`FIL_CONDUCTEUR.md`** — le récit qui relie les EDR.

### `superpowers/{specs,plans}/`
- 1 spec + 1 plan par feature (convention brainstorming → writing-plans). Inchangé.

### Vision (racine du repo, intemporel)
- `0_Taxonomy_Evolution.md`, `1_Micro_NAS.md`, `2_Meso_NAS.md`, `3_Macro_NAS.md`, `4_Meta_NAS.md` —
  la taxonomie fractale à 4 échelles. Référencée par `roadmap/NAS.md`.

## Convention d'écriture
- **roadmap/** ne garde que *ce qui reste* + le statut. Ce qui est livré y reste comme trace courte.
- **BACKLOG.md** = ce qu'on n'ouvre que pour planifier loin.
- Un changement cognitif **gèle l'aval** d'abord (1 variable — Commandement 15).
- Verdict NAS = transfer-ratio appariée (`tools/curriculum_transfer.py`).
