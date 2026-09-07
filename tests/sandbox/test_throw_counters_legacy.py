"""Compteurs de LANCER en régime LEGACY (2026-09-07, défaut 2 du harnais EVO-011).

⚠️ Classe E4 — un compteur qui ne peut lire QUE zéro. `_throw_did` n'est écrit que sous
`use_torch_inworld and torch_throw_gate` : hors torch, il n'existe pas. Toute lecture de « 0 lancer »
en régime legacy était donc un **artefact de compteur**, pas une mesure — et c'est l'un des trois
défauts qui ont bloqué EVO-011 au pré-vol le 2026-08-03.

Ces tests gèlent trois réponses connues, en LEGACY pur (jamais de torch) :
  1. la DÉCISION de lancer est comptée AVANT le gate d'inventaire (sans quoi le défaut E2 « throw
     gaté par l'inventaire » reste invisible : décidé mais jamais exécuté) ;
  2. le lancer EXÉCUTÉ est compté, torch ou non ;
  3. la PHYSIQUE du monde telle qu'elle est : un lancer sur une proie l'ÉTOURDIT, il ne la tue pas —
     une proie n'a pas de clé `energy` (`_spawn_prey_instance`), donc la branche `else` du bloc
     balistique pose `stunned`. C'est le 4ᵉ défaut, trouvé DANS le design scellé d'EVO-011 (qui fait
     peser `mammoth_kills` 400 sur une chaîne obs[4]→throw→kill qui n'existe pas).
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig  # noqa: E402
from src.agents.mamba_agent import MambaAgent                     # noqa: E402


def _world():
    w = Biosphere3D(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.benchmark_mode = True          # cohorte fixe : pas de naissance, pas de repro
    w.current_era = 10_000           # scaffolds/critiques annelés à 0
    return w


def _thrower(w, avec_lance=True):
    """Un agent dont le logit de lancer est POSITIF par câblage explicite (canal constant → sortie 8),
    donc `do_throw` est vrai sans dépendre d'aucun tirage."""
    a = MambaAgent()
    g = a.genome
    o = g.num_nodes - g.num_outputs
    g.W[:] = 0.0
    np.fill_diagonal(g.W, 10.0)      # réflexe : l'état suit l'entrée (sinon la dérive noie le signal)
    g.W[6, o + 8] = 5.0              # obs[6] = canal constant 1.0 -> logits[8] = tanh(5) > 0
    w.add_agent(a, energy=80.0)
    ag = w.agents[-1]
    ag["inventory"] = [{"type": "Spear", "weight": 0.5}] if avec_lance else []
    return ag


def test_a_thrown_spear_is_counted_in_legacy_mode():
    """RÉPONSE CONNUE : l'agent décide ET exécute -> les deux compteurs montent, l'inventaire se vide.
    Sans le patch, `throws` n'existait pas hors torch (E4)."""
    np.random.seed(7)
    w = _world()
    ag = _thrower(w)
    w.step()
    assert ag["throw_decided"] >= 1, "la DÉCISION de lancer doit être comptée"
    assert ag["throws"] >= 1, "le lancer EXÉCUTÉ doit être compté en legacy"
    assert ag["inventory"] == [], "la lance quitte l'inventaire"


def test_the_decision_is_counted_even_when_the_inventory_gate_blocks_it():
    """⚠️ LE cas qui rend le défaut E2 LISIBLE : sans lance, l'agent DÉCIDE de lancer et le gate
    `len(inventory) > 0` l'en empêche. Un compteur posé APRÈS le gate afficherait 0/0 et ferait
    conclure « l'agent ne lance jamais » — alors qu'il essaie à chaque tick."""
    np.random.seed(7)
    w = _world()
    ag = _thrower(w, avec_lance=False)
    w.step()
    assert ag["throw_decided"] >= 1, "la décision existe même sans projectile"
    assert ag["throws"] == 0, "et elle n'est PAS exécutée : c'est exactement le défaut E2"


def test_a_silent_genome_throws_nothing():
    """SPÉCIFICITÉ — sans ce test, des compteurs qui montent toujours passeraient les deux précédents.
    Génome nul : `logits[8] = 0`, `do_throw = logits[8] > 0` est FAUX."""
    np.random.seed(7)
    w = _world()
    a = MambaAgent()
    a.genome.W[:] = 0.0
    w.add_agent(a, energy=80.0)
    ag = w.agents[-1]
    ag["inventory"] = [{"type": "Spear", "weight": 0.5}]
    w.step()
    assert ag["throw_decided"] == 0 and ag["throws"] == 0
    assert ag["inventory"], "rien n'a été lancé"


def test_a_hit_prey_is_STUNNED_not_killed_by_a_throw():
    """⚠️ RÉPONSE CONNUE de PHYSIQUE, et 4ᵉ défaut d'EVO-011 — il est dans le DESIGN SCELLÉ.
    Le bloc balistique fait `hit_entity["energy"] -= damage` SI la clé existe, `stunned` SINON. Une
    proie n'a que `{x, y, type, stunned, hp}` : un lancer ne peut donc PAS tuer, et `mammoth_kills`
    (que la règle scellée fait peser 400) n'est incrémenté que par la mêlée. La chaîne
    obs[4]→throw→kill de la règle est COUPÉE par construction — ce test le grave.
    """
    np.random.seed(7)
    w = _world()
    w.preys = []
    ag = _thrower(w)
    proie = {"x": ag["x"], "y": (ag["y"] + 1) % w.size, "z": ag.get("z", 0),
             "type": "Mammouth", "stunned": 0, "hp": 100.0}
    w.preys.append(proie)
    assert "energy" not in proie, "une proie n'a pas de clé `energy` — c'est la cause du défaut"
    for _ in range(3):
        w.step()
        if ag.get("throw_prey_hits", 0):
            break
    if ag.get("throw_prey_hits", 0):
        assert proie["hp"] == 100.0, "un lancer n'ENLÈVE PAS de hp à une proie"
        assert proie["stunned"] > 0, "il l'ÉTOURDIT — c'est le seul effet disponible"
    else:
        # La visée par défaut (+y) et la position sont déterministes, mais la proie peut avoir été
        # consommée/déplacée par la boucle : on n'affirme alors RIEN sur un tir qui n'a pas eu lieu.
        assert ag["throw_decided"] >= 1, "au minimum, la décision de lancer a bien été comptée"
