"""Contre-exemples GELÉS de la COMPLÉTUDE du graphe de records — 122 arêtes étaient invisibles.

Mesuré le 2026-09-01. `parse_record` jette EN SILENCE toute clé de frontmatter absente de `_LIST_KEYS`
(branche `elif k in rec`). Conséquence : **122 arêtes déclarées n'entraient pas dans le graphe**, dont
`retracted_by`, `corrects`, `corrected_by`, `supersedes_mechanism_of` — c'est-à-dire **toutes les arêtes
de rétractation**. Un graphe de records qui ne lit pas ses rétractations ne peut pas signaler une
conclusion périmée, ce pour quoi il existe.

Plus embarrassant : `adopts` (77 occurrences) était ignoré alors que **CLAUDE.md prescrit explicitement**
d'ancrer un record par « gate: / tests: / adopts: ». L'outil ne connaissait pas une clé que le protocole
impose.

⚠️ Ce que le correctif NE fait PAS, mesuré dans les deux sens avant de l'écrire : il ne résorbe **aucun**
orphelin (0 sur 39). L'hypothèse « la dette d'orphelins est un artefact du parseur » était plausible et
FAUSSE — elle est notée ici pour qu'on ne la re-formule pas.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.check_record_links as C  # noqa: E402
from tools.consolidate_records import _LIST_KEYS, build_graph, scan_records  # noqa: E402

_RETRACTION = ("corrects", "corrected_by", "retracted_by", "supersedes_mechanism_of")


def _record(tmp_path, frontmatter):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True, exist_ok=True)
    (d / "999_Faux.md").write_text(f"---\n{frontmatter}\n---\n\n# corps\n", encoding="utf-8")
    return str(tmp_path)


def test_an_unread_edge_key_is_DETECTED(tmp_path):
    """⚠️ LE test. Une clé qui DÉCLARE une arête mais que le parseur ne lit pas doit être signalée —
    c'est le silence exact qui a coûté 122 arêtes."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ncle_inventee: [EDR-112]")
    non_lues = C.edge_key_silences(root)["non_lues"]
    assert any(k == "cle_inventee" for _, k in non_lues), (
        f"une clé d'arête non lue doit être détectée, or : {non_lues}")


def test_a_scalar_where_a_list_is_expected_is_DETECTED(tmp_path):
    """⚠️ La forme EXACTE trouvée sur EDR-164 à la seconde où les clés manquantes ont été branchées :
    `supersedes_mechanism_of: EDR-162` sans crochets. Le code itère alors la CHAÎNE et produit une arête
    PAR CARACTÈRE ('E','D','R','-','1','6','2') — 7 arêtes fantômes vers des nœuds inexistants."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nsupersedes_mechanism_of: EDR-162")
    scal = C.edge_key_silences(root)["scalaires"]
    assert any(k == "supersedes_mechanism_of" for _, k, _ in scal), (
        f"une valeur scalaire là où une liste est attendue doit être détectée, or : {scal}")


def test_a_well_formed_record_triggers_NOTHING(tmp_path):
    """⚠️ SPÉCIFICITÉ — sans ce test, un détecteur qui signale TOUT passerait les deux précédents tout
    en étant inutilisable."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nadopts: [EDR-112]\ntests: [SDR-G0]")
    r = C.edge_key_silences(root)
    assert r["non_lues"] == [] and r["scalaires"] == [], f"record bien formé signalé à tort : {r}"


def test_the_records_own_id_is_not_mistaken_for_an_edge(tmp_path):
    """DÉFAUT MESURÉ en écrivant le détecteur : `id: SDR-G0` a la FORME d'un identifiant de record, donc
    239 faux positifs. Les champs scalaires sont exclus via le SCHÉMA DÉCLARÉ (`_empty_record`) et non
    une liste écrite à la main, qui se serait désynchronisée à la première évolution du schéma."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nverdict: EXIGE")
    assert C.edge_key_silences(root)["non_lues"] == []


def test_every_RETRACTION_edge_kind_stays_readable():
    """⚠️ La régression la plus grave possible : si quelqu'un rétrécit `_LIST_KEYS`, les rétractations
    redeviennent invisibles SANS que rien n'échoue. Ce test l'attrape."""
    for k in _RETRACTION:
        assert k in _LIST_KEYS, (
            f"« {k} » n'est plus lue : le graphe ne peut plus représenter une rétractation")


def test_the_real_graph_is_complete_and_coherent():
    """État gelé du dépôt : aucune arête déclarée n'est ignorée, aucune valeur mal formée, et le graphe
    porte bien ses arêtes de rétractation."""
    r = C.edge_key_silences()
    assert r["non_lues"] == [], f"arête(s) déclarée(s) mais jamais lue(s) : {r['non_lues']}"
    assert r["scalaires"] == [], f"valeur(s) scalaire(s) là où une liste est attendue : {r['scalaires']}"
    rels = {e["rel"] for e in build_graph(scan_records(C._ROOT))["edges"]}
    assert "RETRACTE_PAR" in rels and "CORRIGE" in rels, (
        f"le graphe ne porte plus d'arête de rétractation : {sorted(rels)}")


# --------------------------------------------------------------------------------------------------
# C3 (2026-09-02) : mismatch gate<->tests. Reponse connue confrontee AVANT de croire le cliquet
# (arbre pre-retaggage : exactement {EDR-S2-007 G4/[SDR-G0], EDR-S2-008 G2/[SDR-G0]} -- le draft du
# panel n'en voyait qu'UN, le refutateur a trouve le second, F1).
# --------------------------------------------------------------------------------------------------

def test_a_gate_tests_mismatch_is_DETECTED(tmp_path):
    """CONTRE-EXEMPLE GELE -- la configuration exacte de S2-008 avant correction (gate d'une porte,
    tests d'une autre) : roadmap_state compterait le record dans DEUX portes."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\ntests: [SDR-G2]")
    mm = C.analyze(root)["gate_tests_mismatch"]
    assert any(m["id"] == "EDR-999" and m["gate"] == "G0" and m["tests_gates"] == ["G2"]
               for m in mm), mm


def test_a_coherent_gate_and_tests_triggers_NOTHING(tmp_path):
    """SPECIFICITE : gate et tests alignes -> rien."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G2\ntests: [SDR-G2]")
    assert C.analyze(root)["gate_tests_mismatch"] == []


def test_foundational_with_sdr_tests_is_NOT_a_mismatch(tmp_path):
    """Semantique TRANCHEE et gelee : foundational n'est pas une porte (_ANCHORS) -- un record
    foundational qui teste une SDR n'est pas un conflit, l'arete tests fait foi."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: foundational\ntests: [SDR-G1]")
    assert C.analyze(root)["gate_tests_mismatch"] == []


# --------------------------------------------------------------------------------------------------
# 2026-09-06 : gate_unlinked entre au regime BASELINE. Il etait calcule (analyze) mais jamais ratchete
# (affiche en --report seulement) : la dette « EDR sans porte » pouvait croitre en silence.
# --------------------------------------------------------------------------------------------------

def test_an_edr_without_gate_nor_sdr_tests_is_gate_unlinked(tmp_path):
    """CONTRE-EXEMPLE GELE : un EDR raccorde par une arete (adopts) mais sans porte ni tests SDR est
    NON RACCORDE A UNE PORTE -- ce n'est pas un orphelin (il a une arete) mais il n'est compte pour
    aucune porte dans roadmap_state."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nadopts: [EDR-112]")
    gu = C.analyze(root)["gate_unlinked"]
    assert any(g["id"] == "EDR-999" for g in gu), gu


def test_an_edr_with_sdr_tests_but_no_gate_is_NOT_gate_unlinked(tmp_path):
    """SPECIFICITE : tests: [SDR-Gx] suffit a raccorder (roadmap_state lit aussi tests)."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ntests: [SDR-G1]")
    assert all(g["id"] != "EDR-999" for g in C.analyze(root)["gate_unlinked"])


def test_a_foundational_edr_is_NOT_gate_unlinked(tmp_path):
    """foundational est un ancrage (_ANCHORS) : pas une porte, mais un raccord legitime."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: foundational")
    assert all(g["id"] != "EDR-999" for g in C.analyze(root)["gate_unlinked"])


# --------------------------------------------------------------------------------------------------
# 2026-09-09 — TROU TROUVE PAR `tools/check_gate_mutation.py`, et il portait sur le verdict CENTRAL.
# `orphans` est ce sur quoi la PORTE 1 du hook BLOQUE, et il n'avait AUCUN contre-exemple : remplacer
# `if not has_gate and not has_edge:` par `if False:` dans `analyze` laissait ce fichier ENTIEREMENT
# VERT. Les 11 tests couvraient les cles d'aretes, `gate_unlinked` et le mismatch gate<->tests --
# c'est-a-dire tout SAUF la detection d'orphelin elle-meme.
# ⚠️ Ce que ce cas apprend, et qui vaut au-dela de lui : un fichier de temoins peut etre FOURNI,
# DETAILLE, exact, et laisser sans contre-exemple precisement le verdict qui bloque. Aucune relecture
# ne l'avait vu en deux mois ; la mutation le dit en trois secondes.
# --------------------------------------------------------------------------------------------------

def test_an_UNLINKED_record_is_an_ORPHAN(tmp_path):
    """CONTRE-EXEMPLE GELE de la porte 1 : ni porte, ni arete -> orphelin, et le cliquet le dit."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR")
    orph = C.analyze(root)["orphans"]
    assert any(o["id"] == "EDR-999" for o in orph), (
        f"un record sans porte NI arete doit etre un orphelin, or : {orph}")


def test_a_record_with_a_GATE_is_NOT_an_orphan(tmp_path):
    """SPECIFICITE (no-op apparie). Sans lui, un detecteur qui declare TOUT orphelin passerait le
    test precedent tout en etant inutilisable -- la paire fires/spares que le depot exige."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0")
    assert all(o["id"] != "EDR-999" for o in C.analyze(root)["orphans"])


def test_a_record_with_an_EDGE_but_no_gate_is_NOT_an_orphan(tmp_path):
    """La SECONDE voie de raccord. Un record adopte par un autre n'est pas orphelin meme sans porte :
    c'est ce qui distingue `orphans` de `gate_unlinked`, et les confondre rendrait l'un des deux
    verdicts muet sans que rien ne rougisse (le meme fichier teste deja l'autre sens juste au-dessus)."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nadopts: [EDR-112]")
    assert all(o["id"] != "EDR-999" for o in C.analyze(root)["orphans"])


# --------------------------------------------------------------------------------------------------
# Tâche 4 (spec PM 2026-09-16 §3.5) : `review:` — porte 1 étendue. Tout NOUVEAU record EDR à verdict
# (gate: G0-G4/foundational OU tests: [SDR-Gx]) doit porter `review:` — le chemin d'une revue
# adversariale à sondes propres, JAMAIS un id de record (edge_key_silences traiterait `EDR-...` comme
# une arête non lue et ferait rendre 1 à la porte 1 sur TOUT l'arbre — piège principal de cette tâche).
#
# ⚠️ Revue du contrôleur (post-Tâche 4) : `not r.get("review")` était satisfait par N'IMPORTE QUELLE
# chaîne non vide — `review: x` passait. Corrigé : `review:` doit être un chemin de FORME
# `docs/reviews/AAAA-MM-JJ-slug.md` ET le fichier doit EXISTER, avec une raison DISTINCTE par défaut
# (`"absente"` / `"forme"` / `"fichier introuvable"`) — ne pas les fondre.
# --------------------------------------------------------------------------------------------------

def _make_review_file(tmp_path, relpath="docs/reviews/2026-09-17-edr-999.md"):
    p = tmp_path / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# revue\n", encoding="utf-8")
    return relpath


def test_a_NEW_edr_with_a_gate_but_no_review_is_review_missing(tmp_path):
    """CONTRE-EXEMPLE GELÉ de la porte 1 étendue (spec PM 2026-09-16 §3.5) : un record à verdict sans revue."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\ntests: [SDR-G0]")
    rv = C.analyze(root)["review_missing"]
    assert any(r["id"] == "EDR-999" and r["raison"] == "absente" for r in rv), rv


def test_an_edr_with_an_INVALID_FORM_review_is_review_missing(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ nommé par la revue du contrôleur : `review: x` n'est PAS un chemin de revue
    -- n'importe quelle chaîne non vide passait avant ce correctif. Raison distincte : 'forme'."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: x")
    rv = C.analyze(root)["review_missing"]
    assert any(r["id"] == "EDR-999" and r["raison"] == "forme" for r in rv), rv


def test_an_edr_with_a_WELLFORMED_but_MISSING_review_file_is_review_missing(tmp_path):
    """CONTRE-EXEMPLE GELÉ : chemin de FORME valide mais fichier ABSENT du disque -- le Réfutateur
    (tâche 6) doit pouvoir distinguer « j'ai oublié d'écrire » de « le chemin est mal formé »."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: docs/reviews/2026-09-23-inexistant.md")
    rv = C.analyze(root)["review_missing"]
    assert any(r["id"] == "EDR-999" and r["raison"] == "fichier introuvable" for r in rv), rv


def _depot_jetable_avec_revue(tmp_path, suivre=True):
    """Un VRAI dépôt git jetable portant le record et sa revue — le second `git add` étant l'objet du test.

    ⚠️ Pas de monkeypatch de l'oracle : c'est le point n°1 de la revue de la porte 20 (« remplacer
    `_tracked` par `return True` laisse 13/13 verts »). Un témoin qui injecte une constante ne prouve
    rien. ⚠️ Identité passée EN LIGNE (`-c`), jamais `git config` : un test qui ÉCRIT une config est à
    une régression d'isolation près de polluer le dépôt réel, et c'est arrivé (33 commits signés
    `Test <test@example.com>`, premier `7d6c04c9`).
    """
    import subprocess  # noqa: PLC0415

    from tools.check_evidence_provenance import _env_isole  # noqa: PLC0415

    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: docs/reviews/2026-09-17-edr-999.md")
    _make_review_file(tmp_path)

    def git(*args):
        # ⚠️ `_env_isole()` retire TOUS les `GIT_*`, pas seulement `GIT_INDEX_FILE`. Première version
        # de ce témoin : n'en retirait qu'UN — vert hors commit, ROUGE sous le hook, parce que
        # `git commit` fixe aussi `GIT_DIR` (et `GIT_PREFIX`, `GIT_AUTHOR_*`). Un `git add` héritant
        # de `GIT_DIR` vise l'index du dépôt RÉEL, pas le jetable. C'est exactement la leçon que ce
        # témoin CITE, appliquée à moitié : réutiliser l'helper de la porte 20 plutôt que le réécrire.
        r = subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
            cwd=str(root), capture_output=True, text=True, env=_env_isole())
        assert r.returncode == 0, f"git {args} : {r.stderr}"

    git("init", "-b", "main")
    if suivre:
        git("add", "docs/reviews/2026-09-17-edr-999.md")
    return root


def test_an_edr_with_a_review_path_SUIVI_PAR_GIT_is_NOT_review_missing(tmp_path):
    """SPÉCIFICITÉ (no-op apparié aux trois précédents) : forme valide, fichier présent ET SUIVI -> passe."""
    root = _depot_jetable_avec_revue(tmp_path, suivre=True)
    assert not any(r["id"] == "EDR-999" for r in C.analyze(root)["review_missing"])


def test_an_edr_dont_la_revue_EXISTE_mais_N_EST_PAS_SUIVIE_est_review_missing(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ (2026-09-24) : la preuve qu'une revue a eu lieu était le SEUL chemin
    d'évidence du dépôt qui n'avait pas à être suivi.

    `_review_defect` testait `os.path.isfile`, donc le DISQUE, alors que la porte 20 — livrée dans la
    MÊME branche pour la MÊME classe (E27, « une évidence qui n'est plus rouvrable ») — exige l'INDEX.
    Sur un arbre que six sessions éditent, un record pouvait donc se committer **certifié revu** en
    pointant vers un fichier qui ne serait jamais dans le clone. Raison distincte : 'non suivi'.
    """
    root = _depot_jetable_avec_revue(tmp_path, suivre=False)
    rv = C.analyze(root)["review_missing"]
    assert any(r["id"] == "EDR-999" and r["raison"] == "non suivi" for r in rv), rv


def test_an_edr_WITHOUT_verdict_anchor_is_not_asked_for_a_review(tmp_path):
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nadopts: [REF-DEMAND-MARKER]")
    assert not any(r["id"] == "EDR-999" for r in C.analyze(root)["review_missing"])


def test_the_review_key_is_READ_by_the_schema_not_silenced(tmp_path):
    """⚠️ Minor 3 de la revue du contrôleur : ce test était VACUE (sa fixture utilisait un CHEMIN, qui
    ne ressemble pas à un id). `review: EDR-999` A la FORME d'un identifiant de record (`_ID_LIKE`) --
    sans `review` dans le schéma (`_empty_record`), `edge_key_silences` le signalerait comme une clé
    d'arête NON LUE (le piège exact nommé en tâche 4). Vise `edge_key_silences`, pas `analyze` : ce
    record sera par ailleurs « sans revue » pour cause de forme, ce qui est cohérent et hors du test."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nreview: EDR-999")
    sil = C.edge_key_silences(root)
    assert not any(k == "review" for _, k in sil["non_lues"]), sil["non_lues"]
    rec = [r for r in scan_records(root) if r["id"] == "EDR-999"][0]
    assert rec["review"] == "EDR-999"
