"""Calibration du cliquet de calibration LUI-MÊME sur les APPRENANTS (P2.62, 2026-09-15).

Le défaut : `learn`, `learn_episode`, `learn_episode_bptt` (backend torch) et `compute_policy_gradient`
(legacy `MambaBatchModel`, actif pendant tout l'arc EVO) sont des INSTRUMENTS — CLAUDE.md le dit depuis
P1.6 : « l'APPRENANT est un instrument : sa DOSE se publie à côté de tout nul, et il a un contrôle
positif ». Or aucun motif de `_INSTRUMENT_PATTERNS` ne les nommait, ET tous les motifs étaient ancrés
`^def` : une MÉTHODE (indentée) était invisible quel que soit son nom. Le cliquet rapportait « 0 non
calibré » sur un dépôt dont les quatre fonctions qui APPRENNENT n'avaient jamais été comptées.

C'est le ONZIÈME élargissement, et il révèle un CINQUIÈME axe de faillibilité de l'heuristique, après
« ce qu'elle cherche / où / comment elle identifie / sous quels verbes » : à quelle PROFONDEUR (module
ou classe). Ces tests portent sur la couche qui IDENTIFIE, par injection d'un arbre factice (coût nul),
plus un ancrage sur l'arbre RÉEL pour les deux apprenants que P1.6 a calibrés.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_instrument_calibration as M  # noqa: E402

# Arbre factice : les apprenants sont des MÉTHODES (classe), pas des fonctions de module.
_FAUX_ARBRE = [
    ("src/agents/backend_torch.py",
     "class TorchPopulationModel:\n"
     "    def forward(self, obs):\n        return 0\n"
     "    def learn(self, rewards_batch, actions_batch=None):\n        return 1\n"
     "    def learn_episode(self, obs_seq, actions_seq, rewards):\n        return 2\n"
     "    def learn_episode_bptt(self, obs_seq, actions_seq, rewards):\n        return 3\n"),
    ("src/agents/mamba_agent.py",
     "class MambaBatchModel:\n"
     "    def compute_policy_gradient(self, rewards_batch, actions_batch=None):\n        return 4\n"
     "    def _helper(self):\n        return 5\n"),
    ("tools/c.py", "def run_unique():\n    return 6\n"),
]


def test_scan_SEES_the_learners_defined_as_METHODS(monkeypatch):
    """CONTRE-EXEMPLE GELÉ : quatre apprenants indentés dans deux classes, exactement la forme réelle."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    for nom in ("learn", "learn_episode", "learn_episode_bptt"):
        assert found.get(nom) == "src/agents/backend_torch.py", (nom, found)
    assert found.get("compute_policy_gradient") == "src/agents/mamba_agent.py", found


def test_the_widening_is_SPECIFIC_to_the_learner_verbs(monkeypatch):
    """SPÉCIFICITÉ (no-op apparié). Les méthodes `forward` et `_helper` du même arbre ne doivent PAS
    entrer : la tolérance à l'indentation ne vaut que pour les verbes d'apprentissage. Étendre les
    autres motifs aux méthodes est un chantier à part, MESURÉ avant de ne pas l'avaler : +12 définitions
    / 7 noms (`measure` ×3, `sweep` ×2, `run_seed` ×2, `run` ×2, `run_once`, `run_era`,
    `assert_isolated`)."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    assert "forward" not in found and "_helper" not in found, found
    assert found.get("run_unique") == "tools/c.py", "les motifs de module restent intacts"


def test_scan_collisions_SEES_a_learner_defined_in_TWO_files(monkeypatch):
    """`learn` vit dans quatre fichiers réels (backend.py, backend_torch.py, learning_events.py,
    s2_reward_ablation.py) : sa déclaration DOIT être qualifiée « fichier.py::learn », donc le détecteur
    de collisions doit le VOIR. Deux fichiers factices suffisent à le prouver."""
    arbre = [
        ("src/agents/backend.py", "class Legacy:\n    def learn(self, r, a=None):\n        return 0\n"),
        ("src/agents/backend_torch.py", "class Torch:\n    def learn(self, r, a=None):\n        return 1\n"),
    ]
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(arbre))
    assert M.scan_collisions() == {"learn": ["src/agents/backend.py", "src/agents/backend_torch.py"]}


def test_a_BARE_declaration_of_learn_is_REFUSED_and_a_QUALIFIED_one_is_recorded(monkeypatch, tmp_path):
    """La règle de qualification s'applique aux apprenants comme aux autres noms en collision : nue ->
    refusée ET DITE (`refusees`), qualifiée -> le CHEMIN est mémorisé pour `collision_coverage`."""
    arbre = [
        ("src/agents/backend.py", "class Legacy:\n    def learn(self, r, a=None):\n        return 0\n"),
        ("src/agents/backend_torch.py", "class Torch:\n    def learn(self, r, a=None):\n        return 1\n"),
    ]
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(arbre))
    faux = tmp_path / "test_calib.py"
    faux.write_text('CALIBRATED = {\n    "learn": ["*"],\n}\n', encoding="utf-8")
    monkeypatch.setattr(M, "_CALIB_TESTS", str(faux))
    assert M.scan_calibrated() == set()
    assert M.scan_calibrated.refusees == ["learn"]

    faux.write_text('CALIBRATED = {\n    "src/agents/backend_torch.py::learn": ["*"],\n}\n', encoding="utf-8")
    assert M.scan_calibrated() == set(), "un seul chemin sur deux : le nom NU ne doit pas verdir"
    assert M.scan_calibrated.qualified_paths == {"learn": ["src/agents/backend_torch.py"]}


def test_the_REAL_tree_exposes_the_P16_learners_and_the_legacy_gradient():
    """ANCRAGE SUR LE RÉEL : les deux apprenants calibrés par P1.6 et le legacy de l'arc EVO sont
    VISIBLES au cliquet dans le dépôt tel qu'il est. Casse si le motif disparaît OU si ces méthodes
    changent de nom — dans les deux cas, la déclaration CALIBRATED qualifiée doit être revue."""
    coll = M.scan_collisions()
    assert "src/agents/backend_torch.py" in coll.get("learn", []), coll.get("learn")
    assert "src/agents/backend_torch.py" in coll.get("learn_episode", []), coll.get("learn_episode")
    assert "src/agents/mamba_agent.py" in coll.get("compute_policy_gradient", []), (
        "le legacy MambaBatchModel.compute_policy_gradient, actif pendant tout l'arc EVO, doit être compté")
