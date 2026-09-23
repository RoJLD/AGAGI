import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, rank=8)
    assert set(r) >= {"plain_median", "bilinear_median", "unlocked", "per_seed",
                      "bar_status", "ceiling_is_proven"}
    assert r["n"] == 2 and len(r["per_seed"]["plain"]) == 2 and len(r["per_seed"]["bilinear"]) == 2
    # ⚠️ P2.15 (2026-09-07) : ce test assertait `isinstance(r["unlocked"], bool)`. La sonde ne CERTIFIE
    # plus tant qu'aucune borne SUPÉRIEURE PROUVÉE du bras incapable n'est déclarée — elle rend `None`
    # et le DIT dans `bar_status`. Un `bool` ici voudrait dire « verdict rendu », ce qui serait un
    # mensonge : le plafond du plain a monté trois fois en une journée (14/36 -> 30/36 -> 34/36).
    assert r["unlocked"] is None and r["bar_status"] in ("CEILING_IS_MINORANT", "UNVALIDATED")
    assert r["ceiling_is_proven"] is False
    # ...et le verdict REDEVIENT un booléen dès qu'une borne prouvée est déclarée : sans ce second
    # volet, « ne certifie jamais » serait indiscernable de « ne sait pas certifier ».
    r2 = run_bilinear_composition_probe(
        seeds=[0], episodes=10, n_agents=4, K=4, rank=8,
        incapable_ceiling=0.30, ceiling_is_proven=True,
        ceiling_provenance="borne superieure PROUVEE par MILP a gap nul, cas de test")
    assert isinstance(r2["unlocked"], bool) and r2["bar_status"] == "SEPARATES_PROVEN"


# --------------------------------------------------------------------------------------------------
# P2.70 (2026-09-15) — alignement ENTRAINEMENT / EVAL. La sonde evalue `argmax` sur `[:K]` mais le softmax
# supervise portait sur les 8 logits de mouvement : deux distracteurs recevaient du gradient. Le seam
# `n_classes` (backend) / `align_train_eval` (sonde) est bit-identique par defaut, et son effet se mesure.
# --------------------------------------------------------------------------------------------------

def _pop(seed, n=4):
    import numpy as np, torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    np.random.seed(seed); torch.manual_seed(seed)
    return make_population([MambaAgent() for _ in range(n)], backend="torch")


def _one_imitation(pop, n_classes, seed=3):
    import numpy as np, torch
    rng = np.random.RandomState(seed)
    obs = [rng.uniform(-1, 1, (pop.B, pop.I)).astype(np.float32)]
    tgt = [rng.randint(0, 6, size=pop.B)]
    pop.opt = torch.optim.Adam([pop.W], lr=0.02)
    pop.imitate_episode_bptt(obs, tgt, n_classes=n_classes)
    return pop.W.detach().cpu().numpy().copy()


def test_n_classes_default_is_bit_identical_to_the_historical_8():
    a = _one_imitation(_pop(0), n_classes=None)
    b = _one_imitation(_pop(0), n_classes=8)
    import numpy as np
    assert np.array_equal(a, b)


def test_n_classes_K_removes_the_gradient_from_the_two_distractor_logits_and_only_them():
    """K=6 : les colonnes des noeuds de sortie 6 et 7 (distracteurs) ne bougent PLUS ; celles des noeuds
    0..5 bougent toujours. Sous le defaut (8), les colonnes 6 et 7 bougent : c'est le desalignement."""
    import numpy as np
    p0 = _pop(1); W0 = p0.W.detach().cpu().numpy().copy(); base = p0.N - p0.O
    Wa = _one_imitation(_pop(1), n_classes=6)
    Wd = _one_imitation(_pop(1), n_classes=None)
    moved = lambda W, j: not np.allclose(W[:, base + j], W0[:, base + j])
    assert all(moved(Wa, j) for j in range(6)), "les 6 classes de la tache apprennent"
    assert not moved(Wa, 6) and not moved(Wa, 7), "aligne : aucun gradient sur les distracteurs"
    assert moved(Wd, 6) and moved(Wd, 7), "defaut historique : les distracteurs recevaient du gradient"


def test_probe_align_flag_is_published_and_default_is_False():
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0], episodes=5, n_agents=4, K=4, rank=8,
                                       same_tick=True, credit_mode="supervised")
    assert r["align_train_eval"] is False
    r2 = run_bilinear_composition_probe(seeds=[0], episodes=5, n_agents=4, K=4, rank=8,
                                        same_tick=True, credit_mode="supervised", align_train_eval=True)
    assert r2["align_train_eval"] is True


# --------------------------------------------------------------------------------------------------
# P4.12 (ADR-005 item 2, 2026-09-16) -- SHAM LINEAIRE A PARAMETRES APPARIES de la piece `bilinear` :
# drapeau de classe BILINEAR_SHAM, memes U/V/W_bl, combinaison additive au lieu du produit. Trois cas :
# OFF = no-op exact ; ON = compte de parametres EGAL (asserte, pas lu) et sortie DIFFERENTE du bilineaire ;
# le drapeau est restaure par la sonde.
# --------------------------------------------------------------------------------------------------

def _bil_pop(seed, sham):
    import numpy as np, torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel as T
    saved = (T.BILINEAR, T.BILINEAR_RANK, T.BILINEAR_SHAM)
    T.BILINEAR, T.BILINEAR_RANK, T.BILINEAR_SHAM = True, 16, bool(sham)
    try:
        np.random.seed(seed); torch.manual_seed(seed)
        pop = make_population([MambaAgent() for _ in range(3)], backend="torch")
        obs = np.random.RandomState(5).uniform(-1, 1, (3, pop.I)).astype(np.float32)
        H = torch.zeros((3, pop.N))
        out = pop._step(torch.tensor(obs), H).detach().cpu().numpy().copy()
        n_params = sum(p.numel() for p in (pop.U, pop.V, pop.W_bl))
        return out, n_params
    finally:
        T.BILINEAR, T.BILINEAR_RANK, T.BILINEAR_SHAM = saved


def test_sham_OFF_is_a_bit_identical_noop_of_the_bilinear_step():
    import numpy as np
    from src.agents.backend_torch import TorchPopulationModel as T
    assert T.BILINEAR_SHAM is False, "defaut = OFF"
    a, _ = _bil_pop(1, sham=False)
    b, _ = _bil_pop(1, sham=False)
    assert np.array_equal(a, b)


def test_sham_ON_has_EXACTLY_the_same_parameter_count_and_a_different_output():
    import numpy as np
    out_bil, n_bil = _bil_pop(1, sham=False)
    out_sham, n_sham = _bil_pop(1, sham=True)          # meme seed -> memes tirages d'init
    assert n_sham == n_bil > 0, "controle a parametres APPARIES : compte egal par construction"
    assert not np.array_equal(out_bil, out_sham), "le sham CHANGE la sortie (somme != produit)"


def test_probe_seam_bilinear_sham_is_off_by_default_and_restores_the_flag():
    from src.agents.backend_torch import TorchPopulationModel as T
    from tools.bilinear_composition_probe import _train_eval_one
    before = T.BILINEAR_SHAM
    a = _train_eval_one(seed=0, bilinear=True, task="composition", episodes=5, n_agents=4, K=4, lr=0.02, rank=8,
                        same_tick=True, credit_mode="supervised")
    b = _train_eval_one(seed=0, bilinear=True, task="composition", episodes=5, n_agents=4, K=4, lr=0.02, rank=8,
                        same_tick=True, credit_mode="supervised", bilinear_sham=False)
    assert a == b and T.BILINEAR_SHAM == before
    _train_eval_one(seed=0, bilinear=True, task="composition", episodes=5, n_agents=4, K=4, lr=0.02, rank=8,
                    same_tick=True, credit_mode="supervised", bilinear_sham=True)
    assert T.BILINEAR_SHAM == before, "le drapeau est restaure apres un run sham"
