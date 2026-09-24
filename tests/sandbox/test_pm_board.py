"""Tableau PM : `compute` est PUR — chaque alerte a son cas positif et son no-op, chaque source absente rend
un AVEUGLEMENT visible et jamais un « 0 alerte »."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import board as B  # noqa: E402

NOW = 1_800_000_000.0
ROOT = "c:/x/agagi"


def _reg(name, sid, cwd=ROOT, started=NOW - 600, alive=True):
    return {"pid": 1, "session_id": sid, "name": name, "cwd": cwd, "kind": "interactive", "alive": alive,
            "started_at": started, "updated_at": NOW}


def _bul(sid, files=(), claims=(), heartbeat=NOW - 60, branch="feat/x"):
    return {"session_id": sid, "files_touched": list(files), "claims": list(claims),
            "heartbeat_at": heartbeat, "branch": branch}


def _snap(**kw):
    base = {"now": NOW, "repo_root": ROOT, "psutil": True,
            "registry": [_reg("agagi-11", "s1"), _reg("agagi-52", "s2"), _reg("elysium-d4", "e1", cwd="c:/x/elysium")],
            "bulletins": [_bul("s1"), _bul("s2")],
            "worktrees": [{"path": ROOT, "branch": "main", "head": "abc", "merged": False, "locked": False,
                           "head_time": NOW}],
            "commits": [{"sha": "abc1234567", "sujet": "ok", "insertions": 3, "deletions": 2, "amputations": []}],
            "leases": {"live": [], "dead": []}, "processes": [], "cpu_pct": 12.0, "hook_errors": {},
            "backlog_paths": {"P4.9": ["tools/evo_runs/s2_credit_ablation.py"], "P2.78": []}}
    base.update(kw)
    return base


def _ids(board, id_):
    return [a for a in board["alertes"] if a["id"] == id_]


def test_NOOP_exact_un_etat_sain_ne_leve_AUCUNE_alerte_ni_aveuglement():
    b = B.compute(_snap())
    assert b["alertes"] == [] and b["aveugle"] == []
    assert [s["name"] for s in b["sessions"]] == ["agagi-11", "agagi-52"]     # elysium hors dépôt


def test_compute_normalise_repo_root_et_worktrees_pas_seulement_cwd():
    """`_sessions` doit tenir l'invariant « norm des deux côtés » ELLE-MÊME : `cwd` était déjà normalisé
    avant ce correctif, mais `repo_root`/`worktrees` ne l'étaient pas — un `cwd` de registre natif à
    BACKSLASHES (Windows) doit apparier une session au dépôt même sans overlap de worktree fortuit.
    Backslashes vs slashes est indépendant de la plateforme (le `.replace` de `norm` est un remplacement
    textuel, pas une résolution de chemin) ; on ne teste PAS une différence de CASSE, `normcase` est
    l'identité sur Linux."""
    reg = [_reg("agagi-11", "s1", cwd="c:\\x\\agagi")]
    b = B.compute(_snap(registry=reg, bulletins=[_bul("s1")]))
    assert [s["name"] for s in b["sessions"]] == ["agagi-11"]
    # discriminant réel du correctif (repo_root lui-même non normalisé côté appelant, sans worktree
    # qui masquerait le défaut par coïncidence) :
    b2 = B.compute(_snap(registry=[_reg("agagi-11", "s1", cwd=ROOT)], bulletins=[_bul("s1")],
                          worktrees=[], repo_root="c:\\x\\agagi"))
    assert [s["name"] for s in b2["sessions"]] == ["agagi-11"]


def test_A1_deux_sessions_sur_le_meme_fichier_et_pas_une_seule():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["src/paths.py"]), _bul("s2", files=["src/paths.py", "x.py"])]))
    a = _ids(b, "A1")
    assert len(a) == 1 and a[0]["preuve"] == {"fichier": "src/paths.py", "cwds": [ROOT],
                                              "sessions": ["agagi-11", "agagi-52"]}
    assert a[0]["cle"] == "A1:" + ROOT + "/src/paths.py" and a[0]["gravite"] == "alerte"
    assert "src/paths.py" in a[0]["message"] and ROOT in a[0]["message"]
    assert _ids(B.compute(_snap(bulletins=[_bul("s1", files=["x.py"]), _bul("s2", files=["y.py"])])), "A1") == []


def test_A1_le_MEME_chemin_relatif_dans_DEUX_worktrees_n_est_PAS_une_collision():
    """CONTRE-EXEMPLE GELE (I7) : la cle d'A1 etait le chemin RELATIF, donc deux sessions editant
    chacune `src/paths.py` dans SON worktree etaient appariees -- alors qu'elles editent deux
    fichiers distincts. C'est le cas NORMAL d'un depot qui multiplie les worktrees : un faux positif
    permanent, donc du bruit qui fait desarmer le tableau."""
    wts = [{"path": ROOT, "branch": "main", "head": "a", "merged": False, "locked": False, "head_time": NOW},
           {"path": ROOT + "/.worktrees/w2", "branch": "chantier/w2", "head": "b", "merged": False,
            "locked": False, "head_time": NOW}]
    reg = [_reg("agagi-11", "s1"), _reg("agagi-52", "s2", cwd=ROOT + "/.worktrees/w2")]
    ailleurs = B.compute(_snap(registry=reg, worktrees=wts,
                               bulletins=[_bul("s1", files=["src/paths.py"]), _bul("s2", files=["src/paths.py"])]))
    assert _ids(ailleurs, "A1") == []
    ensemble = B.compute(_snap(bulletins=[_bul("s1", files=["src/paths.py"]), _bul("s2", files=["src/paths.py"])]))
    assert len(_ids(ensemble, "A1")) == 1                      # meme cwd : la collision REELLE est toujours vue


def test_A2_bail_orphelin_ALERTE_et_ttl_expire_detenteur_vivant_INFO():
    morts = [{"resource": "kuzu", "pid": 9, "owner": "o", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": False},
             {"resource": "pm", "pid": 8, "owner": "p", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": True}]
    b = B.compute(_snap(leases={"live": [], "dead": morts}))
    a = {x["cle"]: x["gravite"] for x in _ids(b, "A2")}
    assert a == {"A2:kuzu": "alerte", "A2:pm": "info"}


def test_A2_sans_psutil_l_identite_des_detenteurs_est_AVEUGLE_pas_fausse():
    b = B.compute(_snap(psutil=False, leases={"live": [], "dead": [{"resource": "kuzu", "pid": 9, "owner": "o",
                  "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False, "detenteur_vivant": False}]}))
    assert _ids(b, "A2") == [] and any("psutil" in x for x in b["aveugle"])


def test_A3_worktree_sans_session_fusionne_ou_inactif_et_pas_celui_d_une_session():
    wts = [{"path": ROOT, "branch": "main", "head": "a", "merged": False, "locked": False, "head_time": NOW},
           {"path": ROOT + "/.claude/worktrees/wf-1", "branch": "wf-1", "head": "b", "merged": True,
            "locked": False, "head_time": NOW},
           {"path": ROOT + "/.worktrees/vieux", "branch": "chantier/vieux", "head": "c", "merged": False,
            "locked": False, "head_time": NOW - 8 * 86400},
           {"path": ROOT + "/.worktrees/actif", "branch": "chantier/actif", "head": "d", "merged": False,
            "locked": False, "head_time": NOW - 8 * 86400}]
    reg = [_reg("agagi-11", "s1"), _reg("agagi-52", "s2", cwd=ROOT + "/.worktrees/actif")]
    b = B.compute(_snap(worktrees=wts, registry=reg))
    assert sorted(a["cle"] for a in _ids(b, "A3")) == ["A3:" + ROOT + "/.claude/worktrees/wf-1", "A3:" + ROOT + "/.worktrees/vieux"]


def test_A3_ne_vise_NI_la_branche_de_BASE_NI_un_worktree_VERROUILLE():
    """CONTRE-EXEMPLE GELE (I1) : `git branch --merged main` liste TOUJOURS `main`, donc un second
    worktree pose sur la branche de base etait A3 a chaque tick -- une alerte qu'aucune action ne
    peut eteindre. Et un worktree VERROUILLE est garde deliberement (git refuse de le supprimer) :
    le signaler est du bruit.

    Le `merged=False` du worktree pose sur `main` n'est PAS une commodite de fixture : c'est ce que
    `read_worktrees` produit desormais (gele dans `test_pm_snapshot.py`). Ici on verifie l'autre
    moitie de la paire — que le tableau n'en fait plus une alerte."""
    wts = [{"path": ROOT, "branch": "main", "head": "a", "merged": False, "locked": False, "head_time": NOW},
           {"path": ROOT + "/.worktrees/sur-main", "branch": "main", "head": "b", "merged": False,
            "locked": False, "head_time": NOW},
           {"path": ROOT + "/.worktrees/verrouille", "branch": "chantier/garde", "head": "c", "merged": True,
            "locked": True, "head_time": NOW - 30 * 86400}]
    b = B.compute(_snap(worktrees=wts))
    assert _ids(b, "A3") == []
    # controle positif : le MEME worktree, deverrouille, EST une A3 -- la garde ne neutralise pas l'alerte
    wts[2]["locked"] = False
    assert [a["cle"] for a in _ids(B.compute(_snap(worktrees=wts)), "A3")] == ["A3:" + ROOT + "/.worktrees/verrouille"]


def test_A4_commit_a_grosse_suppression_OU_amputation_et_pas_un_commit_ordinaire():
    gros = {"sha": "dead000000", "sujet": "menage", "insertions": 0, "deletions": 2372, "amputations": []}
    ampute = {"sha": "beef000000", "sujet": "x", "insertions": 1, "deletions": 120,
              "amputations": [{"chemin": "docs/roadmap/PRIORITES_ET_DETTES.md", "avant": 2352, "apres": 0}]}
    b = B.compute(_snap(commits=[gros, ampute, {"sha": "ok", "sujet": "ok", "insertions": 1, "deletions": 499, "amputations": []}]))
    assert sorted(a["cle"] for a in _ids(b, "A4")) == ["A4:beef000000", "A4:dead000000"]


def test_A5_deux_simulations_en_vol_ou_cpu_sature_et_ni_l_un_ni_l_autre_sinon():
    procs = [{"pid": 1, "age_min": 5, "rss_mb": 10, "cmd": "python tools/evo_runs/x_run.py", "simulation": True},
             {"pid": 2, "age_min": 5, "rss_mb": 10, "cmd": "python tools/s2_probe.py", "simulation": True},
             {"pid": 3, "age_min": 5, "rss_mb": 10, "cmd": "python -m pytest", "simulation": False}]
    b = B.compute(_snap(processes=procs))
    assert [a["cle"] for a in _ids(b, "A5")] == ["A5:sims"] and b["charge_connue"]["sims_en_vol"] == 2
    b2 = B.compute(_snap(cpu_pct=91.0))
    assert [a["cle"] for a in _ids(b2, "A5")] == ["A5:cpu"] and _ids(b2, "A5")[0]["preuve"] == {"cpu_pct": 91.0}
    assert b2["charge_connue"]["cpu_pct"] == 91.0
    assert _ids(B.compute(_snap(processes=procs[:1], cpu_pct=79.9)), "A5") == []


def test_A9_un_hook_qui_echoue_DEUX_fois_est_une_alerte_pas_UNE_fois():
    """Spec §5 : un hook sort 0 quoi qu'il arrive, son echec ne se voit NULLE PART sauf ici."""
    assert _ids(B.compute(_snap(hook_errors={"stop": 1, "start": 1})), "A9") == []
    a = _ids(B.compute(_snap(hook_errors={"stop": 2, "start": 1})), "A9")
    assert [x["cle"] for x in a] == ["A9:hook:stop"]
    assert a[0]["gravite"] == "alerte" and a[0]["preuve"] == {"event": "stop", "erreurs": 2}


def test_A9_journal_des_hooks_ILLISIBLE_est_un_AVEUGLEMENT_pas_zero_echec():
    b = B.compute(_snap(hook_errors=None))
    assert _ids(b, "A9") == [] and any("hook_errors.log" in x for x in b["aveugle"])


def test_A6_meme_P_item_revendique_par_deux_sessions():
    b = B.compute(_snap(bulletins=[_bul("s1", claims=["P4.9"]), _bul("s2", claims=["P4.9", "P2.78"])]))
    a = _ids(b, "A6")
    assert len(a) == 1 and a[0]["preuve"] == {"p_item": "P4.9", "sessions": ["agagi-11", "agagi-52"]}


def test_A7_session_active_plus_d_une_heure_sans_claim_ni_inference_est_une_INFO_clee_par_SESSION_ID():
    """Clé = `session_id`, JAMAIS le nom (défaut 2, 2026-09-24) : ce test exigeait `A7:agagi-11` et PROTÉGEAIT le
    défaut — un nom change au redémarrage, une clé par nom fabriquait un suivi. Le nom reste dans le message et
    dans `preuve.session` : c'est lui qu'on LIT, pas lui qu'on SUIT."""
    reg = [_reg("agagi-11", "s1", started=NOW - 2 * 3600), _reg("agagi-52", "s2", started=NOW - 2 * 3600)]
    bul = [_bul("s1"), _bul("s2", files=["tools/evo_runs/s2_credit_ablation.py"])]
    b = B.compute(_snap(registry=reg, bulletins=bul))
    a = _ids(b, "A7")
    assert [x["cle"] for x in a] == ["A7:s1"] and a[0]["gravite"] == "info"
    assert "agagi-11" in a[0]["message"] and a[0]["preuve"] == {"session": "agagi-11", "session_id": "s1"}
    s2 = [s for s in b["sessions"] if s["name"] == "agagi-52"][0]
    assert s2["claims_inferes"] == ["P4.9"]                     # inféré des fichiers touchés, marqué comme tel


def test_A7_le_MEME_bulletin_sous_DEUX_noms_successifs_produit_UNE_seule_cle_et_AUCUN_suivi_FABRIQUE():
    """CONTRE-EXEMPLE GELÉ (défaut 2, 2026-09-24) : clé par NOM, un renommage (redémarrage de la flotte :
    agagi-52 -> agagi-00) faisait « disparaître » A7:agagi-52 — journal : suivie, comptée dans suivies_48h — et
    émettait une « nouvelle » A7:agagi-00. Deux lignes de journal et un compteur gonflé pour ZÉRO changement réel."""
    from tools.pm import alerts as AL
    bul = [_bul("s1")]
    avant = B.compute(_snap(registry=[_reg("agagi-11", "s1", started=NOW - 2 * 3600)], bulletins=bul))
    apres = B.compute(_snap(registry=[_reg("agagi-e4", "s1", started=NOW - 2 * 3600)], bulletins=bul), now=NOW + 1200)
    assert [a["cle"] for a in _ids(avant, "A7")] == [a["cle"] for a in _ids(apres, "A7")] == ["A7:s1"]
    assert "agagi-11" in _ids(avant, "A7")[0]["message"] and "agagi-e4" in _ids(apres, "A7")[0]["message"]
    journal = AL.diff(avant, [], NOW)["lignes"]                 # premier tick : émise
    assert [l["statut"] for l in journal] == ["emise"]
    d = AL.diff(apres, journal, NOW + 1200)                     # second tick, après le renommage
    assert d["nouvelles"] == [] and d["disparues"] == [] and d["repetees"] == [] and d["lignes"] == []
    c = AL.compteurs(journal + d["lignes"], NOW + 1200)
    assert c["suivies_48h"] == 0 and c["emises"] == 1 and c["ouvertes"] == 1


def test_A7_supprimee_quand_le_backlog_est_AVEUGLE_et_pas_fabriquee():
    """A7 dépend de l'inférence de claims (backlog_paths) : si cette source est AVEUGLE, l'alerte doit
    disparaître elle aussi (porte 14) plutôt que d'affirmer à tort « sans P-item […] ni inféré »."""
    reg = [_reg("agagi-11", "s1", started=NOW - 2 * 3600)]
    b = B.compute(_snap(registry=reg, bulletins=[_bul("s1")], backlog_paths=None))
    assert _ids(b, "A7") == []
    assert any("backlog" in a for a in b["aveugle"])


def test_A8_heartbeat_vieux_de_plus_de_deux_heures_est_une_INFO_clee_par_SESSION_ID():
    """Même correctif qu'A7 (ce test exigeait `A8:agagi-11`) : clé = session_id, nom dans le message et la preuve."""
    b = B.compute(_snap(bulletins=[_bul("s1", heartbeat=NOW - 3 * 3600), _bul("s2")]))
    a = _ids(b, "A8")
    assert [x["cle"] for x in a] == ["A8:s1"] and a[0]["gravite"] == "info"
    assert "agagi-11" in a[0]["message"] and a[0]["preuve"] == {"session": "agagi-11", "session_id": "s1"}


def test_chaque_source_ABSENTE_est_nommee_AVEUGLE_et_ses_alertes_sont_supprimees():
    b = B.compute(_snap(registry=None, bulletins=None, worktrees=None, commits=None, leases=None, processes=None,
                        cpu_pct=None, backlog_paths=None, hook_errors=None))
    assert b["alertes"] == [] and b["sessions"] == []
    assert len(b["aveugle"]) == 8
    assert b["charge_connue"] == {"sims_en_vol": None, "cpu_pct": None, "bails_vivants": None}
    md = B.render_md(b)
    assert md.splitlines()[2].startswith("AVEUGLE SUR")          # en tête, avant toute autre ligne


def test_le_tableau_porte_la_date_de_chaque_fichier_en_vol_et_du_bulletin_et_n_en_invente_aucune():
    """Défaut 3 (2026-09-24) : `files_touched_at` et `updated_at` traversent le tableau tels quels ; un bulletin
    légataire (sans ces champs) rend {} et None, jamais une date fabriquée."""
    bul = [dict(_bul("s1", files=["a.py"]), files_touched_at={"a.py": NOW - 30}, updated_at=NOW - 30), _bul("s2")]
    s = {x["session_id"]: x for x in B.compute(_snap(bulletins=bul))["sessions"]}
    assert s["s1"]["files_touched_at"] == {"a.py": NOW - 30} and s["s1"]["updated_at"] == NOW - 30
    assert s["s2"]["files_touched_at"] == {} and s["s2"]["updated_at"] is None
    assert s["s1"]["files_touched"] == ["a.py"]                             # la liste, elle, ne change pas de forme


def test_une_session_SANS_BULLETIN_est_un_AVEUGLEMENT_nomme_pas_une_session_calme():
    """C2.2 : sans bulletin, la session n'a ni fichiers en vol, ni claims, ni heartbeat — A1, A6, A7
    et A8 sont MUETTES sur elle. Zéro alerte y ressemble exactement à « rien à signaler »."""
    b = B.compute(_snap(bulletins=[_bul("s1")]))                 # agagi-52 (s2) n'a pas de bulletin
    ligne = [a for a in b["aveugle"] if a.startswith("bulletin absent")]
    assert len(ligne) == 1 and "agagi-52" in ligne[0] and "1 session" in ligne[0]
    assert "agagi-11" not in ligne[0]
    assert [a for a in B.compute(_snap())["aveugle"] if a.startswith("bulletin absent")] == []


def test_une_entree_de_registre_ILLISIBLE_est_COMPTEE_et_nommee_pas_avalee():
    """I3 : `read_registry` DÉTECTAIT l'entrée illisible, `_sessions` la sautait en silence."""
    reg = [_reg("agagi-11", "s1"), {"illisible": "casse.json"}, {"illisible": "autre.json"}]
    b = B.compute(_snap(registry=reg, bulletins=[_bul("s1")]))
    assert [a for a in b["aveugle"] if "registre illisible" in a] == ["2 entrée(s) de registre illisible(s)"]


def test_un_bulletin_SANS_session_id_ou_illisible_est_COMPTE_et_nomme():
    bul = [_bul("s1"), _bul("s2"), {"illisible": "x.json"}, {"claims": ["P4.9"]}]
    b = B.compute(_snap(bulletins=bul))
    assert [a for a in b["aveugle"] if "bulletin(s) sans session_id" in a] == \
        ["2 bulletin(s) sans session_id ou illisible(s)"]


def test_une_session_MORTE_est_ECARTEE_du_tableau_et_LISTEE():
    """I4 : le registre natif n'efface pas l'entrée d'une session terminée — sans `alive`, le tableau
    opposait des fantômes à des vivants (A1, A6)."""
    reg = [_reg("agagi-11", "s1"), _reg("agagi-52", "s2", alive=False)]
    b = B.compute(_snap(registry=reg, bulletins=[_bul("s1", files=["a.py"]), _bul("s2", files=["a.py"])]))
    assert [s["name"] for s in b["sessions"]] == ["agagi-11"] and b["sessions_mortes"] == ["agagi-52"]
    assert _ids(b, "A1") == []                                   # la collision avec un MORT n'en est pas une
    assert "agagi-52" in B.render_md(b) and "agagi-52" in B.summary(b)


def test_sans_psutil_la_VIE_des_sessions_est_AVEUGLE_et_aucune_n_est_ecartee():
    reg = [_reg("agagi-11", "s1", alive=None), _reg("agagi-52", "s2", alive=None)]
    b = B.compute(_snap(registry=reg))
    assert [s["name"] for s in b["sessions"]] == ["agagi-11", "agagi-52"] and b["sessions_mortes"] == []
    assert any("vie des sessions" in a for a in b["aveugle"])


def test_render_et_summary_portent_les_alertes_et_la_charge():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["a.py"]), _bul("s2", files=["a.py"])]))
    md = B.render_md(b)
    assert "A1" in md and "agagi-11" in md and "charge connue" in md.lower()
    s = B.summary(b)
    assert len(s.splitlines()) <= 25 and "A1" in s


def test_summary_publie_l_AGE_en_tete_et_dit_INCONNU_plutot_que_se_taire():
    """Défaut 1 (2026-09-24) : un résumé en cache sans âge fait passer du périmé pour du courant."""
    b = B.compute(_snap())
    tete = B.summary(b, age_s=600, source_age="generated_at").splitlines()[0]
    assert "âge 10 min (generated_at)" in tete and "périmé au-delà de 2.0 h" in tete
    assert "âge INCONNU" in B.summary(b).splitlines()[0]


def test_main_ecrit_BOARD_json_et_md_sous_pm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    code = B.main(["--repo-root", os.getcwd(), "--registry-dir", str(tmp_path / "aucun"),
                   "--sessions-dir", str(tmp_path / "aucun")])
    assert code == 0
    j = json.loads((tmp_path / "pm" / "BOARD.json").read_text(encoding="utf-8"))
    assert "registre natif" in " ".join(j["aveugle"])
    assert (tmp_path / "pm" / "BOARD.md").read_text(encoding="utf-8").startswith("# Tableau PM")
