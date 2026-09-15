"""P3.6 — bandeaux de PORTÉE posés APRÈS le verdict mesuré (jamais avant : E8).

Un bandeau est une AFFIRMATION : il se grave après la mesure, et chaque phrase cite la mesure et le
record qui la porte. Ces tests gèlent (a) la PRÉSENCE de chaque bandeau daté 2026-09-15, (b) les
littéraux que la clause de fermeture du backlog exige (`TD par tick` dans S2-010), (c) les chiffres
qui fondent chaque bandeau (dose ≈ 48 ; bassin 35,2 / 36,0 ; drains 2,40 → 1,30 et 11,0 / 15,0), et
(d) l'hygiène : un `corrected_by:` existant est CONSERVÉ, aucun bandeau n'est dupliqué, un bandeau
d'archive est COMPLÉTÉ et non écrasé, et tout record cité par un bandeau du 2026-09-15 EXISTE (un
bandeau qui cite une mesure absente serait la classe E8 commise dans l'outil qui la dénonce).
"""
import glob
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_EDR = os.path.join(_ROOT, "docs", "EDR")

S2_010 = os.path.join(_EDR, "S2-010_InWorld_Credit_Does_Not_Bootstrap_Perception_Even_Under_Curriculum.md")
S2_011 = os.path.join(_EDR, "S2-011_Cold_Credit_Fails_Even_On_Linear_Perception_Task_WarmStart_Confounded.md")
BLIND = os.path.join(_EDR, "S2-BLIND-CHAMPION_Stopped_At_Control_The_Ablation_Instrument_Has_An_8_Percent_RNG_Noise_Floor.md")
SUBJECT = os.path.join(_EDR, "S2-SUBJECT-VARIANCE_Stopped_At_Smoke_No_Positive_Control_Is_Constructible_By_Amplification.md")
SPEC = os.path.join(_ROOT, "docs", "roadmap", "SPECIFICATION_10ANS.md")

DATE = "2026-09-15"


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "frontmatter absent"
    return m.group(1)


def _head_banners(text):
    """Région entre la fin du frontmatter et le premier titre `## ` : c'est là que vivent les
    bandeaux « sous le frontmatter »."""
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    body = text[m.end():] if m else text
    i = body.find("\n## ")
    return body if i < 0 else body[:i]


def _section(text, heading_prefix):
    i = text.find("\n" + heading_prefix)
    assert i >= 0, f"section {heading_prefix!r} introuvable"
    rest = text[i + 1:]
    j = rest.find("\n## ", 1)
    return rest if j < 0 else rest[:j]


def _dated_blockquotes(text):
    """Toutes les lignes de blockquote appartenant à un bloc qui contient la date du bandeau."""
    blocks, cur = [], []
    for line in text.splitlines():
        if line.startswith(">"):
            cur.append(line)
        else:
            if cur:
                blocks.append("\n".join(cur))
            cur = []
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if DATE in b]


def _record_ids():
    ids = set()
    for p in glob.glob(os.path.join(_EDR, "*.md")):
        m = re.search(r"^id:\s*(\S+)", _read(p), re.M)
        if m:
            ids.add(m.group(1))
    return ids


# ----------------------------------------------------------------------------------------------
# (1) S2-010 — §Portée nomme le TD par tick et la dose ≈ 48
# ----------------------------------------------------------------------------------------------

def test_s2_010_portee_names_TD_par_tick_and_the_dose_of_48():
    t = _read(S2_010)
    sec = _section(t, "## Portée")
    assert "TD par tick" in sec, "littéral EXACT exigé par la clause de fermeture de P3.6"
    assert DATE in sec
    assert "48" in sec, "la dose reçue par les cohortes du record (≈ 48 mises à jour / agent)"
    assert "[[EDR-CALIB-LEARNER]]" in sec and "[[EDR-S2-CREDIT-RETENTION]]" in sec


def test_s2_010_head_banner_is_extended_not_duplicated_and_keeps_corrected_by():
    t = _read(S2_010)
    fm = _frontmatter(t)
    assert fm.count("corrected_by:") == 1 and "corrected_by: [EDR-CALIB-LEARNER]" in fm
    head = _head_banners(t)
    assert head.count("PORTÉE CORRIGÉE le 2026-09-14") == 1, "le bandeau du 09-14 reste, une seule fois"
    assert DATE in head, "le complément du 09-15 s'ajoute au bandeau existant"
    assert "[[EDR-S2-CREDIT-RETENTION]]" in head and "[[EDR-S2-REWARD-ABLATION]]" in head
    assert "36,0" in head and "8,0" in head, "l'érosion mesurée (36,0 → 8,0)"


# ----------------------------------------------------------------------------------------------
# (2) S2-011 — le « prochain pas » est exécuté et sa précondition est fausse
# ----------------------------------------------------------------------------------------------

def test_s2_011_next_step_is_marked_executed_with_the_measured_precondition():
    t = _read(S2_011)
    sec = _section(t, "## Prochain pas précis")
    assert DATE in sec
    assert "[[EDR-WARM-001]]" in sec and "[[EDR-WARM-003]]" in sec
    assert "35,2" in sec, "bassin DAgger publié par WARM-003 (35,2 / 200)"
    assert "36,0" in sec, "bassin gelé dans le harnais de S2-CREDIT-RETENTION"
    assert "[[EDR-S2-CREDIT-RETENTION]]" in sec


def test_s2_011_head_banner_is_extended_not_duplicated_and_keeps_corrected_by():
    t = _read(S2_011)
    fm = _frontmatter(t)
    assert fm.count("corrected_by:") == 1 and "corrected_by: [EDR-CALIB-LEARNER]" in fm
    head = _head_banners(t)
    assert head.count("PORTÉE CORRIGÉE le 2026-09-14") == 1
    assert DATE in head and "35,2" in head and "36,0" in head
    assert "[[EDR-S2-REWARD-ABLATION]]" in head


# ----------------------------------------------------------------------------------------------
# (3) S2-BLIND-CHAMPION / S2-SUBJECT-VARIANCE — corps NON apparié (E26, P1.7)
# ----------------------------------------------------------------------------------------------

def test_blind_champion_carries_the_E26_scope_banner_without_corrected_by():
    t = _read(BLIND)
    head = _head_banners(t)
    assert DATE in head and "E26" in head
    assert "2,40" in head and "1,30" in head, "make_blind : drain 2,40 → 1,30 (−46 %)"
    assert "assert_phenotype_matched" in head and "ballast_phenotype" in head
    assert "corrected_by" not in _frontmatter(t), "portée bornée, verdict scellé inchangé : bandeau seul"
    assert head.count("Ce record ne rapporte AUCUN verdict sur sa DV") == 1


def test_subject_variance_carries_the_E26_scope_banner_without_corrected_by():
    t = _read(SUBJECT)
    head = _head_banners(t)
    assert DATE in head and "E26" in head
    assert "11,0" in head and "15,0" in head, "drains des sujets câblés / amplifiés"
    assert "assert_phenotype_matched" in head and "ballast_phenotype" in head
    assert "corrected_by" not in _frontmatter(t)
    assert head.count("Aucune mesure de la DV scellée n'est rapportée") == 1


# ----------------------------------------------------------------------------------------------
# (4) SPECIFICATION_10ANS — bandeau d'archive COMPLÉTÉ, pas écrasé
# ----------------------------------------------------------------------------------------------

def test_specification_10ans_archive_banner_is_completed_not_overwritten():
    t = _read(SPEC)
    assert t.count("DOCUMENT ARCHIVÉ DE FAIT (2026-09-14)") == 1, "le bandeau d'archive reste"
    flat = re.sub(r"\n> ?", " ", t)          # un blockquote replié sur plusieurs lignes
    assert "1 instrument calibré sur 71" in flat, "le bandeau d'origine est CONSERVÉ (complété, pas écrasé)"
    head = t.split("\n## ", 1)[0]
    assert DATE in head
    for rid in ("[[EDR-CALIB-LEARNER]]", "[[EDR-S2-CREDIT-RETENTION]]", "[[EDR-S2-REWARD-ABLATION]]"):
        assert rid in head, rid
    assert "P1.6" in head, "la condition « §2 conditionnelle à P1.6 » est nommée et levée"


# ----------------------------------------------------------------------------------------------
# (5) Garde E8 : tout record cité par un bandeau du 2026-09-15 EXISTE
# ----------------------------------------------------------------------------------------------

def test_every_record_cited_by_a_dated_banner_exists():
    ids = _record_ids()
    assert "EDR-CALIB-LEARNER" in ids, "sanity : l'inventaire des ids lit bien les frontmatters"
    missing = {}
    for p in (S2_010, S2_011, BLIND, SUBJECT, SPEC):
        blocks = _dated_blockquotes(_read(p))
        assert blocks, f"{os.path.basename(p)} : aucun bandeau daté {DATE}"
        for b in blocks:
            for rid in re.findall(r"\[\[(EDR-[A-Za-z0-9-]+)\]\]", b):
                if rid not in ids:
                    missing.setdefault(os.path.basename(p), set()).add(rid)
    assert not missing, f"records cités mais absents : {missing}"
