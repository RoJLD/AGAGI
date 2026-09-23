"""Contre-exemples GELÉS du cliquet de fraîcheur du backlog — il doit pouvoir ÉCHOUER.

Sans ces tests, `tools/check_backlog_freshness.py` serait un outil qui passe au vert quoi qu'il arrive :
exactement le défaut qu'il est censé empêcher ailleurs.

Chaque test forge un backlog minimal contenant UNE péremption connue, et vérifie que le cliquet la voit.
Le dernier vérifie l'inverse — un backlog sain ne doit rien déclencher — parce qu'un détecteur qui
signale tout passerait les autres tests tout en étant inutilisable.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_backlog_freshness as B  # noqa: E402


def _backlog(tmp_path, monkeypatch, texte):
    p = tmp_path / "BACKLOG.md"
    p.write_text(texte, encoding="utf-8")
    monkeypatch.setattr(B, "_BACKLOG", str(p))
    # 2026-09-22 : ces cas jugent un backlog JOUET sur DISQUE. Sous le hook (donc sous la porte 15, qui
    # lance ce fichier), `GIT_INDEX_FILE` est hérité et la porte passerait en mode COMMIT (lecture de
    # l'index) : on le retire ici, et les cas du mode commit le reposent explicitement.
    monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    return p


def test_a_dead_record_link_is_DETECTED(tmp_path, monkeypatch):
    """⚠️ Citer un record qui n'existe pas : le lecteur suit un renvoi vers le vide."""
    _backlog(tmp_path, monkeypatch, "Voir [[EDR-NEXISTE-PAS-999]] pour le détail.\n")
    trouve = B.scan()
    assert any(k.startswith("lien-mort:") for k in trouve), (
        f"un lien de record mort doit être détecté, or : {trouve}")


def test_a_real_record_link_is_SPARED(tmp_path, monkeypatch):
    """Spécificité : un renvoi valide ne doit PAS être signalé."""
    _backlog(tmp_path, monkeypatch, "Mesuré par [[EDR-EVO-010]], sans appel.\n")
    assert not any(k.startswith("lien-mort:") for k in B.scan()), (
        "un record qui existe ne doit pas être signalé comme lien mort")


def test_memory_slugs_are_NOT_treated_as_records(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ (2026-09-01) : deux espaces de noms cohabitent dans les `[[...]]`. Les slugs de
    mémoire de session (kebab minuscule) vivent hors du dépôt ; les signaler comme records manquants
    exigeait qu'un fichier existe là où la convention dit qu'il n'existe pas."""
    _backlog(tmp_path, monkeypatch, "Recoupe [[warm-start-transversal-law]] et [[s2-world-demand-thread]].\n")
    assert B.scan() == {}, "les slugs de mémoire ne sont pas des records et ne doivent rien déclencher"


def test_a_duplicated_task_number_is_DETECTED(tmp_path, monkeypatch):
    """Deux entrées sous le même numéro : l'une est forcément périmée et rien ne dit laquelle."""
    _backlog(tmp_path, monkeypatch,
             "**P2.4 — première version, présentée comme ouverte.**\n\n"
             "**P2.4 — ✅ FAIT, deuxième version.**\n")
    assert "numero-double:P2.4" in B.scan()


def test_a_dead_file_path_is_DETECTED(tmp_path, monkeypatch):
    """Un backlog qui pointe un fichier disparu envoie le lecteur dans le vide."""
    _backlog(tmp_path, monkeypatch, "Le correctif vit dans `tools/ce_fichier_nexiste_pas.py`.\n")
    assert any(k.startswith("chemin-mort:") for k in B.scan())


def test_an_existing_file_path_is_SPARED(tmp_path, monkeypatch):
    """Spécificité du volet chemins."""
    _backlog(tmp_path, monkeypatch, "Le cliquet vit dans `tools/check_backlog_freshness.py`.\n")
    assert not any(k.startswith("chemin-mort:") for k in B.scan())


def _git_repo_with_one_tracked_file(tmp_path):
    """Un dépôt git minimal : `suivi.txt` committé, `local.txt` présent mais JAMAIS ajouté."""
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()

    # ⚠️ Un GIT_INDEX_FILE / GIT_DIR herite (commit depuis un index temporaire, hook pre-commit) ferait
    # ecrire ce depot jouet DANS L'INDEX DU VRAI DEPOT (mesure le 2026-09-14 : le harnais de mutation
    # a vu ce temoin rougir sous le hook). Le depot jouet vit dans un environnement git VIERGE.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*args):
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True, env=env)
    git("init", "-q")
    (repo / "suivi.txt").write_text("x", encoding="utf-8")
    git("add", "suivi.txt")
    git("commit", "-q", "-m", "init")
    (repo / "local.txt").write_text("y", encoding="utf-8")
    return repo


def test_a_path_clause_on_an_UNTRACKED_existing_file_is_REFUSED(tmp_path, monkeypatch):
    """P1.8 (b) — DÉFAUT MESURÉ : la CI est restée ROUGE trois pushes (2026-09-07 → 09-09) sur une clause
    `holds_when:path_present=data/hof_famine_harsh_s42.pkl` — un fichier IGNORÉ par git, donc présent
    ici et absent sur tout clone. Le cliquet passait en local et mentait sur ce que la CI verrait.
    Une clause de chemin dont le fichier existe localement SANS être suivi est INVÉRIFIABLE sur un
    clone : elle est REFUSÉE (bruyamment), jamais évaluée. Un fichier suivi passe ; un fichier absent
    n'est pas concerné (la clause est simplement non satisfaite)."""
    # L'outil INTERROGE git en heritant de l'environnement (c'est voulu : sous le hook, l'index en cours
    # de commit est celui que GIT_INDEX_FILE designe). Ici le depot est un JOUET : un GIT_INDEX_FILE
    # herite designerait l'index d'un AUTRE depot et rendrait `suivi.txt` invisible (mesure sous le hook,
    # 2026-09-14). Le test tient son environnement.
    for k in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
        monkeypatch.delenv(k, raising=False)
    repo = _git_repo_with_one_tracked_file(tmp_path)
    monkeypatch.setattr(B, "_ROOT", str(repo))
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — ✅ CLOSE — cite un fichier présent mais non suivi.**\n"
             "<!-- closes_when:path_present=local.txt -->\n\n"
             "**P9.2 — ✅ CLOSE — cite un fichier suivi.**\n"
             "<!-- closes_when:path_present=suivi.txt -->\n\n"
             "**P9.3 — ouverte, cite un fichier absent.**\n"
             "<!-- closes_when:path_present=futur.txt -->\n")
    trouve = B.scan()
    assert "clause-refusee:P9.1:path_present" in trouve, trouve
    assert "clone" in trouve["clause-refusee:P9.1:path_present"].lower()
    assert not any(k.endswith(":P9.2:path_present") for k in trouve), trouve
    assert not any(k.endswith(":P9.3:path_present") for k in trouve), trouve


def test_a_path_clause_outside_any_git_repo_is_NOT_refused(tmp_path, monkeypatch):
    """Spécificité : hors dépôt git (les autres tests de ce fichier), le suivi est indécidable — on
    n'invente pas un refus, la clause s'évalue comme avant."""
    for k in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / "present.txt").write_text("z", encoding="utf-8")
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    _backlog(tmp_path, monkeypatch,
             "**P9.4 — ✅ CLOSE — hors dépôt.**\n<!-- closes_when:path_present=present.txt -->\n")
    assert not any(k.startswith("clause-refusee:") for k in B.scan())


def test_a_clean_backlog_triggers_NOTHING(tmp_path, monkeypatch):
    """⚠️ Sans ce test, un détecteur qui signale TOUT passerait tous les autres."""
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — une tâche unique.**\n\nMesuré par [[EDR-EVO-010]], code dans "
             "`tools/check_backlog_freshness.py`.\n")
    assert B.scan() == {}, "un backlog sain ne doit rien déclencher"


def test_the_real_backlog_has_no_NEW_staleness():
    """L'état gelé du dépôt. Si ce test tombe, une péremption mécanique vient d'être introduite."""
    base = B._load_baseline()
    nouvelles = {k: v for k, v in B.scan().items() if k not in base}
    assert not nouvelles, (
        f"nouvelles péremptions du backlog : {nouvelles}. Corriger, ou les déclarer explicitement "
        f"avec `--update-baseline` en disant POURQUOI.")


def test_a_PROPOSED_path_is_not_a_dead_path(tmp_path, monkeypatch):
    """⚠️ FAUX POSITIF MESURE (2026-09-01), corrige plutot que gele. Un backlog PROPOSE legitimement des
    fichiers qui n'existent pas encore -- c'est sa fonction. Le detecteur avait signale
    `tools/check_staged_authorship.py`, introduit par « *Correctif candidat, plus fort* : un script ...
    A evaluer ». Le geler dans la baseline aurait masque une classe de faux positifs qui se reproduira
    a chaque proposition."""
    _backlog(tmp_path, monkeypatch,
             "*Correctif candidat* : un script `tools/pas_encore_ecrit.py` qui ferait X. À évaluer.\n")
    assert not any(k.startswith("chemin-mort:") for k in B.scan()), (
        "un chemin PROPOSE ne doit pas etre signale comme mort")


def test_a_path_CITED_AS_EXISTING_is_still_detected(tmp_path, monkeypatch):
    """⚠️ SPECIFICITE de la correction : sans elle, on aurait desactive le detecteur de chemins morts.
    Une citation SANS marqueur de proposition doit toujours etre attrapee."""
    _backlog(tmp_path, monkeypatch,
             "La garde vit dans `tools/ce_fichier_a_ete_supprime.py` et bloque les commits.\n")
    assert any(k.startswith("chemin-mort:") for k in B.scan())


# --- GARDE D'AMPUTATION (2026-09-09) : le cliquet rendait OK sur un backlog VIDE ---------------------
#
# ⚠️ ARMEE SUR UN INCIDENT REEL, subi par la session qui ecrit ces lignes. Une reecriture
# programmatique a vide `PRIORITES_ET_DETTES.md` -- 2352 lignes -> 0 -- SANS LEVER :
#     io.open(p, "w").write(io.open(p).read().replace(old, new))
# Python evalue les arguments de GAUCHE A DROITE : le mode "w" TRONQUE le fichier avant que le
# `read()` interne ne le lise. Le read rend "", le replace rend "", le fichier est ecrase par du vide.
# Meme famille qu'E22 (une suppression rend le signal plus vert) avec un mecanisme NEUF : l'ordre
# d'evaluation des arguments.
#
# Ce cliquet a alors rendu `exit 0` et « OK » -- et il a INVITE a resserrer sa baseline
# (« 2 resorbee(s) -> --update-baseline »), ce qui aurait fige l'amputation. Entree vide -> succes,
# commis par une GARDE : exactement le biais que ce depot traque chez ses sondes.
#
# ⚠️ ET LA PREMIERE VERSION DE LA GARDE ETAIT ELLE-MEME INERTE : elle lisait
# `_load_baseline().get("plancher_entrees")`, or `_load_baseline()` rend le sous-dictionnaire
# `legataires`, donc le plancher valait TOUJOURS 0. Elle a passe son propre contre-exemple. Classe E1,
# commise en armant une garde contre exactement ca -- seul le contre-exemple GELE l'a dit.

def test_the_ratchet_REFUSES_an_amputated_backlog(monkeypatch):
    """CONTRE-EXEMPLE GELE : l'incident rejoue. Un backlog vide doit faire ECHOUER le cliquet."""
    import sys

    import tools.check_backlog_freshness as m
    # `main()` lit `sys.argv` : sous pytest il y trouverait les arguments de pytest et argparse
    # sortirait en erreur. On lui donne un argv NU.
    monkeypatch.setattr(sys, "argv", ["check_backlog_freshness.py"])
    monkeypatch.setattr(m, "compter_entrees", lambda txt=None: 0)
    monkeypatch.setattr(m, "_charger_plancher", lambda: 68)
    assert m.main() == 1, "un backlog AMPUTE doit faire echouer le cliquet, pas passer"


def test_the_ratchet_SPARES_an_intact_backlog(monkeypatch):
    """NO-OP APPARIE, indispensable : une garde qui refuserait TOUT passerait le cas precedent
    sans rien mesurer. Au plancher exact, le cliquet doit se taire."""
    import sys

    import tools.check_backlog_freshness as m
    # `main()` lit `sys.argv` : sous pytest il y trouverait les arguments de pytest et argparse
    # sortirait en erreur. On lui donne un argv NU.
    monkeypatch.setattr(sys, "argv", ["check_backlog_freshness.py"])
    monkeypatch.setattr(m, "compter_entrees", lambda txt=None: 68)
    monkeypatch.setattr(m, "_charger_plancher", lambda: 68)
    assert m.main() == 0, "un backlog au plancher exact ne doit pas etre refuse"


def test_the_FLOOR_can_only_go_UP():
    """Le plancher est un CLIQUET. Geler une baseline contre un backlog ampute figerait l'amputation :
    `--update-baseline` prend donc le MAX de l'ancien et du courant. Verifie sur le code, car c'est
    une propriete du chemin `--update-baseline` qu'aucun appel normal n'exerce."""
    import inspect
    import tools.check_backlog_freshness as m
    src = inspect.getsource(m.main)
    assert "max(n_entrees, plancher)" in src, (
        "le plancher doit etre gele au MAX -- sinon une amputation devient la nouvelle norme")
    assert src.index("if n_entrees < plancher") < src.index("if args.update_baseline"), (
        "la garde doit passer AVANT --update-baseline, sinon on gele l'amputation qu'on refuse")


def test_the_REAL_backlog_is_ABOVE_its_frozen_floor():
    """Ancrage sur le reel : le fichier vivant doit etre au-dessus de son plancher, et le plancher
    doit etre non nul (un plancher a zero serait une garde desarmee)."""
    import tools.check_backlog_freshness as m
    plancher = m._charger_plancher()
    assert plancher > 0, "plancher a zero = garde desarmee"
    assert m.compter_entrees() >= plancher

# --- P3.5 (a) : TITRES COMPOSITES (2026-09-15) ------------------------------------------------------
#
# ⚠️ DEFAUT MESURE. `**P1.x / P2.45 — ...` (l.2326 du backlog) porte DEUX numeros et un `x` de
# substitution (« a numeroter »). `_ENTREE` et `_TASKNUM` exigeaient `P\d+\.\d+` : le titre ENTIER
# etait invisible -- ni entree (son bloc etait avale par l'entree precedente), ni numero (P2.45 est en
# tete d'une SECONDE entree, l.2981, et le compte de doublons rendait OK). Un titre que le cliquet ne
# lit pas ne peut pas etre en double : entree invisible -> succes, la forme (a) de CLAUDE.md.

def test_a_COMPOSITE_title_duplicating_a_number_is_DETECTED(tmp_path, monkeypatch):
    """CONTRE-EXEMPLE GELE : le cas reel, en jouet. `P2.45` en tete d'un titre composite ET d'un
    titre simple doit etre signale comme numero double."""
    _backlog(tmp_path, monkeypatch,
             "**P1.x / P2.45 — ✅ CLOSE par P2.54 — premiere version (composite).**\n\n"
             "**P2.45 — ✅ LIVRÉE — deuxieme version, une autre tache.**\n")
    trouve = B.scan()
    assert "numero-double:P2.45" in trouve, trouve


def test_a_PLACEHOLDER_shared_by_two_composites_is_NOT_a_duplicate(tmp_path, monkeypatch):
    """SPECIFICITE de l'elargissement : `P1.x` est un SUBSTITUT, pas un numero. Deux entrees qui le
    partagent ne sont pas deux versions d'une meme tache -- le signaler FABRIQUERAIT un doublon."""
    _backlog(tmp_path, monkeypatch,
             "**P1.x / P2.45 — une tache.**\n\n**P1.x / P2.46 — une autre.**\n")
    trouve = B.scan()
    assert not any(k.startswith("numero-double:") for k in trouve), trouve


def test_a_COMPOSITE_title_is_an_ENTRY_and_owns_its_clause(tmp_path, monkeypatch):
    """Le bloc d'un titre composite lui appartient : sa clause `closes_when:` se juge contre SON
    statut, pas contre celui de l'entree precedente -- qui l'avalait, et rendait OK sur une
    fermeture REGRESSEE."""
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — ouverte, sans clause.**\n\n"
             "**P1.x / P9.2 — ✅ CLOSE — mais sa condition n'est plus vraie.**\n"
             "<!-- closes_when:path_present=tools/ce_fichier_nexiste_pas.py -->\n")
    trouve = B.scan()
    assert "clause-rouverte:P1.x / P9.2:path_present" in trouve, trouve
    assert not any(":P9.1:" in k for k in trouve), trouve


def test_a_COMPOSITE_title_COUNTS_as_an_entry_for_the_amputation_floor():
    """Le plancher d'amputation compte les MEMES entrees que le reste du cliquet : une entree
    invisible au compte est une entree qu'on peut effacer sans que le plancher bouge."""
    assert B.compter_entrees("**P1.x / P2.45 — a.**\n\n**P2.46 — b.**\n") == 2


# ---------------------------------------------------------------------------------------------
# CHEMIN CITÉ MAIS NON SUIVI PAR GIT (2026-09-22). La porte testait l'EXISTENCE locale du chemin,
# jamais sa traçabilité : un fichier présent chez l'auteur et absent de git est VERT chez lui et
# ROUGE sur tout clone (le chemin « n'existe plus » là-bas). Mesuré sur mon propre commit 72ce45a,
# qui a introduit trois citations de ce genre ; la porte savait pourtant la leçon — son message pour
# les clauses `closes_when` cite déjà la CI rouge du 2026-09-07 (`5b0025e`) — mais ne l'appliquait
# qu'aux clauses, pas à la prose. L'auteur ne pouvait pas voir le défaut qu'il créait.
# ⚠️ Un fichier STAGÉ compte comme suivi : sinon la garde bloquerait le commit même qui l'ajoute
# (le hook tourne sur l'index, temporaire compris, via GIT_INDEX_FILE).

def _fichier(tmp_path, nom, suivi_par):
    """Crée `nom` sous tmp_path et l'inscrit (ou non) dans l'inventaire des chemins suivis."""
    p = tmp_path / nom
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x\n", encoding="utf-8")
    return p


def test_un_chemin_cite_EXISTANT_mais_NON_SUIVI_est_DETECTE(tmp_path, monkeypatch):
    """CONTRE-EXEMPLE GELÉ : le cas réel de 72ce45a — le fichier est là, git ne le connaît pas."""
    _fichier(tmp_path, "tools/td_step_pilot.py", suivi_par=None)
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset())
    _backlog(tmp_path, monkeypatch, "Pilote `tools/td_step_pilot.py`, règle scellée, 144 cellules.\n")
    trouve = B.scan()
    assert "chemin-non-suivi:tools/td_step_pilot.py" in trouve, trouve


def test_un_chemin_cite_et_SUIVI_ne_declenche_RIEN(tmp_path, monkeypatch):
    """SPÉCIFICITÉ : le cas nominal — sans lui, « tout signaler » ferait passer le test précédent."""
    _fichier(tmp_path, "tools/td_step_pilot.py", suivi_par=None)
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset({"tools/td_step_pilot.py"}))
    _backlog(tmp_path, monkeypatch, "Pilote `tools/td_step_pilot.py`, règle scellée, 144 cellules.\n")
    trouve = B.scan()
    assert not any(k.startswith("chemin-non-suivi:") for k in trouve), trouve


def test_un_chemin_STAGE_compte_comme_suivi(tmp_path, monkeypatch):
    """Le commit qui AJOUTE le fichier ne doit pas être bloqué par sa propre citation : `git ls-files`
    lit l'INDEX (temporaire compris), donc un fichier stagé est déjà « suivi » pour la porte."""
    _fichier(tmp_path, "results/td_step_pilot_r0.json", suivi_par=None)
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset({"results/td_step_pilot_r0.json"}))
    _backlog(tmp_path, monkeypatch, "Résultats dans `results/td_step_pilot_r0.json`.\n")
    assert not any(k.startswith("chemin-non-suivi:") for k in B.scan()), "un fichier stagé est suivi"


def test_un_chemin_PROPOSE_non_suivi_reste_EPARGNE(tmp_path, monkeypatch):
    """La règle de 2026-09-01 tient AUSSI pour la traçabilité : un fichier annoncé « à écrire » n'est
    ni mort ni non suivi — c'est du travail à faire. Sans ce cas, la porte crierait sur toute
    proposition (la classe de faux positifs que la baseline aurait masquée)."""
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset())
    _fichier(tmp_path, "tools/harness/propose.py", suivi_par=None)
    _backlog(tmp_path, monkeypatch,
             "Correctif candidat : `tools/harness/propose.py` reste à écrire.\n")
    trouve = B.scan()
    assert not any(k.startswith("chemin-non-suivi:") for k in trouve), trouve


def test_chemins_suivis_lit_l_index_du_VRAI_depot():
    """La source de vérité est `git ls-files` (index), pas une liste en dur : un fichier committé du
    dépôt doit y être, un chemin inventé non. Contrôle apparié, sur le dépôt réel."""
    suivis = B._chemins_suivis()
    assert "tools/check_backlog_freshness.py" in suivis
    assert "tools/ce_fichier_n_existe_pas_42.py" not in suivis


# ---------------------------------------------------------------------------------------------
# MODE COMMIT (2026-09-22) — la porte juge ce qui SERA COMMITTÉ, pas le disque. Blocage circulaire
# mesuré à trois sessions : la porte lisait le backlog sur DISQUE, où l'entrée d'une session B citait
# des fichiers stagés par B ; l'index TEMPORAIRE d'une session A qui committait (HEAD + ses seuls
# chemins) ne les contenait pas -> rouge chez A, à cause de B, sur un texte qu'A ne committait pas.
# Sous `GIT_INDEX_FILE`, texte ET existence se lisent désormais dans l'index.

def test_en_commit_un_fichier_sur_disque_mais_HORS_index_est_MORT_pour_ce_commit(tmp_path, monkeypatch):
    """Le cas réel : le fichier est là (stagé par une autre session), pas dans CET index -> pour ce
    commit il n'existe pas. C'est `chemin-mort`, jamais « existe mais non suivi » (qui ne peut pas
    exister en mode commit : l'index EST la définition de l'existence)."""
    _fichier(tmp_path, "tools/td_step_pilot.py", suivi_par=None)
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    _backlog(tmp_path, monkeypatch, "Pilote `tools/td_step_pilot.py`, règle scellée.\n")
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index-temporaire"))
    monkeypatch.setattr(B, "_tracked_by_git", lambda rel: False)
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset())
    trouve = B.scan()
    assert "chemin-mort:tools/td_step_pilot.py" in trouve, trouve
    assert not any(k.startswith("chemin-non-suivi:") for k in trouve), trouve


def test_en_commit_un_fichier_DANS_l_index_existe_meme_absent_du_disque(tmp_path, monkeypatch):
    """SPÉCIFICITÉ appariée : même citation, fichier dans l'index -> rien, même s'il n'est pas sur le
    disque (un index temporaire n'écrit pas l'arbre)."""
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    _backlog(tmp_path, monkeypatch, "Pilote `tools/td_step_pilot.py`, règle scellée.\n")
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index-temporaire"))
    monkeypatch.setattr(B, "_tracked_by_git", lambda rel: True)
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset({"tools/td_step_pilot.py"}))
    trouve = B.scan()
    assert not any(k.startswith(("chemin-mort:", "chemin-non-suivi:")) for k in trouve), trouve


def test_en_commit_la_clause_path_present_juge_l_INDEX(tmp_path, monkeypatch):
    """La clause `path_present` d'une entrée OUVERTE, sur un fichier présent sur disque mais hors de cet
    index : la condition est FAUSSE (entrée ouverte, cohérente) — et surtout PAS « refusée comme non
    suivie », le refus qui bloquait la session A pour une clause de la session B."""
    _fichier(tmp_path, "results/x.json", suivi_par=None)
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — OUVERTE — essai.**\n<!-- closes_when:path_present=results/x.json -->\n")
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index-temporaire"))
    monkeypatch.setattr(B, "_tracked_by_git", lambda rel: False)
    monkeypatch.setattr(B, "_chemins_suivis", lambda: frozenset())
    trouve = B.scan()
    assert not any("P9.1" in k for k in trouve), trouve


def test_en_commit_une_clause_grep_lit_le_fichier_cible_dans_l_INDEX(tmp_path, monkeypatch):
    """Le cas réel P2.66 : la fonction est sur DISQUE (travail en vol d'une autre session), pas dans cet
    index -> la clause `grep_present` ne doit PAS être satisfaite pour ce commit ; et un fichier hors
    index rend « n'existe pas » (invérifiable), jamais le contenu du disque."""
    _fichier(tmp_path, "src/x.py", suivi_par=None)
    (tmp_path / "src" / "x.py").write_text("def claude_code_llm_fn():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(B, "_ROOT", str(tmp_path))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index-temporaire"))
    monkeypatch.setattr(B, "_tracked_by_git", lambda rel: False)
    assert B._lire_fichier("src/x.py") is None
    ok, raison = B._evalue_clause("grep_present", "src/x.py::def claude_code_llm_fn")
    assert ok is None and "n'existe pas" in raison


def test_en_commit_le_fichier_cible_est_celui_de_l_INDEX_sur_le_VRAI_depot(tmp_path, monkeypatch):
    """Intégration réelle, même patron que pour le backlog : index temporaire depuis HEAD, le contenu lu
    est celui de HEAD, et si le disque diffère (ce fichier est en cours d'édition), ce n'est PAS le disque."""
    import subprocess
    idx = tmp_path / "index-head"
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    subprocess.run(["git", "-C", B._ROOT, "read-tree", "HEAD"], env=env, check=True, capture_output=True)
    rel = "tools/check_backlog_freshness.py"
    head = subprocess.run(["git", "-C", B._ROOT, "show", f"HEAD:{rel}"], capture_output=True,
                          check=True).stdout.decode("utf-8", errors="ignore")
    monkeypatch.setenv("GIT_INDEX_FILE", str(idx))
    lu = B._lire_fichier(rel)
    assert lu == head
    disque = open(os.path.join(B._ROOT, rel), encoding="utf-8", errors="ignore").read()
    if disque != head:
        assert lu != disque, "en commit, le disque ne doit jamais être le contenu jugé"


def test_hors_commit_le_texte_juge_est_celui_du_DISQUE(monkeypatch):
    monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    assert B._lire_backlog() == open(B._BACKLOG, encoding="utf-8").read()


def test_en_commit_le_texte_juge_est_celui_de_l_INDEX_sur_le_VRAI_depot(tmp_path, monkeypatch):
    """Intégration réelle : un index temporaire construit depuis HEAD (la méthode de commit du dépôt) —
    `_lire_backlog()` doit rendre la version de HEAD, et, si le disque en diffère (hunks en vol
    d'autres sessions), NE PAS rendre le disque. C'est exactement la lecture qui manquait."""
    import subprocess
    idx = tmp_path / "index-head"
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    subprocess.run(["git", "-C", B._ROOT, "read-tree", "HEAD"], env=env, check=True, capture_output=True)
    head = subprocess.run(["git", "-C", B._ROOT, "show", "HEAD:docs/roadmap/PRIORITES_ET_DETTES.md"],
                          capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    monkeypatch.setenv("GIT_INDEX_FILE", str(idx))
    lu = B._lire_backlog()
    assert lu == head
    disque = open(B._BACKLOG, encoding="utf-8").read()
    if disque != head:
        assert lu != disque, "en commit, le disque (hunks d'autrui) ne doit jamais être le texte jugé"
