"""Calibration de `tools/evo_memory_inworld.py` (EVO-003) -- les DEUX defauts corriges le 2026-09-08.

Ces cas completent ceux de `tests/sandbox/test_orchestrator_injection.py` (injection a dose connue de
`evolve_inworld` / `benchmark_discrimination`). Ils visent la COUCHE QUI AGREGE, jamais le monde :
aucun de ces tests ne construit de biosphere, donc aucun ne prend le bail `kuzu`.

Deux defauts REELS, chacun expose par une reponse connue avant d'etre corrige :

(a) APPARIEMENT PAR SEED. `main` filtrait les `nan` BRAS PAR BRAS -> il comparait des medianes
    calculees sur des SEEDS DIFFERENTS, alors que le module DECLARE le seed comme unite de
    replication et le contraste comme within-subject. Cas limite : seed 0 mesurable seulement en ON
    (0.90), seed 1 seulement en OFF (0.10) -> ZERO paire, et la synthese affirmait pourtant un ecart
    de 0.80 fabrique a partir d'une ABSENCE de mesure. Corrige par `_paired_occlusion_discs`.

(b) PSEUDO-REPLICATION. Le seed determine ENTIEREMENT le point de tirage (`np.random.seed(seed)` en
    tete de `evolve_inworld`, `np.random.seed(1000 + seed)` dans `benchmark_discrimination`) : deux
    occurrences du meme seed sont le MEME tirage, pas deux replicats. Elles gonflaient le `n` publie.
    Corrige par une deduplication ANNONCEE, posee AVANT toute evolution.

⚠️ Discipline E1 : pour CHAQUE comportement ajoute, le cas NEGATIF apparie est ecrit juste apres --
un appariement qui ecarterait TOUJOURS, ou une deduplication qui ecraserait TOUJOURS, passeraient les
cas positifs sans rien prouver.
"""
import pytest

import tools.evo_memory_inworld as M


# ---------------------------------------------------------------------------------------------
# Harnais d'injection (aucun monde construit)
# ---------------------------------------------------------------------------------------------

def _cell(disc, enc=10):
    """Cellule factice de `benchmark_discrimination` a discrimination IMPOSEE. disc=None -> nan
    (aucune rencontre : la reponse juste est INDETERMINE, surtout pas 0.0)."""
    if disc is None:
        return {"big_kills": 0, "leurre_hits": 0, "disc": float("nan"), "med_age": 0.0, "encounters": 0}
    big = int(round(disc * enc))
    return {"big_kills": big, "leurre_hits": enc - big, "disc": float(disc), "med_age": 1.0,
            "encounters": enc}


def _row(seed, on_occ, off_occ):
    """Ligne de `run_contrast` reduite a ce que la synthese relit."""
    return {"seed": seed, "score_on": 1.0, "score_off": 1.0, "nodes_on": 1, "nodes_off": 1,
            "on_occ": _cell(on_occ), "on_vis": _cell(0.5),
            "off_occ": _cell(off_occ), "off_vis": _cell(0.5)}


def _injecte(monkeypatch, evolue, benchmarke):
    monkeypatch.setattr(M, "evolve_inworld", evolue)
    monkeypatch.setattr(M, "benchmark_discrimination", benchmarke)


def _champion(tag):
    return {"genome": tag, "score": 100.0, "nodes": 12}


# =============================================================================================
# (a) APPARIEMENT PAR SEED -- `_paired_occlusion_discs`
# =============================================================================================

def test_pairing_DROPS_a_seed_measurable_in_only_one_arm():
    """Reponse connue : seed 0 mesurable en ON seulement, seed 1 en OFF seulement -> ZERO paire.
    Les deux listes doivent etre VIDES (l'aval dira « n/a »), et les 2 seeds comptes comme ecartes.
    Aucune valeur ne doit survivre : c'etait exactement le 0.90-contre-0.10 fabrique."""
    app = M._paired_occlusion_discs([_row(0, 0.90, None), _row(1, None, 0.10)])
    assert app["on"] == [] and app["off"] == []
    assert app["n_ecartes"] == 2 and app["seeds_ecartes"] == [0, 1]
    assert app["seeds"] == []


def test_pairing_KEEPS_everything_when_every_seed_has_both_arms():
    """CAS NEGATIF APPARIE (E1) : si l'appariement ecartait toujours, le test ci-dessus passerait
    sans rien prouver. Ici les 3 seeds sont mesurables des DEUX cotes -> RIEN ne doit tomber, et
    l'ordre des seeds doit etre preserve (la mediane appariee doit rester lisible ligne a ligne)."""
    rows = [_row(0, 0.8, 0.1), _row(1, 0.9, 0.2), _row(2, 1.0, 0.3)]
    app = M._paired_occlusion_discs(rows)
    assert app["on"] == [0.8, 0.9, 1.0] and app["off"] == [0.1, 0.2, 0.3]
    assert app["seeds"] == [0, 1, 2]
    assert app["n_ecartes"] == 0 and app["seeds_ecartes"] == []


@pytest.mark.parametrize("bras_manquant", ["on", "off"])
def test_pairing_drops_on_EITHER_missing_arm_and_never_substitutes(bras_manquant):
    """SPECIFICITE, dans les DEUX sens. Un filtre qui ne regarderait qu'UN bras laisserait passer la
    moitie des cas. Reponse connue : seed 0 a un bras manquant, seed 1 est complet -> il reste
    exactement UNE paire, celle du seed 1, et la valeur du seed 0 n'entre dans AUCUNE mediane
    (pas de valeur de remplacement fabriquee)."""
    r0 = _row(0, None, 0.99) if bras_manquant == "on" else _row(0, 0.99, None)
    app = M._paired_occlusion_discs([r0, _row(1, 0.10, 0.20)])
    assert app["seeds"] == [1]
    assert app["on"] == [0.10] and app["off"] == [0.20]
    assert 0.99 not in app["on"] and 0.99 not in app["off"]
    assert app["n_ecartes"] == 1 and app["seeds_ecartes"] == [0]


def test_pairing_KEEPS_the_three_lists_INDEX_ALIGNED_seed_by_seed():
    """LE CONTRAT PORTEUR, qui n'etait pin par AUCUN cas (trouve en refutation, 2026-09-08).

    Tout le correctif existe pour qu'on ne compare plus des medianes calculees sur des SEEDS
    DIFFERENTS. Or les cas ci-dessus ne verifient que le CONTENU des listes ; ils passent tous si
    `off` est renvoye trie. Mesure : la mutation `\"off\": sorted(...)` survit a la suite ENTIERE
    (0 test rougi). Aujourd'hui c'est sans effet sur ce que `main` publie -- il median chaque bras
    separement -- mais la fonction PROMET un appariement, et le pas suivant naturel (test des signes
    / Wilcoxon apparie sur `zip(on, off)`) serait alors FAUX en silence, exactement le defaut que ce
    correctif corrige. On grave donc la CORRESPONDANCE POSITIONNELLE, pas seulement le contenu.

    Fixture choisie pour DISCRIMINER : seeds [3, 1, 2] et valeurs non triees dans les DEUX bras ->
    trier l'un OU l'autre OU les seeds change le resultat."""
    rows = [_row(3, 0.20, 0.70), _row(1, 0.90, 0.30), _row(2, 0.50, 0.10)]
    app = M._paired_occlusion_discs(rows)
    attendu = [(r["seed"], r["on_occ"]["disc"], r["off_occ"]["disc"]) for r in rows]
    assert list(zip(app["seeds"], app["on"], app["off"])) == attendu

    # CAS NEGATIF APPARIE (E1) : l'assertion ci-dessus a-t-elle le pouvoir de REFUSER ? Elle ne le
    # peut QUE si la fixture n'est deja triee dans aucune des trois listes -- sinon un tri silencieux
    # rendrait le MEME resultat et le cas serait tautologique. On le verifie, au lieu de l'esperer.
    assert sorted(app["on"]) != app["on"], "fixture non discriminante : `on` est deja trie"
    assert sorted(app["off"]) != app["off"], "fixture non discriminante : `off` est deja trie"
    assert sorted(app["seeds"]) != app["seeds"], "fixture non discriminante : seeds deja tries"


def test_pairing_on_an_empty_row_list_is_INDETERMINATE_not_zero():
    """Entree VIDE -> aucune affirmation de fond. Les listes sont vides (l'aval imprime « n/a »),
    et surtout PAS une mediane 0.0. Zero seed ecarte : il n'y avait rien a ecarter."""
    app = M._paired_occlusion_discs([])
    assert app["on"] == [] and app["off"] == [] and app["seeds"] == []
    assert app["n_ecartes"] == 0 and app["seeds_ecartes"] == []
    assert M._med(app["on"]) == "n/a" and M._med(app["off"]) == "n/a"


# --- la couche qui AFFIRME : `main` DIT combien de seeds ont ete ecartes -----------------------

def _synthese(monkeypatch, capsys, doses, n_seeds):
    """Chaine complete `main -> run_contrast -> {evolve,benchmark} injectes`, sans aucun monde.
    `doses[(bras, seed)]` = discrimination SOUS OCCULTATION ; absente -> nan."""
    monkeypatch.setenv("EVO3_SEEDS", str(n_seeds))
    monkeypatch.setenv("EVO3_ERAS", "2")
    monkeypatch.setenv("EVO3_TICKS", "5")
    monkeypatch.setenv("EVO3_AGENTS", "4")

    def _evolue(memory_regime, seed, *a, **k):
        return _champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    def _bench(genome, memory_regime, seed, **k):
        bras, s = genome.split("-")[1], int(genome.split("-s")[1])
        if not memory_regime:
            return _cell(0.5)
        return _cell(doses.get((bras, s)))

    _injecte(monkeypatch, _evolue, _bench)
    M.main()
    return capsys.readouterr().out


def test_main_ANNOUNCES_how_many_seeds_the_pairing_discarded(monkeypatch, capsys):
    """Reponse connue : 3 seeds, un seul (le 1) mesurable des deux cotes -> 1 apparie, 2 ecartes,
    et la synthese doit le DIRE (« combien de seeds ont ete ecartes », exigence du correctif).
    Une synthese qui tait ses exclusions publie un n sans son denominateur."""
    out = _synthese(monkeypatch, capsys, {("ON", 1): 0.60, ("OFF", 1): 0.40}, n_seeds=3)
    ligne = [ln for ln in out.splitlines() if "appariement PAR SEED" in ln][0]
    assert "1 seed(s) apparié(s) [1]" in ligne
    assert "2 écarté(s) [0, 2]" in ligne
    assert "méd=0.60 (n=1)" in out and "méd=0.40 (n=1)" in out


def test_main_ANNOUNCES_zero_discarded_when_nothing_is_discarded(monkeypatch, capsys):
    """CAS NEGATIF APPARIE (E1) de l'annonce : les 3 seeds sont complets -> la ligne d'appariement
    doit annoncer 3 apparies et ZERO ecarte. Sans lui, une annonce cablee (« toujours des ecartes »)
    passerait le test precedent."""
    doses = {("ON", 0): 0.8, ("ON", 1): 0.9, ("ON", 2): 1.0,
             ("OFF", 0): 0.1, ("OFF", 1): 0.2, ("OFF", 2): 0.3}
    out = _synthese(monkeypatch, capsys, doses, n_seeds=3)
    ligne = [ln for ln in out.splitlines() if "appariement PAR SEED" in ln][0]
    assert "3 seed(s) apparié(s) [0, 1, 2]" in ligne
    assert "0 écarté(s) []" in ligne
    assert "méd=0.90 (n=3)" in out and "méd=0.20 (n=3)" in out


# =============================================================================================
# (b) PSEUDO-REPLICATION -- deduplication ANNONCEE, posee AVANT toute evolution
# =============================================================================================

def _compteur_evolutions(monkeypatch, disc=0.5):
    """Injecte des faux `evolve_inworld`/`benchmark_discrimination` qui COMPTENT leurs appels."""
    vus = []

    def _evolue(memory_regime, seed, *a, **k):
        vus.append(seed)
        return _champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    _injecte(monkeypatch, _evolue, lambda g, r, s, **k: _cell(disc))
    return vus


def test_run_contrast_DEDUPLICATES_repeated_seeds_and_SAYS_it(monkeypatch, capsys):
    """Reponse connue : [5, 5, 5] ne contient qu'UN point de tirage. Il doit rester UNE ligne, et
    la deduplication doit etre ANNONCEE (une exclusion silencieuse est un n publie sans son
    denominateur). Sans ce comportement, la synthese lisait n=3 pour 1 seul replicat."""
    _compteur_evolutions(monkeypatch)
    rows = M.run_contrast([5, 5, 5])
    assert len(rows) == 1 and rows[0]["seed"] == 5
    out = capsys.readouterr().out
    assert "DUPLIQUE" in out and "2 seed(s)" in out


def test_run_contrast_does_NOT_deduplicate_DISTINCT_seeds(monkeypatch, capsys):
    """CAS NEGATIF APPARIE (E1) : une deduplication qui ecraserait tout rendrait toujours 1 ligne et
    passerait le test precedent. Ici les 3 seeds sont DISTINCTS -> 3 lignes, dans l'ordre, et AUCUNE
    annonce de doublon (l'avertissement doit savoir NE PAS se declencher)."""
    _compteur_evolutions(monkeypatch)
    rows = M.run_contrast([7, 5, 9])
    assert [r["seed"] for r in rows] == [7, 5, 9]
    assert "DUPLIQUE" not in capsys.readouterr().out


def test_run_contrast_PRESERVES_first_occurrence_order_when_deduplicating(monkeypatch):
    """Un doublon ne doit pas REORDONNER la trace : premiere apparition conservee. Un
    `sorted(set(...))` changerait silencieusement l'ordre de la trace par seed que le run imprime.

    ⚠️ FIXTURE CORRIGEE EN REFUTATION (2026-09-08). L'entree d'origine [7, 5, 7, 5, 9] rend [7, 5, 9]
    en ordre de PREMIERE apparition **comme** en ordre de DERNIERE apparition -- mesure : les deux
    formes sont bit-identiques sur cette entree, donc la mutation « garder la derniere occurrence »
    survivait a la suite entiere. Le cas prouvait donc moins que ce que son nom annonce : il
    excluait `sorted`, pas l'ordre inverse. [7, 5, 7, 9] separe les TROIS formes -- premiere
    [7, 5, 9] / derniere [5, 7, 9] / triee [5, 7, 9] -- et c'est LUI qui porte la preuve."""
    _compteur_evolutions(monkeypatch)
    assert [r["seed"] for r in M.run_contrast([7, 5, 7, 5, 9])] == [7, 5, 9]

    rows = M.run_contrast([7, 5, 7, 9])
    assert [r["seed"] for r in rows] == [7, 5, 9], "ordre de PREMIERE apparition non conserve"
    # le cas est-il discriminant ? les deux formes fautives donnent bien autre chose, ici et pas
    # seulement en principe (sans quoi l'assertion ci-dessus ne prouverait rien -- E1).
    assert list(reversed(list(dict.fromkeys(reversed([7, 5, 7, 9]))))) == [5, 7, 9]
    assert sorted({7, 5, 7, 9}) == [5, 7, 9]


def test_run_contrast_deduplicates_BEFORE_spending_a_single_evolution(monkeypatch):
    """OU la garde est posee, pas seulement QU'elle agit. Un seed duplique ne doit couter AUCUNE
    evolution : [5, 5] -> exactement 2 appels (ON et OFF du seed 5), pas 4. Une deduplication faite
    APRES coup rendrait le bon `n` en payant deux fois le run le plus cher du module."""
    vus = _compteur_evolutions(monkeypatch)
    M.run_contrast([5, 5])
    assert vus == [5, 5], vus          # ON puis OFF, une seule fois -- pas [5, 5, 5, 5]


def test_run_contrast_still_REFUSES_degenerate_arguments_before_deduplicating(monkeypatch):
    """NON-REGRESSION de la garde d'entree : la deduplication ne doit pas s'intercaler devant elle.
    Une liste vide reste un refus explicite (jamais une agregation vide lue comme un negatif), et
    un iterateur non vide reste materialise sans etre consomme."""
    def _bombe(*a, **k):
        raise AssertionError("evolution appelee malgre un argument degenere")

    _injecte(monkeypatch, _bombe, _bombe)
    with pytest.raises(ValueError, match="degenere"):
        M.run_contrast([])
    with pytest.raises(ValueError, match="degenere"):
        M.run_contrast([0], eras=0)

    _compteur_evolutions(monkeypatch)
    assert len(M.run_contrast(iter([0, 1]))) == 2
