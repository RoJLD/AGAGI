# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. Les `xfail(strict=True)` restants sont des DEFAUTS REELS ouverts ;
# les blocs NON-REGRESSION sont d'anciens xfail dont le defaut a ete corrige.
# -*- coding: utf-8 -*-
"""INJ6 -- calibration par INJECTION A DOSE CONNUE de `tools/dreaming_probe.py::run_q2`.

`run_q2` est un ORCHESTRATEUR : il ne simule pas. Il appelle `run_era_organ` DEUX fois par seed
(bras ON force a 100 % d'organe / bras OFF a 0 %, tous deux au SWEET SPOT metab=0.25 payoff=3.0),
puis AGREGE ces cohortes en deux grandeurs -- `q2a_delta` (contraste reveurs / non-reveurs INTRA
population ON) et `q2b_ratio` (rapport de competence-survie ON/OFF, apparie par seed) -- que la
porte `dreaming_verdict` lit pour prononcer PAYE / PAS PAYE.

Sa garde d'ARGUMENTS est calibree depuis le 2026-09-06. Ce qui ne l'etait par RIEN, c'est la couche
qui transforme des mesures en affirmation : appariement, regime passe a chaque bras, unite de
replication, traitement des cellules NON INFORMATIVES, et les branches de verdict.

SEAM : `run_era_organ` est defini dans le MEME module et resolu par nom global au moment de l'appel
-> l'attribut a monkeypatcher est `tools.dreaming_probe.run_era_organ`. `survival_competence`,
`q2_split` et `_sign_test_p` sont laisses REELS : la dose s'impose donc en AGES (competence =
mediane(age)/AGE_REF=200, clampee) et trois couches de plus sont testees gratuitement.
AUCUN monde n'est construit ; aucun bail `kuzu` n'est requis ; le cout total est de l'ordre de la
seconde d'import.

CONTROLE E1 PAR MUTATION (`q2/mutq2.py`, lance par `q2/run_mutation.py A|B`). Le source de `run_q2`
est mute EN MEMOIRE -- aucun octet du depot n'est ecrit, l'arbre etant partage avec une session qui
edite ce meme fichier. Deux mutations DISJOINTES :
  A -- AVEUGLE A LA DOSE : seed constant aux deux bras, `deltas.append(0.0)`, `dreams_seen += 0`,
       `c_on, c_off = 0.5, 0.5`. Resultat : 9/9 des tests de dose MEURENT (le seul survivant est le
       test de PLACEMENT de la garde, que A ne touche pas), et 3 des 5 xfail basculent en
       XPASS(strict) -- la mutation fait passer l'instrument pour REPARE alors qu'il ne mesure plus
       rien, ce qui est exactement le motif que ces xfail denoncent.
  B -- GARDE NEUTRALISEE (`if False:`) : 1/1, le test de placement de la garde meurt, et le xfail
       #5 bascule en XPASS -- preuve directe que c'est bien le `list(seeds)` de la garde qui
       consomme l'iterateur.
Total : 10/10 tests passants tues.

Les `xfail(strict=True)` sont des DEFAUTS REELS de `tools/dreaming_probe.py`, NON corriges ici
(consigne : exposer, pas reparer). Ils tomberont d'eux-memes le jour ou le defaut sera corrige.
"""
import math

import pytest


AGE_REF = 200.0        # src/curriculum/competence.AGE_REF -- competence = mediane(age)/AGE_REF, clampee
SWEET = (0.25, 3.0)    # (metab, payoff) du sweet spot, tel que run_q2 doit le passer AUX DEUX BRAS
LETAL = (1.0, 3.0)     # (le regime letal de Q1 est (1.0, 1.0) -- il n'a rien a faire dans Q2)


# ======================================================================================================
# Cellules factices
# ======================================================================================================

def _agent(age, dreams=0, has_organ=True, founder=True, **over):
    """Cellule-agent factice portant TOUTES les cles que `run_era_organ` produit (age, total_dreams,
    has_organ, founder, altars_solved, spears_crafted, preys_eaten). `run_q2` n'en lit aujourd'hui
    que trois (age via `survival_competence`, total_dreams via `q2_split` et la somme de reves) --
    les autres sont imposees pour que l'injection reste fidele au contrat de la fonction remplacee :
    si l'orchestrateur se met a en lire une de plus, ce test ne mentira pas."""
    c = {"age": float(age), "total_dreams": int(dreams), "has_organ": bool(has_organ),
         "founder": bool(founder), "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}
    c.update(over)
    return c


def _cohorte(age, n=8, dreams=0, **over):
    """`n` agents d'age IDENTIQUE -> la mediane est exacte, donc la competence imposee vaut
    EXACTEMENT age/200 (clampee a 1.0)."""
    return [_agent(age, dreams=dreams, **over) for _ in range(n)]


def _cohorte_mixte(age_reveurs, age_autres, n_reveurs=4, n_autres=4, dreams=5):
    """Cohorte ON contenant les DEUX groupes du split intra-population. Indispensable : le contraste
    `q2a_delta` n'a de sens que si le groupe de reference EXISTE (cf. le xfail sur le groupe vide)."""
    return ([_agent(age_reveurs, dreams=dreams) for _ in range(n_reveurs)]
            + [_agent(age_autres, dreams=0) for _ in range(n_autres)])


# ======================================================================================================
# Injection
# ======================================================================================================

def _injecte(monkeypatch, fabrique):
    """Remplace `run_era_organ` DANS le module de la sonde et rend le module."""
    import tools.dreaming_probe as DP
    monkeypatch.setattr(DP, "run_era_organ", fabrique)
    return DP


def _par_bras(cohorte_on, cohorte_off, journal=None, strict_regime=True):
    """Fabrique qui distingue les deux bras par leur DOSE D'ORGANE (`organ_fraction` 1.0 = ON,
    0.0 = OFF), PAS par l'ordre d'appel : un orchestrateur qui intervertirait les bras serait vu.
    Elle exige aussi que les DEUX bras recoivent le SWEET SPOT (0.25, 3.0) -- si le bras OFF etait
    lance au regime letal de Q1, le ratio comparerait « organe au sweet » a « pas d'organe au letal »
    et serait confondu sans que rien ne le signale.
    `cohorte_on` / `cohorte_off` : liste, ou callable(seed) -> liste."""
    def _f(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        if journal is not None:
            journal.append({"target": target, "seed": seed, "organ_fraction": organ_fraction,
                            "metab": metab, "payoff": payoff, "num_agents": num_agents,
                            "max_ticks": max_ticks, "shared_db": shared_db})
        if strict_regime:
            assert (metab, payoff) == SWEET, (
                "run_q2 doit lancer les DEUX bras au SWEET SPOT ; regime recu : %r" % ((metab, payoff),))
            assert organ_fraction in (0.0, 1.0), (
                "run_q2 est le bras FORCE : organ_fraction doit valoir 1.0 (ON) ou 0.0 (OFF), pas %r"
                % (organ_fraction,))
        c = cohorte_on if organ_fraction == 1.0 else cohorte_off
        return list(c(seed)) if callable(c) else list(c)
    return _f


def _run(monkeypatch, cohorte_on, cohorte_off, seeds=(0, 1, 2), journal=None, n_agents=8,
         strict_regime=True):
    DP = _injecte(monkeypatch, _par_bras(cohorte_on, cohorte_off, journal, strict_regime))
    return DP, DP.run_q2(seeds, "stoneage", n_agents, 5, None)


# ======================================================================================================
# 1. LA DOSE : les trois issues que le ratio apparie peut rendre.
# ======================================================================================================

def test_run_q2_READS_the_paired_survival_ratio_it_claims(monkeypatch):
    """Reponse connue x3, en FORME CLOSE. Le bras ON contient les DEUX groupes du split (4 reveurs
    + 4 non-reveurs de MEME age) -> `q2a_delta` vaut exactement 0.0 et n'interfere pas : la seule
    grandeur qui bouge est le ratio apparie.

    POSITIF -- ON age 100 (competence 0.5) / OFF age 50 (0.25) -> ratio EXACTEMENT 2.0 sur 3 seeds ;
               sign_p = 2 x C(3,3)/2^3 = 0.25, n_favorable = 3.
    NEGATIF -- l'inverse exact -> ratio 0.5, n_favorable = 0. Sans cette branche le test ne prouverait
               rien : un instrument qui rendrait `abs()` ou qui intervertirait ON et OFF passerait le
               seul cas positif (classe E1).
    NUL     -- ages IDENTIQUES des deux cotes -> ratio EXACTEMENT 1.0 (valeur charniere : la porte
               exige `> 1.02`), et la cellule sort du test de signe -> sign_p = 1.0 sur n=0 effectif.
    """
    DP, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(50))
    assert r["q2b_ratio"] == pytest.approx(2.0), r
    assert r["per_seed_ratio"] == pytest.approx([2.0, 2.0, 2.0])
    assert r["n"] == 3 and r["n_favorable"] == 3
    assert r["sign_p"] == pytest.approx(0.25)
    assert r["q2a_delta"] == pytest.approx(0.0)

    _, r = _run(monkeypatch, _cohorte_mixte(50, 50), _cohorte(100))
    assert r["q2b_ratio"] == pytest.approx(0.5), r
    assert r["n_favorable"] == 0 and r["sign_p"] == pytest.approx(0.25)

    _, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(100))
    assert r["q2b_ratio"] == 1.0, "ages identiques -> ratio EXACTEMENT 1.0, pas approximativement"
    assert r["n_favorable"] == 0
    assert r["sign_p"] == 1.0, "une egalite parfaite sort du test de signe (n effectif = 0)"


def test_run_q2_feeds_the_gate_that_reads_it(monkeypatch):
    """La grandeur mesuree est-elle celle qui AGIT ? `run_q2` ne prononce pas de verdict : c'est
    `dreaming_verdict` qui lit `q2a_delta` et `q2b_ratio`. Chaine COMPLETE, Q1 tenu FIXE a
    « survit » (delta_sweet=+0.25, delta_letal=-0.25) pour isoler la contribution de Q2 :
      - ON 100 / OFF 50   -> ratio 2.00 > 1.02   -> SURVIT_ET_PAYE
      - ON 55  / OFF 50   -> ratio 1.10 > 1.02   -> SURVIT_ET_PAYE  (le seuil est FRANCHI de peu)
      - ON 50.5 / OFF 50  -> ratio 1.01 < 1.02   -> SURVIT_PAS_PAYE (le seuil MORD)
      - ON 50  / OFF 100  -> ratio 0.50          -> SURVIT_PAS_PAYE
    Les deux cas encadrant `pay_eps` sont la raison d'etre du test : ils prouvent que la porte lit
    bien une grandeur CONTINUE et non un signe."""
    for age_on, age_off, ratio, attendu in ((100, 50, 2.00, "SURVIT_ET_PAYE"),
                                            (55, 50, 1.10, "SURVIT_ET_PAYE"),
                                            (50.5, 50, 1.01, "SURVIT_PAS_PAYE"),
                                            (50, 100, 0.50, "SURVIT_PAS_PAYE")):
        DP, r = _run(monkeypatch, _cohorte_mixte(age_on, age_on), _cohorte(age_off))
        assert r["q2b_ratio"] == pytest.approx(ratio), (age_on, age_off, r["q2b_ratio"])
        v = DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"])
        assert v == attendu, (age_on, ratio, v)


def test_run_q2_CAPS_the_favourable_direction_only(monkeypatch):
    """Specificite du plafond `RATIO_CAP=5.0`. Reponse connue : ON age 200 (competence clampee a
    1.0) / OFF age 2 (0.01) -> le ratio BRUT vaut 100 et doit sortir a 5.0 ; le cas MIROIR (ON 2 /
    OFF 200) sort a 0.01, NON plafonne. Le plafond est donc ASYMETRIQUE -- il tronque le benefice
    publie mais pas le prejudice. C'est sans consequence sur la porte (qui teste `> 1.02`), mais
    `q2b_ratio` est une grandeur PUBLIEE : ce test la fige, pour qu'un futur lecteur ne prenne pas
    un 5.0 pour une mesure."""
    DP, r = _run(monkeypatch, _cohorte_mixte(200, 200), _cohorte(2))
    assert r["q2b_ratio"] == pytest.approx(DP.RATIO_CAP), r
    _, r = _run(monkeypatch, _cohorte_mixte(2, 2), _cohorte(200))
    assert r["q2b_ratio"] == pytest.approx(0.01), "la direction DEFAVORABLE n'est pas plafonnee"


# ======================================================================================================
# 2. CABLAGE et APPARIEMENT (ce que les valeurs de sortie ne peuvent pas prouver).
# ======================================================================================================

def test_run_q2_PAIRS_the_two_arms_WITHIN_the_same_seed_at_the_SWEET_spot(monkeypatch):
    """L'affirmation « l'organe paye » n'a de sens que si ON et OFF partagent le seed (meme monde,
    meme init) et le REGIME ENERGETIQUE. Reponse connue : 3 seeds -> 6 appels, exactement 2 par
    seed, differant UNIQUEMENT par `organ_fraction` (1.0 vs 0.0), tous deux a (metab, payoff) =
    (0.25, 3.0), avec `target` / `num_agents` / `max_ticks` / `shared_db` passes tels quels.
    Deux erreurs silencieuses seraient invisibles sans ce test : apparier entre seeds (le ratio
    resterait plausible) et lancer le bras OFF au regime LETAL de Q1 (le ratio deviendrait un
    melange organe x energie)."""
    journal = []
    DP, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(50), seeds=[7, 8, 9],
                 journal=journal, n_agents=13)
    assert len(journal) == 6, journal
    for s in (7, 8, 9):
        du_seed = [a for a in journal if a["seed"] == s]
        assert len(du_seed) == 2, (s, du_seed)
        assert {a["organ_fraction"] for a in du_seed} == {1.0, 0.0}, du_seed
        assert {(a["metab"], a["payoff"]) for a in du_seed} == {SWEET}, du_seed
        assert {(a["target"], a["num_agents"], a["max_ticks"]) for a in du_seed} == {("stoneage", 13, 5)}
    assert [a["seed"] for a in journal] == [7, 7, 8, 8, 9, 9], (
        "les deux bras d'un seed doivent etre consecutifs : c'est l'appariement")
    assert r["n"] == 3


def test_run_q2_COUNTS_the_dreams_of_the_ON_arm_only(monkeypatch):
    """`total_dreams_seen` est le controle POSITIF de toute la sonde : il repond a « le reve a-t-il
    seulement eu lieu ? ». Reponse connue : bras ON = 4 agents a 5 reves (= 20 par seed, 60 sur
    3 seeds) ; bras OFF dote de 7 reves par agent alors qu'il ne porte PAS l'organe. Si le compteur
    additionnait les deux bras il rendrait 60 + 168 = 228. Un compteur qui melangerait les bras
    ferait passer pour « le reve a eu lieu » un bras ou il ne peut pas avoir lieu."""
    DP, r = _run(monkeypatch, _cohorte_mixte(100, 100, dreams=5), _cohorte(50, dreams=7))
    assert r["total_dreams_seen"] == 60, r["total_dreams_seen"]


def test_run_q2_SPLITS_the_ON_arm_on_the_dream_count_in_both_directions(monkeypatch):
    """`q2a_delta` = competence(reveurs) - competence(non-reveurs), DANS le bras ON, seuil
    `total_dreams > 0`. Reponse connue x3 :
      - reveurs 160 / autres 40 -> 0.8 - 0.2 = +0.6 (le reve paye INTRA population) ;
      - reveurs 40 / autres 160 -> -0.6. Branche NEGATIVE obligatoire (E1) : un instrument qui
        rendrait `abs()` ou qui intervertirait les groupes passerait le seul cas positif ;
      - un agent a EXACTEMENT 0 reve appartient aux non-reveurs (le seuil est STRICT) : reveurs 160
        (dreams=1) / autres 40 (dreams=0) rend le meme +0.6.
    Dans les trois cas le ratio apparie reste 1.0 (mediane des ages ON = 100 = OFF), donc le
    contraste intra-population est isole."""
    DP, r = _run(monkeypatch, _cohorte_mixte(160, 40), _cohorte(100))
    assert r["q2a_delta"] == pytest.approx(0.6), r
    assert r["q2b_ratio"] == 1.0

    _, r = _run(monkeypatch, _cohorte_mixte(40, 160), _cohorte(100))
    assert r["q2a_delta"] == pytest.approx(-0.6), "le split doit savoir rendre un contraste NEGATIF"

    _, r = _run(monkeypatch, _cohorte_mixte(160, 40, dreams=1), _cohorte(100))
    assert r["q2a_delta"] == pytest.approx(0.6), "le seuil du split est `> 0`, strictement"


def test_run_q2_REPLICATES_on_the_SEED_not_on_the_agent(monkeypatch):
    """Unite de replication = le SEED (question 3 du pre-vol), et agregation par MEDIANE.
    Reponse connue : 5 seeds dont UN aberrant -- ratios imposes [4.0, 1.0, 1.0, 1.0, 1.0].
    Mediane = 1.0 ; MOYENNE = 1.6. L'instrument doit rendre 1.0. Et `n` doit valoir 5 (le nombre de
    SEEDS) que les cohortes contiennent 8 ou 400 agents : une agregation sur les AGENTS gonflerait
    le n d'un facteur 800 sans changer la valeur -- la pseudo-replication est invisible dans le
    chiffre publie, seulement dans le n. On verifie enfin que la cellule aberrante EST bien la
    seule favorable (sinon le test passerait sur un instrument qui aplatit tout)."""
    def _on(seed):
        age = 200 if seed == 0 else 100          # competence 1.0 (seed aberrant) sinon 0.5
        return _cohorte_mixte(age, age)

    for taille in (8, 400):
        def _off(seed, _n=taille):
            return _cohorte(50 if seed == 0 else 100, n=_n)   # 0.25 (seed aberrant) sinon 0.5

        DP, r = _run(monkeypatch, _on, _off, seeds=[0, 1, 2, 3, 4])
        assert r["per_seed_ratio"] == pytest.approx([4.0, 1.0, 1.0, 1.0, 1.0]), r
        assert r["q2b_ratio"] == pytest.approx(1.0), "mediane attendue (1.0), pas la moyenne (1.6)"
        assert r["n"] == 5, "l'unite de replication est le SEED, pas l'agent"
        assert r["n_favorable"] == 1
        # `sign_p` est calcule sur les cellules EFFECTIVES (ratio != 1.0), ici UNE seule -> 1.0,
        # alors que `n` publie 5. Les deux denominateurs coexistent dans le meme dict : fige ici
        # pour qu'un lecteur ne lise pas « 1/5, p=1.0 » comme un test sur 5 replicats.
        assert r["sign_p"] == 1.0


def test_run_q2_REFUSES_degenerate_arguments_BEFORE_any_era(monkeypatch):
    """Garde d'arguments (deja calibree le 2026-09-06) -- ce test verifie OU elle est posee. Reponse
    connue : cohorte de seeds vide, num_agents <= 0, max_ticks <= 0 -> ValueError ET ZERO appel a
    `run_era_organ` (la fausse ere COMPTE ses appels). Contre-epreuve appariee dans le meme test :
    un appel valide franchit la garde et declenche exactement 2 appels -- sans elle, une garde qui
    refuserait TOUT passerait ce test (classe E1)."""
    compteur = {"n": 0}

    def _compte(*a, **kw):
        compteur["n"] += 1
        return _cohorte(100)

    DP = _injecte(monkeypatch, _compte)
    for args in (([], "stoneage", 8, 5, None),
                 ([0, 1], "stoneage", 0, 5, None),
                 ([0, 1], "stoneage", 8, 0, None)):
        with pytest.raises(ValueError, match="degenere"):
            DP.run_q2(*args)
        assert compteur["n"] == 0, ("la garde doit etre EN TETE, avant toute ere", args)

    DP.run_q2([0], "stoneage", 8, 5, None)
    assert compteur["n"] == 2, "contre-epreuve : un appel valide DOIT franchir la garde"


def test_run_q2_ratio_follows_the_FOUNDERS_when_there_is_no_reproductive_explosion(monkeypatch):
    """CONTRE-EPREUVE APPARIEE du xfail « founder » ci-dessous. Ici les deux bras ne contiennent QUE
    des fondateurs (aucun ne naissant en cours d'ere) : lecture « tous agents » et lecture
    « fondateurs » COINCIDENT, et le ratio doit suivre les fondateurs -- 1.0 a ages egaux, 2.0 quand
    le bras ON double leur age. Ce test reste vrai que `run_q2` soit corrige ou non ; c'est lui qui
    prouve que le xfail suivant impute la faute a l'EXPLOSION REPRODUCTIVE et pas au ratio."""
    DP, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(100))
    assert r["q2b_ratio"] == 1.0
    _, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(50))
    assert r["q2b_ratio"] == pytest.approx(2.0)


def test_run_q2_delta_is_a_CONTRAST_when_the_reference_group_EXISTS(monkeypatch):
    """CONTRE-EPREUVE APPARIEE du xfail « groupe vide » ci-dessous, et cas NEGATIF de la porte.
    Reponse connue x2, a ratio apparie tenu FIXE a 1.0 (mediane des ages ON = OFF = 100) pour que
    seul `q2a_delta` puisse actionner la porte :
      - 4 reveurs ET 4 non-reveurs de MEME age -> q2a_delta = 0.0 -> SURVIT_PAS_PAYE. L'organe n'a
        aucun effet et l'instrument le dit. Le xfail suivant reprend EXACTEMENT cette dose en vidant
        le seul groupe de reference ;
      - reveurs 160 / non-reveurs 40 -> q2a_delta = +0.6 -> SURVIT_ET_PAYE. Sans ce second cas, un
        instrument qui rendrait 0.0 quoi qu'il arrive passerait le premier (classe E1) : c'est la
        branche qui prouve que `q2a_delta` peut, SEUL, faire basculer la porte."""
    DP, r = _run(monkeypatch, _cohorte_mixte(100, 100), _cohorte(100))
    assert r["q2a_delta"] == pytest.approx(0.0) and r["q2b_ratio"] == 1.0
    assert DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"]) == "SURVIT_PAS_PAYE"

    DP, r = _run(monkeypatch, _cohorte_mixte(160, 40), _cohorte(100))
    assert r["q2a_delta"] == pytest.approx(0.6) and r["q2b_ratio"] == 1.0
    assert DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"]) == "SURVIT_ET_PAYE"


# ======================================================================================================
# 3. DEFAUTS REELS -- exposes, non corriges (consigne). `xfail(strict=True)`.
# ======================================================================================================

# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la passe de correction) : un groupe de reference VIDE produisait un payoff chiffre depuis zero mesure.
def test_run_q2_REFUSES_to_fabricate_a_payoff_from_an_EMPTY_reference_group(monkeypatch):
    """Reponse connue : bras ON = 8 agents qui revent TOUS (age 100), bras OFF = 8 agents de MEME
    age. Effet reel de l'organe : ZERO. Contre-epreuve appariee (test passant ci-dessus) : les
    memes ages avec 4 non-reveurs dans le bras ON rendent bien 0.0 et SURVIT_PAS_PAYE."""
    DP, r = _run(monkeypatch, _cohorte(100, dreams=3), _cohorte(100))
    assert r["q2b_ratio"] == 1.0, "controle : les deux bras sont identiques, le ratio DOIT valoir 1.0"
    verdict = DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"])
    # Dose-reponse de l'ARTEFACT (rapportee dans le message d'echec) : q2a_delta suit l'age absolu.
    _, r20 = _run(monkeypatch, _cohorte(20, dreams=3), _cohorte(20))
    assert math.isnan(r["q2a_delta"]) or r["q2a_delta"] <= 0.02, (
        "effet NUL de l'organe et pourtant q2a_delta=%.3f (age 100) / %.3f (age 20) = la competence "
        "ABSOLUE des reveurs, faute de groupe de reference ; la porte prononce %s"
        % (r["q2a_delta"], r20["q2a_delta"], verdict))


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la passe de correction) : les cohortes fondatrices etaient diluees au lieu d'etre appariees.
def test_run_q2_MATCHES_the_founding_cohorts_instead_of_diluting_them(monkeypatch):
    """Reponse connue, en forme close. Bras ON : 12 fondateurs d'age 100 + 240 nes-tard d'age 5
    (l'explosion x20 documentee dans le code). Bras OFF : les MEMES 12 fondateurs d'age 100, sans
    explosion. Apparie sur les fondateurs -> mediane 100 des deux cotes -> ratio 1.0.
    Sur TOUS les agents -> mediane ON = 5 (les nes-tard sont 240 sur 252) -> competence 0.025 contre
    0.5 -> ratio 0.05. Contre-epreuve appariee (test passant ci-dessus) : SANS explosion, les deux
    lectures coincident et le ratio vaut bien 1.0 puis 2.0 a la dose."""
    on = ([_agent(100, dreams=3, founder=True) for _ in range(12)]
          + [_agent(5, dreams=3, founder=False) for _ in range(240)])
    off = [_agent(100, dreams=0, founder=True) for _ in range(12)]
    DP, r = _run(monkeypatch, on, off)
    assert r["q2b_ratio"] == pytest.approx(1.0), (
        "cohortes FONDATRICES identiques (mediane 100 des deux cotes) et pourtant q2b_ratio=%.4f : "
        "la mesure est portee par les 240 nes-tard du bras ON, pas par l'organe. La porte prononce %s"
        % (r["q2b_ratio"], DP.dreaming_verdict(0.25, -0.25, 0.0, r["q2b_ratio"])))


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la passe de correction) : les seeds sans aucune mesure disparaissaient du rapport au lieu d'etre NOMMES.
def test_run_q2_REPORTS_the_seeds_where_NOTHING_could_be_measured(monkeypatch):
    """Reponse connue : les deux bras s'eteignent a la naissance (age 0 partout) sur les 3 seeds.
    Il n'y a AUCUNE information. Le dict rendu aujourd'hui est indiscernable de celui d'une egalite
    reellement mesuree."""
    DP, r = _run(monkeypatch, _cohorte(0, dreams=0), _cohorte(0))
    expose = any(k in r for k in ("n_degenerate", "n_ecartees", "n_effective", "n_informative"))
    assert expose or math.isnan(r["q2b_ratio"]), (
        "3 seeds sans AUCUNE observation et le dict publie est %r ; la porte prononce %s"
        % ({k: r[k] for k in ("q2a_delta", "q2b_ratio", "n", "n_favorable", "sign_p")},
           DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"])))


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la passe de correction) : une division par un denominateur ETEINT passait sans un mot.
def test_run_q2_REFUSES_to_divide_by_an_EXTINCT_denominator(monkeypatch):
    """Reponse connue : bras OFF eteint a la naissance (age 0 -> competence 0.0), bras ON survivant
    UN tick (age 1 -> competence 0.005). Ni l'un ni l'autre n'a survecu ; la difference est d'un
    tick. Le cas symetrique (les DEUX a 0) est, lui, correctement neutralise -- c'est cette
    asymetrie que le test mesure."""
    DP, r = _run(monkeypatch, _cohorte(1, dreams=3), _cohorte(0))
    assert r["q2b_ratio"] < DP.RATIO_CAP or math.isnan(r["q2b_ratio"]), (
        "un ecart d'UN TICK entre deux populations eteintes publie q2b_ratio=%.1f (le PLAFOND), "
        "n_favorable=%d/%d, sign_p=%.4f, et la porte prononce %s"
        % (r["q2b_ratio"], r["n_favorable"], r["n"], r["sign_p"],
           DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"])))


# NON-REGRESSION (defaut CORRIGE le 2026-09-08 par la refutation) : la garde consommait `seeds` -> boucle vide et medianes retombant sur `else 0.0`/`else 1.0`.
def test_run_q2_REFUSES_to_fabricate_a_verdict_from_a_CONSUMED_iterator(monkeypatch):
    """Reponse connue : la dose est ECRASANTE (ON age 100 / OFF age 50 -> ratio 2.0 sur 3 seeds,
    exactement le cas POSITIF du premier test). Passes en generateur, les 3 seeds sont manges par la
    garde et l'instrument rend le dict du « rien a signaler »."""
    DP = _injecte(monkeypatch, _par_bras(_cohorte_mixte(100, 100), _cohorte(50)))
    r = DP.run_q2((s for s in (0, 1, 2)), "stoneage", 8, 5, None)
    assert r["n"] == 3 and r["q2b_ratio"] == pytest.approx(2.0), (
        "3 seeds manges par la garde : n=%d, q2b_ratio=%r, per_seed_ratio=%r, et la porte prononce %s"
        % (r["n"], r["q2b_ratio"], r["per_seed_ratio"],
           DP.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"])))
