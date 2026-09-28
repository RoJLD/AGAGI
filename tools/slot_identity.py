"""E34 (P2.132) — l'identité portée par une POSITION qui bouge : invariant slot W ↔ corps, et sa remise en ordre.

La population torch persistante d'un monde (`Biosphere3D._torch_pop`, `src/agents/backend_torch.py`) aligne ses
tranches PAR INDEX : la tranche j de `W`, de `H` et de la transition TD en attente appartient à `pop.agents[j]`
(ordre de CONSTRUCTION ; `_write_back` écrit `W[j]` dans `pop.agents[j].genome`). Le monde, lui, passe à chaque
tick les observations et reçoit les logits dans l'ordre COURANT de `e.agents`. Les deux ne restent alignés que si
personne ne réordonne `e.agents` sans reconstruire la population — or le monde ne reconstruit que quand la TAILLE
change (`world_1_stoneage.py:1060-1066`), et la recette de résurrection d'une cohorte immortelle
(`tools/evo_runs/s2_credit_retention.py::immortal_refill`) rend la taille en remettant le mort en FIN de liste :
après une mort en position p, les tranches p..B-1 pilotent chacune le corps d'un autre.

Ce module ne touche ni au monde ni à la population. Il fournit :
  * `slot_identity_violations(e)` — l'INVARIANT, en lecture seule, sans aucun tirage RNG : la liste des tranches
    dont le prochain `forward` apparierait les poids à un AUTRE corps. `None` quand l'appariement n'est pas
    connu (pas de population, ou population dont la taille diffère : le monde la reconstruira) — jamais `[]` par
    défaut : une absence de mesure n'est pas un alignement mesuré.
  * `restore_slot_order(e)` — le correctif : remet `e.agents` dans l'ordre de construction de la population.
    N'est appelé que sous drapeau (défaut = comportement publié, au bit).
"""


class SlotIdentityError(RuntimeError):
    """La cohorte courante ne peut pas être appariée à la population (corps étranger, doublon, taille)."""


def _population(e):
    return getattr(e, "_torch_pop", None)


def slot_identity_violations(e):
    """Tranches j où `pop.agents[j]` n'est PAS le modèle du corps `e.agents[j]` (identité d'objet).

    Rend la liste triée des j fautifs (`[]` = alignement VÉRIFIÉ), ou `None` si l'appariement n'est pas défini :
    pas de population torch, ou `pop.B != len(e.agents)` (le prochain pas reconstruira depuis l'ordre courant)."""
    pop = _population(e)
    if pop is None:
        return None
    slots = getattr(pop, "agents", None)
    if slots is None or getattr(pop, "B", -1) != len(e.agents) or len(slots) != len(e.agents):
        return None
    return [j for j, a in enumerate(e.agents) if slots[j] is not a["model"]]


def population_reindex_refusals(pop):
    """Raisons pour lesquelles `permute_population_rows` REFUSE (liste vide = admis). Périmètre CERTIFIÉ (revue E34 v3,
    décision Master 2) : SGD sans momentum ni autre état d'optimiseur, traces d'éligibilité NON allouées, pas de terme
    bilinéaire (U/V/W_bl portent une tête B qu'il faudrait permuter aussi). Un harnais à trace non nulle (P4.19) n'est
    pas certifié : il devrait permuter aussi les traces."""
    raisons = []
    if getattr(pop, "e_a", None) is not None or getattr(pop, "e_v", None) is not None:
        raisons.append("traces d'éligibilité allouées (e_a / e_v) : hors périmètre certifié")
    if getattr(pop, "_delta_cour", None) or getattr(pop, "_delta_prec", None):
        raisons.append("tampons δ du sham de trace (P4.19 a) non vides : hors périmètre certifié")
    if any(getattr(pop, k, None) is not None for k in ("U", "V", "W_bl")):
        raisons.append("terme bilinéaire (U/V/W_bl) présent : hors périmètre certifié")
    opt = getattr(pop, "opt", None)
    if opt is not None:
        if any(len(s) for s in opt.state.values()):
            raisons.append("l'optimiseur porte un état (momentum ou autre) : hors périmètre certifié")
        if any(float(g.get("momentum", 0.0)) != 0.0 for g in opt.param_groups):
            raisons.append("SGD avec momentum : hors périmètre certifié")
    return raisons


def permute_population_rows(pop, perm):
    """RÉINDEXE la population torch : la nouvelle ligne j est l'ancienne ligne perm[j] — pour W (en place : le paramètre
    de l'optimiseur reste le même objet), H, la transition d'observation `_last`, la transition TD en attente `_prev` et
    `pop.agents`. Rien n'est recalculé, aucun tirage. Refus explicite hors du périmètre certifié
    (`population_reindex_refusals`) ; `perm` doit être une permutation de range(B)."""
    import torch
    B = int(getattr(pop, "B", -1))
    perm = [int(i) for i in perm]
    if sorted(perm) != list(range(B)):
        raise SlotIdentityError(f"permute_population_rows : {perm!r} n'est pas une permutation de range({B})")
    raisons = population_reindex_refusals(pop)
    if raisons:
        raise SlotIdentityError("permute_population_rows refusé : " + " ; ".join(raisons))
    idx = torch.as_tensor(perm, dtype=torch.long)
    with torch.no_grad():
        pop.W.copy_(pop.W.detach()[idx].clone())
    pop.H = pop.H.detach()[idx].clone()
    if pop._last is not None:
        obs_t, h_in = pop._last
        pop._last = (obs_t[idx].clone(), h_in[idx].clone())
    if pop._prev is not None:
        p = pop._prev
        pop._prev = dict(p, obs=p["obs"][idx].clone(), H_in=p["H_in"][idx].clone(), act=[p["act"][i] for i in perm],
                         reward=p["reward"][perm].copy())
    pop.agents = [pop.agents[i] for i in perm]


def restore_slot_order(e):
    """Remet `e.agents` dans l'ordre de CONSTRUCTION de la population (en place). Rend le nombre de positions
    changées (0 = déjà aligné), ou `None` si l'appariement n'est pas défini (cf. `slot_identity_violations`).

    Lève `SlotIdentityError` si un corps porte un modèle absent de la population, ou si deux corps portent le
    même : aucun ordre ne peut alors rétablir l'invariant, et le taire fabriquerait un alignement."""
    pop = _population(e)
    if pop is None:
        return None
    slots = getattr(pop, "agents", None)
    if slots is None or getattr(pop, "B", -1) != len(e.agents) or len(slots) != len(e.agents):
        return None
    rang = {id(m): j for j, m in enumerate(slots)}
    if len(rang) != len(slots):
        raise SlotIdentityError("la population porte deux fois le même modèle : l'appariement n'est pas défini")
    vus = set()
    for a in e.agents:
        k = id(a["model"])
        if k not in rang:
            raise SlotIdentityError(f"corps {a.get('id')!r} : son modèle n'est dans aucune tranche de la population")
        if k in vus:
            raise SlotIdentityError(f"corps {a.get('id')!r} : deux corps portent le même modèle")
        vus.add(k)
    ordonne = sorted(e.agents, key=lambda a: rang[id(a["model"])])
    changes = sum(1 for j in range(len(ordonne)) if ordonne[j] is not e.agents[j])
    e.agents[:] = ordonne
    return changes
