# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. Les `xfail(strict=True)` restants sont des DEFAUTS REELS ouverts ;
# les blocs NON-REGRESSION sont d'anciens xfail dont le defaut a ete corrige.
# -*- coding: utf-8 -*-
"""INJECTION A DOSE CONNUE de `tools/dream_causal_probe.py::run_founder_matched` (voie inj6).

`run_founder_matched` est un ORCHESTRATEUR : il ne simule pas, il APPELLE `run_era_organ` deux fois
par seed (bras `off` / bras `FORCE_DREAM=k`) et AGREGE les mesures en affirmation (ratio de medianes,
test de signe, Wilcoxon signe), puis PERSISTE le tout. Sa garde d'ARGUMENTS est deja calibree
(`tests/sandbox/test_instrument_calibration.py:93` -- "empty-cohort:raises", "guard-before-world").
Ce qui n'etait calibre par RIEN, c'est la couche « mesures -> affirmation » : appariement seed-a-seed,
unite de replication, cablage du regime, et les grandeurs PUBLIEES. C'est exactement la que le record
EDR-DREAM-001 va chercher ses chiffres (il REFUTE le `CAUSE_NUISIBLE` d'EDR-095).

SEAM : `run_era_organ` est importe AU NIVEAU MODULE (`tools/dream_causal_probe.py:16`,
`from tools.dreaming_probe import run_era_organ`) -> l'attribut a monkeypatcher est
`tools.dream_causal_probe.run_era_organ`. Aucun monde n'est construit ; le fichier entier coute
moins d'une seconde de calcul.

PARTICULARITE DE CET ORCHESTRATEUR, et pourquoi le seam suffit a tester le cablage : les DEUX bras
appellent `run_era_organ` avec des arguments RIGOUREUSEMENT IDENTIQUES. La seule chose qui les
distingue est l'etat global de classe `MambaBatchModel.FORCE_DREAM`, pose avant l'appel. La mesure
factice DISPATCHE donc sur cette variable globale : si le regime n'arrivait pas jusqu'a la mesure,
l'injection n'aurait aucun moyen de rendre la bonne cellule -- elle leve.

Les `xfail(strict=True)` sont des DEFAUTS REELS de `tools/dream_causal_probe.py`, NON corriges ici
(fichier hors perimetre de cette voie). Ils tomberont d'eux-memes le jour ou le defaut sera corrige.
"""
import json
import statistics

import logging
import pytest

from src.agents.mamba_agent import MambaBatchModel
from src.seed_ai.s2_stats import wilcoxon_signed_rank
from tools.curriculum_transfer import _sign_test_p


# ======================================================================================================
# Doses connues et injection
# ======================================================================================================

def _inj6_agent(age, founder):
    """UN agent tel que `run_era_organ` le rend REELLEMENT (`tools/dreaming_probe.py:127-132`) :
    TOUTES les cles, pas seulement les deux que `run_founder_matched` lit aujourd'hui. Si
    l'orchestrateur se mettait a lire `total_dreams`, `has_organ`, `altars_solved`, `spears_crafted`
    ou `preys_eaten`, le test ne mentirait pas : la cle existe et porte une valeur explicite."""
    return {"age": float(age), "total_dreams": 0, "has_organ": True, "founder": bool(founder),
            "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}


def _inj6_cellule(ages_fondateurs, ages_nes_tard=()):
    """Cellule factice a DOSE CONNUE : la cohorte FONDATRICE (marquee a t=0 dans `run_era_organ`) et
    les agents NES PENDANT l'ere. La distinction est le sujet meme de la fonction testee : le reve
    force multiplie `n_lived` par ~13-16, donc la mediane sur TOUS les agents compare deux
    populations de compositions incomparables (classe E15), la mediane sur les fondateurs non."""
    return ([_inj6_agent(a, True) for a in ages_fondateurs]
            + [_inj6_agent(a, False) for a in ages_nes_tard])


def _inj6_injecte(monkeypatch, table, journal=None, explose_sur=None):
    """Remplace `tools.dream_causal_probe.run_era_organ` par une mesure a dose imposee.

    `table` : {(seed, "off"|"on"): cellule}. Le bras est deduit de `MambaBatchModel.FORCE_DREAM` tel
    qu'il est POSE AU MOMENT DE L'APPEL -- c'est la seule chose qui distingue les deux bras dans le
    vrai code, donc le seul cablage possible. Un KeyError dit tout de suite qu'un seed a ete croise.
    `explose_sur` : (seed, bras) sur lequel la mesure LEVE -- sert a prouver que le `finally`
    restaure l'etat global meme en cas d'echec (classe E5, etat global partage)."""
    import tools.dream_causal_probe as D

    if not getattr(D.run_era_organ, "_inj6", False):
        assert getattr(D.run_era_organ, "__module__", None) == "tools.dreaming_probe", (
            "le SEAM a bouge : `run_era_organ` n'est plus l'attribut de module importe en tete de "
            "tools/dream_causal_probe.py -- l'injection ne mesure plus l'orchestrateur reel")

    def _fake_run_era_organ(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks,
                            shared_db):
        dose = MambaBatchModel.FORCE_DREAM
        if dose == "off":
            bras = "off"
        elif isinstance(dose, int) and not isinstance(dose, bool):
            bras = "on"
        else:
            raise AssertionError(
                f"FORCE_DREAM={dose!r} au moment de la MESURE : le regime demande n'est pas arrive "
                "jusqu'a l'ere. Les deux bras recoivent des arguments identiques -- sans cette "
                "variable de classe, les deux bras sont le MEME calcul.")
        if journal is not None:
            journal.append({"seed": seed, "bras": bras, "dose": dose, "target": target,
                            "organ_fraction": organ_fraction, "metab": metab, "payoff": payoff,
                            "num_agents": num_agents, "max_ticks": max_ticks,
                            "shared_db": shared_db})
        if explose_sur is not None and (int(seed), bras) == explose_sur:
            raise RuntimeError("mesure en echec (injectee)")
        return table[(int(seed), bras)]

    _fake_run_era_organ._inj6 = True
    monkeypatch.setattr(D, "run_era_organ", _fake_run_era_organ)
    return D


@pytest.fixture(autouse=True)
def _inj6_etat_global_propre():
    """`FORCE_DREAM` est un attribut de CLASSE partage par tout le process : un test qui le laisse
    pose contaminerait les suivants (classe E5). On le remet a None des deux cotes du test."""
    MambaBatchModel.FORCE_DREAM = None
    yield
    MambaBatchModel.FORCE_DREAM = None


K_SEEDS = 12                                     # unite de replication = le SEED (plancher S2 = 12)
_SEEDS = list(range(K_SEEDS))

# Formes closes reutilisees. Test de signe bilateral exact a 12/12 favorables :
#   p = 2 * C(12,12) / 2^12 = 2/4096.
_SIGN_P_12_SUR_12 = 2.0 / 2 ** 12                                  # 0.00048828125
# Wilcoxon signe, 12 differences NON NULLES de meme signe et de meme magnitude : tous les rangs
# valent 6.5, W+ = 78 (ou 0), mean = 12*13/4 = 39, var = 12*13*25/24 = 162.5, cc = 0.5,
# z = 38.5 / sqrt(162.5) = 3.0202... -> p = 2*(1-Phi(z)).
_WIL_P_12_UNANIME = 0.0025261742685023236


def _table_uniforme(cellule_off, cellule_on, seeds=_SEEDS):
    return {(s, "off"): cellule_off for s in seeds} | {(s, "on"): cellule_on for s in seeds}


# --- CRITERE DE REFUS, et sa CALIBRATION ------------------------------------------------------
# Sur une dose ou AUCUNE paire n'est mesurable, l'instrument a deux issues admises : LEVER, ou
# rendre un INDETERMINE. Ce qui lui est interdit, c'est de PUBLIER UN NOMBRE la ou rien n'a ete
# mesure -- peu importe lequel : `0.0` (effondrement), `2e10` (denominateur absent), `1.0` (aucun
# effet) ou une p-valeur significative sont tous des affirmations de FOND tirees du vide.
# Le critere porte donc sur la NATURE de ce qui est publie, pas sur une valeur particuliere : il
# resiste au defaut qui change simplement de colonne (mesure : boucher le `ratio` seul laissait
# `sign_p = 0.00048828125` et `n_favorable = 12` intacts).
# ⚠️ Un critere est un instrument : il est calibre plus bas sur des reponses connues, dans les DEUX
# sens (`test_CONTRE_EXEMPLE_*`) -- sans quoi « le refus passe » ne prouverait rien (classe E1).
_GRANDEURS_D_AFFIRMATION = ("ratio", "sign_p", "wilcoxon_p", "med_off", "med_on", "n_favorable")


def _inj6_griefs_sans_paire_mesurable(bloc):
    """Griefs d'un bloc publie sur une dose ou AUCUNE paire n'est mesurable. Liste VIDE = rien
    n'est affirme. Les COMPTES (`n`, `n_effectif`, `n_ex_aequo`, `n_non_mesurables`) ne sont pas
    des affirmations : ils decrivent le dispositif et doivent, eux, rester lisibles."""
    griefs = []
    for nom in _GRANDEURS_D_AFFIRMATION:
        v = bloc.get(nom)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            griefs.append(f"{nom}={v!r} publie comme un NOMBRE sans qu'aucune paire soit mesurable")
    return griefs


# ======================================================================================================
# 1. La reponse connue centrale : la STATISTIQUE DE POPULATION et la COHORTE FONDATRICE se
#    contredisent, et c'est la raison d'etre de la fonction (EDR-095 refute par EDR-DREAM-001).
# ======================================================================================================

def test_run_founder_matched_READS_the_founder_dose_and_EXPOSES_the_confounded_population_stat(
        monkeypatch):
    """Dose imposee, identique sur les 12 seeds, choisie pour que les DEUX lectures soient
    significatives ET DE SIGNE OPPOSE -- exactement le motif mesure dans le monde reel :

      bras off : 5 fondateurs a 10 ticks, aucun ne-tard        -> n_lived  5, med_all 10, med_fond 10
      bras on  : 5 fondateurs a 20 ticks + 60 nes-tard a 1 tick-> n_lived 65, med_all  1, med_fond 20

    Formes closes attendues :
      med_founder : 20/10 = 2.0,  12/12 favorables, sign_p = 2/2^12, wilcoxon = 0.00252617
      med_all     :  1/10 = 0.1,   0/12 favorables, MEME p (le test est bilateral) -> la meme dose
                    rend `CAUSE_BENEFIQUE` sur les fondateurs et `CAUSE_NUISIBLE` sur la population
      n_lived     : 65/5 = 13.0  -- le facteur x13-16 documente par E15, qui est la CAUSE du confond

    Si l'orchestrateur lisait `med_all` la ou il annonce `med_founder` (ou l'inverse), le signe du
    verdict PUBLIE s'inverserait sans qu'aucune autre grandeur ne bouge. C'est ce que ce test
    interdit, et c'est la seule chose qui separe EDR-095 d'EDR-DREAM-001."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5),
        cellule_on=_inj6_cellule([20.0] * 5, [1.0] * 60)))

    out = D.run_founder_matched(_SEEDS, num_agents=25, max_ticks=80, k=8)

    fond = out["med_founder"]
    assert fond["med_off"] == 10.0 and fond["med_on"] == 20.0, fond
    assert fond["ratio"] == pytest.approx(2.0), fond
    assert fond["n_favorable"] == 12 and fond["n"] == 12, fond
    assert fond["sign_p"] == pytest.approx(_SIGN_P_12_SUR_12), fond
    assert fond["wilcoxon_p"] == pytest.approx(_WIL_P_12_UNANIME), fond

    tous = out["med_all"]
    assert tous["med_off"] == 10.0 and tous["med_on"] == 1.0, tous
    assert tous["ratio"] == pytest.approx(0.1), tous
    assert tous["n_favorable"] == 0 and tous["n"] == 12, tous
    assert tous["sign_p"] == pytest.approx(_SIGN_P_12_SUR_12), tous

    vivants = out["n_lived"]
    assert vivants["med_off"] == 5.0 and vivants["med_on"] == 65.0, vivants
    assert vivants["ratio"] == pytest.approx(13.0), vivants

    # Le confond E15 doit etre LISIBLE dans l'artefact : les deux lectures publiees sont de signe
    # oppose sur la MEME dose. Un instrument qui ne publierait qu'une des deux ne permettrait pas de
    # trancher entre « le reve nuit » et « le reve deplace la composition de la population ».
    assert fond["ratio"] > 1.0 > tous["ratio"], (fond["ratio"], tous["ratio"])


# ======================================================================================================
# 2. LES DEUX ISSUES (classe E1). Un instrument qui ne saurait rendre que « le reve aide » ne
#    prouverait rien : on exige le NO-OP EXACT et le signe INVERSE sur la meme machinerie.
# ======================================================================================================

def test_run_founder_matched_CAN_say_NOTHING_and_CAN_say_HARMFUL(monkeypatch):
    """Deux doses appariees sur la meme structure de cellules.

    (a) NO-OP EXACT -- les deux bras a 5 fondateurs de 10 ticks. Aucune difference n'existe, donc
        rien ne doit etre affirme : ratio 1.0, 0 favorable, sign_p 1.0 (le test de signe retire les
        ex aequo, il ne reste AUCUNE paire informative), wilcoxon 1.0 (n=0 apres retrait des zeros).
        C'est le controle de SPECIFICITE : sans lui, tout ce fichier ne prouverait que la capacite a
        crier.
    (b) SIGNE INVERSE -- off 20 ticks, on 10 ticks. Le reve NUIT : ratio 0.5, 0/12 favorables, et le
        MEME p qu'au cas benefique (0.00048828125), le test de signe etant bilateral.

    Les deux issues sont donc atteignables, et c'est la MEME dose retournee qui les separe."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5), cellule_on=_inj6_cellule([10.0] * 5)))
    rien = D.run_founder_matched(_SEEDS)["med_founder"]
    assert rien["med_off"] == 10.0 and rien["med_on"] == 10.0, rien
    assert rien["ratio"] == pytest.approx(1.0), rien
    assert rien["n_favorable"] == 0, rien
    assert rien["sign_p"] == 1.0 and rien["wilcoxon_p"] == 1.0, rien

    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([20.0] * 5), cellule_on=_inj6_cellule([10.0] * 5)))
    nuit = D.run_founder_matched(_SEEDS)["med_founder"]
    assert nuit["med_off"] == 20.0 and nuit["med_on"] == 10.0, nuit
    assert nuit["ratio"] == pytest.approx(0.5), nuit
    assert nuit["n_favorable"] == 0 and nuit["n"] == 12, nuit
    assert nuit["sign_p"] == pytest.approx(_SIGN_P_12_SUR_12), nuit
    assert nuit["wilcoxon_p"] == pytest.approx(_WIL_P_12_UNANIME), nuit


# ======================================================================================================
# 3. APPARIEMENT et UNITE DE REPLICATION.
# ======================================================================================================

def test_run_founder_matched_PAIRS_each_arm_with_ITS_OWN_seed_and_replicates_on_SEEDS(monkeypatch):
    """Chaque seed recoit une SIGNATURE unique (off = 10+s fondateurs a 10+s ticks ; on = 100+s), donc
    tout croisement seed-a-seed, tout decalage de ligne et toute reutilisation d'une cellule pour un
    autre seed est VISIBLE ligne par ligne. Un appariement casse ne changerait pourtant ni le nombre
    de lignes ni l'allure des p : c'est le defaut le plus silencieux d'un design apparie.

    Unite de REPLICATION (classe E7) : 12 seeds x 5..16 agents = 132 agents mesures, mais le n publie
    doit valoir 12, PAS 132. Les agents d'un meme seed partagent monde, init et regime -- ce ne sont
    pas des replicats. Un instrument qui compterait les agents rendrait ici sign_p = 2/2^132.

    Le JOURNAL verifie la meme chose du cote des APPELS : les 2 bras d'une ligne portent le meme
    seed, dans l'ordre (off, on), et il y a exactement 2 appels par seed -- ni un bras rejoue, ni un
    seed mesure une seule fois puis reutilise pour les deux bras."""
    table, attendu = {}, []
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([10.0 + s] * (5 + s))
        table[(s, "on")] = _inj6_cellule([100.0 + s] * (5 + s))
        attendu.append({"seed": s,
                        "off_n_lived": 5 + s, "off_med_all": 10.0 + s,
                        "off_med_founder": 10.0 + s, "off_n_founder": 5 + s,
                        "on_n_lived": 5 + s, "on_med_all": 100.0 + s,
                        "on_med_founder": 100.0 + s, "on_n_founder": 5 + s})
    journal = []
    D = _inj6_injecte(monkeypatch, table, journal=journal)
    out = D.run_founder_matched(_SEEDS)

    assert out["rows"] == attendu, [ligne for ligne, att in zip(out["rows"], attendu)
                                    if ligne != att]

    fond = out["med_founder"]
    assert fond["n"] == K_SEEDS, (
        f"n publie = {fond['n']} : l'unite de replication doit etre le SEED (12), pas l'agent "
        f"({sum(5 + s for s in _SEEDS)} agents mesures) -- classe E7")
    assert fond["med_off"] == pytest.approx(statistics.median([10.0 + s for s in _SEEDS]))
    assert fond["med_on"] == pytest.approx(statistics.median([100.0 + s for s in _SEEDS]))
    assert fond["n_favorable"] == 12, fond

    assert [j["seed"] for j in journal] == [s for s in _SEEDS for _ in range(2)], journal
    assert [j["bras"] for j in journal] == ["off", "on"] * K_SEEDS, journal


# ======================================================================================================
# 4. CABLAGE DU REGIME et HYGIENE DE L'ETAT GLOBAL.
# ======================================================================================================

def test_run_founder_matched_WIRES_the_requested_regime_into_EVERY_call(monkeypatch):
    """Reponse connue : k=3 (et non le defaut 8), cible `famine`, organ_fraction 0.5, metab 0.9,
    payoff 2.5, 7 agents, 33 ticks, 2 seeds -> 4 appels qui doivent TOUS porter ce regime, et dont
    les doses doivent etre exactement ["off", 3, "off", 3].

    Ce que ce test attrape et qu'aucun ratio ne montrerait : un bras `on` lance a la profondeur par
    DEFAUT (8) au lieu du k demande -- la courbe dose-reponse deviendrait plate sans qu'aucune
    grandeur publiee ne change d'allure. Et `dose` doit etre un `int` VRAI : `_resolve_dreaming`
    (`src/agents/mamba_agent.py:286`) exclut explicitement les booleens du cas « profondeur K », donc
    un `True` y basculerait silencieusement vers l'auto-selection historique.

    On verifie aussi que les DEUX bras recoivent le meme regime (sinon la comparaison n'est plus
    within-subject : elle opposerait deux mondes differents) et que `shared_db` reste None."""
    table = {(s, b): _inj6_cellule([10.0] * 4) for s in (0, 1) for b in ("off", "on")}
    journal = []
    D = _inj6_injecte(monkeypatch, table, journal=journal)

    D.run_founder_matched([0, 1], target="famine", num_agents=7, max_ticks=33, k=3,
                          organ_fraction=0.5, metab=0.9, payoff=2.5)

    assert len(journal) == 4, journal
    assert [j["dose"] for j in journal] == ["off", 3, "off", 3], [j["dose"] for j in journal]
    for j in journal:
        if j["bras"] == "on":
            assert type(j["dose"]) is int, (
                f"dose {j['dose']!r} de type {type(j['dose'])} : `_resolve_dreaming` exclut les "
                "booleens du cas profondeur-K et retomberait sur l'auto-selection")
    assert {j["target"] for j in journal} == {"famine"}
    assert {j["organ_fraction"] for j in journal} == {0.5}
    assert {j["metab"] for j in journal} == {0.9}
    assert {j["payoff"] for j in journal} == {2.5}
    assert {j["num_agents"] for j in journal} == {7}
    assert {j["max_ticks"] for j in journal} == {33}
    assert {j["shared_db"] for j in journal} == {None}


def test_run_founder_matched_RESTORES_the_global_FORCE_DREAM_even_when_a_measure_RAISES(monkeypatch):
    """`FORCE_DREAM` est un attribut de CLASSE : laisse pose, il contamine toute mesure ulterieure du
    process -- y compris celle d'une AUTRE sonde (classe E5, etat global partage). Deux epreuves :

      (a) chemin nominal : on pose une SENTINELLE avant l'appel ; apres, l'attribut doit valoir None
          (donc le `finally` a bien ecrase la sentinelle -- l'assertion n'est pas vide) ;
      (b) chemin d'ECHEC : la mesure du bras `on` du seed 0 leve. L'exception doit remonter (elle ne
          doit surtout pas etre avalee : un bras muet donnerait une demi-mesure), ET l'attribut doit
          etre revenu a None malgre l'echec.

    Sans (b), la restauration ne serait prouvee que sur le chemin ou elle est facile."""
    table = {(s, b): _inj6_cellule([10.0] * 4) for s in (0, 1) for b in ("off", "on")}

    D = _inj6_injecte(monkeypatch, table)
    MambaBatchModel.FORCE_DREAM = "SENTINELLE-INJ6"
    D.run_founder_matched([0, 1], k=4)
    assert MambaBatchModel.FORCE_DREAM is None, MambaBatchModel.FORCE_DREAM

    D = _inj6_injecte(monkeypatch, table, explose_sur=(0, "on"))
    MambaBatchModel.FORCE_DREAM = "SENTINELLE-INJ6"
    with pytest.raises(RuntimeError, match="mesure en echec"):
        D.run_founder_matched([0, 1], k=4)
    assert MambaBatchModel.FORCE_DREAM is None, (
        "FORCE_DREAM reste pose apres une mesure en echec : toute sonde lancee ensuite dans le meme "
        "process mesurerait un regime force sans le savoir")


# ======================================================================================================
# 5. PERSISTANCE : ce qui est RENDU doit etre ce qui est ARCHIVE.
# ======================================================================================================

def test_run_founder_matched_PERSISTS_EXACTLY_what_it_returns(monkeypatch, tmp_path):
    """La docstring de la fonction fait de la persistance une raison d'etre (« sans artefact, des
    chiffres publies ne sont re-derivables d'aucun fichier »). On exige donc l'egalite STRICTE entre
    l'objet rendu et le JSON ecrit -- un rapport enrichi APRES le dump serait publie sans etre
    archive, et le defaut serait invisible a la lecture des chiffres.

    La dose est celle du cas central (ratio fondateurs = 2.0) : l'artefact doit porter cette valeur,
    pas seulement une structure de bonne forme. On verifie aussi que le sous-repertoire est CREE."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5),
        cellule_on=_inj6_cellule([20.0] * 5, [1.0] * 60)))

    chemin = tmp_path / "sous" / "repertoire" / "inj6.json"
    out = D.run_founder_matched(_SEEDS, num_agents=25, max_ticks=80, k=8, out_path=str(chemin))

    assert chemin.exists(), chemin
    archive = json.loads(chemin.read_text(encoding="utf-8"))
    assert archive == out, "l'artefact archive differe de l'objet rendu"
    assert archive["med_founder"]["ratio"] == pytest.approx(2.0), archive["med_founder"]
    assert archive["config"] == {"target": "stoneage", "seeds": _SEEDS, "k": 8,
                                 "num_agents": 25, "max_ticks": 80}, archive["config"]


# ======================================================================================================
# 6. DEFAUTS REELS exposes ici, puis CORRIGES le meme jour dans `tools/dream_causal_probe.py`.
#    Regle du depot : une entree ABSENTE ou VIDE ne doit JAMAIS produire une affirmation de FOND.
#
#    ⚠️ LES DEUX `xfail(strict=True)` ONT ETE RETIRES le 2026-09-08 par le 2e refuteur, et il faut
#    dire pourquoi : le correctif avait ete livre SANS eux, donc les deux tests XPASSaient et la
#    suite etait ROUGE (`2 failed, 15 passed`). Un xfail(strict) qui passe n'est pas un detail de
#    forme -- c'est le mecanisme meme par lequel le depot distingue « defaut ouvert » de « defaut
#    ferme », et le laisser en place apres correction rend la suite illisible dans les DEUX sens :
#    le rouge cesse de signaler une regression, et le defaut corrige continue d'etre annonce comme
#    ouvert dans la raison du marqueur. Les deux tests deviennent donc des NON-REGRESSIONS, au meme
#    titre que les quatre qui suivaient deja. Leur capacite a ENCORE echouer est prouvee par
#    mutation : remettre `... if fond else 0.0` (l'etat d'avant le correctif) fait rougir le
#    premier ; remettre `ratio = med_n / max(med_o, 1e-9)` fait rougir le second.
# ======================================================================================================

# NON-REGRESSION (defaut expose ici le 2026-09-08, CORRIGE le meme jour).
# Etat d'AVANT : `tools/dream_causal_probe.py` fabriquait `med_founder = 0.0` quand la cohorte
# mesuree etait VIDE (`... if fond else 0.0`), et `_pair` traitait ce 0.0 comme une MESURE. Dose :
# bras `on` sans AUCUN agent sur les 12 seeds. Publie : med_founder {med_off 10.0, med_on 0.0,
# ratio 0.0, n_favorable 0, n 12, sign_p 0.00048828125, wilcoxon_p 0.00252617} -- soit « le reve
# force ANNULE la survie des fondateurs, p<0.001 » prononce sur un bras ou RIEN n'a ete mesure.
# L'information existait pourtant dans l'artefact (`on_n_lived = 0` sur chaque ligne) : l'instrument
# SAVAIT et ne le disait pas.
def test_run_founder_matched_REFUSES_to_publish_a_collapse_measured_on_an_EMPTY_arm(monkeypatch):
    """Reponse connue : le bras `on` ne rend AUCUN agent sur aucun seed. Il n'y a rien a comparer."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5), cellule_on=[]))
    out = D.run_founder_matched(_SEEDS)
    mf = out["med_founder"]
    assert not (mf["ratio"] == 0.0 and mf["sign_p"] < 0.05), (
        f"effondrement SIGNIFICATIF publie depuis un bras vide : {mf} ; "
        f"on_n_lived par seed = {[r['on_n_lived'] for r in out['rows']]}")


# NON-REGRESSION (defaut expose ici le 2026-09-08, CORRIGE le meme jour).
# MEME DEFAUT, autre porte d'entree et signe OPPOSE : quand c'est le bras `off` qui est vide,
# `_pair` divisait par `max(0.0, 1e-9)` et publiait ratio = 2e10. Un instrument qui rend
# 20 000 000 000 comme rapport de medianes ne rapporte pas un effet, il rapporte une absence de
# denominateur. Issues admises : refus explicite, ou INDETERMINE.
def test_run_founder_matched_REFUSES_to_publish_an_astronomical_ratio_from_an_absent_denominator(
        monkeypatch):
    """Reponse connue : bras `off` sans aucun agent, bras `on` a 20 ticks.

    ⚠️ L'ASSERTION A ETE REECRITE le 2026-09-08, et il faut dire pourquoi : dans sa premiere forme
    elle s'ecrivait `assert mf["ratio"] < 1e6`, c.-a-d. qu'elle ne refusait QUE le symptome nomme
    dans la raison du xfail (le 2e10). Elle presupposait donc un ratio NUMERIQUE -- exactement ce
    que l'issue attendue (« refus ou INDETERMINE ») interdit de publier. Sur l'instrument corrige,
    qui rend `ratio = None`, elle levait un `TypeError` : le test echouait sur sa propre forme, pas
    sur le defaut. Elle exprime desormais l'attente DECLAREE, et elle est plus forte que l'ancienne
    puisqu'elle refuse aussi le meme defaut passe dans une autre colonne (`sign_p`, `n_favorable`).
    Sa capacite a ENCORE echouer est prouvee sur des reponses connues par les deux
    `test_CONTRE_EXEMPLE_*` ci-dessous (classe E1)."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=[], cellule_on=_inj6_cellule([20.0] * 5)))
    try:
        out = D.run_founder_matched(_SEEDS)
    except ValueError as exc:                    # refus explicite : l'AUTRE issue admise
        assert "mesur" in str(exc).lower(), exc
        return
    mf = out["med_founder"]
    assert _inj6_griefs_sans_paire_mesurable(mf) == [], (
        f"affirmation de fond publiee sur un bras `off` VIDE : {mf} ; "
        f"off_n_lived par seed = {[r['off_n_lived'] for r in out['rows']]}")


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la refutation) : `_pair` fabriquait un ratio 0.0 depuis DEUX bras eteints, soit un effondrement total affirme sans une seule mesure.
def test_run_founder_matched_does_not_read_TWO_extinguished_arms_as_a_total_collapse(monkeypatch):
    """Reponse connue : les deux bras eteints sur les 12 seeds. Aucune difference n'existe."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(cellule_off=[], cellule_on=[]))
    mf = D.run_founder_matched(_SEEDS)["med_founder"]
    assert mf["ratio"] != 0.0, (
        f"deux bras identiques et eteints -> ratio 0.0 publie comme un effondrement total : {mf}")


# NON-REGRESSION (defaut REPRODUIT par cette injection le 2026-09-08, CORRIGE le meme jour dans
# `tools/dream_causal_probe.py` par une voie parallele du meme workflow -- ligne 245, `seeds =
# list(seeds)` pose AVANT le test au lieu de `if not list(seeds)`).
def test_run_founder_matched_MEASURES_when_seeds_is_an_ITERATOR(monkeypatch):
    """Famille E23 occ.1 (`run_s2` iterait `worlds` DEUX FOIS), ici sur `seeds`.

    Le defaut, tel que mesure avant correction : la garde d'arguments evaluait `list(seeds)` DANS SA
    CONDITION, ce qui CONSOMME l'entree quand `seeds` est un iterateur (forme naturelle : un
    generateur, un `map`). La garde passait, la boucle de mesure tournait ZERO fois, `rows` restait
    vide, et l'instrument s'arretait sur `StatisticsError: no median for empty data` levee au fond de
    `_pair` -- une garde ECRITE POUR refuser une entree vide qui DETRUISAIT elle-meme l'entree
    qu'elle validait, avec un message ne nommant ni la cause ni l'appelant.

    Reponse connue : la MEME dose que le cas central, passee en generateur. Le resultat doit etre
    identique a celui obtenu avec une liste -- un iterateur n'est pas une dose."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5), cellule_on=_inj6_cellule([20.0] * 5)))
    out = D.run_founder_matched((s for s in _SEEDS))
    assert out["med_founder"]["ratio"] == pytest.approx(2.0), out["med_founder"]
    assert out["med_founder"]["n"] == K_SEEDS, out["med_founder"]


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la refutation) : la fraction publiee n'avait pas le denominateur du test de signe, qui JETTE les ex aequo.
def test_run_founder_matched_PUBLISHES_a_fraction_whose_denominator_matches_its_own_sign_test(
        monkeypatch):
    """Reponse connue : 3 seeds favorables (20 vs 10) et 9 seeds ex aequo (10 vs 10)."""
    table = {}
    for i, s in enumerate(_SEEDS):
        table[(s, "off")] = _inj6_cellule([10.0] * 5)
        table[(s, "on")] = _inj6_cellule([20.0 if i < 3 else 10.0] * 5)
    D = _inj6_injecte(monkeypatch, table)
    mf = D.run_founder_matched(_SEEDS)["med_founder"]
    coherent = (_sign_test_p(mf["n_favorable"], mf["n"]) == pytest.approx(mf["sign_p"])
                or "n_ecartees" in mf or "n_ex_aequo" in mf or "n_effectif" in mf)
    assert coherent, (
        f"{mf} : n_favorable/n = {mf['n_favorable']}/{mf['n']} se lit comme un taux, mais sign_p "
        f"vaut {mf['sign_p']} (calcule sur 3 paires informatives) et _sign_test_p(3, 12) = "
        f"{_sign_test_p(3, 12)} ; les ex aequo ne sont declares nulle part")


# ======================================================================================================
# 7. CAS NEGATIFS APPARIES du correctif du 2026-09-08 (classe E1 : un correctif qui rend
#    l'instrument INCREVABLE ou MUET est pire que le defaut). Chaque comportement ajoute est
#    confronte a la dose ou il doit se TAIRE, et le critere de refus a la dose ou il doit CRIER.
# ======================================================================================================

# Blocs GELES tels qu'ils ETAIENT PUBLIES, mesures par injection sur le code d'avant le correctif.
# Ce sont les reponses connues du critere de refus : s'il ne les attrape pas, il ne prouve rien.
_BLOC_AVANT_bras_on_vide = {                      # dose : bras `on` sans aucun agent, 12 seeds
    "med_off": 10.0, "med_on": 0.0, "ratio": 0.0, "n_favorable": 0, "n": 12, "n_effectif": 12,
    "n_ex_aequo": 0, "n_cellules_doublement_nulles": 0, "sign_p": 0.00048828125,
    "wilcoxon_p": 0.0025261742685023236}
_BLOC_AVANT_bras_off_vide_HISTORIQUE = {          # forme d'origine : division par max(0.0, 1e-9)
    "med_off": 0.0, "med_on": 20.0, "ratio": 2e10, "n_favorable": 12, "n": 12,
    "sign_p": 0.00048828125, "wilcoxon_p": 0.0025261742685023236}
_BLOC_AVANT_bras_off_vide_HEAD = {                # forme du jour : `ratio` bouche, le RESTE publie
    "med_off": 0.0, "med_on": 20.0, "ratio": None, "n_favorable": 12, "n": 12, "n_effectif": 12,
    "n_ex_aequo": 0, "n_cellules_doublement_nulles": 0, "sign_p": 0.00048828125,
    "wilcoxon_p": 0.0025261742685023236, "why": "ratio INDEFINI ..."}


def test_CONTRE_EXEMPLE_le_critere_de_refus_ATTRAPE_les_blocs_publies_AVANT_le_correctif():
    """Le critere doit ENCORE savoir crier, sur les trois formes REELLEMENT publiees.

    La troisieme est la plus instructive : elle a un `ratio` deja boucha `None` et un `why` qui
    annonce l'indetermination -- et elle publie quand meme `sign_p = 0.00048828125` et
    `n_favorable = 12`. Un critere qui ne regarderait que le `ratio` la declarerait saine. C'est
    exactement ainsi qu'un defaut survit a son correctif : en changeant de colonne."""
    for nom, bloc, attendu in (
            ("bras on vide", _BLOC_AVANT_bras_on_vide, "ratio"),
            ("bras off vide (historique 2e10)", _BLOC_AVANT_bras_off_vide_HISTORIQUE, "ratio"),
            ("bras off vide (HEAD, ratio deja None)", _BLOC_AVANT_bras_off_vide_HEAD, "sign_p")):
        griefs = _inj6_griefs_sans_paire_mesurable(bloc)
        assert griefs, f"{nom} : le critere de refus ne voit RIEN dans {bloc}"
        assert any(g.startswith(attendu) for g in griefs), (nom, attendu, griefs)


def test_CONTRE_EXEMPLE_le_critere_de_refus_ACCEPTE_le_bloc_INDETERMINE(monkeypatch):
    """No-op EXACT du critere : sur la MEME dose, l'instrument corrige ne doit lui donner AUCUNE
    prise. Sans cette moitie, le critere pourrait etre « refuse tout », donc increvable dans
    l'autre sens -- et le test qui s'appuie dessus ne prouverait plus rien."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=[], cellule_on=_inj6_cellule([20.0] * 5)))
    mf = D.run_founder_matched(_SEEDS)["med_founder"]
    assert _inj6_griefs_sans_paire_mesurable(mf) == [], mf
    assert mf["n"] == 0 and mf["n_non_mesurables"] == K_SEEDS, mf
    assert mf["seeds_non_mesurables_off"] == _SEEDS and mf["seeds_non_mesurables_on"] == [], mf


def test_run_founder_matched_EXCLUDES_and_NAMES_the_unmeasurable_pair_WITHOUT_silencing_the_others(
        monkeypatch):
    """Le cas REALISTE, et le plus insidieux : UNE ere sur 24 ne rend rien (seed 3, bras `on`).

    Avant le correctif, la paire absente entrait dans le test comme une paire DEFAVORABLE
    (`0.0 - 10.0 = -10.0`, difference non nulle) : l'instrument publiait `n_favorable 11, n 12,
    n_effectif 12, sign_p 0.00634765625`. Numerateur ET denominateur faux, et dans le sens du
    negatif. La forme close attendue sur les 11 paires reellement appariees est
    `2 * C(11,11) / 2^11 = 0.0009765625`.

    C'est aussi le cas negatif apparie de l'INDETERMINE : un correctif qui refuserait tout des
    qu'une cellule manque rendrait l'instrument MUET sur 11 mesures valides. Ici il doit PARLER,
    en NOMMANT ce qu'il a ecarte."""
    table = {}
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([10.0] * 5)
        table[(s, "on")] = [] if s == 3 else _inj6_cellule([20.0] * 5)
    D = _inj6_injecte(monkeypatch, table)
    out = D.run_founder_matched(_SEEDS)

    mf = out["med_founder"]
    assert mf["n"] == 11 and mf["n_non_mesurables"] == 1, mf
    assert mf["n_favorable"] == 11 and mf["n_effectif"] == 11, mf
    assert mf["ratio"] == pytest.approx(2.0), mf
    assert mf["sign_p"] == pytest.approx(2.0 / 2 ** 11), mf
    assert mf["seeds_non_mesurables_on"] == [3], mf
    assert mf["seeds_non_mesurables_off"] == [], mf
    assert mf["n"] + mf["n_non_mesurables"] == len(out["rows"]), mf
    assert out["rows"][3]["on_n_lived"] == 0 and out["rows"][3]["on_med_founder"] is None, \
        out["rows"][3]


def test_run_founder_matched_stays_SILENT_about_exclusions_when_NOTHING_is_missing(monkeypatch):
    """NO-OP EXACT du correctif (specificite) : sur une dose entierement mesurable, la machinerie
    d'exclusion ne doit rien retrancher et rien annoncer, et les grandeurs publiees doivent etre
    celles d'AVANT le correctif -- `ratio 2.0`, `n 12`, `sign_p 2/2^12`, `wilcoxon 0.00252617`.
    Sans ce cas, « l'instrument ne fabrique plus de negatif » pourrait simplement signifier
    « l'instrument ne mesure plus rien »."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5), cellule_on=_inj6_cellule([20.0] * 5)))
    mf = D.run_founder_matched(_SEEDS)["med_founder"]
    assert mf["statut"] == "MESURE", mf
    assert mf["n_non_mesurables"] == 0, mf
    assert mf["seeds_non_mesurables_off"] == [] and mf["seeds_non_mesurables_on"] == [], mf
    assert "why_non_mesurables" not in mf and "why" not in mf, mf
    assert mf["ratio"] == pytest.approx(2.0) and mf["n"] == K_SEEDS, mf
    assert mf["sign_p"] == pytest.approx(_SIGN_P_12_SUR_12), mf
    assert mf["wilcoxon_p"] == pytest.approx(_WIL_P_12_UNANIME), mf


def test_run_founder_matched_SEPARATES_a_missing_founder_marker_from_an_empty_era(monkeypatch):
    """Deux CAUSES d'absence, qui n'ont pas la meme consequence -- et que l'instrument confondait.

    Dose : les deux bras rendent 5 agents (donc l'ere a bien tourne), mais AUCUN n'est marque
    `founder`. Avant le correctif, `med_founder` publiait `med_off 0.0, med_on 0.0` et
    `n_cellules_doublement_nulles = 12`, ce qui se lit « les deux bras sont ETEINTS » alors que dix
    agents par seed avaient vecu : un echec du MARQUAGE devenait une extinction du MONDE.

    Attendu : `med_founder` INDETERMINE (aucun fondateur), tandis que `med_all` et `n_lived`, eux,
    restent MESURES -- l'absence est localisee a la grandeur qu'elle concerne, pas etendue au bloc
    voisin."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([], [10.0] * 5), cellule_on=_inj6_cellule([], [20.0] * 5)))
    out = D.run_founder_matched(_SEEDS)

    mf = out["med_founder"]
    assert mf["statut"] == "INDETERMINE_AUCUNE_PAIRE_MESURABLE", mf
    assert _inj6_griefs_sans_paire_mesurable(mf) == [], mf
    assert mf["n_cellules_doublement_nulles"] == 0, (
        f"{mf} : « deux bras eteints » affirme alors que 5 agents par bras ont vecu")
    assert out["rows"][0]["off_n_lived"] == 5 and out["rows"][0]["off_n_founder"] == 0, out["rows"][0]

    tous, vivants = out["med_all"], out["n_lived"]
    assert tous["statut"] == "MESURE" and tous["ratio"] == pytest.approx(2.0), tous
    assert vivants["statut"] == "MESURE" and vivants["ratio"] == pytest.approx(1.0), vivants


def test_pair_rows_REFUSES_a_degenerate_call_and_STILL_measures_a_valid_one():
    """La couche « mesures -> affirmation » est sortie de la fermeture le 2026-09-08 : elle est
    donc appelable seule, et sa garde d'ARGUMENTS doit se poser EN TETE.

    `rows` vide n'est PAS un INDETERMINE : il n'y a rien a ne pas savoir, c'est un appel invalide.
    Un `key` hors vocabulaire non plus. Les deux doivent LEVER -- sinon `_pair_rows([], ...)`
    rendrait « 0 paire sur 0 mesurable », qui se lit comme un constat sur des donnees. Et le cas
    NEGATIF apparie : un appel valide doit continuer de mesurer, sinon la garde serait un refus
    universel."""
    import tools.dream_causal_probe as D

    with pytest.raises(ValueError, match="argument degenere"):
        D._pair_rows([], "med_founder")
    with pytest.raises(ValueError, match="argument degenere"):
        D._pair_rows([{"seed": 0}], "med_inconnu")
    with pytest.raises(ValueError, match="lignes incompletes"):
        D._pair_rows([{"seed": 0, "off_med_founder": 1.0, "on_med_founder": 2.0}], "med_founder")

    rows = [{"seed": s, "off_med_founder": 10.0, "on_med_founder": 20.0,
             "off_n_lived": 5, "on_n_lived": 5, "off_n_founder": 5, "on_n_founder": 5}
            for s in _SEEDS]
    bloc = D._pair_rows(rows, "med_founder")
    assert bloc["ratio"] == pytest.approx(2.0) and bloc["n"] == K_SEEDS, bloc
    assert bloc["sign_p"] == pytest.approx(_SIGN_P_12_SUR_12), bloc


# ======================================================================================================
# 8. AJOUTS DU 2e REFUTEUR (2026-09-08). Tout ce qui suit vient de sondes lancees sur le code
#    LIVRE, pas d'une relecture. Deux sources :
#
#    (i)  TEST PAR MUTATION du correctif du matin : je casse UN comportement ajoute, la suite DOIT
#         rougir. Mesure sur `test_inj_run_founder_matched.py` + `test_dream_causal_probe.py`
#         (baseline `2 failed, 41 passed`) -- CINQ comportements sur onze n'ont tue AUCUN test :
#           M2  `statut` fige a "MESURE"                           -> 2 failed, 41 passed (INCHANGE)
#           M3  `med_all` d'une cohorte vide remis a 0.0           -> 2 failed, 41 passed (INCHANGE)
#           M7  `_fmt_mediane` rendant "0.0" au lieu de NON-MESURE -> 2 failed, 41 passed (INCHANGE)
#           M8  WARNING de cellule non mesurable supprime          -> 2 failed, 41 passed (INCHANGE)
#           M9  WARNING de bloc INDETERMINE/PARTIEL supprime       -> 2 failed, 41 passed (INCHANGE)
#         (temoins vivants, meme protocole : M1 exclusion desactivee -> 5 failed ; M4 `med_founder`
#         remis a 0.0 -> 3 failed ; M5/M6 gardes de tete -> 3 failed ; M11 ratio 2e10 -> 3 failed.)
#         M3 est le plus grave : c'est LE correctif revendique (« cohorte VIDE -> None, JAMAIS
#         0.0 »), et il n'etait tenu que sur `med_founder` -- la moitie du perimetre etait hors du
#         REGIME de tout test. Or `med_all` est precisement la grandeur de POPULATION qui a produit
#         le `CAUSE_NUISIBLE` d'EDR-095, que `run_founder_matched` existe pour refuter.
#
#    (ii) DEFAUT NEUF, mesure par injection : la garde de PUISSANCE n'a jamais ete retro-appliquee
#         a `_pair_rows` (classe E14), alors que c'est le correctif d'EXCLUSION lui-meme qui rend
#         son regime atteignable.
# ======================================================================================================

def _inj6_bloc(monkeypatch, off, on, key="med_founder"):
    """Raccourci : dose uniforme sur les 12 seeds -> le bloc publie pour `key`."""
    D = _inj6_injecte(monkeypatch, _table_uniforme(cellule_off=off, cellule_on=on))
    return D.run_founder_matched(_SEEDS)[key]


# --- (i) M3 : le correctif central, sur la MOITIE du perimetre qu'aucun test ne couvrait ---------

def test_run_founder_matched_does_not_read_an_EMPTY_era_as_a_med_all_of_ZERO(monkeypatch):
    """M3 -- `med_all`, la grandeur de POPULATION, n'etait protegee par AUCUN test.

    Le correctif « cohorte VIDE -> None, JAMAIS 0.0 » est ecrit DEUX FOIS dans la boucle de mesure
    (une par grandeur) et n'etait teste qu'UNE seule (`med_founder`). Remettre `... if ages else
    0.0` sur la ligne `med_all` ne faisait rougir aucune des 43 assertions des deux suites : le
    regime ou la garde agit n'etait atteint par aucun cas. C'est la forme mesuree trois fois le
    2026-09-08 -- une garde verte parce que rien ne tourne la ou elle s'active.

    Ce qui rend l'angle mort couteux : `med_all` est la statistique qui a produit le verdict
    `CAUSE_NUISIBLE` d'EDR-095, celui-la meme que cette fonction existe pour refuter.

    Dose : les DEUX bras rendent une ere VIDE. Aucun age n'existe nulle part."""
    out = _inj6_injecte(monkeypatch, _table_uniforme(cellule_off=[], cellule_on=[])
                        ).run_founder_matched(_SEEDS)
    for cellule in out["rows"]:
        assert cellule["off_med_all"] is None and cellule["on_med_all"] is None, (
            f"{cellule} : mediane 0.0 fabriquee sur une ere qui n'a rendu AUCUN agent -- "
            "« ils ont vecu ZERO tick » affirme sans qu'un seul age soit lu")
    tous = out["med_all"]
    assert tous["statut"] == "INDETERMINE_AUCUNE_PAIRE_MESURABLE", tous
    assert _inj6_griefs_sans_paire_mesurable(tous) == [], tous


def test_run_founder_matched_med_all_KNOWS_HOW_TO_BE_A_NUMBER(monkeypatch):
    """CAS NEGATIF APPARIE (E1) du test ci-dessus : sur des cohortes PLEINES, `med_all` doit rester
    un nombre et porter la confusion E15 que le bloc existe pour exposer.

    Dose : fondateurs identiques (10 vs 10) mais 20 nes-tard a age 1 dans le seul bras `on` --
    l'explosion reproductive. `med_founder` doit dire 1.0 (aucun effet sur qui que ce soit) et
    `med_all` beaucoup moins : c'est l'ecart entre les deux qui EST la mesure."""
    out = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5),
        cellule_on=_inj6_cellule([10.0] * 5, [1.0] * 20))).run_founder_matched(_SEEDS)
    assert out["rows"][0]["on_med_all"] == pytest.approx(1.0), out["rows"][0]
    assert out["med_founder"]["ratio"] == pytest.approx(1.0), out["med_founder"]
    assert out["med_all"]["statut"] == "MESURE", out["med_all"]
    assert out["med_all"]["ratio"] == pytest.approx(0.1), out["med_all"]


# --- (i) M2 : `statut`, annonce comme « CE QUE LIT L'AVAL », verifie par aucun test -------------

def test_the_statut_field_DISCRIMINATES_the_three_regimes_it_declares(monkeypatch):
    """M2 -- figer `statut` a "MESURE" ne faisait rougir aucun test.

    Le champ est pourtant la seule chose que la docstring de `run_founder_matched` designe a
    l'aval (« Chacun des trois blocs porte un `statut` : MESURE / MESURE_PARTIEL /
    INDETERMINE_AUCUNE_PAIRE_MESURABLE »). Deux de ses trois valeurs etaient assertees ici ou la,
    jamais les trois ENSEMBLE sur des doses qui les separent -- donc rien ne prouvait que le champ
    DISCRIMINE au lieu de porter une constante. Une etiquette qui vaut toujours la meme chose est
    aussi informative que pas d'etiquette, et elle inspire davantage confiance."""
    plein, vide = _inj6_cellule([10.0] * 5), []
    table_partielle = {}
    for s in _SEEDS:
        table_partielle[(s, "off")] = plein
        table_partielle[(s, "on")] = vide if s == 3 else _inj6_cellule([20.0] * 5)

    vus = {
        "MESURE": _inj6_bloc(monkeypatch, plein, _inj6_cellule([20.0] * 5))["statut"],
        "MESURE_PARTIEL": _inj6_injecte(monkeypatch, table_partielle).run_founder_matched(
            _SEEDS)["med_founder"]["statut"],
        "INDETERMINE_AUCUNE_PAIRE_MESURABLE": _inj6_bloc(monkeypatch, plein, vide)["statut"],
    }
    assert vus == {k: k for k in vus}, (
        f"`statut` ne discrimine pas ses trois regimes declares : {vus}")


# --- (i) M7/M8/M9 : le JOURNAL, ou un humain lit le resultat sans ouvrir l'artefact -------------

def test_the_LOG_never_writes_a_zero_where_NOTHING_was_measured(monkeypatch, caplog):
    """M7 + M8 -- `_fmt_mediane` et le WARNING par cellule etaient DECORATIFS.

    Les deux existent pour une raison ecrite noir sur blanc dans le module (« un journal qui ecrit
    0.0 la ou rien n'a ete mesure fabrique la meme affirmation negative que l'artefact, a l'endroit
    ou un humain la lit »). Aucun test ne les regardait : `_fmt_mediane` rendant "0.0" et le
    WARNING entierement supprime laissaient les deux suites au vert.

    C'est l'angle mort le plus naturel d'une revue d'artefact -- on verifie le JSON, on ne relit
    pas la sortie console. Or la console est ce que lit l'operateur du run."""
    caplog.set_level(logging.INFO, logger="AGIseed.DreamCausal")
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5), cellule_on=[]))
    with caplog.at_level(logging.INFO, logger="AGIseed.DreamCausal"):
        D.run_founder_matched(_SEEDS)
    texte = caplog.text

    assert "NON-MESURE" in texte, (
        "le journal n'annonce pas l'absence de mesure ; il ecrit une mediane numerique la ou "
        f"aucun age n'existe. Sortie : {texte[:400]}")
    assert "NON MESURABLE" in texte, f"aucun WARNING par cellule non mesurable : {texte[:400]}"
    lignes_seed = [l for l in texte.splitlines() if "fondateurs" in l]
    assert lignes_seed, texte[:400]
    assert all(l.rstrip().endswith("NON-MESURE") for l in lignes_seed), (
        f"une mediane numerique est journalisee pour un bras VIDE : {lignes_seed[:2]}")


def test_the_LOG_stays_SILENT_when_every_cell_is_measurable(monkeypatch, caplog):
    """CAS NEGATIF APPARIE (E1) des cris ci-dessus : sur une dose entierement mesurable, ni
    NON-MESURE, ni NON MESURABLE, ni ATTENTION ne doivent apparaitre -- sinon le journal crierait
    toujours et ne signalerait plus rien.

    ⚠️ LA DOSE A ETE CORRIGEE au moment de l'ecrire, et c'est la lecon du test. Sa premiere version
    donnait 5 fondateurs a chaque bras : `med_founder` et `med_all` etaient bien mesures, mais le
    bloc `n_lived` comparait alors 5 a 5 sur les DOUZE seeds -- douze ex aequo exacts, donc un
    `sign_p` calcule sur ZERO paire, et le cri `sans RESOLUTION` partait a juste titre. Le cas
    negatif tournait dans un regime DEGENERE que le monde reel ne produit pas : le fait central de
    ce fil est que le reve force multiplie `n_lived` par 13-16 (et l'artefact publie
    `results/dream_founder_matched_n20.json` le confirme -- `n_ex_aequo = 0` sur ses trois blocs).
    C'est le symetrique exact du defaut que cette section corrige : une garde jugee sur des cas
    hors de son regime, ici dans le sens « elle crie » plutot que « elle se tait ».

    La dose est donc celle du regime REEL : bras `on` a 65 agents contre 5, comme mesure."""
    caplog.set_level(logging.INFO, logger="AGIseed.DreamCausal")
    D = _inj6_injecte(monkeypatch, _table_uniforme(
        cellule_off=_inj6_cellule([10.0] * 5),
        cellule_on=_inj6_cellule([20.0] * 5, [1.0] * 60)))
    with caplog.at_level(logging.INFO, logger="AGIseed.DreamCausal"):
        D.run_founder_matched(_SEEDS)
    for interdit in ("NON-MESURE", "NON MESURABLE", "ATTENTION"):
        assert interdit not in caplog.text, (
            f"{interdit!r} crie sur une dose ou TOUT est mesure : {caplog.text[:400]}")


def test_the_LOG_SHOUTS_when_a_whole_block_is_INDETERMINATE(monkeypatch, caplog):
    """M9 -- le cri de BLOC etait decoratif lui aussi (le supprimer ne rougissait rien), alors que
    la docstring en fait sa raison d'etre : « L'aval ne peut pas ignorer une absence de mesure :
    elle est CRIEE, pas seulement ecrite dans l'artefact. Sans ce cri, le seul signe d'un bras non
    mesure serait un `None` au milieu d'un bloc de nombres. »

    Les DEUX regimes sont verifies : INDETERMINE (rien n'a pu etre apparie) et MESURE_PARTIEL (des
    paires ont ete exclues) ne passent pas par la meme branche."""
    caplog.set_level(logging.WARNING, logger="AGIseed.DreamCausal")
    _inj6_bloc(monkeypatch, _inj6_cellule([10.0] * 5), [])
    assert "ATTENTION -- med_founder" in caplog.text, caplog.text[:400]
    assert "ABSENCE DE MESURE" in caplog.text, caplog.text[:400]

    caplog.clear()
    table = {}
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([10.0] * 5)
        table[(s, "on")] = [] if s == 3 else _inj6_cellule([20.0] * 5)
    _inj6_injecte(monkeypatch, table).run_founder_matched(_SEEDS)
    assert "EXCLUES du test" in caplog.text, caplog.text[:400]


# --- (ii) DEFAUT NEUF : la garde de PUISSANCE jamais retro-appliquee a `_pair_rows` (E14) --------

def test_a_block_reduced_to_ONE_pair_by_EXCLUSION_is_not_published_as_a_measured_null(monkeypatch):
    """DEFAUT NEUF, mesure par injection (2e refuteur, 2026-09-08) -- classe E14.

    Le correctif (c) du matin avait dote `dose_response_verdict` de `underpowered` /
    `sign_p_plancher` / `sans_resolution`, avec cette justification : « sous 5 paires le verdict ne
    PEUT pas etre autre chose que NEUTRE, quelle que soit l'amplitude ». Sa fonction SOEUR du MEME
    fichier, qui fait EXACTEMENT le meme test de signe sur les memes grandeurs, n'a rien recu.

    Ce n'etait pas latent : c'est le correctif d'EXCLUSION de l'apres-midi qui a OUVERT le regime.
    Avant lui `n` valait toujours `len(rows)` (12 ou 20, largement puissant) ; depuis, toute paire
    non mesurable est retranchee et `n` peut tomber a 1. Mesure AVANT la retro-application, sur
    11 paires non mesurables sur 12 :
      * 12e paire FAVORABLE   (10 -> 20) -> {ratio 2.0,  n 1, sign_p 1.0, statut MESURE_PARTIEL}
      * 12e paire DEFAVORABLE (20 -> 1)  -> {ratio 0.05, n 1, sign_p 1.0, statut MESURE_PARTIEL}
    A n=1 le test de signe rend 1.0 pour TOUTE donnee imaginable (plancher 2/2**1). Un `sign_p` de
    1.0 publie nu se lit « pas d'effet » : c'est le NEUTRE fabrique, par le chemin qu'avait ouvert
    le correctif precedent. Le second cas est le pire -- « le reve divise la survie par 20 » y
    voisine avec la p-valeur qui rassure.

    Le drapeau ne touche NI `statut`, NI `ratio`, NI `sign_p` : mesurabilite et puissance sont deux
    axes, et deplacer un seuil dans le `statut` changerait le contrat de toutes les fixtures
    existantes (E14 dans l'autre sens). Il s'ajoute, comme dans `dose_response_verdict`."""
    table = {}
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([20.0] * 5) if s == 0 else []
        table[(s, "on")] = _inj6_cellule([1.0 if s == 0 else 20.0] * 5)
    mf = _inj6_injecte(monkeypatch, table).run_founder_matched(_SEEDS)["med_founder"]

    assert mf["n"] == 1 and mf["n_non_mesurables"] == 11, mf
    assert mf["ratio"] == pytest.approx(0.05), mf          # « divise la survie par 20 »
    assert mf["sign_p"] == 1.0, mf
    assert mf["underpowered"] is True, (
        f"{mf} : sign_p={mf['sign_p']} publie sur {mf['n']} paire(s) sans drapeau de puissance -- "
        "or a n=1 le test de signe rend 1.0 QUELLES QUE SOIENT les valeurs")
    assert mf["sign_p_plancher"] == 1.0, mf
    assert "why_puissance" in mf and "1 paire" in mf["why_puissance"], mf


def test_the_power_flag_of_pair_rows_KNOWS_HOW_TO_STAY_DOWN(monkeypatch):
    """CAS NEGATIF APPARIE (E1) du drapeau ci-dessus, aux DEUX frontieres qui comptent.

    Sans lui, `underpowered` pourrait etre une constante vraie -- un instrument qui se declare
    toujours sous-puissant ne dit rien non plus, et il a le meme air de prudence.

    * 12 paires sur 12 : plancher 2/2**12 = 0.00049, tres en dessous d'alpha -> muet.
    * 5 paires sur 12 (7 exclues)  : plancher 2/2**5 = 0.0625 < alpha=0.1 -> muet AUSSI, alors meme
      que le bloc est `MESURE_PARTIEL`. C'est la frontiere exacte, et elle prouve que le drapeau lit
      le NOMBRE DE PAIRES et non la simple presence d'exclusions."""
    mf = _inj6_bloc(monkeypatch, _inj6_cellule([10.0] * 5), _inj6_cellule([20.0] * 5))
    assert mf["n"] == K_SEEDS and mf["underpowered"] is False, mf
    assert "why_puissance" not in mf, mf

    table = {}
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([10.0] * 5) if s < 5 else []
        table[(s, "on")] = _inj6_cellule([20.0] * 5)
    cinq = _inj6_injecte(monkeypatch, table).run_founder_matched(_SEEDS)["med_founder"]
    assert cinq["n"] == 5 and cinq["statut"] == "MESURE_PARTIEL", cinq
    assert cinq["underpowered"] is False, (
        f"{cinq} : a 5 paires le plancher vaut 0.0625 < alpha -- le design PEUT trancher, et le "
        "drapeau doit se taire meme quand des paires ont ete exclues")
    assert cinq["sign_p"] == pytest.approx(2.0 / 2 ** 5) and "why_puissance" not in cinq, cinq


def test_the_LOG_SHOUTS_when_exclusion_has_destroyed_the_power(monkeypatch, caplog):
    """Le drapeau doit etre CRIE, sinon il rejoint les cinq champs decoratifs que ce bloc corrige.

    Le cri est pose HORS du `if/elif` des statuts : un bloc peut etre `MESURE_PARTIEL` ET
    sous-puissant, et c'est meme le cas le plus courant -- ce sont les MEMES exclusions qui
    produisent les deux. Le cas negatif apparie est `test_the_LOG_stays_SILENT_...` ci-dessus, qui
    interdit tout ATTENTION sur une dose entierement mesurable."""
    caplog.set_level(logging.WARNING, logger="AGIseed.DreamCausal")
    table = {}
    for s in _SEEDS:
        table[(s, "off")] = _inj6_cellule([10.0] * 5) if s == 0 else []
        table[(s, "on")] = _inj6_cellule([20.0] * 5)
    _inj6_injecte(monkeypatch, table).run_founder_matched(_SEEDS)
    assert "SOUS-PUISSANT" in caplog.text, caplog.text[:500]
    assert "med_founder" in caplog.text and "med_all" in caplog.text, caplog.text[:500]


def test_pair_rows_publishes_the_power_of_the_test_that_ACTUALLY_ran(monkeypatch):
    """Deux planchers parce que DEUX denominateurs, et ils se separent.

    Dose : 12 paires toutes MESUREES et toutes EX AEQUO. Le design est puissant (12 paires,
    plancher 0.00049) mais le test de signe, qui JETTE les ex aequo, a tourne sur ZERO paire. Le
    bloc doit donc dire `underpowered False` ET `sans_resolution True` -- deux faits distincts, et
    les confondre redonnerait le defaut (d) corrige le matin dans la fonction soeur.

    Le cas n'est pas exotique : `med_*` est une mediane d'ages sur une grille discrete."""
    mf = _inj6_bloc(monkeypatch, _inj6_cellule([10.0] * 5), _inj6_cellule([10.0] * 5))
    assert mf["n"] == K_SEEDS and mf["n_effectif"] == 0 and mf["n_ex_aequo"] == K_SEEDS, mf
    assert mf["underpowered"] is False, mf
    assert mf["sans_resolution"] is True, mf
    assert mf["sign_p_plancher"] == pytest.approx(_SIGN_P_12_SUR_12), mf
    assert mf["sign_p_plancher_effectif"] == 1.0, mf
    assert "why_resolution" in mf, mf
    assert mf["ratio"] == pytest.approx(1.0), "un nul MESURE reste publie comme un nul"


def test_pair_rows_REFUSES_a_row_without_its_SEED_instead_of_a_raw_KeyError(monkeypatch):
    """La garde de tete ne couvrait pas `seed`, mesure : `KeyError: 'seed'` NU, leve au fond de la
    fonction APRES la garde censee refuser les lignes incompletes.

    Ce n'est pas cosmetique. `seed` est l'identifiant que `_pair_rows` republie dans
    `seeds_non_mesurables_off/on` -- c'est-a-dire la seule chose qui rend DIAGNOSTIQUABLE quelles
    cellules ont ete exclues. Le champ dont depend tout le dispositif de tracabilite ajoute le
    matin meme etait le seul a echapper au controle des arguments.

    Cas NEGATIF apparie inclus : une ligne complete continue de mesurer."""
    import tools.dream_causal_probe as D

    incomplete = [{"off_med_founder": 1.0, "on_med_founder": 2.0, "off_n_lived": 5,
                   "on_n_lived": 5, "off_n_founder": 5, "on_n_founder": 5}]
    with pytest.raises(ValueError, match="lignes incompletes") as exc:
        D._pair_rows(incomplete, "med_founder")
    assert "seed" in str(exc.value), exc.value

    complete = [dict(incomplete[0], seed=s) for s in _SEEDS]
    bloc = D._pair_rows(complete, "med_founder")
    assert bloc["ratio"] == pytest.approx(2.0) and bloc["n"] == K_SEEDS, bloc
    assert bloc["seeds_non_mesurables_off"] == [] and bloc["statut"] == "MESURE", bloc
