# EDR 015 : World Model par-agent — et clôture de l'arc exploration de V0

## Contexte

Dernier levier de l'exploration (EDR 014, levier I « curiosité forte ») : donner à
**chaque agent son propre World Model** (raffinement noté dans l'EDR 011), pour une
curiosité par-agent censée moins saturer que le modèle partagé/linéaire.

## Décision (V18.2)

World Model **par agent** : `P` (projection cible) reste **partagée** (cible commune
comparable), mais `Wp` (prédicteur appris) devient **par agent**, round-trip via les
agents comme `last_obs` (`world_model.observe_batch`, `mamba_agent.MambaBatchModel`).

Chaque agent apprend son prédicteur depuis **sa propre trajectoire**.

## Résultat — contre-intuitif, et concluant

Micro-test (surprise par-agent) : t5 = **0.125** (plus haute au départ) → t60 = **0.005**
(plus basse en régime que le partagé ~0.03). Run complet (30 ères) : **SPEAR_CRAFTED 3 → 4**
(+1, marginal), surprise globale ~0.015.

> **Le World Model par-agent fait l'inverse de l'espoir.** Chaque agent apprend *sa*
> trajectoire — plus simple et plus prévisible que la moyenne de population — donc son Wp
> converge encore plus vite et la surprise résiduelle est **encore plus basse**. La
> curiosité par-agent est plus forte au démarrage mais **plus faible en régime**.

## Clôture de l'arc exploration de V0

Bilan chiffré de tous les leviers d'incitation testés (lances craftées / run de 30 ères) :

| Levier | Lances/run |
|---|---|
| Reward-shaping (scaffold grab/craft) | 0 |
| Curiosité World Model (partagé) | 0 |
| Nouveauté count-based (inventaire) | +1 |
| Nouveauté + curiosité ×2 (boost) | +1 |
| World Model par-agent | +1 |

> **Conclusion rigoureuse** : cinq mécanismes, deux magnitudes — toujours ~1 lance/run.
> Le goulot n'est **pas** la magnitude d'incitation. C'est la **profondeur de la chaîne** :
> `grab→grab→rub` est une séquence de 3 actions coordonnées qu'une politique faible
> n'exécute quasi jamais, *peu importe* comment on récompense les états précurseurs.
> L'hypothèse « plus d'exploration → le craft émerge » est **falsifiée**.

## Conséquences — les deux seules voies restantes

- **(II) Réduire la profondeur de chaîne — auto-craft** : la lance se forme en tenant
  `rock+stick` (collapse `grab→grab→rub` → `grab→grab`). La nouveauté count-based pousse
  déjà vers cet état → le craft deviendrait **commun**. La donnée soutient ce choix.
  Permet enfin d'étudier les **conséquences** du craft (chasse au Mammouth, chaîne
  moyens→fins complète) — le vrai objet de recherche.
- **(III) Curriculum de sous-compétences** : enseigner `grab`, puis `rub`, séparément
  (CurriculumRunner sur sous-tâches) avant de les composer. Plus ambitieux.

Le World Model par-agent reste un acquis de Step 1 (curiosité individualisée), même s'il
ne sert pas le craft. À conserver ou simplifier selon le coût/bénéfice mesuré ultérieurement.

## Variables d'expérience

Portée du World Model (partagé vs par-agent), `lr` du World Model, profondeur de la chaîne
de craft (le vrai levier identifié).
