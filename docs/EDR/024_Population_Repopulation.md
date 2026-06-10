# EDR 024 : Progrès au niveau Population — fin des agents inertes dans la régénération

## Contexte — étape 3 de la Vague 0bis

L'élite évolue (preys 6→15, EDR 016) mais la **moyenne de population restait plate**. On a
inspecté la régénération inter-ère (`init_primordial_soup`).

### Diagnostic : 67 % de la population était INERTE

```python
for score, genome, stats in valid_hof:
    genomes.append(genome)                       # champion
    while len(genomes) < num_agents and np.random.rand() < 0.2:   # ~0.25 enfant/champion
        genomes.append(apply_mutations(...))
# Compléter avec de l'aléatoire pur :
while len(genomes) < num_agents:
    W = np.zeros((N, N))                          # <-- connectome NUL = agent INERTE
```

Mesuré (HoF de 10 champions, population de 30) : **10 non-inertes + 20 inertes (W=zéros)** =
**67 % d'agents do-nothing** (logits nuls → aucune action). La pièce géométrique `rand()<0.2`
donnait ~0 enfant. La moyenne était **mécaniquement plombée au plancher** par la majorité inerte,
quelle que soit l'amélioration de l'élite. Ce n'était pas « trop de mutation » mais « **pas de
descendance des bons génomes, comblée par du vide** ».

## Décision (V18.11)

`src/seed_ai/repopulation.build_population(champions, num_agents, mut_config, mutate_fn,
heavy_config, heavy_frac)` : **toute la population descend des champions**.
- Élitisme : les champions passent intacts.
- Le reste = enfants mutés (round-robin sur les champions), **jamais de W=zéros**.
- Dosage **explore/exploit** : `heavy_frac=0.3` des enfants subissent une mutation FORTE
  (diversité), le reste une mutation standard (raffinement).

## Résultat

| | Avant | Après |
|---|---|---|
| Composition (pop 30, HoF 10) | 10 actifs / **20 inertes** | **30 actifs / 0 inerte** |
| Moyenne life_score (8 ères) | plancher | **~40–120** (saine, réactive) |

- Le **plancher est levé** : chaque agent agit et descend d'un champion. 106 tests verts.
- *Honnêteté* : sur 8 ères bruitées, **pas de montée monotone claire** (la variance inter-ère
  domine à court horizon) — mais la moyenne n'est plus épinglée au sol et répond à la sélection.

## Limites & suites

- **Explore/exploit** (`heavy_frac`, intensités de mutation) = variables d'expérience à calibrer ;
  c'est le levier de diversité vs convergence.
- **Cold-start tabula rasa** (HoF vide) remplit encore en W=zéros inertes — toléré car l'ε-greedy
  (EDR 019) force les actions en entraînement ; à revoir pour les runs hors curriculum.
- Montée de la moyenne à mesurer sur un horizon plus long (et avec la sélection consolidée).

## Variables d'expérience

`heavy_frac`, intensités `heavy_config`, taille du HoF (nb de champions parents), num_agents.
