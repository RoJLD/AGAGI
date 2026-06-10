"""
Régénération de population à partir du Hall of Fame — cf. docs/EDR/024.

Bug (EDR 024) : la régénération inter-ère gardait les champions puis **remplissait le
reste avec des connectomes W=zéros INERTES** (67 % de la population) → la moyenne ne
pouvait jamais monter, seule l'élite évoluait.

Fix : toute la population descend des champions. Élitisme (champions intacts) + enfants
mutés (round-robin), avec un dosage **explore/exploit** : la plupart raffinés (mutation
standard), une fraction fortement mutés (diversité). Plus aucun agent inerte.
"""
import copy


def build_population(champions, num_agents, mut_config, mutate_fn,
                     heavy_config=None, heavy_frac=0.3):
    """Construit `num_agents` génomes à partir des `champions` du HoF.

    champions   : liste de Genome (les meilleurs, sauvés au HoF).
    mutate_fn   : fonction (genome, mut_config) -> genome muté (apply_mutations).
    heavy_config: config de mutation FORTE pour la fraction exploratrice (ou None).
    heavy_frac  : part des enfants soumis à la mutation forte (explore).

    Élitisme : les champions passent intacts. Le reste = enfants mutés (round-robin sur
    les champions). JAMAIS de W=zéros inerte. Renvoie exactement num_agents génomes
    (ou moins si pas de champion).
    """
    if not champions or num_agents <= 0:
        return []

    pop = []
    for g in champions:                      # élite intacte (exploit pur)
        if len(pop) >= num_agents:
            break
        pop.append(g)

    n_children = max(0, num_agents - len(pop))
    n_heavy = int(round(heavy_frac * n_children)) if heavy_config is not None else 0

    slot = 0
    while len(pop) < num_agents:
        parent = champions[slot % len(champions)]
        cfg = heavy_config if slot < n_heavy else mut_config   # explore d'abord, puis exploit
        pop.append(mutate_fn(copy.deepcopy(parent), cfg))
        slot += 1

    return pop
