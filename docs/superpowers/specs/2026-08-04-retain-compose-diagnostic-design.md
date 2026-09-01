# Diagnostic : le mur retain+compose est-il la RÉTENTION apprise ou la lecture d'un état porté ?

**Date** : 2026-08-04
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy + SOTA-gap. Le sous-projet BILINEAR (2026-08-03) a débloqué la composition
`(q+key)%K` à opérandes CO-PRÉSENTS (0.932) mais le 2-tick (retenir key PUIS composer) est resté nul (0.178)
— même sous BPTT non-tronqué, donc PAS un problème de gradient. La rétention SEULE marche (MEM-PERCEPTION,
delayed-match 0.967) ; la composition SEULE marche (BILINEAR). C'est la COMBINAISON qui échoue. Ce diagnostic
CHEAP tranche OÙ est le gap avant de construire un mécanisme. Cf. [[bilinear-substrate-unlocks-composition]],
[[agi-taxonomy-os-taxonomy-bridge]], [[sota-gap-substrate]].

---

## 1. Objectif

Trancher, à coût minimal (aucun nouveau mécanisme substrat), si le mur retain+compose est :
- **(H1) la RÉTENTION APPRISE** — le bilinéaire SAIT composer un état retenu, mais le substrat ne sait pas
  HOLD le key tout en apprenant à composer ; ou
- **(H2) la lecture d'un état PORTÉ** — le bilinéaire ne compose un opérande que s'il est en position
  d'ENTRÉE, pas porté en état caché (gap représentationnel plus profond).

La réponse dit QUOI construire ensuite (mécanisme de rétention si H1 ; refonte de la composition si H2).

## 2. Le proxy : 3 conditions comparées (bilinéaire + supervisé)

`tools/retain_compose_diagnostic_probe.py` (NOUVEAU) — self-contained. Réutilise le substrat bilinéaire
(`TorchPopulationModel.BILINEAR=True`), `imitate_episode_bptt` (supervisé, BPTT non-tronqué), `MambaAgent`,
`make_population`. K=6, tâche cible `(q+key)%K`, readout `argmax(logits[:, :K])`, floor=1/K, bar=`1/K+0.15`≈0.32.

- **SAME_TICK** (baseline, connu marche ~0.932) : reset H, un pas, obs = key one-hot @slots `[0:K]` +
  q one-hot @slots `[K:2K]`. Les deux opérandes CO-PRÉSENTS en ENTRÉE.
- **ORACLE_RETENTION** (le diagnostic) : reset H, **injecter le key PAR FIAT dans des nœuds CACHÉS**
  `mem_start = (N-O) + K`, `mem_slots = [mem_start : mem_start+K]` — APRÈS la fenêtre de readout
  `[N-O : N-O+K]` (aux valeurs par défaut I=59,N=172,O=108,K=6 : `mem_slots=[70:76]` vs readout `[64:70]`,
  disjoint, aucun chevauchement) : `H[arange, mem_start+key] = 1.0`. Puis un pas, obs = q one-hot @`[K:2K]`. Le key est PARFAITEMENT retenu
  (état caché propre) ; le bilinéaire `((H·U)⊙(H·V))` lit tout H → il PEUT multiplier `mem_slot-key × input-q`.
- **LEARNED_RETENTION** (le cas qui échoue ~0.178) : reset H, pas 1 = encode(key @`[0:K]`), pas 2 =
  use(q @`[K:2K]`). Le key doit être retenu par la dynamique APPRISE puis composé.

SAME_TICK et LEARNED sont entraînées par `imitate_episode_bptt` (cross-entropy sur la cible via `mask_seq`).
⚠️ ORACLE ne peut PAS l'utiliser tel quel : `imitate_episode_bptt` remet `H=0` en interne, ce qui effacerait
l'injection dans `mem_slots`. ORACLE utilise donc une **boucle supervisée CUSTOM** : par pas d'entraînement,
reset H, `H[:, mem_slots]=key`, `forward(q)`, cross-entropy `logits[:, :K]` vs cible, `backward`,
`opt.step` (opt = Adam sur `[W, U, V, W_bl]`). Le gradient circule par le bilinéaire et W depuis la CE.
BILINEAR on partout. n=12 seeds. Éval miroir de l'entraînement (même injection oracle à l'éval).

## 3. Le verdict

- **H1 (rétention apprise = le gap)** si : `same_tick` > bar (contrôle positif, le bilinéaire compose) ET
  `oracle` > bar (le bilinéaire compose un état RETENU propre) ET `learned` ≤ bar (le 2-tick échoue).
  → le bilinéaire sait composer un état porté ; ce qui manque est la RÉTENTION APPRISE (holder le key en
  apprenant simultanément à composer). Prochain sous-projet : mécanisme de rétention.
- **H2 (lecture d'état porté = le gap)** si : `same_tick` > bar MAIS `oracle` ≤ bar. → le bilinéaire ne
  compose PAS un key porté en état caché comme une entrée co-présente → gap représentationnel (position
  d'entrée vs état porté). Prochain sous-projet : refonte de la composition/lecture d'état.
- **Unité = seed, n ≥ 12.** Le verdict est la comparaison des 3 médianes vs bar, avec séparation par-seed.

La sonde `run_retain_compose_diagnostic_probe(...)` (nom `run_*probe` → trippe le cliquet) renvoie
`{"same_tick_median": float, "oracle_median": float, "learned_median": float, "gap_verdict": "RETENTION"|
"REPRESENTATION"|"INCONCLUSIVE", "per_seed": {...}, "n": int}`.

## 4. Calibration (obligatoire — la sonde trippe le cliquet, générateur A)

- **Contrôle POSITIF (le bilinéaire compose)** : `same_tick` > bar. Prouve que l'instrument PEUT montrer la
  composition (sinon un `oracle ≤ bar` serait ininterprétable).
- **Contrôle NÉGATIF (oracle DÉCORRÉLÉ)** : injecter un key ALÉATOIRE dans `mem_slots` (décorrélé de la
  cible `(q+key)%K` calculée sur le VRAI key) → la composition est impossible (l'état retenu est faux) →
  `oracle_decorrelated ≤ bar`. Prouve que l'instrument n'invente pas un positif quand l'état retenu ne porte
  pas la bonne info (le « oracle » mesure bien la LECTURE de l'état retenu, pas un artefact).
- Cas dans `tests/sandbox/test_instrument_calibration.py` + entrée `CALIBRATED`.

## 5. Bornage du coût

Pur torch CPU, aucun bail `kuzu`, aucun monde. Pré-vol `declare_design`. SMOKE d'abord (les 3 conditions +
débit). Run-verdict n=12 en **FOREGROUND** borné (< ~9 min ; leçons SP-2/MEM-PERCEPTION). Supervisé BPTT →
un peu plus lent ; tuner `episodes` au smoke. Persister accuracies + `_params`. Provenance : fonction
calibrée réelle.

## 6. Livrable final

La sonde diagnostique + le record `docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md` nommant
OÙ est le gap (H1 rétention apprise / H2 lecture d'état / inconclusif). PAS d'arête, PAS de nouveau mécanisme
substrat (ce round DIAGNOSTIQUE ; le mécanisme est le round SUIVANT selon le verdict). Frontmatter EDR
`gate:`/`tests:`/`adopts:`.

## 7. Fichiers

- `tools/retain_compose_diagnostic_probe.py` (NOUVEAU) — la sonde 3-conditions.
- `tests/test_retain_compose_diagnostic_probe.py` (NOUVEAU) — smoke unitaire.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — CALIBRATED + positif (same_tick) / négatif (oracle décorrélé).
- `results/retain_compose_diagnostic.json` (NOUVEAU) — accuracies + `_params`.
- `docs/EDR/EDR-RETAIN-COMPOSE_Where_Is_The_Retain_Compose_Wall.md` (NOUVEAU) — le record.

## 8. Critères de succès

1. Sonde calibrée : positif (same_tick compose), négatif (oracle décorrélé inerte), sous cliquet.
2. Run-verdict n=12 : les 3 médianes mesurées ; `gap_verdict` ∈ {RETENTION, REPRESENTATION, INCONCLUSIVE}
   selon les seuils (§3), avec séparation par-seed.
3. Record gravé nommant le gap (honnête si INCONCLUSIVE) ; `check_record_links` non-orphelin.

## 9. Hors scope

- Construire le mécanisme de rétention (round SUIVANT si H1).
- Re-tenter `language→memory` (dépend de la résolution du mur retain+compose).
- Rétention APPRISE réaliste (le diagnostic utilise un oracle PARFAIT à dessein, pour isoler la variable).

## 10. Risques et pièges

- **L'oracle est trop facile / trop propre** (le key dans un slot connu vs porté par une dynamique apprise) :
  assumé — le but est d'isoler « le bilinéaire PEUT-il composer un état retenu PROPRE ? ». Si oui, le gap est
  côté rétention (holder ET/OU holder en forme lisible). Le contrôle NÉGATIF (oracle décorrélé) garantit que
  le « oracle » mesure bien la lecture de l'état, pas un artefact.
- **same_tick ne reproduit pas ~0.93** (contrôle positif raté) : le banc ne sait pas composer → tout le
  diagnostic est ininterprétable → augmenter episodes/re-smoke (précédent BILINEAR : same-tick supervisé
  apprend).
- **learned ne reproduit pas ~0.18** : re-vérifier le pipeline 2-tick (doit rester nul, cf. BILINEAR Task 3).
- **Confusion capacité/émergence** : ce diagnostic mesure une CAPACITÉ sous oracle, pas l'émergence.
- **Sonde non calibrée = résultat fabriqué** : la calibration (positif same_tick / négatif oracle décorrélé)
  est un livrable.
