"""Contre-exemple GELÉ du crochet de fusion `tools/hooks/commit-msg` — il doit pouvoir REFUSER.

LE TROU (mesuré le 2026-09-24 sur dépôt jetable, git 2.54.0.windows.1). Sur une fusion PROPRE :

    pre-commit           0 appel       (1 sur un commit ordinaire : la sonde marche)
    prepare-commit-msg   armé, code 1 -> fusion ANNULÉE
    commit-msg           armé, code 1 -> fusion ANNULÉE, MERGE_HEAD présent
    post-merge           appelé, code de retour IGNORÉ -- il ne peut rien refuser

Les portes du dépôt ne s'armaient donc PAS au moment exact où le code d'une autre branche entre dans
la sienne. `commit-msg` est le seul crochet qui (a) tire sur une fusion propre et (b) sait refuser.

⚠️ LA FORME DU CONTRE-EXEMPLE EST LE CŒUR DU FICHIER, et elle porte sur l'UNION, pas sur une branche :
deux branches corrigent le MÊME compte publié à la MÊME valeur en comptant des objets DIFFÉRENTS.
Chacune est localement juste ; git fusionne SANS CONFLIT (les deux côtés écrivent la même ligne) ; à
l'union il y a un objet de plus que ce que la balise annonce. C'est la situation vivante qui a motivé
la tâche : deux sessions qui corrigent les mêmes compteurs publiés, à des valeurs différentes, en
comptant des objets différents — seule leur mémoire l'empêche aujourd'hui.

⚠️ DEUXIÈME MESURE, celle qui a décidé la FORME du crochet : relancer le pre-commit tel quel ne
suffit pas. Ses portes se déclenchent sur `git diff --cached`, qui compare au PREMIER PARENT :

    diff vs HEAD = [docs/preregistrations/b.json]                       <- la porte 8 NE tire PAS
    diff vs BASE = [CLAUDE.md, .../a.json, .../b.json]                  <- elle tire

Le document porteur du compte est identique à HEAD (les deux côtés y ont écrit la même chose), donc
absent du diff. Un crochet naïf aurait laissé passer son propre contre-exemple. D'où le bloc
`AGAGI:FUSION-SCOPE` du pre-commit, dont ce fichier extrait les lignes VERBATIM — si quelqu'un le
retire, ces cas rougissent.

Chaque cas construit son dépôt JETABLE dans `tmp_path` (jamais un worktree d'AGAGI : `core.hooksPath`
y pointe en ABSOLU vers `.git/hooks` du dépôt principal, donc tout test de crochet dans un worktree
armerait la flotte entière). L'environnement git est purgé des `GIT_*` hérités — sous le hook,
`GIT_INDEX_FILE` désigne l'index du VRAI dépôt (défaut mesuré le 2026-09-14).
"""
import os
import re
import shutil
import subprocess

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PRE_COMMIT = os.path.join(_ROOT, "tools", "hooks", "pre-commit")
_COMMIT_MSG = os.path.join(_ROOT, "tools", "hooks", "commit-msg")
_PORTE = os.path.join(_ROOT, "tools", "check_synthesis_counts.py")

# Le compteur jouet : `regles_scellees` compte les .json de docs/preregistrations/. C'est le seul du
# registre qui ne lit QUE le système de fichiers (aucun import d'un autre cliquet) -- un dépôt jetable
# peut donc le faire tourner tel quel, sans copier la moitié de tools/.
_BALISE = "Règles scellées : **{n} scellées** <!-- count:regles_scellees={n} -->\n"


# --------------------------------------------------------------------------------------------------
# Extraction VERBATIM des blocs du hook versionné. Recopier ces lignes les ferait diverger en silence :
# le dépôt jouet exécute les vraies lignes, et leur disparition fait ROUGIR (jamais passer).
# --------------------------------------------------------------------------------------------------

def _lire(chemin):
    with open(chemin, encoding="utf-8") as fh:
        return fh.read()


def _bloc(src, debut, fin, quoi):
    i = src.find(debut)
    assert i >= 0, f"{quoi} : marqueur « {debut} » absent de tools/hooks/pre-commit"
    j = len(src) if fin is None else src.find(fin, i)
    assert j >= 0, f"{quoi} : marqueur de fin « {fin} » absent de tools/hooks/pre-commit"
    return src[i:j if fin is None else j + len(fin)]


def _pre_commit_jouet(log_rel):
    """Le pre-commit du dépôt jouet : le squelette du vrai (porte absente + portée de fusion + porte 8 +
    témoin), plus un COMPTEUR D'APPELS. Les quatre blocs sont extraits verbatim du fichier versionné.

    ⚠️ PORTE-ABSENTE (2026-09-26, P2.121 famille 2). La « queue du hook » court de FUSION-SANS-TEMOIN à la
    sortie, et elle contient désormais les portes 23 et 24, dont les outils n'existent pas dans le dépôt
    jetable : `python tools/check_e19_optimizer_sweep.py` y rendait « can't open file », la porte le lisait
    comme un refus, et le commit de BASE échouait — 18 cas rouges, sur POSIX ET sous Windows (mesuré le
    2026-09-26 : l'inventaire les disait verts sous Windows). Le vrai hook porte déjà la parade — le bloc
    PORTE-ABSENTE saute une porte absente du disque ET de HEAD, en le disant — et le squelette jouet ne
    l'extrayait pas. Il l'extrait : toute porte future ajoutée dans la queue sera sautée ici à voix haute,
    au lieu de rendre ce fichier rouge pour une raison étrangère à la fusion."""
    src = _lire(_PRE_COMMIT)
    absente = _bloc(src, "# >>> AGAGI:PORTE-ABSENTE >>>", "# <<< AGAGI:PORTE-ABSENTE <<<", "porte absente")
    scope = _bloc(src, "# >>> AGAGI:FUSION-SCOPE >>>", "# <<< AGAGI:FUSION-SCOPE <<<", "portée de fusion")
    porte8 = _bloc(src, "# 8. COMPTES PUBLIES", "# 9. SEPARATION DE LA BARRE", "porte 8")
    marqueur = _bloc(src, "# >>> AGAGI:FUSION-SANS-TEMOIN >>>", None, "queue du hook")
    assert "exit $fail" in marqueur, (
        "le bloc AGAGI:FUSION-SANS-TEMOIN doit courir jusqu'à la sortie du hook")
    assert "check_synthesis_counts" in porte8, "la porte 8 extraite ne lance pas son cliquet"
    return (
        "#!/bin/sh\n"
        "fail=0\n"
        f'echo appel >> "$(git rev-parse --git-dir)/{log_rel}"\n'
        "\n" + absente + "\n\n" + scope + "\n\n" + porte8 + "\n" + marqueur
    )


# --------------------------------------------------------------------------------------------------
# Le dépôt jetable.
# --------------------------------------------------------------------------------------------------

def _env_git_vierge():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class _Depot:
    def __init__(self, chemin, env):
        self.p = chemin
        self.env = env
        self.log = os.path.join(chemin, ".git", "appels.log")

    def git(self, *args, check=True, env=None):
        r = subprocess.run(
            ["git", "-C", str(self.p), "-c", "user.name=t", "-c", "user.email=t@t", *args],
            capture_output=True, env=env if env is not None else self.env)
        sortie = (r.stdout + r.stderr).decode("utf-8", errors="replace")
        if check and r.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} a échoué ({r.returncode}) :\n{sortie}")
        return r.returncode, sortie

    def ecrire(self, rel, texte):
        p = os.path.join(self.p, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texte)

    def balise(self, n):
        self.ecrire("CLAUDE.md", _BALISE.format(n=n))

    def appels(self):
        if not os.path.isfile(self.log):
            return 0
        with open(self.log, encoding="utf-8") as fh:
            return len([l for l in fh if l.strip()])

    def raz(self):
        """Remet le compteur d'appels a zero : chaque cas ne mesure QUE son action finale."""
        if os.path.isfile(self.log):
            os.remove(self.log)

    def head(self):
        return self.git("rev-parse", "HEAD")[1].strip()


def _depot(tmp_path, monkeypatch, avec_commit_msg=True):
    """Dépôt jetable armé : hooks dans `<repo>/.githooks` désigné par `core.hooksPath` en ABSOLU —
    la configuration EXACTE d'AGAGI, pour que le crochet soit jugé dans les conditions réelles."""
    for k in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY"):
        monkeypatch.delenv(k, raising=False)
    if shutil.which("git") is None:
        pytest.skip("git introuvable sur cette machine : le crochet de fusion n'est pas mesurable ici")

    repo = tmp_path / "jetable"
    repo.mkdir()
    d = _Depot(str(repo), _env_git_vierge())
    rc, sortie = d.git("init", "-q", "-b", "base", ".", check=False)
    if rc != 0:
        pytest.skip(f"git refuse d'initialiser un dépôt jetable (git init -b) : {sortie.strip()}")

    hooks = os.path.join(str(repo), ".githooks")
    os.makedirs(hooks, exist_ok=True)
    d.git("config", "core.hooksPath", hooks)

    with open(os.path.join(hooks, "pre-commit"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_pre_commit_jouet("appels.log"))
    os.chmod(os.path.join(hooks, "pre-commit"), 0o755)

    # ⚠️ Copié SI PRÉSENT, jamais fabriqué : tant que `tools/hooks/commit-msg` n'existe pas, la
    # fusion fautive passe et le cas (1) ROUGIT. C'est le RED de ce fichier, pas un skip.
    if os.path.isfile(_COMMIT_MSG) and avec_commit_msg:
        shutil.copyfile(_COMMIT_MSG, os.path.join(hooks, "commit-msg"))
        os.chmod(os.path.join(hooks, "commit-msg"), 0o755)

    os.makedirs(os.path.join(str(repo), "tools"), exist_ok=True)
    shutil.copyfile(_PORTE, os.path.join(str(repo), "tools", "check_synthesis_counts.py"))

    d.ecrire("docs/preregistrations/base.json", "{}\n")
    d.ecrire("notes.txt", "base\n")
    d.balise(1)
    d.git("add", "-A")
    d.git("commit", "-q", "-m", "base")
    d.raz()
    return d


def _deux_branches(d, divergent, conflit=False):
    """A ajoute un objet et porte la balise à 2. B fait de même (divergent) ou non (contrôle)."""
    d.git("checkout", "-q", "-b", "A")
    d.ecrire("docs/preregistrations/a.json", "{}\n")
    d.balise(2)
    if conflit:
        d.ecrire("notes.txt", "version A\n")
    d.git("add", "-A")
    d.git("commit", "-q", "-m", "A : un objet de plus, balise a 2")

    d.git("checkout", "-q", "base")
    d.git("checkout", "-q", "-b", "B")
    if divergent:
        # ⚠️ MÊME balise, MÊME valeur, AUTRE objet : c'est ça qui ne conflicte pas.
        d.ecrire("docs/preregistrations/b.json", "{}\n")
        d.balise(2)
    else:
        d.ecrire("lisezmoi.txt", "cote B : rien qui se compte\n")
    if conflit:
        d.ecrire("notes.txt", "version B\n")
    d.git("add", "-A")
    d.git("commit", "-q", "-m", "B")

    d.git("checkout", "-q", "A")
    d.raz()


# --------------------------------------------------------------------------------------------------
# 1. LE CAS NÉGATIF — la fusion dont le compte publié est faux À L'UNION doit être REFUSÉE.
# --------------------------------------------------------------------------------------------------

def test_une_fusion_PROPRE_fausse_a_l_UNION_est_REFUSEE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc != 0, (
        "la fusion a été ACCEPTÉE alors que la balise annonce 2 règles scellées pour 3 fichiers à "
        f"l'union — aucune porte n'a tiré.\n{sortie}")
    assert "CHIFFRE" in sortie.upper(), f"le refus ne vient pas de la porte des comptes :\n{sortie}"
    assert d.head() == avant, f"un commit de fusion a quand même été créé :\n{sortie}"
    assert os.path.isfile(os.path.join(d.p, ".git", "MERGE_HEAD")), (
        "la fusion doit rester en cours (rien n'est committé), pas être avalée")
    assert d.appels() == 1, (
        f"le pre-commit doit tourner UNE fois sur une fusion propre, or {d.appels()}")


# --------------------------------------------------------------------------------------------------
# 2. LE CONTRÔLE POSITIF — sans divergence, la MÊME fusion doit PASSER. Sans ce cas, la garde ne
# pourrait pas échouer : un crochet qui refuse toute fusion passerait le cas (1) en ne mesurant rien.
# --------------------------------------------------------------------------------------------------

def test_controle_positif_la_meme_fusion_SANS_divergence_PASSE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=False)
    avant = d.head()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc == 0, f"une fusion dont le compte est JUSTE à l'union doit passer :\n{sortie}"
    assert d.head() != avant, "le commit de fusion n'a pas été créé"
    assert d.git("rev-parse", "HEAD^2")[0] == 0, "le commit créé n'est pas une fusion"
    assert "syntheses :" in sortie, (
        f"la porte n'a pas tourné : le vert de ce contrôle ne prouverait rien.\n{sortie}")
    assert d.appels() == 1, f"pre-commit doit avoir tourné UNE fois, or {d.appels()}"


# --------------------------------------------------------------------------------------------------
# 3. (a) Un commit ORDINAIRE ne double pas le travail.
# --------------------------------------------------------------------------------------------------

def test_un_commit_ORDINAIRE_ne_double_pas_les_portes(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    d.ecrire("docs/preregistrations/c.json", "{}\n")
    d.balise(2)
    d.git("add", "-A")
    rc, sortie = d.git("commit", "-q", "-m", "commit ordinaire", check=False)

    assert rc == 0, f"le commit ordinaire doit passer :\n{sortie}"
    assert d.appels() == 1, (
        f"commit-msg doit sortir immédiatement hors fusion : {d.appels()} appels de pre-commit "
        f"au lieu de 1.\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 3. (b) Une fusion CONFLICTUELLE résolue ne lance pas les portes DEUX fois (témoin du pre-commit).
# --------------------------------------------------------------------------------------------------

def test_une_fusion_CONFLICTUELLE_resolue_tire_les_portes_DEUX_fois_et_c_est_le_prix_assume(
        tmp_path, monkeypatch):
    """⚠️ CE CAS A CHANGÉ DE SENS LE 2026-09-24, et c'est le point de la troisième version.
    Il exigeait UNE exécution : un témoin posé par `pre-commit` disait à `commit-msg` de ne pas
    relancer. Ce témoin est SUPPRIMÉ — sa dernière identité couvrait l'INDEX alors que les portes de
    ce dépôt jugent le DISQUE, et l'arbre est partagé donc le disque change tout seul (mesure
    appariée : le même état du monde passait avec zéro porte grâce à un résidu, et était refusé sans
    lui). Les portes tournent donc DEUX fois ici : une au commit de résolution, une relancée par
    `commit-msg`. C'est un COÛT, pas un défaut, et il était déjà payé sans qu'on le sache — dès qu'un
    éditeur de message dépassait 120 s, le témoin périmait et les portes tournaient deux fois.
    Le cas le GÈLE pour que personne ne « ré-optimise » ce raccourci sans relire pourquoi il est
    tombé : un chiffre qui passerait de 2 à 1 signifierait qu'un mécanisme de saut est revenu."""
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=False, conflit=True)

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion conflictuelle", check=False)
    assert rc != 0 and "CONFLICT" in sortie.upper(), f"le conflit attendu n'a pas eu lieu :\n{sortie}"
    assert d.appels() == 0, "aucun pre-commit ne doit tourner avant la résolution"

    d.ecrire("notes.txt", "resolution\n")
    d.git("add", "notes.txt")
    rc, sortie = d.git("commit", "-q", "-m", "resolution", check=False)

    assert rc == 0, f"le commit de résolution doit passer :\n{sortie}"
    assert d.appels() == 2, (
        f"{d.appels()} exécution(s) des portes au lieu de 2. Si c'est 1, un mécanisme de SAUT est "
        f"revenu : relire pourquoi le témoin a été supprimé (classe E31) avant de le rétablir.\n{sortie}")
    assert not os.path.isfile(_temoin(d)), (
        "un témoin a été posé : le raccourci supprimé est revenu, et avec lui la possibilité de "
        "désarmer les portes par un résidu dans un git-dir PARTAGÉ")


# --------------------------------------------------------------------------------------------------
# 3. (c) Sans pre-commit installé, le crochet le DIT et laisse passer — il ne plante pas.
# --------------------------------------------------------------------------------------------------

def test_un_pre_commit_ABSENT_laisse_passer_avec_un_message(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    os.remove(os.path.join(d.p, ".githooks", "pre-commit"))

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion sans pre-commit", check=False)

    assert rc == 0, (
        f"un pre-commit absent doit laisser passer (jamais bloquer la flotte) :\n{sortie}")
    assert "aucun pre-commit" in sortie, (
        f"le crochet doit DIRE que les portes ne sont pas armées, pas se taire :\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 4. Le fichier versionné porte bien les deux blocs dont dépend tout le reste.
# --------------------------------------------------------------------------------------------------

def test_le_pre_commit_versionne_porte_la_portee_de_fusion_et_le_temoin():
    src = _lire(_PRE_COMMIT)
    assert "# >>> AGAGI:FUSION-SCOPE >>>" in src, (
        "sans la portée de fusion, relancer les portes ne verrait que le côté ENTRANT (mesuré)")
    assert "merge-base" in src, "la portée de fusion doit comparer à la BASE, pas au premier parent"
    assert "# >>> AGAGI:FUSION-SANS-TEMOIN >>>" in src, (
        "le bloc qui DOCUMENTE la suppression du témoin a disparu. Il ne fait rien s'exécuter — sa "
        "seule fonction est d'empêcher qu'une session future, voyant les portes tourner deux fois "
        "sur une fusion conflictuelle, ne « ré-optimise » un jeton dont trois identités sont tombées")
    assert "AGAGI:FUSION-MARQUEUR" not in src, (
        "l'ancien bloc de pose du témoin est revenu : relire la classe E31 avant de le rétablir")
    assert os.path.isfile(_COMMIT_MSG), (
        "tools/hooks/commit-msg est le livrable : sans lui, une fusion propre n'arme aucune porte")


# --------------------------------------------------------------------------------------------------
# 5. DEFAUT 1 (gravite HAUTE) -- LE TEMOIN DOIT AVOIR UNE IDENTITE.
# Mesure de la revue adversariale (2026-09-24) : `GIT_EDITOR=false git commit` fait AVORTER le commit
# (rc=1) mais le temoin survivait dans le git-dir ; ensuite N'IMPORTE QUELLE fusion propre le voyait
# et sautait TOUTES les portes, en silence. Le git-dir etant PARTAGE par une dizaine de sessions, le
# temoin d'une session desarmait la fusion d'une autre. Les deux cas ci-dessous gelent la propriete :
# un temoin qui ne decrit pas CETTE fusion-ci ne peut pas la desarmer.
# --------------------------------------------------------------------------------------------------

def _temoin(d):
    return os.path.join(d.p, ".git", "agagi-pre-commit-ran")


def test_un_temoin_ETRANGER_ne_desarme_PAS_une_fusion_fautive(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    # Temoin pose A LA MAIN : exactement ce que laissait un commit avorte, ou une autre session.
    with open(os.path.join(d.p, ".git", "agagi-pre-commit-ran"), "w", encoding="utf-8") as fh:
        fh.write("")

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc != 0, (
        "un temoin ETRANGER a desarme les portes : la fusion fausse a l'union est passee. Un temoin "
        f"sans identite est une garde qu'on desarme sans le savoir.\n{sortie}")
    assert "CHIFFRE" in sortie.upper(), f"le refus ne vient pas de la porte des comptes :\n{sortie}"
    assert d.head() == avant, f"un commit de fusion a quand meme ete cree :\n{sortie}"
    assert d.appels() == 1, f"les portes doivent tourner UNE fois, or {d.appels()}"


def test_un_commit_ORDINAIRE_AVORTE_ne_desarme_PAS_la_fusion_suivante(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    # Commit ordinaire AVORTE : pre-commit tourne, puis l'editeur echoue et git annule tout.
    d.ecrire("notes.txt", "brouillon\n")
    d.git("add", "notes.txt")
    env = dict(d.env)
    env["GIT_EDITOR"] = "false"
    rc, sortie = d.git("commit", check=False, env=env)  # sans -m : l'editeur est sollicite
    assert rc != 0, f"le cas exige un commit AVORTE ; il a reussi :\n{sortie}"
    assert d.head() == avant, "rien ne doit avoir ete committe"

    # ⚠️ POURQUOI CE CAS EST VERT, MESURE PLUTOT QUE SUPPOSE (2026-09-24, DEUXIEME revue). Il l'est
    # parce qu'un commit ORDINAIRE ne pose plus AUCUN temoin (correction (a)) : il n'y a rien a
    # desarmer, donc ce cas ne peut PAS juger l'identite du temoin. Sans l'assertion ci-dessous il
    # serait vert « parce qu'il ne se passe rien » -- un vert qui ne mesure rien ressemble a tous les
    # autres. Le cas qui juge vraiment l'identite est la fusion avortee a l'editeur (section 10),
    # SEUL scenario des cinq testes qui laisse un residu.
    assert not os.path.isfile(_temoin(d)), (
        "un commit ORDINAIRE avorte a pose un temoin : la correction (a) -- ne poser un temoin que "
        "si MERGE_HEAD est present -- a ete perdue, et ce cas ne mesure plus ce qu'il annonce")

    d.git("reset", "-q", "--hard", "HEAD")  # la session abandonne ; le git-dir garde ce qu'il garde
    d.raz()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc != 0, (
        "un commit ordinaire AVORTE a laisse de quoi desarmer la fusion suivante : elle est passee "
        f"alors que son compte est faux a l'union.\n{sortie}")
    assert d.head() == avant, f"un commit de fusion a quand meme ete cree :\n{sortie}"
    assert d.appels() == 1, f"les portes doivent tourner UNE fois, or {d.appels()}"


# --------------------------------------------------------------------------------------------------
# 6. DEFAUT 2 -- `git merge --squash` reproduisait le trou INTEGRALEMENT.
# Mesure (2026-09-24, git 2.54.0.windows.1) : un squash ne pose AUCUN MERGE_HEAD (git ecrit
# SQUASH_MSG), donc ni le crochet ni le bloc FUSION-SCOPE ne s'armaient, et la meme divergence
# passait (rc=0). Le commit qui conclut un squash est ORDINAIRE : git lance pre-commit lui-meme
# (mesure : 1 appel) -- il n'y a donc rien a relancer, seulement une PORTEE a elargir.
# --------------------------------------------------------------------------------------------------

def test_un_SQUASH_faux_a_l_UNION_est_REFUSE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    rc, sortie = d.git("merge", "--squash", "B", check=False)
    assert rc == 0, f"le squash lui-meme doit passer (aucun conflit) :\n{sortie}"
    assert not os.path.isfile(os.path.join(d.p, ".git", "MERGE_HEAD")), (
        "la mesure qui motive ce cas est justement l'ABSENCE de MERGE_HEAD pendant un squash")
    assert os.path.isfile(os.path.join(d.p, ".git", "SQUASH_MSG")), (
        "git doit poser SQUASH_MSG : c'est la seule trace du cote entrant pendant un squash")
    d.raz()

    rc, sortie = d.git("commit", "-q", "-m", "squash de B", check=False)

    assert rc != 0, (
        "le squash est passe alors que la balise annonce 2 regles scellees pour 3 fichiers a "
        f"l'union : le trou de la fusion se reproduit integralement sur --squash.\n{sortie}")
    assert "CHIFFRE" in sortie.upper(), f"le refus ne vient pas de la porte des comptes :\n{sortie}"
    assert d.head() == avant, f"un commit a quand meme ete cree :\n{sortie}"
    assert d.appels() == 1, (
        f"le commit qui conclut un squash est ORDINAIRE : pre-commit doit tourner UNE fois, "
        f"or {d.appels()}")


def test_controle_positif_un_SQUASH_sans_divergence_PASSE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=False)
    avant = d.head()

    d.git("merge", "--squash", "B", check=False)
    d.raz()
    rc, sortie = d.git("commit", "-q", "-m", "squash de B", check=False)

    assert rc == 0, f"un squash dont le compte est JUSTE a l'union doit passer :\n{sortie}"
    assert d.head() != avant, "le commit de squash n'a pas ete cree"
    assert "syntheses :" in sortie, (
        f"la porte n'a pas tourne : le vert de ce controle ne prouverait rien.\n{sortie}")
    assert d.appels() == 1, f"pre-commit doit avoir tourne UNE fois, or {d.appels()}"


# --------------------------------------------------------------------------------------------------
# 7. DEFAUT 3 -- la branche « pre-commit non executable » de commit-msg avait zero cas.
# MESURE sur cette machine (Git Bash / Windows, git 2.54.0.windows.1) : `test -x` ne lit PAS le bit
# de mode -- `chmod -x` est un no-op et un fichier a 644 PORTANT UN SHEBANG est vu executable. Ce qui
# decide ici, c'est le SHEBANG : un fichier sans shebang est vu NON executable, meme a 755. Le cas
# ci-dessous fabrique donc un pre-commit sans shebang, et MESURE `test -x` avant d'exiger quoi que ce
# soit -- sur une plate-forme ou le bit de mode decide vraiment, le meme cas reste valable.
# --------------------------------------------------------------------------------------------------

def test_un_pre_commit_NON_EXECUTABLE_laisse_passer_avec_un_message(tmp_path, monkeypatch):
    if shutil.which("sh") is None:
        pytest.skip("sh introuvable : `test -x` n'est pas mesurable ici")
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)

    pre = os.path.join(d.p, ".githooks", "pre-commit")
    corps = _lire(pre)
    assert corps.startswith("#!"), "le pre-commit jouet doit partir d'un shebang pour qu'on l'ote"
    with open(pre, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(corps.split("\n", 1)[1])
    os.chmod(pre, 0o644)

    vu_executable = subprocess.run(
        ["sh", "-c", '[ -x "$1" ]', "sonde", pre], capture_output=True).returncode == 0

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    if vu_executable:
        # La branche est INATTEIGNABLE dans cette configuration : le crochet lance le script quand
        # meme, et les portes tirent. On le DIT, on ne le presente pas comme une couverture.
        assert rc != 0, (
            "sur cette plate-forme `test -x` voit le fichier executable : les portes devaient donc "
            f"tirer normalement.\n{sortie}")
    else:
        assert rc == 0, (
            f"un pre-commit inexecutable doit laisser passer (jamais bloquer la flotte) :\n{sortie}")
        assert "cutable" in sortie, (
            f"le crochet doit DIRE que les portes ne sont pas armees, pas se taire :\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 8. DEFAUT 5 -- la base de fusion doit se poser AVANT un eventuel `--`, jamais apres.
# Aucun des appels actuels n'ecrit `--`, mais un site futur du type
# `git diff --cached --name-only -- <chemin>` recevrait la base APRES le `--`, ou git la lit comme un
# PATHSPEC : la sortie serait vide et la porte se tairait en silence. Le controle negatif (git NU)
# est dans le meme cas : sans lui, un vert ne prouverait pas que la portee a ete elargie.
# --------------------------------------------------------------------------------------------------

def _sonde_portee(d, ligne):
    scope = _bloc(_lire(_PRE_COMMIT), "# >>> AGAGI:FUSION-SCOPE >>>", "# <<< AGAGI:FUSION-SCOPE <<<",
                  "portee de fusion")
    chemin = os.path.join(d.p, "sonde.sh")
    with open(chemin, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("#!/bin/sh\n" + scope + "\n" + ligne + "\n")
    r = subprocess.run(["sh", "sonde.sh"], cwd=d.p, capture_output=True, env=d.env)
    return (r.stdout + r.stderr).decode("utf-8", errors="replace")


def test_la_portee_de_fusion_survit_a_un_pathspec_apres_double_tiret(tmp_path, monkeypatch):
    if shutil.which("sh") is None:
        pytest.skip("sh introuvable : le bloc de portee n'est pas executable ici")
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    # Fusion arretee AVANT le commit : MERGE_HEAD present, index = UNION, aucun conflit, aucun hook.
    d.git("merge", "--no-ff", "--no-commit", "B", check=False)
    assert os.path.isfile(os.path.join(d.p, ".git", "MERGE_HEAD")), "la fusion doit etre en cours"

    nu = _sonde_portee(d, 'command git diff --cached --name-only -- .')
    assert "CLAUDE.md" not in nu, (
        "CONTROLE NEGATIF : sans elargissement, le document porteur du compte est identique au "
        f"premier parent, donc ABSENT du diff. S'il y est deja, ce cas ne mesure rien.\n{nu}")

    sans_tiret = _sonde_portee(d, 'git diff --cached --name-only')
    assert "CLAUDE.md" in sans_tiret, (
        f"CONTROLE POSITIF : la forme SANS `--` doit voir le document porteur du compte.\n{sans_tiret}")

    avec_tiret = _sonde_portee(d, 'git diff --cached --name-only -- .')
    assert "CLAUDE.md" in avec_tiret, (
        "la base de fusion a ete posee APRES le `--` : git l'a lue comme un pathspec, la sortie est "
        f"amputee et la porte se tairait en silence.\n{avec_tiret}")


# --------------------------------------------------------------------------------------------------
# 9. DEFAUT 4 -- un chiffre publie se RECOMPUTE (regle du depot). Les commentaires annoncaient
# « 18 appels » ; la mesure en rend 17. Le piege est dans la commande elle-meme : un `grep -c` sans
# ancre compte AUSSI les lignes de commentaire qui citent la commande. La forme retenue (et ecrite
# dans le commentaire, pour qu'un lecteur la rejoue) exclut les commentaires.
# --------------------------------------------------------------------------------------------------

_MOTIF_APPELS = re.compile(r"^[^#\n]*git diff --cached --name-only", re.M)


def test_le_nombre_d_appels_annonce_dans_les_commentaires_se_RECOMPUTE():
    reel = len(_MOTIF_APPELS.findall(_lire(_PRE_COMMIT)))
    assert reel > 0, "aucun appel a `git diff --cached --name-only` : le motif est faux"
    for chemin in (_PRE_COMMIT, _COMMIT_MSG):
        src = _lire(chemin)
        annonces = re.findall(r"(\d+) appels", src)
        assert annonces, (
            f"{os.path.basename(chemin)} n'annonce aucun compte d'appels : le chiffre doit etre "
            "ecrit ET recomputable, pas sous-entendu")
        for a in annonces:
            assert int(a) == reel, (
                f"{os.path.basename(chemin)} annonce {a} appels a `git diff --cached --name-only`, "
                f"la mesure en rend {reel}. Recompute : "
                "grep -c '^[^#]*git diff --cached --name-only' tools/hooks/pre-commit")
        assert "grep -c" in src, (
            f"{os.path.basename(chemin)} doit porter la COMMANDE qui recompute son chiffre, "
            "sinon le lecteur ne peut que le croire")


# --------------------------------------------------------------------------------------------------
# 10. LE TEMOIN A ETE SUPPRIME -- et ces cas gelent le fait qu'AUCUN residu ne peut desarmer.
# TROIS identites ont ete essayees, TROIS refutees, la derniere par une re-verification adversariale
# qui lancait ses propres sondes :
#   v1  la seule PRESENCE du fichier -- un commit avorte laissait un residu qui desarmait TOUT ;
#   v2  (horodatage, HEAD, MERGE_HEAD) -- certifie « une fusion de B dans A », pas « CET etat-ci » :
#       la meme paire est reatteignable avec un index DIFFERENT (sequence reproduite 4 fois) ;
#   v3  + `git write-tree` -- REFUTEE AUSSI, et c'est la mesure qui tranche : l'identite couvre
#       l'INDEX, mais les portes de ce depot jugent le DISQUE (`check_synthesis_counts` compte des
#       FICHIERS, `check_amputation` et `check_instrument_calibration` balayent l'ARBRE). L'index
#       peut etre identique pendant que CE QUI EST JUGE a change -- et l'arbre est PARTAGE entre une
#       dizaine de sessions, donc il change tout seul. Mesure APPARIEE du refutateur : le meme etat
#       du monde passe rc=0 avec ZERO porte quand le residu est la, et est REFUSE rc=1 sans lui.
# CE QU'ON EN TIRE (classe E31) : quand l'identite d'un jeton ne peut pas couvrir ce que la
# verification JUGE, on ne raffine pas une quatrieme identite -- ON SUPPRIME LE RACCOURCI. Retirer
# le seul mecanisme capable de SAUTER des portes ne peut pas ouvrir de trou : remede MONOTONE.
# Les cas ci-dessous ne testent donc plus une identite : ils gelent qu'AUCUN fichier pose dans le
# git-dir, quel qu'il soit, ne change quoi que ce soit. C'est une propriete plus forte et plus
# simple a defendre -- et elle survit a toute future idee de jeton.
# ⚠️ Leur CONTROLE POSITIF est ailleurs : `test_controle_positif_la_meme_fusion_SANS_divergence_PASSE`
# (la fusion saine passe) et `..._CONFLICTUELLE_resolue_tire_les_portes_DEUX_fois_...` (le cout du
# retrait est chiffre). Sans eux, « refuser toujours » passerait tout ce qui suit sans rien mesurer.
# --------------------------------------------------------------------------------------------------

def test_une_FUSION_AVORTEE_A_L_EDITEUR_ne_laisse_AUCUN_residu_et_ne_desarme_rien(tmp_path, monkeypatch):
    """La sequence EXACTE qui a tue la v2 et la v3, rejouee contre la version sans temoin.
       (1) une fusion est REFUSEE par une porte  -> MERGE_HEAD RESTE en place ;
       (2) l'auteur corrige, git add, git commit -> pre-commit PASSE ;
       (3) le commit AVORTE a l'editeur         -> commit-msg n'a jamais tourne, donc n'a rien
           consomme. C'etait le SEUL des cinq scenarios testes qui laissait un residu ;
       (4) la fusion est abandonnee puis refaite avec un index DIFFERENT -> doit etre REFUSEE.
    Deux assertions, et la premiere est celle qui a du sens maintenant : il n'y a RIEN a consommer."""
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)
    assert rc != 0, f"la sequence part d'une fusion REFUSEE ; elle est passee :\n{sortie}"
    assert os.path.isfile(os.path.join(d.p, ".git", "MERGE_HEAD")), (
        f"la sequence repose sur le fait MESURE qu'un refus LAISSE MERGE_HEAD en place :\n{sortie}")

    d.balise(3)
    d.git("add", "CLAUDE.md")
    env = dict(d.env)
    env["GIT_EDITOR"] = "false"
    rc, sortie = d.git("commit", check=False, env=env)  # sans -m : l'editeur est sollicite
    assert rc != 0, f"le cas exige un commit AVORTE ; il a reussi :\n{sortie}"
    assert d.head() == avant, f"rien ne doit avoir ete committe :\n{sortie}"

    # LA PROPRIETE : plus aucun residu, donc plus rien a desarmer. C'est ce qui remplace toute
    # discussion d'identite -- un fichier qui n'existe pas n'a pas besoin d'etre bien identifie.
    assert not os.path.isfile(_temoin(d)), (
        "un jeton a survecu a l'avortement : le raccourci supprime est revenu. Relire pourquoi les "
        "trois identites sont tombees (classe E31) AVANT de le retablir")

    d.git("merge", "--abort")
    d.raz()
    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc != 0, (
        "la fusion fautive est passee apres un commit avorte a l'editeur : quelque chose desarme "
        f"encore les portes.\n{sortie}")
    assert "CHIFFRE" in sortie.upper(), f"le refus ne vient pas de la porte des comptes :\n{sortie}"
    assert d.head() == avant, f"un commit de fusion a quand meme ete cree :\n{sortie}"


def test_un_jeton_FABRIQUE_quelle_que_soit_son_identite_ne_desarme_rien(tmp_path, monkeypatch):
    """Generalisation des deux cas d'identite qui existaient ici. On fabrique le jeton le plus
    CREDIBLE possible -- horodatage frais pris de git, HEAD juste, MERGE_HEAD juste, et un arbre
    d'index REEL (pas une chaine de zeros, qui aurait pu etre rejetee pour sa forme). Sous la v3 un
    tel jeton desarmait ; il ne doit plus rien faire du tout."""
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avant = d.head()

    d.git("merge", "--no-ff", "--no-commit", "B", check=False)
    mh = _lire(os.path.join(d.p, ".git", "MERGE_HEAD")).replace("\n", " ").strip()
    assert mh, "MERGE_HEAD doit etre present et lisible"
    rc, arbre = d.git("write-tree", check=False)
    assert rc == 0 and arbre.strip(), "l'arbre de l'index doit etre calculable pour fabriquer le jeton"
    maintenant = int(subprocess.run(["git", "-C", d.p, "log", "-1", "--format=%ct"],
                                    capture_output=True, env=d.env).stdout.decode().strip() or 0)
    with open(_temoin(d), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("{}\n{}\n{} \n{}\n".format(maintenant, avant, mh, arbre.strip()))

    d.git("merge", "--abort")
    d.raz()
    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc != 0, (
        "un jeton fabrique a desarme les portes : un fichier depose dans un git-dir PARTAGE ne doit "
        f"plus avoir le moindre effet.\n{sortie}")
    assert d.head() == avant, f"un commit de fusion a quand meme ete cree :\n{sortie}"


def test_le_crochet_ne_LIT_jamais_un_jeton_et_ne_laisse_aucun_residu(tmp_path, monkeypatch):
    """Garde de la garde, TEXTUELLE et donc invisible au harnais de mutation (qui mute en memoire) :
    le crochet doit RETIRER un residu d'ancienne version sans jamais le lire. Si un futur `sed -n`
    ou un `[ -f ... ]` conditionnel revenait sur ce fichier, ce cas le nomme."""
    src = _lire(_COMMIT_MSG)
    assert "agagi-pre-commit-ran" in src, (
        "le crochet doit continuer a NETTOYER le residu des anciennes versions : un git-dir partage "
        "par une dizaine de sessions ne doit pas garder de fichier orphelin")
    apres_rm = src.split("agagi-pre-commit-ran", 1)[1]
    for interdit in ("sed -n 1p", "sed -n 2p", "sed -n 3p", "sed -n 4p"):
        assert interdit not in src, (
            f"le crochet relit un jeton ({interdit}) : les trois identites essayees ont ete "
            "refutees, la troisieme par mesure appariee. Relire la classe E31 avant de recommencer")
    assert "deja=1" not in src and "$deja" not in src, (
        "une variable de saut est revenue dans le crochet : il n'y a plus rien qui doive faire "
        "sauter les portes")
    assert apres_rm, "le nettoyage doit etre suivi du reste du crochet"


def test_le_pre_commit_ne_POSE_plus_aucun_jeton(tmp_path, monkeypatch):
    """Pendant a l'autre bout : la SOURCE du hook ne doit plus ecrire de jeton nulle part."""
    src = _lire(_PRE_COMMIT)
    assert "# >>> AGAGI:FUSION-SANS-TEMOIN >>>" in src, (
        "le bloc qui documente la SUPPRESSION du temoin a disparu : sans lui, la prochaine session "
        "qui verra les portes tourner deux fois le reintroduira sans savoir pourquoi il est tombe")
    assert "agagi-pre-commit-ran" not in src, (
        "le pre-commit ecrit de nouveau un jeton dans le git-dir")
    assert "AGAGI:FUSION-MARQUEUR" not in src, "l'ancien bloc de pose du temoin est revenu"


# --------------------------------------------------------------------------------------------------
# 11. DEFAUT 2-bis -- une DEGRADATION DE PORTEE doit se DIRE. `git merge-base` rend du vide sans
# echouer bruyamment sur des histoires sans ancetre commun : la portee retombait alors au PREMIER
# PARENT -- exactement le trou que le bloc existe pour boucher -- et rien ne le disait, alors que la
# branche SQUASH criait deja pour le meme symptome. Une degradation SILENCIEUSE de perimetre est
# indiscernable d'un controle qui passe : c'est la forme (a) du biais de ce depot.
# --------------------------------------------------------------------------------------------------

def test_une_fusion_SANS_ANCETRE_COMMUN_DIT_que_la_portee_est_degradee(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    # Une branche ORPHELINE : aucune base de fusion avec A, par construction.
    d.git("checkout", "-q", "--orphan", "orpheline")
    d.git("rm", "-q", "-rf", ".")
    d.ecrire("docs/preregistrations/o.json", "{}\n")
    d.ecrire("ailleurs.txt", "histoire sans ancetre\n")
    d.git("add", "-A")
    d.git("commit", "-q", "-m", "orpheline")
    d.git("checkout", "-q", "base")
    d.raz()

    # ⚠️ LA BASE SE MESURE AVANT LA FUSION. Premiere redaction : elle etait calculee APRES, et le
    # cas SAUTAIT -- si la fusion aboutit, HEAD a l'orpheline pour PARENT, donc `merge-base` la rend
    # elle-meme (rc 0) et le garde-fou lisait « cette version de git trouve une base ». Un cas qui
    # saute pour cette raison est exactement la degradation silencieuse qu'il est cense attraper.
    avant = d.head()
    base_calculable, base_sortie = d.git("merge-base", avant, "orpheline", check=False)
    assert base_calculable != 0, (
        "deux histoires SANS ancetre commun doivent rendre une base INCALCULABLE ; git en rend une "
        f"({base_sortie.strip()!r}) : le depot jouet ne construit pas ce que le cas annonce")

    rc, sortie = d.git("merge", "--no-ff", "--allow-unrelated-histories", "orpheline",
                       "-m", "fusion sans ancetre", check=False)
    assert "INCALCULABLE" in sortie.upper(), (
        "la portee est retombee au PREMIER PARENT sans le dire. Une porte qui voit moins que "
        f"l'union doit l'annoncer, sinon son vert ne veut rien dire.\n{sortie}")
    assert "PREMIER PARENT" in sortie.upper(), (
        f"le message doit nommer la portee reellement utilisee, pas seulement l'echec :\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 12. GRAVITE HAUTE -- NE PAS ANNONCER CE QU'ON N'A PAS VERIFIE.
# Mesure de la re-verification adversariale (2026-09-24) : `commit-msg` imprimait « portes relancees
# sur l'UNION -- portee = base de fusion » SANS jamais verifier que le pre-commit qu'il lance porte
# le bloc AGAGI:FUSION-SCOPE. Ce n'etait pas hypothetique : le pre-commit DEPLOYE ce jour-la ne
# portait AUCUN des deux blocs (0 occurrence mesuree dans .git/hooks/pre-commit), l'installation
# etant manuelle « par clone / par session ». La fusion fautive passait donc pendant que le crochet
# imprimait l'affirmation inverse -- la forme (a) du biais de ce depot (une absence ressort en
# affirmation de fond) appliquee a l'outillage lui-meme.
# --------------------------------------------------------------------------------------------------

def _pre_commit_sans_portee(log_rel):
    """Le meme pre-commit jouet, AMPUTE de son bloc de portee : la configuration reellement
    observee sur le depot le jour de la mesure (copie deployee anterieure aux deux blocs)."""
    entier = _pre_commit_jouet(log_rel)
    scope = _bloc(_lire(_PRE_COMMIT), "# >>> AGAGI:FUSION-SCOPE >>>", "# <<< AGAGI:FUSION-SCOPE <<<",
                  "portee de fusion")
    ampute = entier.replace(scope, "# (bloc de portee ABSENT : copie deployee perimee)")
    # le MARQUEUR, pas le nom nu : PORTE-ABSENTE cite ce nom dans un commentaire (2026-09-26, E1)
    assert "# >>> AGAGI:FUSION-SCOPE >>>" not in ampute, "l'amputation n'a pas eu lieu, le cas ne mesure rien"
    return ampute


def test_commit_msg_AVOUE_quand_le_pre_commit_lance_n_a_PAS_le_bloc_de_portee(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True)
    avec = os.path.join(d.p, ".githooks", "pre-commit")
    with open(avec, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_pre_commit_sans_portee("appels.log"))
    os.chmod(avec, 0o755)
    d.raz()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert "NE PORTE PAS" in sortie.upper(), (
        "le crochet a relance un pre-commit AMPUTE de son bloc de portee sans le dire. Il annonce "
        f"alors une verification qu'il ne fait pas, ce qui est pire que de se taire.\n{sortie}")
    assert "PREMIER PARENT" in sortie.upper(), (
        f"le message doit nommer la portee REELLEMENT utilisee :\n{sortie}")
    assert d.appels() == 1, f"le pre-commit ampute doit quand meme avoir tourne :\n{sortie}"


def test_controle_positif_avec_le_bloc_le_crochet_annonce_la_base(tmp_path, monkeypatch):
    """Sans ce controle, un crochet qui dirait TOUJOURS « ne porte pas » passerait le cas ci-dessus
    en ne mesurant rien. Le pre-commit COMPLET doit produire l'annonce d'elargissement."""
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=False)
    d.raz()

    rc, sortie = d.git("merge", "--no-ff", "B", "-m", "fusion B dans A", check=False)

    assert rc == 0, f"la fusion saine doit passer :\n{sortie}"
    assert "NE PORTE PAS" not in sortie.upper(), (
        f"le crochet accuse un pre-commit qui porte pourtant le bloc :\n{sortie}")
    assert "base de fusion" in sortie, (
        f"l'annonce d'elargissement doit etre produite quand le bloc EST la :\n{sortie}")


# --------------------------------------------------------------------------------------------------
# 13. GRAVITE HAUTE -- LE CHERRY-PICK CONFLICTUEL A LA MEME MALADIE QUE LE SQUASH.
# Mesure : un `git cherry-pick` CONFLICTUEL arme bien le pre-commit (1 appel) -- mais MERGE_HEAD est
# ABSENT, c'est CHERRY_PICK_HEAD qui porte le cote entrant. Le bloc de portee ne testait que
# MERGE_HEAD et SQUASH_MSG : la portee restait le PREMIER PARENT, le document porteur du compte
# etait identique a HEAD, et la porte se taisait. Meme mecanisme que le trou `--squash`, sur une
# autre reference.
# ⚠️ Le cherry-pick PROPRE, lui, n'est couvert par RIEN (0 appel de pre-commit ET de commit-msg) --
# c'est ecrit dans l'en-tete de `tools/hooks/commit-msg` comme une LIMITE, et le cas ci-dessous ne
# pretend pas le couvrir.
# --------------------------------------------------------------------------------------------------

def test_un_CHERRY_PICK_CONFLICTUEL_faux_a_l_UNION_est_REFUSE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=True, conflit=True)
    avant = d.head()

    rc, sortie = d.git("cherry-pick", "B", check=False)
    assert rc != 0, f"le cas exige un cherry-pick CONFLICTUEL ; il est passe seul :\n{sortie}"
    assert not os.path.isfile(os.path.join(d.p, ".git", "MERGE_HEAD")), (
        "la mesure qui motive ce cas est justement l'ABSENCE de MERGE_HEAD pendant un cherry-pick")
    assert os.path.isfile(os.path.join(d.p, ".git", "CHERRY_PICK_HEAD")), (
        "git doit poser CHERRY_PICK_HEAD : c'est la seule trace du cote entrant ici")

    d.ecrire("notes.txt", "resolution\n")
    d.git("add", "notes.txt")
    d.raz()
    rc, sortie = d.git("commit", "-q", "-m", "cherry-pick de B", check=False)

    assert d.appels() == 1, (
        f"le commit qui conclut un cherry-pick est ORDINAIRE : pre-commit doit tourner UNE fois, "
        f"or {d.appels()}")
    assert rc != 0, (
        "le cherry-pick est passe alors que la balise annonce 2 regles scellees pour 3 fichiers a "
        f"l'union : la portee n'a pas ete elargie a CHERRY_PICK_HEAD.\n{sortie}")
    assert "CHIFFRE" in sortie.upper(), f"le refus ne vient pas de la porte des comptes :\n{sortie}"
    assert d.head() == avant, f"un commit a quand meme ete cree :\n{sortie}"


def test_controle_positif_un_CHERRY_PICK_sans_divergence_PASSE(tmp_path, monkeypatch):
    d = _depot(tmp_path, monkeypatch)
    _deux_branches(d, divergent=False, conflit=True)
    avant = d.head()

    d.git("cherry-pick", "B", check=False)
    d.ecrire("notes.txt", "resolution\n")
    d.git("add", "notes.txt")
    d.raz()
    rc, sortie = d.git("commit", "-q", "-m", "cherry-pick de B", check=False)

    assert rc == 0, f"un cherry-pick dont le compte est JUSTE a l'union doit passer :\n{sortie}"
    assert d.head() != avant, "le commit de cherry-pick n'a pas ete cree"
    assert "syntheses :" in sortie, (
        f"la porte n'a pas tourne : le vert de ce controle ne prouverait rien.\n{sortie}")
