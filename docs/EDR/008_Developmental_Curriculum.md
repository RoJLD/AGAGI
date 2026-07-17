---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-008
type: EDR
title: "Curriculum Développemental (Axe Ontogénétique)"
status: legacy
gate: foundational
---

# EDR 008 : Curriculum Développemental (Axe Ontogénétique)

## Contexte

Depuis l'EDR 007 (Swarm Biosphere), la fitness n'est plus dictée : la survie EST la mesure. Mais un cerveau vit et meurt dans **un seul monde** (`WORLD_TYPE`), pour 30 ères, puis recommence. Les worlds (`soup`, `stoneage`, `agricultural`, `industrial`) sont des **alternatives**, jamais une **séquence**.

Or la tuyauterie de transfert existe déjà :
- `init_primordial_soup(import_agent_id=...)` réimporte un connectome depuis KuzuDB (`CognitiveSnapshot`) et applique une **neuro-chirurgie** de redimensionnement quand les dimensions diffèrent (`main_biosphere.py`).
- `KEEP_MEMORY=1` transporte la mémoire NTM.

Ces briques sont utilisées pour du transfert *manuel, ponctuel* ("Transfert Interdimensionnel"). Cet EDR les promeut en **pipeline développemental** : un cerveau qui traverse les mondes par maîtrise successive, comme un enfant franchit les stades de Piaget.

C'est l'axe **ontogénétique** (ce qu'un individu maîtrise), orthogonal à l'axe **phylogénétique** des 7 Arcs (ce que le système gagne, version après version).

## Décision (V17.0)

1. **Un cerveau, plusieurs mondes.** Une population n'est plus instanciée *tabula rasa* à chaque monde. Le champion d'un monde maîtrisé est **promu** : son `agent_id` est passé comme `import_agent_id` à la genèse du monde suivant.
2. **Graduation par plateau, pas par compteur.** On ne change pas de monde après N ères fixes. On change quand la **compétence plafonne** (la stagnation devient un signal de *promotion*, recyclant l'« Observateur de Famine Cognitive »).
3. **Compétence ≠ énergie.** Chaque monde définit un **bulletin de notes** (KPI spécifiques au skill), au-delà de la seule énergie.
4. **L'axe est une variable d'expérience.** Le seuil de graduation, la politique de progression et le carry-over mémoire sont des variables soumises au Commandement 15 (1 variable, 30 ères, valide ou revert).

### Échelle de Développement & KPI par monde

Les stats par agent disponibles (`persistence.calculate_life_score`, `base_world.run_era`) : `age`, `energy`, `preys_eaten`, `altars_solved`, `total_dreams`, `total_reflexes`, `last_spoken`.

| Monde | Stade | Compétence cible | KPI de maîtrise (normalisé 0–1) |
|---|---|---|---|
| **0 — Soup** | Sensorimoteur | Homéostasie | `survie = median(age)/age_max` ; `stabilité = energy_stability` (tuner) |
| **1 — Stoneage** | Causalité / outil | Usage d'outils, crafting | `chasse = median(preys_eaten)/P_ref` ; `craft = craft_events/agent` |
| **2 — Agricultural** | Planification | Gratification différée | `horizon = total_dreams/dream_ref` (proxy MCTS) ; `stock = ressources_stockées` |
| **3 — Industrial** | Abstraction / composition | Coopération, chaînes | `coop = social_density` (tuner) ; `chaînes = compositions_outils` |
| **Gym cognitif** | Opérations formelles | Logique / calcul / jeux | `résolution = altars_solved/altar_total` |

**Score de compétence d'un monde** à l'ère *e* :
```
C(e) = Σ_k  w_k · KPI_k(e)        (w_k = poids, Σ w_k = 1, par défaut uniformes)
```
Agrégé sur la population via la **médiane** (robuste aux outliers), pas la moyenne.

### Critère de graduation (détection de plateau)

Une population **diplôme** du monde courant quand, sur une fenêtre glissante de `W` ères (défaut `W=5`) :

```
PLATEAU   : pente_OLS( C(e-W..e) )  <  ε_plateau      (défaut ε = 0.01 / ère)
ET PLANCHER : median( C(e-W..e) )   ≥  C_floor         (défaut 0.6)
ET PATIENCE : la condition tient sur K ères consécutives (défaut K=2)
```

- **PLATEAU** seul ne suffit pas : un plateau *bas* (population qui stagne dans la médiocrité) ne doit pas promouvoir → garde-fou `C_floor`.
- **Garde-temps** : un `MAX_ERAS_PER_WORLD` (défaut 30) force la promotion (ou l'abandon) même sans plateau, pour éviter un blocage.
- **Anti-entrenchment** : `C_floor` *modéré* (0.6, pas 0.95) est délibéré — sur-maîtriser un monde simple peut *entrener* (overfit aux quirks) et ralentir le transfert. « Assez bon puis on avance » est l'hypothèse par défaut, à tester contre la maîtrise totale.

### Protocole de transfert (promotion)

À la graduation du monde *N* → *N+1* :
1. Sélectionner le **champion** (meilleur `calculate_life_score` de la dernière ère).
2. Récupérer son `agent_id = champion["id"][:8]` (déjà la clé des `CognitiveSnapshot`).
3. Instancier le monde *N+1* avec `init_primordial_soup(import_agent_id=agent_id, keep_memory=...)`.
4. La neuro-chirurgie existante redimensionne le connectome si les I/O changent (`add_node` implicite).

### Politique de progression

- **Linéaire** (défaut) : `0 → 1 → 2 → 3 → gym`.
- **Adaptative** : le Supervisor choisit le prochain monde selon le KPI le plus faible (lien `SupervisorLoop`).
- **Branchante** : des espèces graduent vers des mondes différents (lien co-évolution des architectures, Améliorations § 2). Hors scope V17.0.

## Conséquences

- La simulation passe de « 30 ères dans un monde fixe » à un **pipeline de mondes à portes de maîtrise**. La "2ᵉ échelle de temps" devient observable.
- **Risque : oubli catastrophique** (entrer dans le monde N+1 écrase les skills de N). Parades prévues (hors scope strict de cet EDR, voir roadmap § Relicat) : périodes critiques (gel des sous-réseaux précoces), rehearsal interleaved, réseaux progressifs.
- **Risque : entrenchment** mitigé par `C_floor` modéré + garde-temps.
- La fonction de graduation reste **paramétrable et testable** : `ε_plateau`, `C_floor`, `W`, `K`, `MAX_ERAS_PER_WORLD` sont des variables d'expérience.

## Questions ouvertes

- Pondération `w_k` des KPI : uniforme, ou apprise par le Supervisor ?
- Le carry-over NTM (`KEEP_MEMORY`) aide-t-il ou nuit-il au transfert ? (À mesurer : avec vs sans.)
- Promotion d'**un** champion vs d'une **cohorte** (top-k) — la diversité génétique au transfert influence-t-elle la vitesse d'adaptation ?
