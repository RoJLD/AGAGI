"""Procédure des vagues de déport (tools/td_step_pilot_r3_vague.py) : le classeur rend le verdict CONNU sur les cas de la
table P2.168 PUBLIÉE (docs/REF/REF-DEPORT-NEXUS.md), journaux écrits au FORMAT de tools/jobs/remote.py (dont l'ancien
refus en code 2 lu au journal, un code 0 sans sortie jamais OK, et un code réservé rendu par le RUNNER) ; « relançable
tel quel » suit la colonne « quoi faire » ; le bras apparié sans ρ n'est JAMAIS soumis ; une vague rend un verdict PAR
cellule. Aucune soumission réelle : `soumettre` et `rho` sont injectés."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.jobs.remote as remote  # noqa: E402
import tools.td_step_pilot_r3_vague as vg  # noqa: E402


def _ligne(code, texte):
    """Une ligne de journal au format d'executer (tools/jobs/remote.py, main) : « [remote] <libellé> (<code>) … »."""
    return f"[remote] {remote.LIBELLES_SORTIE[code]} ({code}) : {texte}"


REFUS_QUOTA = _ligne(85, "td-x : quota du namespace plein (exceeded quota: cpu) — attendre qu'un run finisse")
FIN_OOM = (f"[remote] {remote.LIBELLES_SORTIE[88]} (88) — td-x : "
           + json.dumps({"etat": "oom", "relancable": True}, ensure_ascii=False))
FIN_DELAI = (f"[remote] {remote.LIBELLES_SORTIE[88]} (88) — td-x : "
             + json.dumps({"etat": "delai_depasse", "relancable": False}, ensure_ascii=False))


@pytest.mark.parametrize("rc,journal,present,attendu", [
    (0, "", True, "OK"), (0, "", False, "RUNNER"), (85, REFUS_QUOTA, False, "REFUS_LOCAL"),
    (2, "[remote] REFUS : quota du namespace plein", False, "REFUS_LOCAL"),        # avant P2.168 : refus local en 2
    (86, _ligne(86, "sha absent"), False, "REFUS_POD"), (87, _ligne(87, "pod disparu"), False, "SORTIE_PERDUE"),
    (88, FIN_OOM, False, "SANS_SORTIE"), (89, _ligne(89, "API injoignable"), True, "A_RAPATRIER"),
    (87, "[remote] ⚠ le RUNNER a rendu 87, un code RÉSERVÉ au déport", True, "RUNNER"),
    (1, "", True, "RUNNER"), (None, "", False, "RUNNER")])
def test_the_known_cases_of_the_PUBLISHED_P2_168_table(rc, journal, present, attendu):
    assert vg.classer_cellule(rc, journal, present) == attendu


def test_only_the_85_starts_with_the_local_refusal_prefix_in_the_publisher():
    """Le classeur lit « [remote] REFUS » : vrai seulement si AUCUN autre libellé publié ne commence ainsi (table)."""
    debuts = {c: f"[remote] {lib}".startswith(vg.PREFIXE_REFUS_LOCAL) for c, lib in remote.LIBELLES_SORTIE.items()}
    assert debuts == {85: True, 86: False, 87: False, 88: False, 89: False}
    assert vg.QUOTA_PLEIN in open(remote.__file__, encoding="utf-8").read()     # la phrase filtrée existe chez l'émetteur


def test_relaunchable_AS_IS_follows_the_what_to_do_column():
    assert vg.relancable("REFUS_LOCAL", REFUS_QUOTA)
    assert not vg.relancable("REFUS_LOCAL", _ligne(85, "quota du namespace : cpu = 2 demandé par CE pod > hard 1 — il "
                                                       "ne serait JAMAIS admis"))
    assert not vg.relancable("REFUS_LOCAL", _ligne(85, "fenêtre du nœud dépassée ; base de fuseaux pleine"))
    assert vg.relancable("SORTIE_PERDUE", _ligne(87, "pod disparu"))
    assert vg.relancable("SANS_SORTIE", FIN_OOM) and not vg.relancable("SANS_SORTIE", FIN_DELAI)
    assert not vg.relancable("A_RAPATRIER", REFUS_QUOTA) and not vg.relancable("REFUS_POD", _ligne(86, "x"))


def test_specs_map_to_the_runner_commands_and_unknown_forms_are_refused():
    assert vg.analyser_spec("cellule:lam09:p1:3")[:3] == (
        "tools.td_step_pilot_r3", ["cellule", "--bras", "lam09", "--pas", "p1", "--seed", "3"], "lam09_p1_seed3")
    assert vg.analyser_spec("reference:lr0_reference:7")[2] == "lr0_reference_seed7"
    assert vg.analyser_spec("tau:lam0:13")[:3] == ("tools.td_step_pilot_r3_tau",
                                                   ["cellule", "--bras", "lam0", "--seed", "13"], "lam0_seed13")
    assert vg.analyser_spec("tau:sham_dose:p2:14")[1:3] == (
        ["cellule", "--bras", "sham_dose", "--seed", "14", "--pas", "p2"], "sham_dose_p2_seed14")
    assert vg.analyser_spec("tau:lam09:p1:13:1")[1:3] == (
        ["cellule", "--bras", "lam09", "--seed", "13", "--replique", "1"], "lam09_seed13_rep1")
    with pytest.raises(ValueError, match="inconnue"):
        vg.analyser_spec("cellule:lam09:3")


def test_a_wave_gives_a_verdict_PER_CELL_and_never_submits_the_paired_arm_without_rho(monkeypatch, tmp_path):
    monkeypatch.setattr(vg, "results_file", lambda *parties: tmp_path.joinpath("results", *parties))
    (tmp_path / "results" / "td_step_pilot_r3").mkdir(parents=True)
    (tmp_path / "results" / "td_step_pilot_r3" / "lam0_p1_seed1.json").write_text("{}", encoding="utf-8")
    soumis = []

    def soumettre(cmd, journal):
        soumis.append(cmd)
        nom = cmd[cmd.index("--bras") + 1] if "--bras" in cmd else cmd[cmd.index("--ref") + 1]
        if nom == "lam09":
            open(journal, "w", encoding="utf-8").write(REFUS_QUOTA)
            return 85
        return {"lam0": 0, "lr0_reference": 89}[nom]

    def rho(pas, sd):
        raise FileNotFoundError("lam09 non rapatrié")
    bilan = vg.lancer_vague("abc", "v1", ["cellule:lam0:p1:1", "cellule:lam09:p1:1", "cellule:td0_app:p1:1",
                                          "reference:lr0_reference:1"], str(tmp_path / "journaux"),
                            soumettre=soumettre, rho=rho, pause_s=0)
    c = bilan["cellules"]
    assert c["lam0_p1_seed1"]["etat"] == "OK" and c["lam09_p1_seed1"] == {"etat": "REFUS_LOCAL", "rc": 85,
                                                                          "relancable": True}
    assert c["td0_app_p1_seed1"]["etat"] == "RHO_ABSENT" and c["lr0_reference_seed1"]["etat"] == "A_RAPATRIER"
    assert len(soumis) == 3 and not any("td0_app" in cmd for cmd in soumis)
    assert bilan["ok"] == 1 and bilan["n"] == 4
    assert all(cmd[cmd.index("--") - 10:cmd.index("--")] == vg.REGLAGES for cmd in soumis)
    assert json.load(open(tmp_path / "journaux" / "v1.json", encoding="utf-8"))["ok"] == 1
