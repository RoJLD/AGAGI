# Design — Pont proxy→in-world du demand-marker + formalisation de l'instrument

**Date** : 2026-07-15
**Auteur** : session Claude (poste robla), arbre partagé — commits path-scopés
**Portées** : G0 (le monde exige-t-il l'intelligence ?) — consolidation causale in-world
**Records visés** : EDR-S2-002 (`gate: G0`, `tests: [SDR-G0]`) + REF-DEMAND-MARKER
**Prérequis vérifiés** : HoF peuplé (`data/hall_of_fame.pkl`, 10 entrées) ; `tools/s2_demand.py` importable ; seam `batch_model_cls` in-world confirmé (`world_1_stoneage.py:973` instancie `batch_model_cls(models, world_model=...)`).

---

## 1. Problème & objectif

Le méta-gap dominant du programme est le **pont proxy → in-world** : ~80-90 % des résultats forts
sont en isolation (proxies numpy standalone), tandis que les tests in-world sont presque tous NEUTRES.
L'instrument transversal — **le témoin causal de « la capacité X est-elle exigée » = ablation
WITHIN-subject de X** (pas « un agent équipé de X survit », qui faux-positive en between-subject) — a
été validé sur 4 modalités **en proxy** (perception S2-001, communication LANG-006, généralisation
G1-001, mémoire MEM-001).

Le benchmark in-world existant `tools/s2_demand.py` établit la demande **en BETWEEN-subject** (survie du
champion HoF vs baselines RandomAction/RandomGenome/Reflex × 5 mondes). Sa propre spec documente le
caveat : « le champion est un SURVIVANT, pas un marqueur » — un survivant compétent peut exister dans un
monde qui n'exige PAS de perception. Le between-subject peut donc faux-positiver la demande.

**Objectif du push** : porter le témoin within-subject (ablation de perception) sur le VRAI monde, pour
produire un verdict CAUSAL in-world de la demande perceptive — et le contraster avec le verdict
between existant pour montrer, in-world, où between sur-revendique.

**Objectif de la formalisation** : extraire le demand-marker en instrument de première classe —
module réutilisable + record REF adoptable par le graphe + note méthodes transversale.

**Non-objectifs (YAGNI)** :
- Pas de ré-entraînement / évolution : on réutilise le champion HoF tel quel.
- Pas de migration moteur (torch/Dreamer) : hors périmètre.
- Pas d'attribution chirurgicale perception-vs-proprioception au premier jet (voir §4, follow-up B).
- Aucune modification de `tools/s2_demand.py` (benchmark pré-enregistré) ni d'aucun monde / outil
  //-authored : tout passe par de NOUVEAUX fichiers qui importent.

## 2. Mécanisme d'ablation (décision : Approche A — permutation de ligne)

`PerceptionAblatedMamba(MambaBatchModel)` surcharge `forward` :

```
def forward(self, batch_obs, env_surprise_batch=None):
    ablated = _derange_rows(batch_obs)      # chaque agent reçoit l'obs d'un PAIR
    return super().forward(ablated, env_surprise_batch)
```

- **Permutation (dérangement) des lignes** de `batch_obs` entre agents : chaque agent reçoit une obs
  **réelle et bien formée** (celle d'un pair), donc DÉCORRÉLÉE de sa propre réalité mais parfaitement
  dans-distribution. Pas de choc OOD (le confond que le proxy évitait déjà en utilisant un one-hot
  d'action aléatoire plutôt qu'un vecteur bruité).
- **World-agnostic** : un seul mécanisme sur les 5 mondes, aucun mapping de colonnes par monde (fragile
  aux éditions // des mondes). C'est la raison décisive du choix de A vs B.
- **Portée du verdict assumée** : A ablate le flux sensori-égocentrique COMPLET (perception externe +
  proprioception : hp/energy/age/inventaire/mémoire). Le verdict lu est donc « le flux égocentrique de
  l'agent porte-t-il causalement sa survie », qui EST la question de demande in-world. L'affinage
  « perception externe seule » (Approche B, mapping par monde) est un **follow-up** si A déclenche et
  qu'on veut disséquer.
- **Propreté** : permuter ne change QUE ce que la politique voit ; l'état-vérité (énergie réelle sur le
  dict agent, décrémentée par `env`) n'est jamais touché. Ablation propre = désinformer le cerveau sans
  toucher le monde. Test dédié le vérifie (§6).
- **Détails** : dérangement (aucun point fixe) pour B≥2 ; identité pour B<2 (near-death, fuite
  négligeable et CONSERVATRICE — affaiblit l'ablation). RNG tiré du flux global `np.random` (seedé aux
  frontières par le Harness → appariement préservé, jamais de RNG privé, cohérent avec
  `RandomActionBatchModel`).

## 3. Push — `tools/s2_demand_ablation.py` (nouveau, standalone)

**Imports depuis `s2_demand`** (réutilisation, zéro modif) : `run_condition`, `WORLDS`,
`load_champion_genome`, éventuellement `pilot_required_k`.

**Conditions comparées, par monde** :
- `champion` : génome champion, moteur normal (`batch_model_cls=None`) — la référence intacte.
- `champion_ablated` : génome champion, `batch_model_cls=PerceptionAblatedMamba` — within-subject.

**Métriques par monde** :
- survie médiane intact `S_intact`, ablated `S_abl`.
- **ratio within** = `S_intact / max(S_abl, ε)`.
- **verdict** via l'instrument formalisé (§5) : `PERCEPTION_DEMANDED` si effondrement franc + n
  suffisant ; `PERCEPTION_DECOY` si plat ; `INCONCLUSIVE` sinon (garde-fou n<12).
- **contraste between** : réutilise le verdict between de `s2_demand` (champion vs strongest baseline).
  Sortie : tableau per-monde `{between_ratio, within_ratio, accord ?}` — met en évidence les mondes où
  between crie « demande » alors que within dit « leurre » (analogue in-world de S2-001).

**Sortie** : tableau console + dict sauvé (sous `results/`, gitignored — le verdict va dans l'EDR).
Paramétrable par env (seeds, K éres, num_agents, max_ticks) comme les autres probes.

**Runtime** : 5 mondes × 2 conditions × K éres. K piloté modéré (réutilise la power-analysis de
`s2_demand`) pour rester en minutes/monde. `benchmark_mode=True` (cohorte fixe), `memory_retriever.stop()`
après chaque ère (repro — cf. garde biosphère mémoire ambiante).

## 4. Interprétation des verdicts (per-monde)

| within ratio | between ratio | lecture |
|---|---|---|
| effondrement (≫1) | ≫1 | perception DEMANDÉE + survivant existe : accord, demande causale confirmée |
| ~1 (plat) | ≫1 | between FAUX-POSITIVE : un survivant existe mais sa perception n'est pas porteuse → LEURRE |
| effondrement | ~1 | demande causale malgré baselines proches (rare, à noter) |
| ~1 | ~1 | monde ne demande pas (ou champion ne s'appuie pas dessus) |

Le résultat scientifique du push = **la carte per-monde** de la demande perceptive causale + le
recensement des désaccords between/within (= le faux-positif rendu visible in-world).

## 5. Formalize — instrument de première classe

### 5.1 `tools/demand_marker.py` (module réutilisable)
Fonction pure, sans dépendance monde :
```
def ablation_verdict(intact, ablated, weight_on_x=None,
                     n_floor=12, collapse_factor=1.5, decoy_ceiling=1.3):
    # intact, ablated : listes/arrays de survies (ou de tout proxy de fitness) appariées
    # -> {ratio, collapse: bool, decoy: bool, corroborant, n, verdict}
```
- `ratio = median(intact) / max(median(ablated), ε)`.
- **Garde-fou n** : pas de verdict POSITIF (`DEMANDED`) si `n < n_floor` → `INCONCLUSIVE` (cohérent avec le
  garde-fou « le signal petit-n s'évapore sous puissance » ; on ne rejoue PAS `compute_ab_verdict`
  partagé, on porte notre propre garde local).
- **Corroborant optionnel** `weight_on_x` : le poids que la politique met sur le canal X (|W|). Sert de
  second témoin (le proxy montre |W|→0 quand X ne paie pas). En in-world, non calculable simplement sur
  le champion HoF (poids non exposés) → passé `None` ici ; le champ existe pour les proxies.
- Verdict ∈ {`X_DEMANDED`, `X_DECOY`, `INCONCLUSIVE`}.

**Refactor** : `tools/world_demand_marker_probe.py` (S2-001, mon fichier) ET
`tools/s2_demand_ablation.py` importent cette fonction → une seule définition du témoin (DRY). Le
refactor de S2-001 conserve son verdict/sortie (test de non-régression).

### 5.2 `docs/REF/REF-DEMAND-MARKER.md` (record REF adoptable)
Record REF (comme REF-LTC) que les EDR peuvent `adopt_for` :
- énoncé de l'instrument, prédiction (between faux-positive / within tranche), corroborant poids ;
- table des 4 modalités déjà couvertes (S2-001, LANG-006, G1-001, MEM-001) + cette 1re application
  in-world (S2-002) ;
- `adopt_for: [S2-001, LANG-006, G1-001, MEM-001, S2-002]` → ancre l'instrument dans le graphe et
  dé-orphanise en prime les EDR qui l'adoptent.

### 5.3 `docs/roadmap/DEMAND_MARKER_METHOD.md` (note méthodes, 2-3 p.)
- Le témoin causal transversal : problème (between faux-positif), solution (ablation within-subject),
  corroborant (poids→0).
- Protocole générique : « pour toute capacité X dé-risquée en proxy, ajouter un bras d'ablation-X
  within-subject comme KPI causal, pas la survie brute ».
- Les 4 modalités + le passage in-world (S2-002) : le pont proxy→in-world instancié.
- Limites : ablation de flux complet vs canal isolé (A vs B) ; corroborant poids indisponible sur
  champion HoF.

## 6. Tests (`tests/`, nouveaux fichiers)

1. `test_perception_ablation.py` :
   - `_derange_rows` : B≥2 → permutation sans point fixe ; B∈{0,1} → identité ; préserve shape/dtype.
   - `PerceptionAblatedMamba.forward` : appelle `super().forward` avec obs permutée ; **ne mute pas**
     l'obs d'entrée ni l'état-monde (obs passée ≠ obs vue, mais `env` inchangé) — via un stub minimal de
     MambaBatchModel si instancier le vrai est trop lourd.
2. `test_demand_marker.py` :
   - effondrement (intact≫ablated) → `X_DEMANDED` ;
   - plat (intact≈ablated) → `X_DECOY` ;
   - n<12 → `INCONCLUSIVE` même si effondrement (garde-fou) ;
   - non-régression S2-001 : le refactor donne le même verdict qu'avant.
3. `test_s2_ablation_smoke.py` : l'outil tourne sur 1 monde (stoneage), K minimal, num_agents réduit,
   renvoie un dict bien formé (marqué `slow`/opt-in si trop lent en CI).

## 7. Ancrage records & hygiène

- **EDR-S2-002** (`docs/EDR/`) : `id: EDR-S2-002`, `gate: G0`, `tests: [SDR-G0]`, verdict du push
  (carte per-monde + désaccords between/within). Convention préfixe thématique (P4).
- **REF-DEMAND-MARKER** : §5.2, avec `adopt_for`.
- Après écriture : `python tools/consolidate_records.py` (doit rester `problemes=0`) +
  `python tools/check_record_links.py --report` (0 nouvel orphelin ; les EDR adoptés via REF perdent
  leur statut d'orphelin).

## 8. Plan de commits (path-scopés, séparés)

1. **Formalize-core** : `tools/demand_marker.py` + `tests/test_demand_marker.py` + refactor
   `tools/world_demand_marker_probe.py`.
2. **Push** : `tools/s2_demand_ablation.py` + `tests/test_perception_ablation.py` +
   `tests/test_s2_ablation_smoke.py`.
3. **Records & docs** : `docs/EDR/…S2-002…md`, `docs/REF/REF-DEMAND-MARKER.md`,
   `docs/roadmap/DEMAND_MARKER_METHOD.md`, mise à jour mémoire projet.

Chaque commit ne touche QUE des fichiers créés par cette session (ou mon propre S2-001) — jamais un
fichier //-authored ni le benchmark `s2_demand.py`.

## 9. Risques & mitigations

- **Le champion s'effondre partout sous ablation, même mondes « faciles »** : possible si toute survie
  dépend d'un minimum d'égocentrisme (bouger vers la nourriture). C'est un RÉSULTAT valide (perception
  demandée partout), pas un bug ; le contraste between/within reste informatif (accord).
- **Le champion NE s'effondre nulle part** (survie plate sous ablation) : signifierait que le champion
  survit par politique quasi-ouverte (peu dépendante de l'obs). Résultat valide (in-world = leurre pour
  CE champion) et cohérent avec le fil « in-world NEUTRE ». À rapporter honnêtement.
- **Runtime trop long sur 5 mondes** : réduire K/num_agents ; le smoke test tourne 1 monde. K piloté.
- **`from_genome` / dims** : le champion HoF peut avoir des dims spécifiques ; `run_condition` gère déjà
  `a.from_genome(genome)`. On ne change pas ce chemin.
- **Non-déterminisme mémoire ambiante** : `memory_retriever.stop()` déjà appelé par `run_condition`.

## 10. Critères de succès

- `s2_demand_ablation.py` produit une carte per-monde {within_ratio, between_ratio, verdict} sur les 5
  mondes, reproductible à seed fixe.
- `demand_marker.ablation_verdict` est l'unique définition du témoin, importée par S2-001 (proxy) et le
  push (in-world), avec garde-fou n<12.
- REF-DEMAND-MARKER + note méthodes livrés ; EDR-S2-002 raccordé G0 ; `problemes=0`, 0 nouvel orphelin.
- Verdict du push écrit honnêtement dans l'EDR, quel qu'il soit (demande confirmée / leurre / mixte).
