# EDR 032 : Ablation systématique + Ontologie scientifique branchée (Vague 1)

## Contexte

Vague 1, leviers 5 (ablation) & 6 (ontologie). Maintenant que la chaîne s'exprime, **mesurer ce
qui compte vraiment** (Commandement 15 retourné sur le projet), et **brancher** l'ontologie
Hypothesis/Fact (schéma déclaré mais resté vide).

## Décision (V18.19)

- **Flags d'ablation** : `MambaBatchModel.ABLATE_THRESHOLDS / ABLATE_ROUTER` (gènes câblés EDR 031) ;
  les leviers du monde s'ablate en réglant leur scale à 0.
- **`ExperimentGraph.log_hypothesis` / `log_fact`** : peuplent enfin `Hypothesis`/`Fact` +
  `SUPPORTS`/`REFUTES` dans KuzuDB. Notre méthode scientifique rendue machine-lisible.
- **`tools/ablation.py`** : désactive un mécanisme à la fois, mesure le Δ de `proies_moy` vs
  baseline (monde fixe, rareté 12, ère 1 = scaffolds pleins, **HoF non muté** = mesure pure sur la
  même population mûre), et **écrit le verdict dans l'ontologie**.

## Résultat — la mesure dit la vérité, même contre nos ajouts

Population **mûre** (HoF de fin de Vague 0), rareté 12, n=5 ères :

| Mécanisme ablé | Δ proies_moy | Lecture |
|---|---|---|
| `scaffold_craft` | **−0.10** | aide (faible) |
| `scaffold_grab` | −0.09 | aide un peu |
| `scaffold_bighit` | −0.01 | neutre |
| `seuils` (EDR 031) | +0.04 | neutre |
| `router` (EDR 031) | +0.12 | *retirer* aide un peu |
| `nouveauté` | +0.15 | *retirer* aide |
| `curiosité` | +0.25 | *retirer* aide |
| `crit` | +0.30 | *retirer* aide |

> **Les scaffolds essentiels à l'ÉMERGENCE sont contre-productifs pour une population MÛRE.**
> Curiosité / nouveauté / crit — vitaux pour qu'un agent *naïf* découvre la chaîne — **distraient
> l'expert** (ils poussent à explorer/parier au lieu d'exploiter l'acquis). L'ablation **quantifie
> le principe de sevrage** (EDR 030 validé a posteriori) : à maturité, ces leviers doivent être
> *entièrement* annealés. Seuls les scaffolds de *tâche* (grab/craft) gardent une valeur résiduelle.
> Le `router` (neuromodulation, EDR 031) ne sert pas la pop mûre : c'est du **substrat pour
> l'évolution future**, pas un booster immédiat.

## Conséquences

1. **Valide le sevrage** : confirme empiriquement qu'il faut anneler curiosité/nouveauté/crit à
   maturité (pas seulement le crit/prime). Action : étendre l'annealing à curiosité & nouveauté.
2. **Feedback sur EDR 031** : `router` léger négatif, `seuils` neutre. Attendu (gènes tout juste
   connectés, l'évolution ne les exploite pas encore). À re-mesurer après évolution ; affiner la
   sémantique du router si confirmé inutile.
3. **Ontologie vivante** : `ablation.py` peuple Hypothesis/Fact. Réutilisable pour tout EDR futur.

## Limites (honnêteté)

- **Un seul réglage** : pop *mûre*, rareté 12, n=5 (bruité, σ≈0.15) → les petits Δ (±0.1) sont au
  ras du bruit ; seuls curiosité/crit/nouveauté sont du signal net. Une pop *naïve* inverserait le
  verdict (les scaffolds y sont vitaux). L'ablation mesure « utile à l'expert ? », pas « utile à
  l'émergence ? » — deux questions distinctes.

## Variables d'expérience

Maturité de la population (naïve vs mûre), rareté, n_eras, métrique (proies vs mammouth vs craft).
