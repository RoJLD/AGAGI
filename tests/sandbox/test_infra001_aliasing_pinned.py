"""P2.64 (2026-09-15) — l'ALIASING de production d'[[EDR-INFRA-001]] est ÉPINGLÉ, pas corrigé.

Le défaut : `TorchPopulationModel.forward` renvoie une VUE de `self.H`, et le MONDE écrit dans les logits
qu'il reçoit (`world_1_stoneage.py` : pénalité anti-répétition `logits[last_action] -= 0.1`, consensus
social `batch_logits[idx] = consensus_logits`) — donc chaque écriture du monde MUTE l'état récurrent.
INFRA-001 l'a mesuré NON INERTE : 3/6 génomes persistés diffèrent entre pop aliasée et pop découplée, jusqu'à
+37 % (ag02, `[50.5, 46.0, 55.0]` vs `[35.0, 36.0, 41.0]`). Ces six génomes ne sont pas versionnés : on
rejoue ici le MÊME dispositif (`_torch_survival_eras`, étalon `GroundTruthCarryWorld`, W gelé) sur des
génomes FRAIS seedés, et on gèle le fait — pas la valeur (E25).

La correction (renvoyer une copie côté monde) change TOUTES les baselines torch ; elle est reportée après le
run P4.4, sur décision (P1.4). D'ici là, ce fichier doit rester VERT : s'il rougit, c'est que l'aliasing a
été corrigé quelque part — alors mettre à jour INFRA-001, re-mesurer les baselines torch, et retirer ce
gel EN LE DISANT.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.agents.mamba_agent import MambaAgent  # noqa: E402
from tools.ground_truth_worlds import GroundTruthCarryWorld  # noqa: E402
from tools.warmstart_evolution_inworld import COG_DEFAULT, METAB_DEFAULT, _torch_survival_eras  # noqa: E402

# Régime de la re-mesure (2026-09-15, bail libre) : 4 génomes frais, 2 diffèrent, 2 « idem » dont un au
# plancher de drain (9,0 — cf. bandeau du 2026-09-02 : idem au plancher ne prouve pas l'inertie).
_KW = dict(seed=2026, K=2, num_agents=6, max_ticks=60, metab=METAB_DEFAULT, cog=COG_DEFAULT,
           world_cls=GroundTruthCarryWorld)
_GENOMES_QUI_DIFFERENT = (101, 102)      # mesurés : [50.5, 44.5] vs [47.0, 45.5] ; [14.0, 13.5] vs [14.5, 12.5]


def _genome(seed):
    np.random.seed(seed)
    return MambaAgent().genome


def _aliase(g):
    # pop torch NUE : le monde écrit dans la vue -> H muté (défaut 1 d'INFRA-001)
    return _torch_survival_eras(g, False, ablate_kind="perception", **_KW)


def _decouple(g):
    # `_DecoupledTorchPop` : `forward` renvoie une COPIE, les écritures du monde n'atteignent plus H
    return _torch_survival_eras(g, False, ablate_kind="grab_off", **_KW)


def test_the_world_still_writes_into_the_logits_it_receives():
    """Les DEUX sites d'écriture nommés par INFRA-001 existent toujours. S'ils disparaissent, l'aliasing
    n'a plus de porteur côté monde : mettre à jour le record, pas ce test."""
    import src.worlds.world_1_stoneage as W
    src = open(W.__file__, encoding="utf-8").read()
    assert 'logits[agent["last_action"]] -= 0.1' in src, "pénalité anti-répétition : site disparu"
    assert "batch_logits[idx] = consensus_logits" in src, "consensus social : site disparu"


@pytest.mark.parametrize("gseed", _GENOMES_QUI_DIFFERENT)
def test_aliasing_is_NOT_inert_survival_differs_between_aliased_and_decoupled_pop(gseed):
    """LE GEL : même génome, même seed, même étalon, W gelé — seule diffère la prise en compte des
    écritures du monde dans H. Les survies d'ère DIFFÈRENT : l'aliasing agit (INFRA-001, défaut 1)."""
    g = _genome(gseed)
    alias, decoup = _aliase(g), _decouple(g)
    assert len(alias) == len(decoup) == 2
    assert alias != decoup, (
        f"génome {gseed} : aliasé {alias} == découplé {decoup}. L'aliasing est devenu INERTE ou a été "
        f"CORRIGÉ : mettre à jour EDR-INFRA-001 et re-mesurer les baselines torch (P1.4/P2.64).")


def test_decoupled_pop_is_deterministic_so_the_difference_above_is_the_aliasing_not_noise():
    """NO-OP apparié : deux passes découplées sur le même génome sont bit-identiques -> l'écart du test
    précédent ne peut pas être du bruit de simulation."""
    g = _genome(_GENOMES_QUI_DIFFERENT[0])
    assert _decouple(g) == _decouple(g)
