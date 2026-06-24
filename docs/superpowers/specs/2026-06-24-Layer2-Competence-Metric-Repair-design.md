# Design — Réparer la métrique de compétence couche-2 (signal vivant, EDR 096)

Date : 2026-06-24

Remplacer dans `stoneage_competence` le terme d'autel MORT (pondéré 0.6) par une **échelle moyens→ends
de signaux VIVANTS** (apex coop / lance), agrégés par **fraction de participation** (rare-event-aware),
pour que la compétence gradue au-delà de la chasse triviale et reflète la vraie hiérarchie de
comportements — débloquant la graduation du curriculum.

## Contexte

EDR 096 : sur stoneage, l'autel n'a aucun code de résolution → `altars_solved ≡ 0`. Or
`stoneage_competence` (`src/curriculum/competence.py:45-58`) le pondère 0.6 → la compétence s'effondre
à `0.4 × médiane(chasse)`, une métrique morte. Pourtant le substrat produit des comportements durs
VIVANTS : apex-prédation (mammouth, 21.7% des agents) et craft de lance (1.6%). Cf.
[[world-floor-survivability-gate]] (reframe couche 2), méta-leçon [[nas-bottleneck-is-substrate-not-search]]
(le goulot est le répertoire moyens→ends vivant).

**Piège central (à NE PAS reproduire)** : l'agrégateur actuel est la MÉDIANE (`_median_norm`). Les
signaux vivants sont des conduites de MINORITÉ (apex 21.7%, lance 1.6%) → leur médiane sur tous les
agents est 0 (EDR 094, lavage médian). Remplacer juste le champ sans changer l'agrégateur déplacerait
l'artefact (un autre zéro). La réparation change DONC l'agrégateur : **fraction d'agents atteignant le
barreau** (binaire par agent → aussi robuste à l'inflation de crédit-groupe d'EDR 028 : un agent crédité
de 1 ou 5 kills compte une fois).

## Périmètre

Réparer `stoneage_competence` UNIQUEMENT (la fonction diagnostiquée par EDR 096). `industrial`/`gym`
souffrent du même lavage-médiane sur `altars_solved` mais sont marquées PROVISOIRE pour d'autres mondes
où l'autel n'est peut-être pas mort → hors périmètre (YAGNI). `_median_norm`, `soup_competence`,
`survival_competence`, le registre et les signatures restent inchangés.

## Architecture — approche A (réparation en place)

Modif ciblée de `src/curriculum/competence.py`. Le registre `COMPETENCE_REGISTRY`/`competence_for` et
la signature `List[Dict] -> float` sont inchangés → consommateurs (`CurriculumRunner`, transfert)
intacts.

### Unité 1 — helper pur `_frac_reaching`

`_frac_reaching(agent_stats: List[Dict], key: str, threshold: float = 1.0) -> float` : fraction des
agents avec `a.get(key, 0) >= threshold`. Liste vide → 0.0. Rare-event-aware ; binaire par agent →
neutralise l'inflation de crédit-groupe. C'est l'agrégateur des barreaux VIVANTS (distinct de
`_median_norm`, conservé pour les métriques de survie/homéostasie).

### Unité 2 — `stoneage_competence` réparée

Échelle moyens→ends sur fractions de participation à des champs vivants (confirmés EDR 096) :

```
frac_hunt = _frac_reaching(stats, "preys_eaten")     # chasse triviale (~0.5)
frac_apex = _frac_reaching(stats, "mammoth_kills")   # apex coop (~0.22)
frac_tool = _frac_reaching(stats, "spears_crafted")  # lance, bonus (~0.016)
competence = clip(W_HUNT*frac_hunt + W_APEX*frac_apex + W_TOOL*frac_tool, 0, 1)
```

Poids (constantes module, conservent le split historique chasse 0.4 / avancé 0.6, l'avancé allant
majoritairement à l'apex) :

```
W_HUNT = 0.4    # chasse triviale (plancher)
W_APEX = 0.45   # apex-prédation coop (barreau dur vivant)
W_TOOL = 0.15   # lance (pathway outil, froid mais récompensé pour le nudge)
```

Somme des poids = 1.0, chaque `frac_*` ∈ [0,1] → `competence` ∈ [0,1] (clip de sécurité). Pas de
division par une réf arbitraire (≠ `_median_norm`). Docstring réécrite (le commentaire actuel
« altars 0.6 » est FAUX). La constante `ALTAR_REF` reste dans le fichier (lue par `industrial`/`gym`
PROVISOIRE) mais n'est plus utilisée par stoneage.

### Vérification numérique (données réelles EDR 096)

frac_hunt 0.505, frac_apex 0.217, frac_tool 0.016 →
`0.4·0.505 + 0.45·0.217 + 0.15·0.016 ≈ 0.302` — VIVANT, au-dessus du plancher (vs ancienne ~0.07),
et gradué (chasse seule plafonne à `0.4·frac_hunt ≈ 0.20` ; l'apex pousse à ~0.30).

## Garde-fous anti-théâtre

- **La validation est un TEST, pas une promesse** : un test de **non-plancher gradué** reproduit les
  fractions réelles EDR 096 et exige `competence > 0.15` ET `> ` celle d'une population identique mais
  `mammoth_kills=0` partout. Preuve mesurée que l'apex est vivant et compte (pas un swap cosmétique).
- **Inflation-robustesse testée** : un agent à `mammoth_kills=5` doit donner la même fraction qu'à
  `mammoth_kills=1` (binaire ≥ seuil).
- **Décomposition** : la fonction reste transparente (somme pondérée de 3 fractions nommées) ; les poids
  sont des constantes module ajustables.
- **Signaux VIVANTS confirmés** (EDR 096) : `preys_eaten`/`mammoth_kills`/`spears_crafted` sont
  incrémentés dans `world_1_stoneage.py` (`:717-723`, `:1210`), contrairement à `altars_solved` (mort).

## Tests (purs, sans biosphère)

- **`_frac_reaching`** : fraction correcte (2/5 → 0.4) ; inflation-robuste (`mammoth_kills=5` ≡ `=1`) ;
  liste vide → 0.0 ; seuil par défaut 1.0.
- **`stoneage_competence`** : plancher quand tous champs 0 → 0.0 ; **non-plancher gradué** (validation
  EDR 096 : fractions réelles → >0.15 ET > population sans apex) ; apex domine (franchir l'apex augmente
  strictement le score vs chasse seule) ; bornes (champs hauts → ≤ 1.0).
- **Non-régression** : `tests/sandbox/test_curriculum_transfer.py` + `test_retention.py` restent verts
  (signature et `_median_norm`/`survival_competence` inchangés).

## Hors périmètre (YAGNI)

- Pas de correction de `industrial`/`gym` (PROVISOIRE, autres mondes).
- Pas de `big_kills` (compteur monde, absent des `agent_stats` par-agent ; la fraction de participation
  apex suffit et évite le plumbing).
- Pas de re-tuning du seuil de graduation du curriculum (le `CurriculumRunner` s'auto-adapte à la
  nouvelle échelle ; un re-tuning éventuel est un chantier distinct, mesuré).
