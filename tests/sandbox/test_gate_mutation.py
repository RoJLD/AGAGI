# -*- coding: utf-8 -*-
"""Calibration du CLIQUET DES CLIQUETS — `tools/check_gate_mutation.py`.

⚠️ Ce module est un outil de vérification, donc il se calibre comme un instrument : « un outil de
vérification non calibré ne se contente pas d'échouer — il PRODUIT un verdict » (CLAUDE.md). Et le
verdict qu'il produit est plus dangereux que la moyenne, puisqu'il porte sur la capacité des AUTRES
gardes à refuser. Un harnais de mutation qui déclarerait « TUEE » quoi qu'il arrive certifierait
comme discriminantes des gardes creuses — la classe E1 remontée d'un cran encore.

La paire fires/spares porte donc sur le harnais lui-même, en une phrase : il doit dire TUEE sur une
mutation qui casse VRAIMENT la porte, et SURVECUE sur une mutation INERTE de la même porte. Sans le
second cas, un harnais qui répondrait toujours « TUEE » passerait le premier.
"""
import io
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_gate_mutation as G  # noqa: E402
from tools._git_env import env_isole  # noqa: E402

_ROOT = G._ROOT
_PORTE_RAPIDE = "14"        # temoins les plus rapides du lot (~1 s), donc le moins cher a muter


# ==================================================================================================
# 1. LA PAIRE — le harnais sait dire TUEE, et il sait dire SURVECUE
# ==================================================================================================

def test_le_harnais_dit_TUEE_sur_une_mutation_qui_CASSE_la_porte():
    """Contrôle POSITIF. La mutation déclarée de la porte 14 vide sa source de vérité ; au moins un
    témoin doit rougir."""
    e = G.etat_une_porte(_PORTE_RAPIDE, G.PORTES[_PORTE_RAPIDE])
    assert e["intact"] == "VERT", ("les temoins doivent passer AVANT toute mutation", e)
    assert [m["verdict"] for m in e["mutations"]] == ["TUEE"], e["mutations"]


def test_le_harnais_dit_SURVECUE_sur_une_mutation_INERTE():
    """⚠️ NO-OP EXACT, et c'est LE test qui donne un sens au précédent. On applique à la même porte
    une mutation sémantiquement NULLE — un commentaire ajouté à une ligne d'import. Les témoins
    doivent rester verts, donc le harnais doit répondre SURVECUE.

    Sans ce cas, un harnais qui répondrait « TUEE » sur n'importe quoi (témoins instables, plugin qui
    plante, pytest qui sort en erreur pour une raison sans rapport) passerait le contrôle positif et
    certifierait comme discriminantes des gardes qu'il n'a jamais mises à l'épreuve."""
    porte = dict(G.PORTES[_PORTE_RAPIDE])
    porte["mutations"] = [{
        "nom": "mutation INERTE (commentaire sur une ligne d'import)",
        "avant": "import ast",
        "apres": "import ast  # mutation INERTE : aucun changement de comportement",
        "motif": "rien — c'est le point",
    }]
    e = G.etat_une_porte(_PORTE_RAPIDE, porte)
    assert e["intact"] == "VERT"
    assert [m["verdict"] for m in e["mutations"]] == ["SURVECUE"], (
        "une mutation sans effet DOIT survivre : si elle est declaree TUEE, le harnais mesure du "
        "bruit et tous ses verdicts positifs sont sans valeur", e["mutations"])


def test_une_mutation_INAPPLICABLE_est_un_ECHEC_et_jamais_un_succes():
    """Un motif absent ou ambigu ne mute rien. Le compter comme « TUEE » (parce que pytest sort en
    erreur) ou comme « SURVECUE » (parce qu'il ne casse rien) reviendrait au même : le harnais
    affirmerait quelque chose sur une mutation qui n'a jamais eu lieu. Il rend `INVALIDE`, et
    `echecs()` le BLOQUE."""
    porte = dict(G.PORTES[_PORTE_RAPIDE])
    porte["mutations"] = [{"nom": "motif absent", "avant": "CE_MOTIF_N_EXISTE_NULLE_PART_XYZ",
                           "apres": "pass", "motif": "rien"}]
    e = G.etat_une_porte(_PORTE_RAPIDE, porte)
    assert [m["verdict"] for m in e["mutations"]] == ["INVALIDE"], e["mutations"]
    assert [p["genre"] for p in G.echecs({_PORTE_RAPIDE: e})] == ["invalide"]


# ==================================================================================================
# 2. LE CONTRÔLE INTACT — sans lui, une suite déjà rouge « tuerait » tous les mutants
# ==================================================================================================

def test_des_temoins_ROUGES_rendent_la_mesure_NULLE_et_le_disent(tmp_path):
    """⚠️ LE piège que ce contrôle ferme, et il n'est pas hypothétique : neuf tests de ce dépôt
    dormaient rouges dans des fichiers qu'aucun job de CI ne lançait. Un harnais naïf aurait vu leurs
    rougeurs, conclu « mutant tué » pour CHAQUE mutation, et annoncé une couverture parfaite en ne
    mesurant strictement rien — un verdict positif fabriqué par l'absence de contrôle, exactement la
    forme (a) documentée dans CLAUDE.md."""
    faux = tmp_path / "test_temoin_rouge.py"
    faux.write_text("def test_rouge():\n    assert False\n", encoding="utf-8")
    porte = {"module": "tools.check_fabricated_defaults", "titre": "factice",
             "temoins": [str(faux)],
             "mutations": [{"nom": "peu importe", "avant": "import ast", "apres": "import ast",
                            "motif": "jamais atteinte"}]}
    e = G.etat_une_porte("X", porte)
    assert e["intact"] == "ROUGE" and e["mutations"] == [], (
        "des temoins rouges doivent SUSPENDRE la mesure, pas la teinter", e)
    assert [p["genre"] for p in G.echecs({"X": e})] == ["temoins_rouges"]


# ==================================================================================================
# 3. LE PLUGIN — il ne doit rien faire quand on ne lui demande rien, et refuser l'ambiguïté
# ==================================================================================================

def test_le_plugin_est_SILENCIEUX_sans_specification():
    """Le harnais mesure le contrôle intact avec la MÊME ligne de commande, au plugin près. Si le
    plugin agissait sans spécification, « intact » ne serait pas intact."""
    from tools import _mutation_plugin as P
    ancien = os.environ.pop("AGAGI_MUTATION_SPEC", None)
    try:
        assert P.pytest_configure(None) is None
    finally:
        if ancien is not None:
            os.environ["AGAGI_MUTATION_SPEC"] = ancien


def test_le_plugin_REFUSE_un_motif_AMBIGU():
    """Un motif présent DEUX fois muterait les deux sites — dont un que l'auteur n'a pas choisi. Le
    verdict porterait alors sur une mutation inconnue de celui qui lit le rapport."""
    from tools import _mutation_plugin as P
    with pytest.raises(RuntimeError, match="INAPPLICABLE"):
        P._installer({"module": "tools.check_fabricated_defaults",
                      "chemin": os.path.join(_ROOT, "tools", "check_fabricated_defaults.py"),
                      "avant": "\n", "apres": "\n"})


def test_le_plugin_N_ECRIT_RIEN_dans_l_arbre():
    """⚠️ CONTRAINTE D'ARBRE PARTAGE, vérifiée et non seulement écrite. La mutation vit en mémoire :
    après un cycle complet, le fichier du cliquet doit être BIT-IDENTIQUE. Un harnais qui muterait
    sur disque laisserait, en cas de kill, une garde sabotée dans l'arbre d'une autre session — et
    le sabotage y serait du type que ce dépôt ne sait pas voir : la garde tourne, elle ne refuse
    plus rien."""
    cible = os.path.join(_ROOT, "tools", "check_fabricated_defaults.py")
    avant = io.open(cible, "rb").read()
    G.etat_une_porte(_PORTE_RAPIDE, G.PORTES[_PORTE_RAPIDE])
    assert io.open(cible, "rb").read() == avant, "le cliquet a ete modifie SUR DISQUE"


# ==================================================================================================
# 4. ANTI-DERIVE — le harnais doit couvrir les portes du hook, RECOMPUTEES depuis le hook
# ==================================================================================================

def test_toute_porte_du_hook_est_DECLAREE_ici_ou_HORS_PERIMETRE():
    """⚠️ Le compte est RECOMPUTE depuis `tools/hooks/pre-commit`, jamais recopié. C'est ce qui fait
    qu'ajouter une porte 15 au hook sans lui déclarer de mutation FERA ROUGIR ce test — sinon la
    couverture du harnais se périmerait en silence, ce que ce dépôt a déjà mesuré trois fois sur des
    chiffres publiés (« 5 cliquets, tous branchés » alors qu'il y en avait 6)."""
    hook = io.open(os.path.join(_ROOT, "tools", "hooks", "pre-commit"), encoding="utf-8").read()
    import re
    modules_du_hook = {m for m in re.findall(r"python tools/(check_\w+)\.py", hook)}
    couverts = {G.PORTES[p]["module"].split(".")[-1] for p in G.PORTES}
    # ⚠️ Les exemptions sont LUES depuis `G.HORS_PERIMETRE`, jamais recopiées ici : une liste
    # recopiée se périme, et c'est précisément le défaut que ce test existe pour empêcher.
    manquants = modules_du_hook - couverts - set(G.HORS_PERIMETRE)
    assert not manquants, (
        f"ces cliquets tirent dans le hook mais n'ont AUCUNE mutation declaree : {sorted(manquants)}. "
        "Une porte sans mutation n'a jamais prouve qu'elle sait encore refuser.")
    assert G.HORS_PERIMETRE and all(len(v) > 20 for v in G.HORS_PERIMETRE.values()), (
        "toute exemption doit porter une raison ECRITE et relisible")


def test_chaque_porte_declaree_pointe_un_module_et_des_temoins_REELS():
    """Une mutation sur un module inexistant, ou des témoins disparus, rendraient `INVALIDE` en
    masse — mais trois mois plus tard. Autant le décider ici, à coût nul."""
    for pid, p in G.PORTES.items():
        assert os.path.isfile(G._chemin_module(p["module"])), (pid, p["module"])
        for t in p["temoins"]:
            assert os.path.isfile(os.path.join(_ROOT, t)), (pid, t)
        assert p["mutations"], pid
        for m in p["mutations"]:
            assert len(m["motif"]) > 25, ("le motif dit ce que la mutation SUPPRIME", pid, m["nom"])


def test_le_harnais_est_BRANCHE_sur_le_hook_et_la_CI():
    """⚠️ La leçon la plus chère du dépôt : une règle exécutable non branchée est violée (E10). Le
    cliquet le plus strict du dépôt (`check_agi_taxonomy`) a vécu des mois sans tirer nulle part."""
    hook = io.open(os.path.join(_ROOT, "tools", "hooks", "pre-commit"), encoding="utf-8").read()
    assert "check_gate_mutation" in hook, "le harnais n'est branche sur AUCUNE porte du hook"
    ci = io.open(os.path.join(_ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8").read()
    assert "check_gate_mutation" in ci, "le harnais ne tourne dans AUCUN job de CI"


def test_le_scope_par_FICHIERS_ne_reveille_que_les_portes_concernees():
    """Le hook ne doit payer que l'affecté : muter 13 portes à chaque commit serait un cliquet qu'on
    désactive."""
    assert G.portes_pour_fichiers(["tools/check_test_census.py"]) == ["10"]
    assert G.portes_pour_fichiers(["tests/sandbox/test_bar_separation.py"]) == ["9"]
    assert G.portes_pour_fichiers(["README.md", "src/world.py"]) == []
    deux = G.portes_pour_fichiers(["tools/check_test_census.py", "tools/check_data_paths.py"])
    assert deux == ["10", "12"], deux


# ==================================================================================================
# 5. LE CLIQUET SAIT SORTIR EN ERREUR — et se taire
# ==================================================================================================

def test_le_CLIQUET_sort_en_ERREUR_quand_un_mutant_survit(monkeypatch, capsys):
    """`main` doit rendre 1, pas seulement imprimer. Un cliquet qui décrit sans bloquer est un
    document, pas une garde."""
    monkeypatch.setattr(G, "scan", lambda only=None: {
        "9": {"intact": "VERT", "code_intact": 0, "sortie": "",
              "mutations": [{"nom": "n", "motif": "m", "verdict": "SURVECUE", "code": 0, "sortie": ""}]}})
    assert G.main([]) == 1
    assert "SURVIVANTE" in capsys.readouterr().out


def test_le_CLIQUET_se_TAIT_quand_tout_est_tue(monkeypatch, capsys):
    """NO-OP APPARIE de l'assertion précédente."""
    monkeypatch.setattr(G, "scan", lambda only=None: {
        "9": {"intact": "VERT", "code_intact": 0, "sortie": "",
              "mutations": [{"nom": "n", "motif": "m", "verdict": "TUEE", "code": 1, "sortie": ""}]}})
    assert G.main([]) == 0
    assert "OK" in capsys.readouterr().out


def test_le_CLIQUET_ne_fait_RIEN_quand_aucune_porte_n_est_concernee(capsys):
    """`--pour-fichiers` sur des chemins sans rapport doit sortir 0 SANS lancer un seul pytest —
    c'est ce qui rend le branchement au hook payable."""
    assert G.main(["--pour-fichiers", "README.md"]) == 0
    assert "aucune porte" in capsys.readouterr().out


# ==================================================================================================
# LE LANCEUR ne transmet pas le dépôt du commit à ses témoins (famille GIT_*, 2026-09-24)
# ==================================================================================================

_TEMOIN_GIT_INIT = (
    "import os, subprocess\n"
    "def test_git_init_dans_B():\n"
    "    subprocess.run(['git', 'init', '-q'], cwd=os.environ['AGAGI_TEMOIN_B'], check=True)\n"
)


def _core_bare(depot):
    p = subprocess.run(["git", "config", "--file", os.path.join(str(depot), ".git", "config"),
                        "--get", "core.bare"], capture_output=True, text=True, env=env_isole())
    return p.stdout.strip()


@pytest.mark.parametrize("purge", [True, False], ids=["avec_purge", "sans_purge_defaut_restaure"])
def test_le_LANCEUR_purge_GIT_un_temoin_qui_fait_git_init_ne_vise_plus_le_depot_du_commit(
        tmp_path, monkeypatch, purge):
    """Contre-exemple gelé, DEUX issues, par le VRAI lanceur `G._pytest`. Un dépôt A (réel, jetable)
    joue le dépôt du commit : `GIT_DIR` le désigne, comme pendant un hook. Le témoin lancé fait
    `git init -q` dans un répertoire B — la forme SANS `-b` du site réel, qui n'imprime RIEN.
    Donc ancrage sur l'ÉTAT, jamais sur la sortie : B a-t-il reçu un `.git`, `core.bare` de A a-t-il
    basculé ? Avec purge : B est un dépôt, A intact. Défaut restauré (`dict(os.environ)`) : B reste
    vide et A passe `core.bare = true` — le contrôle POSITIF, qui prouve que le témoin VOIT la fuite.
    Le témoin est écrit hors de `tests/` : aucune purge de `tests/conftest.py` ne peut le masquer."""
    A, B = tmp_path / "A", tmp_path / "B"
    A.mkdir()
    B.mkdir()
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(k)                       # un hook ambiant ne doit rien viser d'autre que A
    subprocess.run(["git", "init", "-q"], cwd=str(A), check=True, env=env_isole())
    assert _core_bare(A) == "false"
    temoin = tmp_path / "temoin" / "test_temoin_git_init.py"
    temoin.parent.mkdir()
    temoin.write_text(_TEMOIN_GIT_INIT, encoding="utf-8")
    # ⚠️ Sans ini À CÔTÉ du témoin, pytest descend depuis la racine et crée un nœud par entrée de
    # chaque niveau : mesuré le 2026-09-24, Temp en porte 30 407 -> collecte > 180 s, le témoin ne
    # tourne JAMAIS. L'ini fixe rootdir/confcutdir ici : collecte en 0,25 s.
    (temoin.parent / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    monkeypatch.setenv("GIT_DIR", str(A / ".git"))  # ce que git exporte à ses hooks
    monkeypatch.setenv("AGAGI_TEMOIN_B", str(B))
    if not purge:
        monkeypatch.setattr(G, "env_isole", lambda: dict(os.environ))  # le défaut d'avant, restauré
    code, sortie = G._pytest([str(temoin)])
    assert code == 0 and "1 passed" in sortie, sortie  # le témoin a TOURNÉ, sinon B vide ne prouve rien
    if purge:
        assert (B / ".git").is_dir() and _core_bare(A) == "false", sortie
    else:
        assert not (B / ".git").exists() and _core_bare(A) == "true", sortie


@pytest.mark.timeout(1200)
def test_TOUTES_LES_PORTES_du_hook_tuent_leurs_mutants():
    """⚠️ L'ANCRAGE SUR LE REEL, et le seul test de ce fichier qui coûte cher. Il rejoue la mesure
    COMPLETE : 21 portes, 37 mutations au 2026-09-25, fusion de pm-portes (recompte : `len(PORTES)` et la
    somme des `mutations` ; 19/28 la veille sur la branche seule). Le nom disait TREIZE et le corps « 13
    portes, 16 mutations, ~4 min » : perime avant cette branche, aggrave par elle. Un compte fige dans un
    NOM DE TEST ne peut pas se recomputer -- c'est la meme faute que les comptes publies dans la prose,
    traquee par `check_synthesis_counts`.
    ⚠️ Son plafond de 1200 s n'a PAS ete re-mesure a 21 portes : a re-mesurer machine libre.
    C'est lui qui a trouvé QUATRE défauts réels le jour de
    sa livraison — trois verdicts de porte SANS aucun contre-exemple (`orphans` de la porte 1,
    `scan_collisions` de la porte 2, le report de la porte 6) et un test qui PUNISSAIT son propre
    correctif (porte 14, seuil figé à 100 sur une dette tombée à 85)."""
    p = subprocess.run([sys.executable, "tools/check_gate_mutation.py"], cwd=_ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**env_isole(), "PYTHONIOENCODING": "utf-8"})  # pas de GIT_* du hook
    assert p.returncode == 0, p.stdout + p.stderr
