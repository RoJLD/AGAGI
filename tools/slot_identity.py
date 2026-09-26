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
