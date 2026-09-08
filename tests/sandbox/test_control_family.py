# -*- coding: utf-8 -*-
"""Calibration de la garde **E23** — « une FAMILLE de contrôles n'est pas traitée comme une famille ».

Deux occurrences mesurées le 2026-09-07, en sens OPPOSÉS :
* la correction de Holm de `run_s2` DISPARAISSAIT en silence (famille non corrigée du tout) ;
* le contrôle (i) d'EVO-011 appliquait une bande fixe à 24 cellules → **0,216 de fausse alarme** sous
  un harnais PARFAIT, et le premier run a bien rendu `INDÉTERMINÉ-HARNAIS`.

Ce qui rend la classe automatisable n'est PAS un motif syntaxique : mesuré, un détecteur « seuil
littéral dans une boucle » trouve 2 sites dans tout le dépôt et **aucun des deux vrais** — dans les
deux occurrences la famille se forme ENTRE les appels, pas dans une boucle. On ne proxifie donc pas
ce qu'on ne sait pas décider : on fait **DÉCLARER** le nombre de cellules, seule chose que l'auteur
sait et que le code ne peut pas deviner. C'est la forme de la garde E8 (`allow_inferred_reason`).

Chaque cas positif est apparié à sa branche NÉGATIVE : une garde qui ne sait pas se TAIRE est aussi
inutilisable qu'une garde qui ne sait pas crier (classe E1).
"""
import math

import pytest

from tools.experiment_preflight import (PreflightError, assert_control_family, declare_design)

_LINKS = {"cablage->reponse": "measured"}


# --------------------------------------------------------------------------------------------------
# 1. `assert_control_family` — le seuil rendu, et les refus
# --------------------------------------------------------------------------------------------------

def test_famille_de_24_rend_le_seuil_de_bonferroni_exact():
    """RÉPONSE CONNUE, en forme close : 24 cellules à alpha 0,05 → 0,05/24. C'est EXACTEMENT le seuil
    que la règle EVO-011-PREVOL-bis scelle, et que le runner applique."""
    f = assert_control_family(cells=24, alpha_family=0.05)
    assert f["cells"] == 24 and f["method"] == "bonferroni"
    assert abs(f["alpha_cell"] - 0.05 / 24) < 1e-15
    assert f["fwer_bound"] == 0.05


def test_une_seule_cellule_ne_corrige_RIEN():
    """Spécificité (no-op EXACT) : sans famille, le seuil par cellule EST le seuil de famille. Une
    garde qui corrigerait même à cells=1 rendrait tout test unique 1 fois trop strict."""
    f = assert_control_family(cells=1, alpha_family=0.05)
    assert f["alpha_cell"] == 0.05 and f["fwer_bound"] == 0.05


def test_REFUSE_un_seuil_par_cellule_trop_large():
    """LE défaut d'EVO-011, réduit à sa forme pure : appliquer 0,05 à chacune des 24 cellules. Le
    message doit NOMMER la borne de fausse alarme, sinon l'auteur ne sait pas ce qu'il risque."""
    with pytest.raises(PreflightError) as e:
        assert_control_family(cells=24, alpha_family=0.05, alpha_cell=0.05)
    m = str(e.value)
    assert "E23" in m and "24" in m and "1.000" in m


def test_ACCEPTE_un_seuil_par_cellule_PLUS_STRICT_que_necessaire():
    """Branche négative appariée : Holm est plus puissant que Bonferroni, et un auteur prudent peut
    serrer davantage. Refuser ici ferait de la garde un carcan, pas un contrôle."""
    f = assert_control_family(cells=24, alpha_family=0.05, alpha_cell=0.0005, method="holm")
    assert f["alpha_cell"] == 0.0005


def test_method_none_EXIGE_une_raison_ecrite_et_publie_la_borne():
    """« Pas de correction » reste possible — c'est parfois juste (contrôles déterministes) — mais
    doit être DÉCLARÉ. Sans raison : refus. Avec raison : la borne réelle est PUBLIÉE, pas cachée."""
    with pytest.raises(PreflightError):
        assert_control_family(cells=24, method="none")
    f = assert_control_family(cells=24, method="none", reason="contrôles déterministes, évalués une fois")
    assert f["fwer_bound"] == 1.0 and f["reason"]


def test_REFUSE_les_entrees_qui_ne_sont_pas_une_famille():
    """Formes dégénérées : une famille vide n'est pas une famille, une méthode inconnue n'est pas une
    méthode, un alpha hors (0,1) n'est pas un risque."""
    for kw in ({"cells": 0}, {"cells": 3, "method": "fdr_bh"}, {"cells": 3, "alpha_family": 1.0},
               {"cells": 3, "alpha_family": 0.0}):
        with pytest.raises(PreflightError):
            assert_control_family(**kw)


# --------------------------------------------------------------------------------------------------
# 2. `declare_design` — la garde ne se contourne pas par l'oubli
# --------------------------------------------------------------------------------------------------

def test_declare_design_REFUSE_n_superieur_a_1_sans_famille_declaree():
    """C'est CE refus qui aurait attrapé EVO-011 avant le run. Le message doit porter la mesure
    (0.216), pas une exhortation : c'est elle qui rend le défaut croyable."""
    with pytest.raises(PreflightError) as e:
        declare_design(question="q", replication_unit="seed", n_independent=12, links=_LINKS)
    m = str(e.value)
    assert "E23" in m and "0.216" in m and "assert_control_family" in m


def test_declare_design_n_egal_1_n_exige_RIEN():
    """Branche négative : un run à réplicat unique n'a pas de famille. Exiger une déclaration ici
    rendrait la garde bruyante donc contournée — c'est ainsi que meurent les gardes."""
    d = declare_design(question="q", replication_unit="génome", n_independent=1, links=_LINKS)
    assert d["control_family"] is None


def test_declare_design_PUBLIE_la_famille_dans_le_design():
    """Une déclaration qui n'atterrit pas dans le record ne peut pas être jugée par un lecteur."""
    f = assert_control_family(cells=24)
    d = declare_design(question="q", replication_unit="seed", n_independent=12, links=_LINKS,
                       control_family=f)
    assert d["control_family"]["cells"] == 24
    assert abs(d["control_family"]["alpha_cell"] - 0.05 / 24) < 1e-15


def test_declare_design_REFUSE_une_declaration_AMBIGUE_en_CRIANT():
    """Leçon des deux cliquets du 2026-09-01 : ils refusaient une déclaration ambiguë **en silence**.
    Passer `control_family=24` (le nombre, pas la déclaration) doit lever, jamais être avalé."""
    for mauvais in (24, "24 cellules", {"cells": 24}, True):
        with pytest.raises(PreflightError):
            declare_design(question="q", replication_unit="seed", n_independent=12, links=_LINKS,
                           control_family=mauvais)


# --------------------------------------------------------------------------------------------------
# 3. CONTRE-EXEMPLE GELÉ — la mesure qui a motivé la classe, rejouée en forme close
# --------------------------------------------------------------------------------------------------

# n RÉELLEMENT observés au premier run d'EVO-011 (results/evo011_preflight.json), pas des n supposés.
_N_CELLULES = [26, 23, 25, 20, 26, 27, 22, 31, 25, 25, 26, 20] + \
              [24, 31, 40, 38, 35, 27, 45, 38, 37, 56, 39, 33]


def _hors_bande(n, lo=0.25, hi=0.75):
    return sum(math.comb(n, k) for k in range(n + 1) if not (lo < k / n < hi)) / 2 ** n


def test_CONTRE_EXEMPLE_la_garde_aurait_refuse_le_controle_qui_a_echoue():
    """RÉPONSE CONNUE. La bande fixe (0,25 ; 0,75) revient, aux n observés, à un seuil par cellule de
    ~0,0146 — appliqué à 24 cellules, soit une fausse alarme de 0,216 sur un harnais PARFAIT. La garde
    doit REFUSER ce réglage, et le refuser en nommant la borne."""
    alpha_cell_effectif = _hors_bande(25)
    assert 0.014 < alpha_cell_effectif < 0.015, alpha_cell_effectif
    aucune = 1.0
    for n in _N_CELLULES:
        aucune *= (1 - _hors_bande(n))
    assert 0.20 < 1 - aucune < 0.23, "le contre-exemple ne reproduit plus la mesure d'origine"

    with pytest.raises(PreflightError):
        assert_control_family(cells=24, alpha_family=0.05, alpha_cell=alpha_cell_effectif)


def test_CONTRE_EXEMPLE_la_garde_ACCEPTE_le_reglage_qui_a_repare_le_run():
    """Le no-op apparié : le seuil du sceau `-bis` (0,05/24) doit passer SANS bruit. Sans ce cas, le
    précédent ne distinguerait pas « la garde voit le défaut » de « la garde refuse tout »."""
    f = assert_control_family(cells=24, alpha_family=0.05, alpha_cell=0.05 / 24)
    assert f["fwer_bound"] == 0.05


def test_le_runner_EVO011_declare_la_MEME_famille_que_celle_qu_il_applique():
    """GARDE DE LA GARDE : une déclaration qui diverge du seuil réellement appliqué serait
    décorative — c'est la classe E10 (règle documentée sans application exécutable), la plus
    récidivante du registre (19 occurrences)."""
    from tools.evo_runs import evo011_preflight as R

    f = assert_control_family(cells=R.FAMILY_CELLS, alpha_family=R.ALPHA_FAMILY,
                              alpha_cell=R.ALPHA_CELL, method="bonferroni")
    assert R.FAMILY_CELLS == 2 * R.SEALED_SEEDS == 24
    assert abs(f["alpha_cell"] - R.ALPHA_CELL) < 1e-15


# --------------------------------------------------------------------------------------------------
# 4. Le CLIQUET `check_control_family.py` — une garde d'appel ne protège que ceux qui l'appellent.
#    Mesuré le 2026-09-07 : 9 runners scellés sur 12 ne déclaraient AUCUN design, donc n'étaient
#    jamais interrogés sur leur famille. C'est la classe E10, la plus récidivante du registre.
# --------------------------------------------------------------------------------------------------

_RUNNER_NU = '''
from tools.preregister import verify
rule = verify("MA-REGLE")
for seed in range(12):
    ...
'''

_RUNNER_COMPLET = '''
from tools.preregister import verify
from tools.experiment_preflight import declare_design, assert_control_family
rule = verify("MA-REGLE")
design = declare_design(question=rule["question"], replication_unit="seed", n_independent=12,
                        links={"a": "measured"}, control_family=assert_control_family(cells=24))
'''

# Le faux positif qu'un scan TEXTUEL produirait : `verify(` n'existe que dans une docstring.
_FAUX_POSITIF = '''
"""Ce module explique comment on ferait verify("X") et preregister("X"), mais ne le fait pas."""
# from tools.preregister import verify
def aide():
    return "appeler verify(nom) apres avoir scelle"
'''

# Appelle `verify` mais d'un AUTRE module : ce n'est pas un runner scellé.
_AUTRE_VERIFY = '''
from tools.check_staged_authorship import verify
verify(["a.py"])
'''


def test_le_cliquet_voit_un_runner_SCELLE_SANS_design():
    from tools.check_control_family import runners_nus, scan_runners

    etat = scan_runners([("tools/faux_runner.py", _RUNNER_NU)])
    assert etat["tools/faux_runner.py"] == {"scelle": True, "declare": False}
    assert runners_nus(etat) == ["tools/faux_runner.py"]


def test_le_cliquet_se_TAIT_sur_un_runner_qui_declare():
    """Branche négative appariée : sans elle, un cliquet qui crierait TOUJOURS passerait le test
    précédent — c'est la forme exacte du faux positif mesuré sur les cliquets du 2026-09-01."""
    from tools.check_control_family import runners_nus, scan_runners

    etat = scan_runners([("tools/bon_runner.py", _RUNNER_COMPLET)])
    assert etat["tools/bon_runner.py"] == {"scelle": True, "declare": True}
    assert runners_nus(etat) == []


def test_le_cliquet_n_est_PAS_trompe_par_une_docstring():
    """C'est LA raison pour laquelle la détection est AST et non textuelle. Un scan textuel comptait
    `tools/check_staged_authorship.py` comme runner scellé — vérifié au moment de l'écrire."""
    from tools.check_control_family import runners_nus, scan_runners

    assert runners_nus(scan_runners([("tools/doc.py", _FAUX_POSITIF)])) == []


def test_le_cliquet_ne_confond_pas_un_AUTRE_verify():
    """`verify` est un nom courant. Sans l'exigence d'IMPORTER `tools.preregister`, tout module qui
    vérifie n'importe quoi deviendrait un runner scellé — un cliquet qui crie partout est désarmé."""
    from tools.check_control_family import runners_nus, scan_runners

    assert runners_nus(scan_runners([("tools/autre.py", _AUTRE_VERIFY)])) == []


def test_le_CLIQUET_sait_SORTIR_EN_ERREUR_et_se_TAIRE(monkeypatch, capsys):
    """GARDE DE LA GARDE, bout en bout : les fonctions pures peuvent être justes pendant que la CLI
    ne bloque jamais (faux vert mesuré le 2026-09-01, classe E4 occ. 5)."""
    from tools import check_control_family as C

    monkeypatch.setattr(C, "scan_runners", lambda *a, **k: {"tools/neuf.py": {"scelle": True, "declare": False}})
    monkeypatch.setattr(C, "_load_baseline", lambda: [])
    assert C.main([]) == 1
    assert "tools/neuf.py" in capsys.readouterr().out

    monkeypatch.setattr(C, "_load_baseline", lambda: ["tools/neuf.py"])   # légataire gelé
    assert C.main([]) == 0
    assert "aucun nouveau runner" in capsys.readouterr().out


def test_le_CLIQUET_restreint_son_blocage_avec_only(monkeypatch):
    """L'arbre est PARTAGÉ : un runner nu écrit par une AUTRE session ne doit pas bloquer mon commit
    (même principe que les portes 1, 2 et 10 du hook)."""
    from tools import check_control_family as C

    monkeypatch.setattr(C, "scan_runners", lambda *a, **k: {"tools/autrui.py": {"scelle": True, "declare": False}})
    monkeypatch.setattr(C, "_load_baseline", lambda: [])
    assert C.main(["--only", "tools/a_moi.py"]) == 0
    assert C.main(["--only", "tools/autrui.py"]) == 1


def test_la_dette_legataire_est_REELLE_et_pas_un_commentaire():
    """Une dette qui ne peut plus être invalidée n'est plus une dette (leçon EVO-009, retiré de la
    dette prereg le 2026-09-02). On vérifie que les runners gelés existent ENCORE et sont ENCORE nus."""
    import json
    import os

    from tools.check_control_family import _BASELINE, runners_nus, scan_runners

    if not os.path.exists(_BASELINE):
        import pytest as _p
        _p.skip("baseline pas encore gelée")
    gelés = json.load(open(_BASELINE, encoding="utf-8"))["runners_nus"]
    nus = set(runners_nus(scan_runners()))
    disparus = [p for p in gelés if p not in nus]
    assert not disparus, f"dette périmée : {disparus} — re-geler la baseline"


# --------------------------------------------------------------------------------------------------
# 5. Garde E24 — le CHEVAUCHEMENT entrée/sortie (2026-09-08). Aucun monde, aucun génome réel chargé :
#    la propriété est arithmétique, elle se confronte à une réponse connue en trois entiers.
# --------------------------------------------------------------------------------------------------

class _Gen:
    def __init__(self, num_inputs, num_outputs, num_nodes):
        self.num_inputs, self.num_outputs, self.num_nodes = num_inputs, num_outputs, num_nodes


def test_le_chevauchement_du_CHAMPION_est_refuse_et_CHIFFRE():
    """RÉPONSE CONNUE, mesurée le 2026-09-08 : le champion HoF déclare 64 entrées et 126 sorties dans
    172 nœuds. 64+126 = 190 > 172 → 18 slots partagés, et ses 18 premiers logits d'action SONT
    l'observation. Le message doit porter le CHIFFRE, sinon l'auteur ne sait pas ce qu'il risque."""
    from tools.experiment_preflight import PreflightError, assert_no_io_overlap

    with pytest.raises(PreflightError) as e:
        assert_no_io_overlap(_Gen(64, 126, 172), label="champion HoF")
    m = str(e.value)
    assert "18" in m and "64" in m and "126" in m and "172" in m and "E24" in m


def test_un_genome_FRAIS_passe_sans_bruit():
    """Branche NÉGATIVE appariée : un agent frais fait 59 + 108 = 167 ≤ 172. Une garde qui crierait
    aussi sur lui serait inutilisable — et c'est ce qui distingue « défaut de lignée » de « défaut du
    substrat »."""
    from tools.experiment_preflight import assert_no_io_overlap

    assert assert_no_io_overlap(_Gen(59, 108, 172)) == -5


def test_le_cas_LIMITE_exact_passe():
    """`num_inputs + num_outputs == num_nodes` : zéro nœud caché, mais AUCUN slot partagé. La garde
    porte sur le chevauchement, pas sur l'existence d'une couche cachée — les confondre refuserait
    des connectomes plats qui sont légitimes (cf. `intelligence-typing-flat-connectome`)."""
    from tools.experiment_preflight import assert_no_io_overlap

    assert assert_no_io_overlap(_Gen(64, 108, 172)) == 0


def test_la_garde_REFUSE_ce_qui_n_est_pas_un_genome():
    """Une déclaration ambiguë est refusée en CRIANT : passer un modèle batch (qui expose `max_I` et
    non `num_inputs`) doit lever, jamais être avalé comme un chevauchement de zéro."""
    from tools.experiment_preflight import PreflightError, assert_no_io_overlap

    class _Batch:
        max_I, max_O, max_N = 64, 126, 172

    with pytest.raises(PreflightError, match="n'expose pas"):
        assert_no_io_overlap(_Batch(), label="modele batch")


# --------------------------------------------------------------------------------------------------
# 6. CONTRÔLE POSITIF GRATUIT de l'opérateur de saillance de DÉCISION (2026-09-08).
#    Le chevauchement entrée/sortie du champion (classe E24) fournit 18 paires (canal, logit) dont la
#    réponse est connue PAR IDENTITÉ : `logits[k]` EST `obs[46+k]`. Perturber le canal à ±1 doit donc
#    faire basculer le SIGNE du logit — saillance 1,0 — et ne rien faire ailleurs.
#    C'est le contrôle positif que la sonde de saillance n'avait jamais eu, et il était déjà dans le
#    sujet. Pur `recurrent_forward` : aucun monde, aucun bail.
# --------------------------------------------------------------------------------------------------

def test_l_operateur_de_saillance_VOIT_une_dependance_qui_existe_par_IDENTITE():
    """RÉPONSE CONNUE, mesurée : 18/18 bascules sur les paires identitaires, 0/18 hors diagonale, et
    le no-op de la sonde (deux appels identiques) vaut 0 exactement. Si ce cas tombe un jour, ce n'est
    PAS que le champion a cessé de lire : c'est que l'opérateur de saillance ne voit plus une
    dépendance parfaite — et alors aucune saillance nulle qu'il rapporte n'est interprétable."""
    import numpy as np

    from tools.s2_demand import load_champion_genome          # AVANT tout module qui repointe HOF_PATH

    g = load_champion_genome()
    from src.seed_ai.rl_evolution import recurrent_forward

    deb = g.num_nodes - g.num_outputs
    chev = g.num_inputs - deb
    if chev <= 0:
        pytest.skip("ce champion n'a plus de chevauchement entrée/sortie : le contrôle gratuit disparaît")

    H = np.zeros((1, g.num_nodes), dtype=np.float32)
    base = np.random.RandomState(0).normal(0, 0.3, size=(1, g.num_inputs)).astype(np.float32)

    def logit(obs, idx):
        return float(np.asarray(recurrent_forward(g, obs, H.copy(), None, None)[0]).ravel()[idx])

    assert logit(base, 0) == logit(base, 0), "l'opérateur n'est pas déterministe : rien n'est mesurable"

    diag = hors = 0
    for k in range(chev):
        op, om = base.copy(), base.copy()
        op[0, deb + k], om[0, deb + k] = 1.0, -1.0
        diag += int(np.sign(logit(op, k)) != np.sign(logit(om, k)))
        autre = (k + 40) % g.num_outputs
        hors += int(np.sign(logit(op, autre)) != np.sign(logit(om, autre)))

    assert diag == chev, f"l'opérateur rate {chev - diag} dépendance(s) PARFAITE(S) sur {chev}"
    assert hors == 0, f"{hors} bascule(s) hors diagonale : l'opérateur voit ce qui n'existe pas"


def test_la_sonde_de_saillance_SIGNALE_une_paire_d_IDENTITE_AVANT_de_construire_le_monde(monkeypatch, capsys):
    """E10 : une garde qu'on n'appelle jamais est une garde absente. `assert_no_io_overlap` est donc
    BRANCHÉE dans `measure_decision_saliency` — là où la confusion se produirait.

    Deux propriétés exigées, et la seconde compte autant : l'avertissement doit sortir, et il doit
    sortir **AVANT** `_make_env`. Une alerte émise après la construction du monde coûte une simulation
    pour dire une chose connue d'avance — c'est la règle « garde en tête » du dépôt."""
    import tools.evo_cognitive_objective as M

    class _Sentinelle(Exception):
        pass

    def _pas_de_monde(*a, **k):
        raise _Sentinelle("le monde a été construit")

    monkeypatch.setattr(M, "_make_env", _pas_de_monde)

    class _G:
        num_inputs, num_outputs, num_nodes = 64, 126, 172

    # paire d'IDENTITE : canal 46+k -> logit k
    with pytest.raises(_Sentinelle):
        M.measure_decision_saliency(_G(), seed=0, channel=46 + 3, out_idx=3)
    err = capsys.readouterr().err
    assert "IDENTITE" in err and "CONTROLE POSITIF" in err

    # branche NEGATIVE appariée : une paire ORDINAIRE ne doit RIEN dire, sinon l'alerte est du bruit
    # et personne ne la lira quand elle comptera.
    with pytest.raises(_Sentinelle):
        M.measure_decision_saliency(_G(), seed=0, channel=4, out_idx=8)
    assert "IDENTITE" not in capsys.readouterr().err

    # et sur un génome SANS chevauchement, aucune paire n'est identitaire
    class _Frais:
        num_inputs, num_outputs, num_nodes = 59, 108, 172

    with pytest.raises(_Sentinelle):
        M.measure_decision_saliency(_Frais(), seed=0, channel=64, out_idx=0)
    assert "IDENTITE" not in capsys.readouterr().err


def test_dix_decisions_du_monde_sont_EXACTEMENT_une_observation_du_champion():
    """RÉPONSE CONNUE, mesurée le 2026-09-08 sur le champion INTACT (400 tirages, no-op à 0,0) :
    les logits 8 à 17 valent `0,5 · obs[46+k]` à une constante près — corrélation **+1,0000 exacte**,
    pente **+0,5000** — donc `do_throw`, `do_jump`, `do_duck`, la visée, `out_share`, `out_accept` et
    `out_mate` sont le SIGNE d'un canal d'observation, sans aucun poids appris.

    Ce cas gèle le fait, pas une opinion : s'il tombe, c'est que la lignée du HoF a changé — et alors
    tout ce qui a été lu sur ce sujet doit être relu."""
    import numpy as np

    from tools.s2_demand import load_champion_genome

    g = load_champion_genome()
    from src.seed_ai.rl_evolution import recurrent_forward

    deb = g.num_nodes - g.num_outputs
    chev = g.num_inputs - deb
    if chev < 18:
        pytest.skip("ce champion n'a plus 18 slots partagés : le fait gelé ne s'applique plus")

    H = np.zeros((1, g.num_nodes), dtype=np.float32)
    rng = np.random.RandomState(0)
    L, O = [], []
    for _ in range(200):
        obs = rng.normal(0, 0.6, size=(1, g.num_inputs)).astype(np.float32)
        L.append(np.asarray(recurrent_forward(g, obs, H.copy(), None, None)[0]).ravel()[:chev])
        O.append(obs[0, deb:deb + chev])
    L, O = np.array(L), np.array(O)

    for k in range(8, 18):
        r = float(np.corrcoef(L[:, k], O[:, k])[0, 1])
        pente = float(np.polyfit(O[:, k], L[:, k], 1)[0])
        assert r > 0.9999, f"logit {k} n'est plus une identité de obs[{deb + k}] : r={r:.4f}"
        assert abs(pente - 0.5) < 1e-3, f"logit {k} : pente {pente:.4f} au lieu de 0,5"

    # l'opérateur que le monde applique VRAIMENT : un test de signe. Accord total attendu.
    assert float(np.mean((L[:, 8] > 0) == (O[:, 8] > 0))) == 1.0, "do_throw n'est plus obs[54] > 0"

    # branche NÉGATIVE appariée : le MOUVEMENT, lui, n'est PAS une identité — le réseau y contribue.
    acc = float(np.mean(np.argmax(L[:, :8], axis=1) == np.argmax(O[:, :8], axis=1)))
    assert 0.125 < acc < 0.95, (
        f"argmax du mouvement : accord {acc:.3f} — s'il vaut 1.0 le réseau ne décide plus rien, "
        "s'il vaut 0.125 il n'y a plus de chevauchement du tout")
