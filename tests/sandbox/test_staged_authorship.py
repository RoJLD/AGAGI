"""Garde EXÉCUTABLE de la classe E10 (occurrences 4 et 5 du 2026-09-01, promotion P2.22) — « hunks
étrangers happés par un commit path-scopé mais pas contenu-scopé ».

Calibration sur la RÉPONSE CONNUE (cf. CLAUDE.md §Calibration des instruments) : ces tests reproduisent
la FORME du cas gelé `e21c1f3` (2026-09-01) — un `git add` path-scopé mais pas contenu-scopé a happé du
travail non committé d'une session parallèle sur `tests/sandbox/test_instrument_calibration.py` — dans un
dépôt git TEMPORAIRE (jamais le dépôt réel), avec le cas POSITIF apparié : seuls MES hunks stagés doit
PASSER. Sans le positif, une garde qui refuse tout serait aussi inutile qu'une garde qui accepte tout.

⚠️ SUITE LENTE — MESURÉE À 593 s (16 tests, ~37 s chacun) : chaque cas construit un dépôt git temporaire
et enchaîne des sous-processus `git`, coûteux sous Windows. Le module entier est donc marqué `slow` :
laissée dans la suite rapide, elle la ferait passer de quelques minutes à plus de dix, et le registre note
lui-même qu'« une garde disponible et NON DÉCLENCHÉE vaut zéro » — une suite qu'on cesse de lancer est
exactement ça. Aucun test individuel ne dépasse le `timeout` de `pytest.ini` (le plus lent ~37 s), donc le
marquage porte sur le COÛT CUMULÉ, pas sur un risque de hang. Dette ouverte : mutualiser le dépôt-fixture
entre les cas ferait tomber ce coût d'un ordre de grandeur — à faire avant d'ajouter d'autres cas ici.
"""
import os
import subprocess
import sys

import pytest

# Marque TOUT le module (cf. docstring) : coût cumulé 593 s, désélectionné par `-m "not slow"`.
pytestmark = pytest.mark.slow

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.check_staged_authorship import (  # noqa: E402
    snapshot, verify, confirm_commit, detect_preempted, _cli,
    NoSnapshotError, ForeignHunkDetected, MissingPathsInCommit, WorkPreempted)

_FILE = "shared_module.py"
_OTHER = "other_module.py"


def _git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {args} a échoué : {r.stderr}"
    return r.stdout


def _init_repo(tmp_path):
    """Dépôt git temporaire avec un commit initial portant `shared_module.py` (jamais le dépôt réel)."""
    repo = str(tmp_path)
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    with open(os.path.join(repo, _FILE), "w", encoding="utf-8") as f:
        f.write("def foo():\n    return 1\n")
    _git(["add", _FILE], repo)
    _git(["commit", "-q", "-m", "init"], repo)
    return repo


def _append(repo, text, name=_FILE):
    with open(os.path.join(repo, name), "a", encoding="utf-8") as f:
        f.write(text)


def _init_repo_two_files(tmp_path):
    """Comme `_init_repo`, plus un SECOND fichier suivi — nécessaire pour la course `add`/`commit` :
    le commit doit survivre à la disparition d'un chemin pour que la perte soit SILENCIEUSE."""
    repo = _init_repo(tmp_path)
    with open(os.path.join(repo, _OTHER), "w", encoding="utf-8") as f:
        f.write("def bar():\n    return 2\n")
    _git(["add", _OTHER], repo)
    _git(["commit", "-q", "-m", "init other"], repo)
    return repo


def _head_sha(repo):
    return _git(["rev-parse", "HEAD"], repo).strip()


def test_verify_without_a_prior_snapshot_is_refused(tmp_path):
    """Sans empreinte, rien n'est comparable — la garde doit le dire, pas laisser passer en silence."""
    repo = _init_repo(tmp_path)
    with pytest.raises(NoSnapshotError):
        verify([_FILE], owner="tache", snapshot_dir=str(tmp_path / "snaps"), cwd=repo)


def test_FORME_e21c1f3_a_foreign_uncommitted_hunk_swept_by_git_add_is_caught(tmp_path):
    """⚠️ LE CŒUR DE LA GARDE — reproduit la forme du cas gelé `e21c1f3` (2026-09-01) :

    1. une session PARALLÈLE édite `shared_module.py` SANS committer (travail étranger, déjà dans
       l'arbre de travail avant que ma tâche ne commence) ;
    2. JE prends mon empreinte (`snapshot`) — elle capture ce contenu étranger + le HEAD réel ;
    3. J'édite le MÊME fichier (mon propre travail) ;
    4. `git add` stage TOUT (mon travail + le hunk étranger, jamais committé) — c'est exactement le
       mécanisme `e21c1f3` : path-scopé, pas contenu-scopé ;
    5. `verify()` doit TIRER et NOMMER le hunk étranger (pas seulement dire non).
    """
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    # 1. session parallèle : hunk étranger, jamais committé.
    _append(repo, "\n\ndef parallel_session_uncommitted():\n    return 'foreign'\n")

    # 2. mon empreinte de départ — capture le hunk étranger ci-dessus + le HEAD réel (juste `foo`).
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # 3. mon propre travail, écrit APRÈS l'empreinte.
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")

    # 4. je stage tout, sans distinguer les hunks (exactement le geste qui a produit e21c1f3).
    _git(["add", _FILE], repo)

    # 5. la garde doit tirer et nommer le hunk étranger.
    with pytest.raises(ForeignHunkDetected) as exc:
        verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    report = exc.value.report
    assert _FILE in report
    foreign_text = "\n".join(l for h in report[_FILE] for l in h["lines"])
    assert "parallel_session_uncommitted" in foreign_text
    assert "'foreign'" in foreign_text
    # le hunk qui EST le mien ne doit PAS apparaître dans le rapport d'ÉTRANGERS.
    assert "my_own_work" not in foreign_text
    # le message doit NOMMER, pas seulement refuser.
    assert "parallel_session_uncommitted" in str(exc.value)


def test_FORME_occ13_a_long_run_copied_from_HEAD_must_not_STEAL_the_anchor(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ de l'occurrence 13 d'E10 (2026-09-02) — la SECONDE passe de diff, qui
    corrigeait la fusion de hunks contigus (`e21c1f3`, correctif `cdbc6a2`), reste un ALIGNEMENT
    GLOBAL unique : `SequenceMatcher.get_opcodes()` n'attribue chaque ligne qu'à UN rôle, et il
    ancre sur le PLUS LONG appariement. Si mon propre ajout contient un run de lignes qui figure
    AUSSI dans l'empreinte (ici : un bloc RECOPIÉ de HEAD, motif banal quand on écrit un test en
    partant d'un test existant) et que ce run est PLUS LONG que le bloc étranger, l'ancre part sur
    MA copie et le bloc étranger retombe dans un opcode non-`equal` : il devient INVISIBLE.

    Ce n'est PAS l'adjacence qui casse la garde (le cas contigu pur est couvert par le test
    `test_FORME_e21c1f3_…` ci-dessus, et le rejeu des artefacts réels de l'occurrence 13 — empreinte
    `e4-assert-blindspot` + blob stagé `acde3e8` — DÉTECTE bien ses 55 lignes étrangères). C'est la
    COMPÉTITION D'ANCRE : mesurée sur le fichier réel, un bloc étranger de ≤ 41 lignes disparaît
    face à un run copié de 40 lignes, et réapparaît à 60.

    Le seuil est ici : HEAD porte un corps de 9 lignes, le bloc étranger en fait 4, ma copie en
    reprend 9 -> 9 > 4, l'ancre bascule."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    # HEAD porte une fonction dont le CORPS servira d'appât d'ancre (9 lignes contiguës).
    _append(repo, "\n\ndef check_alpha(data):\n    total = 0\n    for item in data:\n"
                  "        if item is None:\n            continue\n        total += item\n"
                  "    if total < 0:\n        raise ValueError('negatif')\n    return total\n")
    _git(["add", _FILE], repo)
    _git(["commit", "-q", "-m", "HEAD porte check_alpha"], repo)

    # 1. session parallèle : bloc étranger COURT (4 lignes), jamais committé.
    _append(repo, "\n\ndef parallel_session_uncommitted():\n    return 'foreign'\n")

    # 2. mon empreinte — capture le bloc étranger ci-dessus + le HEAD réel.
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # 3. MON travail : un nouveau `check_beta` écrit en RECOPIANT le corps de `check_alpha`.
    #    9 lignes identiques à HEAD, contiguës -> appât d'ancre plus long que les 4 lignes étrangères.
    _append(repo, "\n\ndef check_beta(data):\n    total = 0\n    for item in data:\n"
                  "        if item is None:\n            continue\n        total += item\n"
                  "    if total < 0:\n        raise ValueError('negatif')\n    return total\n")

    _git(["add", _FILE], repo)

    with pytest.raises(ForeignHunkDetected) as exc:
        verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    foreign_text = "\n".join(l for h in exc.value.report[_FILE] for l in h["lines"])
    assert "parallel_session_uncommitted" in foreign_text, \
        "l'ancre a été volée par ma propre copie : le bloc étranger est redevenu invisible"


def test_POSITIVE_occ13_my_copy_of_HEAD_alone_is_NOT_flagged(tmp_path):
    """Positif apparié du cas ci-dessus : MÊME copie de HEAD, mais AUCUN travail étranger dans
    l'arbre au moment de l'empreinte -> la garde doit PASSER. Sans lui, on ne saurait pas si le
    correctif de l'ancre se contente de crier sur tout run recopié depuis HEAD."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    _append(repo, "\n\ndef check_alpha(data):\n    total = 0\n    for item in data:\n"
                  "        if item is None:\n            continue\n        total += item\n"
                  "    if total < 0:\n        raise ValueError('negatif')\n    return total\n")
    _git(["add", _FILE], repo)
    _git(["commit", "-q", "-m", "HEAD porte check_alpha"], repo)

    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)   # arbre PROPRE
    _append(repo, "\n\ndef check_beta(data):\n    total = 0\n    for item in data:\n"
                  "        if item is None:\n            continue\n        total += item\n"
                  "    if total < 0:\n        raise ValueError('negatif')\n    return total\n")
    _git(["add", _FILE], repo)

    checked = verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert checked[_FILE] == 1


def test_POSITIVE_only_my_own_hunks_staged_PASSES(tmp_path):
    """Cas positif apparié : AUCUN travail étranger dans l'arbre au moment de l'empreinte -> seul MON
    hunk est stagé -> la garde doit PASSER. Sans ce test, une garde qui refuse tout passerait la revue."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    # empreinte prise immédiatement après le commit initial : rien d'étranger dans l'arbre.
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # mon propre travail, écrit après l'empreinte.
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")
    _git(["add", _FILE], repo)

    checked = verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert checked[_FILE] == 1                        # un seul hunk stagé, et il est attribuable


def test_verify_with_nothing_staged_is_a_silent_noop(tmp_path):
    """Un fichier snapshotté mais jamais retouché ni restagé n'a rien à vérifier -> pas d'erreur."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    checked = verify([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert checked[_FILE] == 0                         # rien de nouveau stagé par rapport au HEAD capturé


def test_different_owners_do_not_share_a_snapshot(tmp_path):
    """Deux tâches sur le même fichier ne doivent pas se marcher dessus : `owner` scope l'empreinte."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="tache-a", snapshot_dir=snap_dir, cwd=repo)
    with pytest.raises(NoSnapshotError):
        verify([_FILE], owner="tache-b", snapshot_dir=snap_dir, cwd=repo)


# =====================================================================================================
# LIMITE 1 — SENS B : « quelqu'un a committé MON travail avant moi ».
# Déclaré « insoluble par construction » à la livraison ; il est détectable par la CONJONCTION
# (arbre != empreinte) ∧ (`git diff HEAD` vide). Les trois cas ci-dessous sont appariés : celui qui doit
# TIRER, celui du travail normal, et le DISCRIMINANT « je n'ai simplement rien édité » — sans lequel la
# garde produirait un faux positif à chaque tâche sans modification.
# =====================================================================================================

def test_FORME_sensB_a_parallel_session_committed_my_work_is_DETECTED(tmp_path):
    """⚠️ LE CŒUR DE LA LEVÉE DE LIMITE — forme réelle du 2026-09-01 (arrivé DEUX fois) : un
    implémenteur trouve `git diff HEAD` VIDE sur ses propres chemins parce qu'une session parallèle a
    committé son contenu.

    1. je prends mon empreinte ; 2. j'écris mon travail ; 3. une session PARALLÈLE committe ce chemin
    (`git commit -- <path>`, path-scopé, exactement la discipline du dépôt) et emporte mon contenu ;
    4. `detect_preempted()` doit TIRER et NOMMER le commit porteur.
    """
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")

    # la session parallèle committe MON contenu, sans le savoir : commit path-scopé sur le même chemin.
    _git(["commit", "-q", "-m", "session parallele emporte mon travail", "--", _FILE], repo)
    voleur = _head_sha(repo)

    # état constaté par l'implémenteur : plus rien à committer, alors qu'il a bel et bien édité.
    assert _git(["diff", "HEAD", "--name-only", "--", _FILE], repo).strip() == ""

    report = detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert _FILE in report, "le sens B n'a PAS été détecté alors qu'il est mécaniquement détectable"
    assert report[_FILE]["commit"] == voleur          # le commit est NOMMÉ, pas juste « un commit »
    assert report[_FILE]["matched_by_content"] is True  # apparié PAR CONTENU, pas par simple `log -1`
    assert "session parallele emporte mon travail" in report[_FILE]["subject"]

    # le message doit dire QUOI FAIRE, pas seulement constater.
    msg = str(WorkPreempted(report))
    assert voleur[:8] in msg
    assert "NE PAS re-committer" in msg
    assert "SIGNALER" in msg


def test_POSITIVE_sensB_normal_work_in_progress_is_NOT_flagged(tmp_path):
    """Cas positif apparié : j'ai du travail à committer -> silence. Sans lui, une garde qui alerte
    toujours serait aussi inutile qu'une garde qui n'alerte jamais.

    ⚠️ HEAD AVANCE ici sur le chemin (commit d'une session parallèle) — sans cela le test ne tiendrait
    RIEN : le bornage `head_sha..HEAD` le rendrait muet quoi qu'il arrive, et il passerait même si la
    condition « il reste du diff » était retirée (vérifié par mutation). C'est la configuration réelle :
    dans un arbre partagé, HEAD bouge pendant qu'on travaille."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    _append(repo, "\n\ndef parallel_work():\n    return 'theirs'\n")
    _git(["commit", "-q", "-m", "session parallele", "--", _FILE], repo)   # HEAD avance sur le chemin

    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")
    _git(["add", _FILE], repo)
    assert detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo) == {}


def test_DISCRIMINANT_sensB_no_edit_at_all_is_NOT_flagged(tmp_path):
    """⚠️ LE CAS QUI SÉPARE : « on a committé mon travail » et « je n'ai rien édité » ont TOUS DEUX un
    `git diff HEAD` vide. Les confondre produirait un faux positif à CHAQUE tâche sans modification.
    Le discriminant est le contenu de l'arbre comparé à l'EMPREINTE, pas le diff.

    ⚠️ Là encore HEAD doit AVANCER sur le chemin pour que le test tienne quelque chose : ici la session
    parallèle committe le contenu qu'elle avait laissé dans l'arbre AVANT mon empreinte. Sans ce commit,
    le test passerait même en retirant le discriminant (vérifié par mutation) ; avec lui, le retirer
    produit l'alerte à tort."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")

    _append(repo, "\n\ndef parallel_uncommitted():\n    return 'theirs'\n")   # AVANT mon empreinte
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    _git(["commit", "-q", "-m", "parallele committe son propre travail", "--", _FILE], repo)

    assert _git(["diff", "HEAD", "--name-only", "--", _FILE], repo).strip() == ""  # même symptôme...
    # ...mais l'arbre est IDENTIQUE à l'empreinte : je n'ai rien édité, rien n'a été préempté.
    assert detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo) == {}


def test_LIMITE_CONNUE_sensB_content_from_another_session_also_alerts(tmp_path):
    """⚠️ PORTÉE HONNÊTE, gravée exécutablement : la garde observe « l'arbre a changé », pas « J'ai
    édité » — et dans un arbre PARTAGÉ, une session parallèle peut écrire dans l'arbre après mon
    empreinte. Ce contenu-là, committé par elle, déclenche AUSSI l'alerte, alors qu'il n'est pas le mien.

    Ce n'est pas un bug qu'on masque : c'est la raison pour laquelle (a) l'alerte est un AVERTISSEMENT et
    non un blocage, et (b) son message impose de VÉRIFIER que le contenu porté est bien le sien."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    # ce n'est PAS moi qui écris : session parallèle, après mon empreinte, dans l'arbre partagé.
    _append(repo, "\n\ndef not_mine_at_all():\n    return 'theirs'\n")
    _git(["commit", "-q", "-m", "parallele", "--", _FILE], repo)

    report = detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert _FILE in report                                    # la garde ne sait pas distinguer l'auteur
    assert "bien LE TIEN" in str(WorkPreempted(report))        # ...donc elle le fait vérifier


def test_sensB_untracked_new_file_is_NOT_flagged(tmp_path):
    """Second faux positif fermé : `git diff HEAD -- <chemin>` est AUSSI vide pour un fichier non tracké
    (il n'est pas dans HEAD, donc pas dans le diff). Un nouveau fichier que je viens de créer et pas
    encore stagé ne doit pas être annoncé comme « committé par quelqu'un d'autre ».

    ⚠️ Test de PROPRIÉTÉ, pas de ligne : la mutation montre que le garde-fou « aucun commit identifiable »
    couvre déjà ce cas, l'exclusion « absent de HEAD » étant de la défense en profondeur."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    nouveau = "brand_new.py"
    snapshot([nouveau], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)   # n'existe pas encore
    with open(os.path.join(repo, nouveau), "w", encoding="utf-8") as f:
        f.write("def neuf():\n    return 3\n")

    assert _git(["diff", "HEAD", "--name-only", "--", nouveau], repo).strip() == ""  # même symptôme...
    assert detect_preempted([nouveau], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo) == {}


def test_sensB_my_OWN_commit_declared_via_confirm_is_NOT_flagged(tmp_path):
    """Faux positif principal restant : avoir committé SOI-MÊME laisse exactement la même signature
    (arbre != empreinte, `git diff HEAD` vide). `confirm_commit(..., owner=...)` inscrit le SHA dans
    l'empreinte, ce qui le désamorce — c'est la raison pour laquelle les deux limites sont solidaires."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")
    _git(["add", _FILE], repo)
    _git(["commit", "-q", "-m", "mon propre commit", "--", _FILE], repo)
    mien = _head_sha(repo)

    # sans déclaration, la signature est indiscernable d'une préemption -> alerte (attendu).
    assert _FILE in detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)

    confirm_commit(mien, [_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    assert detect_preempted([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo) == {}


def test_CLI_sensB_is_a_WARNING_by_default_and_blocks_only_with_strict(tmp_path, capsys):
    """Le CHOIX de conception se teste, il ne se déclare pas : par (2) il n'y a RIEN à committer sur le
    chemin préempté, donc bloquer n'empêcherait aucun dégât mais ferait échouer le commit légitime des
    AUTRES chemins de la même tâche. Défaut = avertissement VISIBLE (stderr) + code 0 ; `--strict` pour
    qui veut un hook dur."""
    repo = _init_repo(tmp_path)
    snap_dir = str(tmp_path / "snaps")
    snapshot([_FILE], owner="ma-tache", snapshot_dir=snap_dir, cwd=repo)
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n")
    _git(["commit", "-q", "-m", "session parallele", "--", _FILE], repo)

    rc = _cli(["verify", _FILE, "--owner", "ma-tache", "--dir", snap_dir, "--cwd", repo])
    err = capsys.readouterr().err
    assert rc == 0, "un commit légitime ne doit pas échouer sur un avertissement de préemption"
    assert "PRÉEMPTÉ" in err and "NE PAS re-committer" in err   # mais l'alerte doit être VISIBLE

    rc = _cli(["verify", _FILE, "--owner", "ma-tache", "--dir", snap_dir, "--cwd", repo, "--strict"])
    assert rc == 2, "--strict doit rendre la préemption bloquante"


# =====================================================================================================
# LIMITE 2 — `git add` et `git commit` ne sont PAS atomiques sur un index partagé.
# Le rituel « inspecter `git diff --cached` avant de committer » est nécessaire mais PAS suffisant :
# la fenêtre de course est APRÈS l'inspection.
# =====================================================================================================

def test_FORME_race_between_add_and_commit_drops_a_path_SILENTLY(tmp_path):
    """⚠️ Forme réelle du 2026-09-01 : une session parallèle committe le même chemin ENTRE mon
    `git add` et mon `git commit`. Le chemin disparaît de mon commit SANS erreur ni avertissement.

    Ce test prouve d'abord la NÉCESSITÉ de la garde (le chemin était bien dans `git diff --cached`,
    l'inspection pré-commit passait) puis que `confirm_commit()` TIRE en nommant le manquant.
    """
    repo = _init_repo_two_files(tmp_path)

    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n", _FILE)
    _append(repo, "\n\ndef my_other_work():\n    return 'mine too'\n", _OTHER)
    _git(["add", _FILE, _OTHER], repo)

    # rituel pré-commit : l'inspection du stage PASSE — les deux chemins y sont.
    stage = _git(["diff", "--cached", "--name-only"], repo).split()
    assert _FILE in stage and _OTHER in stage

    # COURSE : la session parallèle committe _FILE juste après mon inspection, avant mon commit.
    _git(["commit", "-q", "-m", "session parallele", "--", _FILE], repo)

    # mon commit : aucune erreur, aucun avertissement — mais _FILE n'y est plus.
    _git(["commit", "-q", "-m", "mon commit", "--", _FILE, _OTHER], repo)
    mien = _head_sha(repo)
    porte = _git(["diff-tree", "--no-commit-id", "--name-only", "-r", mien], repo).split()
    assert porte == [_OTHER], "la perte silencieuse n'a pas été reproduite — le test ne prouve rien"

    with pytest.raises(MissingPathsInCommit) as exc:
        confirm_commit(mien, [_FILE, _OTHER], cwd=repo)
    assert exc.value.missing == [_FILE]
    assert exc.value.present == [_OTHER]
    assert _FILE in str(exc.value)                     # NOMME le manquant
    assert "CORRECTIF" in str(exc.value)               # et dit quoi faire


def test_POSITIVE_a_commit_carrying_all_expected_paths_PASSES(tmp_path):
    """Cas positif apparié : sans course, le commit porte les deux chemins -> `confirm_commit` passe.
    Sans lui, une vérification qui refuse tout passerait la revue."""
    repo = _init_repo_two_files(tmp_path)
    _append(repo, "\n\ndef my_own_work():\n    return 'mine'\n", _FILE)
    _append(repo, "\n\ndef my_other_work():\n    return 'mine too'\n", _OTHER)
    _git(["add", _FILE, _OTHER], repo)
    _git(["commit", "-q", "-m", "mon commit", "--", _FILE, _OTHER], repo)

    res = confirm_commit(_head_sha(repo), [_FILE, _OTHER], cwd=repo)
    assert sorted(res["present"]) == sorted([_FILE, _OTHER])
    assert res["unexpected"] == []


def test_confirm_reports_an_unknown_sha_instead_of_passing_silently(tmp_path):
    """Un SHA inexistant ne doit pas être un succès vide : rien n'est confirmé, donc la garde TIRE."""
    repo = _init_repo(tmp_path)
    with pytest.raises(MissingPathsInCommit):
        confirm_commit("0" * 40, [_FILE], cwd=repo)


def test_check_prefix_is_excluded_from_the_instrument_calibration_ratchet():
    """⚠️ Piège de nommage signalé dans la dette P2.22 : ce fichier s'appelle `check_*.py`, donc
    `check_instrument_calibration.scan_instruments` doit l'EXCLURE (comme `check_record_links.py`) —
    sinon cette garde elle-même deviendrait une dette de calibration non calibrée par accident."""
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from tools.check_instrument_calibration import scan_instruments
    found = scan_instruments()
    assert all(not path.endswith("check_staged_authorship.py") for path in found.values())
