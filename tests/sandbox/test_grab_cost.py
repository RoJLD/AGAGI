"""Calibration des trois classes d'ablation du GRAB (P4.1, `EDR-GRAB-COST`).

Le resultat -- retirer le grab AMELIORE la survie de 39 % dans un regime ou grabber NOURRIT -- ne vaut
que si l'instrument est lisible. Deux proprietes le rendent lisible, et les deux sont MESUREES ici :

  1. le PLANCHER DE BRUIT est EXACTEMENT NUL. `NullGrabOffMamba` fait le meme travail que l'ablation
     (copie, garde d'aliasing, ecriture dans la colonne 24) mais reecrit la valeur lue -> bit-identique.
     ⚠️ C'est la difference structurelle avec `PerceptionAblatedMamba`, qui appelle `derange_rows` et
     CONSOMME des tirages : sa bande de bruit vaut [0,92 ; 1,06], et son propre resultat publie (0,991)
     TOMBE DEDANS. Ecrire une constante dans une sortie ne consomme aucun tirage ;
  2. la manipulation INVERSE existe. Sans `GrabForcedMamba`, « grab_off survit mieux » resterait
     compatible avec « toute perturbation de la colonne 24 aide ». Mesure : elle n'aide PAS (10+/18-).
"""
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent
from tools.s2_demand_ablation import (_GRAB_LOGIT, GrabForcedMamba, GrabOffMamba, NullGrabOffMamba)

_N = 4


def _sortie(cls):
    ags = [MambaAgent() for _ in range(_N)]
    obs = np.zeros((_N, ags[0].genome.num_inputs), dtype=np.float32)
    preds, _ = cls(ags).forward(obs)
    return np.asarray(preds)


def test_the_grab_logit_index_matches_the_WORLD():
    """L'indice n'est pas un choix : le monde lit `do_grab = float(logits[24])` et le seuille a `> 0`
    (`src/worlds/world_1_stoneage.py`). Si le monde changeait d'indice, l'ablation viserait une AUTRE
    action et le record deviendrait faux en silence -- ce test l'interdit."""
    import re
    with open("src/worlds/world_1_stoneage.py", encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"do_grab\s*=\s*float\(logits\[(\d+)\]\)", src)
    assert m, "le motif `do_grab = float(logits[N])` a disparu du monde"
    assert int(m.group(1)) == _GRAB_LOGIT, (
        f"le monde lit logits[{m.group(1)}], l'ablation vise {_GRAB_LOGIT}")


def test_the_ablation_and_its_INVERSE_write_OPPOSITE_signs():
    """`GrabOff` force le logit NEGATIF (grab off), `GrabForced` le force POSITIF (grab a chaque tick).
    Le seuil du monde etant `> 0`, ce sont bien les deux issues opposees de la meme action."""
    off = _sortie(GrabOffMamba)[:, _GRAB_LOGIT]
    forc = _sortie(GrabForcedMamba)[:, _GRAB_LOGIT]
    assert (off <= 0).all(), off
    assert (forc > 0).all(), forc


def test_the_NOOP_leaves_the_column_UNTOUCHED():
    """Le no-op doit etre indiscernable du bras intact SUR LA SORTIE : meme copie, meme garde, valeur
    inchangee. C'est ce qui fait de lui un plancher de bruit et non une seconde ablation."""
    ags = [MambaAgent() for _ in range(_N)]
    obs = np.zeros((_N, ags[0].genome.num_inputs), dtype=np.float32)
    from src.agents.mamba_agent import MambaBatchModel
    ref, _ = MambaBatchModel(ags).forward(obs)
    ags2 = [MambaAgent() for _ in range(_N)]
    for a, b in zip(ags2, ags):                       # memes genomes -> meme sortie attendue
        a.genome = b.genome
    nul, _ = NullGrabOffMamba(ags2).forward(obs)
    assert np.array_equal(np.asarray(ref), np.asarray(nul)), "le no-op doit etre BIT-IDENTIQUE"


def test_the_ablation_does_NOT_alias_the_model_state():
    """⚠️ Ecrire dans une sortie de `forward` peut muter l'etat recurrent quand cette sortie est une
    VUE -- c'est le bug d'aliasing d'EDR-WARM-007, qui avait produit dose-reponse, correlations et
    controle negatif COHERENTS pendant une passe entiere. Les trois classes copient, et
    `assert_no_aliasing` tourne a chaque appel ; ce test verifie la propriete de bout en bout."""
    for cls in (GrabOffMamba, NullGrabOffMamba, GrabForcedMamba):
        ags = [MambaAgent() for _ in range(_N)]
        m = cls(ags)
        obs = np.zeros((_N, ags[0].genome.num_inputs), dtype=np.float32)
        preds, _ = m.forward(obs)
        arr = np.asarray(preds)
        internes = [v for k, v in vars(m).items() if isinstance(v, np.ndarray)]
        assert not any(np.shares_memory(arr, v) for v in internes), cls.__name__
        assert arr.base is None or not any(np.shares_memory(arr.base, v) for v in internes), cls.__name__


def test_the_PUBLISHED_numbers_are_INTERNALLY_COHERENT():
    """VALEURS GELEES d'`EDR-GRAB-COST` (30 eres appariees, 3 champions). Purement numerique : ce test
    protege la lecture du record, pas la simulation."""
    intact, noop, off, forc = 29.25, 29.25, 40.75, 28.75
    assert noop == intact, "le plancher de bruit est EXACTEMENT nul -- c'est ce qui rend le reste lisible"
    assert off / intact > 1.35, off / intact          # +39 %
    assert forc < intact, "la manipulation INVERSE va dans le bon sens..."
    assert forc / intact > 0.95, "...mais faiblement : p = 0.185, NON significatif (a ne pas sur-lire)"
    # le bras inverse REFUTE « toute perturbation de la colonne 24 aide » : c'est sa vraie fonction
    assert not (forc > intact), "si forcer aidait aussi, l'effet serait un artefact d'ablation"


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_the_ZERO_noise_floor_REPRODUCES_in_the_world():
    """VERIFICATION DE BOUT EN BOUT, sous bail `kuzu` : le no-op rend la MEME liste de survies que le
    bras intact, dans le vrai monde. C'est la mesure qui autorise a lire le bras ablate contre un
    plancher NUL au lieu des +-8 % de la sonde soeur."""
    # `pickle` : ces .pkl sont les Hall-of-Fame produits LOCALEMENT par les runs d'evolution de ce
    # depot (juillet 2026) ; ils ne viennent d'aucune source externe, et `tools/s2_demand.py`
    # les charge deja ainsi via `load_hall_of_fame`. Aucune donnee non fiable n'est deserialisee.
    import pickle

    from src.worlds.world_famine import FamineWorld
    from tools.jobs.run import hold
    from tools.s2_demand import run_condition
    with open("data/hof_famine_harsh_s42.pkl", "rb") as fh:
        champ = pickle.load(fh)["entries"][0].genome
    kw = dict(num_agents=12, max_ticks=200, n_eras=2)
    with hold("kuzu", owner="test-grab-cost"):
        intact = run_condition(FamineWorld, None, champ, 2026, **kw)
        nul = run_condition(FamineWorld, NullGrabOffMamba, champ, 2026, **kw)
    assert intact["survival"] == nul["survival"], "plancher de bruit NON nul : le record devient illisible"
