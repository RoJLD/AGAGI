"""Garde EXÉCUTABLE de la classe E11 du registre des erreurs — « choix d'analyse post-hoc ».

E11 était, avec E13, la seule classe marquée **garde : AUCUNE** (backlog P3.1). Sa forme : arrêter un
seuil, une partition ou un critère APRÈS avoir vu les données, ce qui rend n'importe quel résultat
atteignable. La discipline manuelle (écrire la règle dans le record avant le run) a été tenue sur EVO-005
et EVO-006, mais rien ne l'ATTESTAIT — un lecteur ne peut pas distinguer une règle écrite avant d'une
règle écrite après, et l'auteur non plus, six mois plus tard.

`tools/preregister.py` scelle la règle ; ces tests vérifient que le sceau tient ses deux promesses, et
surtout qu'il **échoue** quand il le doit (une garde qui ne peut pas échouer est la classe E4).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.preregister import (  # noqa: E402
    preregister, verify, PreregistrationConflict, PreregistrationTampered)

_RULE = {"dv": "raw", "seuil": 0.5, "claim": "existence"}


def test_roundtrip_seals_and_returns_the_rule(tmp_path):
    """Cas nominal : ce qui est scellé est relu à l'identique."""
    preregister("X", _RULE, _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path)) == _RULE


def test_reregistering_the_same_rule_is_idempotent(tmp_path):
    """Ré-enregistrer À L'IDENTIQUE ne doit pas gêner (un script relancé ne doit pas exploser)."""
    preregister("X", _RULE, _dir=str(tmp_path))
    preregister("X", dict(_RULE), _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path)) == _RULE


def test_changing_the_rule_under_the_same_name_is_REFUSED(tmp_path):
    """⚠️ LE CŒUR DE LA GARDE. Changer la règle après coup sous le même nom doit être IMPOSSIBLE.
    Sinon la pré-inscription n'est qu'un commentaire : on la réécrirait en voyant les résultats."""
    preregister("X", _RULE, _dir=str(tmp_path))
    with pytest.raises(PreregistrationConflict):
        preregister("X", {**_RULE, "seuil": 0.3}, _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path))["seuil"] == 0.5, "la règle d'origine doit SURVIVRE à la tentative"


def test_hand_editing_the_file_is_DETECTED(tmp_path):
    """L'autre voie de contournement : éditer le JSON à la main. Le sceau doit la détecter."""
    p = preregister("X", _RULE, _dir=str(tmp_path))
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    payload["rule"]["seuil"] = 0.3                      # falsification silencieuse
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    with pytest.raises(PreregistrationTampered):
        verify("X", _dir=str(tmp_path))


def test_missing_preregistration_is_an_ERROR_not_a_default(tmp_path):
    """Absence de règle = échec BRUYANT. Un défaut silencieux ferait exactement ce que la classe décrit :
    laisser le critère se décider plus tard."""
    with pytest.raises(FileNotFoundError):
        verify("jamais-enregistre", _dir=str(tmp_path))


def test_the_repository_preregistrations_are_all_intact():
    """Cliquet sur le dépôt RÉEL : toute règle scellée sous `docs/preregistrations/` doit encore
    correspondre à son sceau. C'est ce test qui transforme la garde en régression permanente — si
    quelqu'un retouche une règle d'un record déjà gravé, la suite tombe."""
    from tools.preregister import _DIR
    if not os.path.isdir(_DIR):
        pytest.skip("aucune pré-inscription dans ce dépôt")
    names = [f[:-5] for f in sorted(os.listdir(_DIR)) if f.endswith(".json")]
    assert names, "le répertoire existe mais est VIDE — vérification creuse (classe E4)"
    for n in names:
        verify(n)                                        # lève si retouché


# --- E11 occurrence 3 (2026-08-04) : les branches doivent couvrir le CONTINUUM ------------------------
# Née d'un ECHEC de cette garde meme. EDR-EVO-019 avait scelle « >= 3/12 » et « 0/12 » ; le resultat est
# tombe a **1/12**, dans le TROU entre les deux. Le sceau protegeait le SEUIL, pas l'EXHAUSTIVITE.
from tools.preregister import IncompleteDiscrimination  # noqa: E402

_GAPPED = {"dv": "taux", "discrimination": {">= 3/12": "confirme", "0/12": "refute"}}


def test_gapped_discrimination_is_REFUSED(tmp_path):
    """⚠️ LE CŒUR DE LA NOUVELLE GARDE. Des branches « >= 3 » et « 0 » laissent 1 et 2 sans lecture —
    exactement la latitude post-hoc que la pré-inscription existe pour supprimer."""
    with pytest.raises(IncompleteDiscrimination):
        preregister("gap", _GAPPED, _dir=str(tmp_path))


def test_catchall_branch_makes_it_acceptable(tmp_path):
    rule = {**_GAPPED, "discrimination": {**_GAPPED["discrimination"],
                                          "sinon (1 ou 2 seeds)": "observation isolee, non elevee"}}
    preregister("ok", rule, _dir=str(tmp_path))
    assert verify("ok", _dir=str(tmp_path))["discrimination"]


def test_continuous_reading_rule_also_accepted(tmp_path):
    """L'autre forme valable : decrire la lecture sur TOUTE l'echelle plutot que par branches."""
    rule = {**_GAPPED, "regle_de_lecture_continue": "verdict = f(taux) : Fisher vs baseline, p<0.05 requis"}
    preregister("cont", rule, _dir=str(tmp_path))
    assert verify("cont", _dir=str(tmp_path))


def test_rule_without_discrimination_is_untouched(tmp_path):
    """La garde ne doit pas gener une regle qui ne declare aucune branche (pas de faux positif)."""
    preregister("nodisc", {"dv": "taux", "seuil": 0.5}, _dir=str(tmp_path))
    assert verify("nodisc", _dir=str(tmp_path))["seuil"] == 0.5


# ==================================================================================================
# P2.68 (2026-09-15) -- la PROVENANCE d'un run (git_sha / dirty / seal de la regle) a UN seul site :
# `tools.preregister.provenance` ; `stamp` tamponne un dict de resultats repris entre sessions. 14
# runners scelles sur 15 n'ecrivaient ni l'un ni l'autre : leur regle etait scellee par hash, leur code
# ne l'etait pas. Aucune valeur n'est inventee : sans git, `git_sha` et `dirty` valent None.
# ==================================================================================================
from tools.preregister import provenance, stamp  # noqa: E402


def test_provenance_reads_HEAD_and_the_seal_of_the_named_rule(tmp_path):
    import subprocess
    p = preregister("PROV-X", _RULE, _dir=str(tmp_path))
    prov = provenance("PROV-X", _dir=str(tmp_path))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert prov["git_sha"] == head and isinstance(prov["dirty"], bool)
    assert prov["rule"] == "PROV-X" and prov["seal"] == json.load(open(p, encoding="utf-8"))["seal"]


def test_provenance_without_git_publishes_None_never_a_value(tmp_path):
    """Un depot sans git : la provenance est ABSENTE et le dit -- forme (a) de CLAUDE.md, pas de valeur
    de fond fabriquee."""
    prov = provenance(_root=str(tmp_path))
    assert prov["git_sha"] is None and prov["dirty"] is None and "error" in prov


def test_provenance_of_an_unsealed_rule_says_seal_None(tmp_path):
    prov = provenance("JAMAIS-SCELLEE", _dir=str(tmp_path))
    assert prov["rule"] == "JAMAIS-SCELLEE" and prov["seal"] is None


def test_stamp_appends_once_per_distinct_provenance_and_keeps_cells_intact(tmp_path):
    preregister("PROV-Y", _RULE, _dir=str(tmp_path))
    db = {"lr=0.002|ep=100|seed=0": {"lang_i": 0.5}}
    stamp(db, "PROV-Y", _dir=str(tmp_path))
    stamp(db, "PROV-Y", _dir=str(tmp_path))
    assert len(db["_provenance"]) == 1 and db["lr=0.002|ep=100|seed=0"] == {"lang_i": 0.5}
    db["_provenance"][-1]["git_sha"] = "autre-commit"           # reprise apres un commit
    stamp(db, "PROV-Y", _dir=str(tmp_path))
    assert len(db["_provenance"]) == 2 and db["_provenance"][0]["git_sha"] == "autre-commit"


# ==================================================================================================
# Tâche 5 (spec PM 2026-09-16 §2.3) : `reviewed_by` -- exigé à l'ENVELOPPE de toute NOUVELLE
# pré-inscription qui DÉCLARE un coût (clés cout/budget_s/garde_cout/plafond/cout_scelle). Décision du
# contrôleur : pas de seuil numérique deviné -- aucun champ de coût homogène n'existe dans le dépôt.
#
# ⚠️ Revue du contrôleur (post-Tâche 5) : `not reviewed_by` était satisfait par N'IMPORTE QUELLE chaîne
# non vide -- `reviewed_by="x"` scellait. Corrigé : `reviewed_by` doit avoir la FORME
# `docs/reviews/AAAA-MM-JJ-slug.md` (jamais l'existence -- une règle peut être scellée depuis un cwd où
# `docs/reviews/` n'est pas visible).
# ==================================================================================================

def test_une_NOUVELLE_regle_qui_declare_un_cout_exige_reviewed_by(tmp_path):
    from tools import preregister as PR
    rule = {"question": "q", "cout": "~40 min sous bail", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    with pytest.raises(PR.ReviewRequired, match="reviewed_by"):
        PR.preregister("T-COUT", rule, _dir=str(tmp_path))
    p = PR.preregister("T-COUT", rule, _dir=str(tmp_path), reviewed_by="docs/reviews/2026-09-17-t-cout.md")
    import json
    env = json.load(open(p, encoding="utf-8"))
    assert env["reviewed_by"] == "docs/reviews/2026-09-17-t-cout.md" and set(env) == {"name", "rule", "seal", "reviewed_by"}
    assert PR.verify("T-COUT", _dir=str(tmp_path)) == rule                      # le sceau ne porte que rule


def test_une_regle_SANS_cout_declare_ne_l_exige_pas_et_une_existante_se_rescelle_sans(tmp_path):
    from tools import preregister as PR
    rule = {"question": "q", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    PR.preregister("T-LIBRE", rule, _dir=str(tmp_path))                          # pas de coût : pas de revue exigée
    couteuse = {"question": "q", "budget_s": 3600, "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    PR.preregister("T-EXIST", couteuse, _dir=str(tmp_path), reviewed_by="docs/reviews/2026-09-23-t-exist.md")
    PR.preregister("T-EXIST", couteuse, _dir=str(tmp_path))                     # identique : idempotent, sans reviewed_by
    assert PR.declare_un_cout(couteuse) is True and PR.declare_un_cout(rule) is False


def test_reviewed_by_with_INVALID_FORM_is_REFUSED(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ nommé par la revue du contrôleur : `reviewed_by="x"` n'a pas la forme
    docs/reviews/AAAA-MM-JJ-slug.md -- une chaîne quelconque ne doit plus suffire."""
    from tools import preregister as PR
    rule = {"question": "q", "cout": "~40 min sous bail", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    with pytest.raises(PR.ReviewRequired, match="forme"):
        PR.preregister("T-COUT-BADFORM", rule, _dir=str(tmp_path), reviewed_by="x")


def test_reviewed_by_with_VALID_FORM_seals_EVEN_IF_the_file_does_not_exist(tmp_path):
    """SPÉCIFICITÉ (no-op apparié au précédent) : `preregister` ne vérifie que la FORME, jamais
    l'EXISTENCE -- le fichier de revue n'est PAS créé sous `tmp_path`, le scellement doit réussir quand
    même (une règle peut être scellée depuis un cwd où docs/reviews/ n'est pas visible)."""
    from tools import preregister as PR
    rule = {"question": "q", "cout": "~40 min sous bail", "regle_de_lecture_continue": "ORDRE IMPOSE : INCOMPLET, AUTRE."}
    p = PR.preregister("T-COUT-OKFORM", rule, _dir=str(tmp_path), reviewed_by="docs/reviews/2026-09-23-okform.md")
    import json
    assert json.load(open(p, encoding="utf-8"))["reviewed_by"] == "docs/reviews/2026-09-23-okform.md"


def test_every_sealed_runner_carries_the_provenance_stamp():
    """TEMOIN de P2.68 : tout runner que la porte 11 reconnait comme SCELLE (`verify` importe et
    appele -- analyse AST) appelle `provenance(` ou `stamp(`. La liste des exceptions est VIDE et doit
    le rester : un runner scelle sans tampon ne sait pas dire quel code a produit sa mesure."""
    import ast as _ast
    from tools.check_control_family import scan_runners
    sans = []
    for path, etat in scan_runners().items():
        if not etat["scelle"]:
            continue
        src = open(path, encoding="utf-8").read()
        appels = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                  for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Call)}
        if not ({"provenance", "stamp", "_git_provenance"} & appels):
            sans.append(path)
    assert sans == [], f"runners scelles SANS tampon de provenance : {sans}"
