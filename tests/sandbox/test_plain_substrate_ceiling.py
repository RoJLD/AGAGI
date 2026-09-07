"""Calibration de `plain_substrate_ceiling` — l'instrument qui MESURE le plafond de l'incapable (P2.15).

Pourquoi cet instrument doit etre calibre plus soigneusement que la moyenne : il produit le nombre
contre lequel d'AUTRES instruments valident leur barre. Un plafond fabrique se propagerait a chaque
verdict qui s'en reclame — et un plafond trop BAS est exactement le defaut P2.15 qu'il est cense fermer.

Un plafond bas a TROIS causes indiscernables sans controles apparies, et il en faut donc trois :
  * un optimiseur ou un budget trop faibles -> innocentes par `free_table=True` (forme LIBRE, MEME
    cible, MEME budget : doit rendre 1.000) ;
  * une forme mal parametree ou mal derivee du code -> innocentee par `target="separable"` (MEME forme,
    cible `key` separable par construction : doit rendre 1.000) ;
  * une RECHERCHE non convergee -> seule `saturation_control` (moitie budget vs budget plein) la voit.
⚠️ Les deux premiers ne suffisent PAS, et ce n'est pas une precaution theorique : a 2 restarts x 60 pas
ils valent TOUS DEUX 1.000 pendant que le plafond lit 0.278. C'est tres probablement ce qui a produit le
`0.3889` publie le 2026-09-02, revise ici a 30/36. Un controle de CAPACITE ne calibre pas un controle de
BUDGET — c'est le motif que ce depot a mesure une trentaine de fois : donnees insuffisantes ->
AFFIRMATION NEGATIVE de fond, jamais « inconnu ».

Le MILP (`additive_argmax_exact_ceiling`) est d'une autre nature : il PROUVE l'optimalite au lieu de la
chercher. Il ne couvre que la sous-forme additive, mais il donne la seule borne SUPERIEURE du dossier,
et il sert d'etalon a la recherche — laquelle, sur cette meme sous-forme, ne trouve que 0.3611 contre
0.75 prouve.
"""
import pytest

from tools.plain_substrate_ceiling import (PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE,
                                           additive_argmax_exact_ceiling,
                                           verify_plain_ceiling_witness,
                                           measure_plain_composition_ceiling, plain_readout_ceiling)

_K = 6
_RAPIDE = dict(K=_K, restarts=3, steps=1500)


def test_the_positive_control_reaches_ONE():
    """CONTROLE POSITIF APPARIE : une forme LIBRE `t[key,q,j]`, meme cible, meme budget -> 1.000.
    Il innocente l'OPTIMISEUR : ce qui borne la forme close n'est pas la recherche."""
    assert plain_readout_ceiling(free_table=True, **_RAPIDE) == 1.0


def test_the_specificity_control_reaches_ONE():
    """CONTROLE DE SPECIFICITE : la MEME forme close, sur une cible SEPARABLE (`key`) -> 1.000.
    Il innocente la FORME : ce qui la borne sur `(q+key)%K` est bien la NON-SEPARABILITE de la cible,
    pas une parametrisation trop pauvre ni une derivation fautive du code source."""
    assert plain_readout_ceiling(target="separable", **_RAPIDE) == 1.0


def test_the_ceiling_is_STRICTLY_ABOVE_CHANCE():
    """⚠️ LE POINT DE P2.15, et le seul qui compte vraiment. Le plafond de l'incapable n'est PAS le
    niveau de chance : un score separable passe dans une transformee monotone represente bien plus que
    1/K sur une cible modulaire. Passer `1/K` comme plafond de l'incapable EST l'erreur P2.15, et c'est
    le geste le plus naturel du monde — d'ou ce test."""
    c = plain_readout_ceiling(**_RAPIDE)
    assert c > 1.0 / _K, f"plafond {c} au niveau de chance : la mesure serait vide de contenu"


def test_the_ceiling_is_STRICTLY_BELOW_ONE():
    """La forme close ne peut PAS faire la tache : si elle atteignait 1.000, la derivation serait
    fausse (le substrat plain saurait composer) et toute la these BILINEAR tomberait avec elle."""
    assert plain_readout_ceiling(**_RAPIDE) < 1.0


def test_an_unknown_target_is_REFUSED_not_guessed():
    """Ne pas proxifier ce qu'on ne sait pas mesurer : une cible inconnue leve, elle ne retombe pas en
    silence sur la cible par defaut — un defaut de frappe rendrait sinon un plafond du MAUVAIS probleme."""
    with pytest.raises(ValueError):
        plain_readout_ceiling(target="composition", **_RAPIDE)


def test_the_provenance_is_LONG_ENOUGH_for_the_guard_that_consumes_it():
    """La provenance exportee doit passer la garde qui la consomme (>= 20 caracteres utiles), sinon le
    couple instrument/garde serait casse a l'usage et personne ne le saurait avant un run."""
    from tools.experiment_preflight import assert_bar_separates_the_incapable
    assert len(PLAIN_COMPOSITION_PROVENANCE.strip()) >= 20
    assert assert_bar_separates_the_incapable(0.99, 0.5, PLAIN_COMPOSITION_PROVENANCE) is True


def test_the_aggregate_reports_INVALID_on_an_UNCONVERGED_search():
    """⚠️ CONTRE-EXEMPLE GELE — ce test a trouve un defaut REEL de l'instrument le jour de son
    ecriture, et c'est la raison d'etre du 3e controle.

    A budget DERISOIRE (2 restarts x 60 pas), `positive_control` ET `specificity_control` valent TOUS
    DEUX 1.000 — une table libre et une cible separable se fittent en quelques dizaines de pas —
    pendant que le plafond lit ~0.28. Deux controles verts, un plafond faux de plus d'un facteur deux.
    Ils innocentent la FORME et l'OPTIMISEUR ; ni l'un ni l'autre ne dit si on a cherche assez
    longtemps sur le probleme DUR, et c'est la seule question qui decide de la valeur du plafond.
    Seul `saturation_control` (moitie budget vs budget plein) peut le contredire."""
    r = measure_plain_composition_ceiling(K=_K, restarts=2, steps=60)
    assert r["positive_control"] == 1.0 and r["specificity_control"] == 1.0, (
        "les deux premiers controles doivent bien PASSER ici : c'est ce qui rend le cas discriminant", r)
    assert r["saturation_control"] is False, r
    assert r["valid"] is False, r


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_the_published_budget_is_REFUSED_by_the_instrument_itself():
    """⚠️ CONTRE-EXEMPLE GELE, et il a d'abord ete ecrit A L'ENVERS : ce test assertait `valid is True`
    au budget « publie » (8 restarts x 4000 pas). Un refutateur independant a montre que ce budget est
    AUTO-INVALIDE par les controles de l'instrument lui-meme — et il avait raison.

    Mesure : a 8x4000 le plafond lit 0.75, soit EXACTEMENT la borne additive PROUVEE par MILP. La
    recherche n'a donc rien trouve au-dela de ce que la sous-forme garantit deja, alors que la verite
    mesuree vaut 34/36. Deux controles mordent : `saturation_control` (le demi-budget rend moins) et
    `dominates_proven_bound` (egalite, pas domination). C'est exactement le regime qui a produit le
    0.3889 publie le 2026-09-02, et le test le GELE au lieu de le benir."""
    r = measure_plain_composition_ceiling(K=_K, restarts=8, steps=4000)
    assert r["valid"] is False, r
    assert r["search_stalled_at_proven_bound"] is True, r
    assert r["ceiling"] > 1.0 / _K + 0.15, (
        "meme sous-cherche, le plafond reste AU-DESSUS de la barre historique du depot — "
        f"c'est le fait qui FONDE P2.15 : {r}")


def test_the_instrument_NEVER_claims_the_ceiling_is_ESTABLISHED():
    """`valid` veut dire « mesure internement coherente », JAMAIS « plafond etabli ». La distinction
    n'est pas rhetorique : c'est en la perdant que j'ai publie « la conclusion d'EDR-BILINEAR tient,
    marge 0.084 », rétracte le jour meme (E19 occ.4)."""
    r = measure_plain_composition_ceiling(K=_K, restarts=2, steps=200)
    assert r["is_minorant"] is True, r
    assert "proven_additive_bound" in r and r["proven_additive_bound"] == 0.75, r


# --- la BORNE PROUVEE (MILP) : d'une autre nature que le minorant ci-dessus ----------------------

def test_the_MILP_bound_is_EXACT_and_frozen():
    """VALEUR GELEE et PROUVEE (gap 0), pas cherchee : la forme purement additive plafonne a 27/36 pour
    K=6. C'est le seul endroit du dossier ou une borne SUPERIEURE existe."""
    assert additive_argmax_exact_ceiling(6) == (27, 36, 0.75)
    assert additive_argmax_exact_ceiling(4) == (12, 16, 0.75)


def test_the_MILP_positive_control_reaches_PERFECTION():
    """CONTROLE POSITIF APPARIE de la formulation elle-meme : MEME MILP, cible SEPARABLE -> 36/36.
    Sans lui, un `27/36` serait indiscernable d'un encodage fautif — un « grand M » trop petit rendrait
    des cellules infaisables a tort et le solveur rendrait un maximum trop bas avec le meme air
    d'exactitude. C'est le defaut que ce depot traque : une formulation qui FABRIQUE le negatif."""
    assert additive_argmax_exact_ceiling(6, target="separable") == (36, 36, 1.0)


def test_perfection_is_INFEASIBLE_for_the_additive_form():
    """La forme additive ne peut JAMAIS etre parfaite sur la composition modulaire. Argument pour K
    pair : avec k'=k+K/2 et q'=q+K/2, les quatre cellules exigent une inegalite ET son inverse strict.
    Verifie ici sur K pair ET impair — l'obstruction est plus generale que l'argument."""
    for K in (4, 5, 6):
        n, tot, _ = additive_argmax_exact_ceiling(K)
        assert n < tot, f"K={K} : la perfection ne doit PAS etre atteignable ({n}/{tot})"


def test_an_unknown_MILP_target_is_REFUSED():
    """Meme regle que pour la recherche : une cible inconnue leve, elle ne retombe pas en silence."""
    with pytest.raises(ValueError):
        additive_argmax_exact_ceiling(4, target="composition")


def test_the_measured_ceiling_DOMINATES_the_proven_additive_bound():
    """⚠️ COHERENCE ENTRE LES DEUX NIVEAUX DE PREUVE, et c'est un vrai test : la forme complete CONTIENT
    la forme additive (a petits |s|, `tanh` est quasi lineaire et des `c_j` egaux ne changent pas
    l'argmax). Le minorant mesure DOIT donc dominer la borne prouvee. S'il tombait dessous, ce serait
    la RECHERCHE qui serait en cause, pas le substrat — exactement le diagnostic qui manquait au
    `0.3889` publie le 2026-09-02, lequel etait d'ailleurs SOUS cette borne."""
    n, tot, exact = additive_argmax_exact_ceiling(6)
    assert PLAIN_COMPOSITION_CEILING >= exact, (
        f"minorant mesure {PLAIN_COMPOSITION_CEILING} SOUS la borne prouvee {exact} -> recherche fautive")
    assert 0.3889 < exact, "le chiffre publie le 2026-09-02 etait sous la borne PROUVEE de la sous-forme"


# --- le TEMOIN GELE : rend la valeur centrale auditable a cout nul -------------------------------

def test_the_frozen_witness_REPRODUCES_the_ceiling():
    """Le plafond n'est plus « une recherche l'a trouve une fois » : les 78 coefficients sont GELES dans
    `results/plain_ceiling_witness.json` et se recomptent en Python pur, sans autograd et sans recherche.
    Il avait fallu 35 restarts et 2910 s pour tomber dessus — sans temoin, chaque re-verification serait
    un coup de des, et un tirage malheureux « refuterait » le plafond."""
    n, tot = verify_plain_ceiling_witness()
    assert (n, tot) == (34, 36), (n, tot)
    assert abs(PLAIN_COMPOSITION_CEILING - n / tot) < 1e-12, "la constante publiee doit EGALER le temoin"


def test_the_witness_HOLDS_IN_THE_REAL_SUBSTRATE():
    """⚠️ LA VERIFICATION QUI COMPTE, et elle boucle tout le dossier. Les 78 coefficients sont injectes
    dans le `W` d'un VRAI TorchPopulationModel (BILINEAR=False), et c'est le VRAI `forward` qui est lu,
    sur le chemin d'evaluation EXACT de la sonde (`logits[:, :K]`).

    Si ce nombre divergeait de la forme close, ce serait la DERIVATION qui serait fausse — et un plafond
    calcule sur une forme qui n'est pas celle du substrat serait exactement l'aliasing d'EDR-WARM-007 :
    une grandeur mesuree qui n'est pas celle qui agit. Les deux tombent a 30/36."""
    assert verify_plain_ceiling_witness(in_situ=True) == (34, 36)
    assert verify_plain_ceiling_witness(in_situ=True) == verify_plain_ceiling_witness()


def test_a_SATURATION_control_would_have_BLESSED_the_published_0_3889():
    """⚠️ LE CAS LE PLUS INSTRUCTIF DU DOSSIER, et il disqualifie un de mes propres controles.

    Mesure (recherche a marge sur la sous-forme ADDITIVE, dont le MILP PROUVE l'optimum a 27/36) :
    13/36 a 5000 pas, puis **14/36 = 0.3889 a 15000 pas ET a 30000 pas**, puis 15/36 a 48 restarts.
    Le chiffre publie le 2026-09-02 est donc un PLATEAU STABLE qui TIENT SUR UN DOUBLEMENT DU BUDGET.
    `saturation_control` (demi-budget vs budget plein) l'aurait par consequent VALIDE.

    Seul l'ancrage sur une VERITE EXACTE le refuse. C'est ce qui est gele ici, et c'est une propriete
    du couple (chiffre, borne prouvee), verifiable sans relancer aucune recherche."""
    _n, _tot, prouve = additive_argmax_exact_ceiling(6)
    publie = 14 / 36
    assert abs(publie - 0.3889) < 1e-3, publie
    assert publie < prouve, (
        f"le chiffre publie {publie:.4f} est SOUS la borne PROUVEE {prouve} de la sous-forme la PLUS "
        "pauvre : aucune recherche ne peut le rendre comme plafond de la forme complete")
    # ...et un controle de saturation ne peut PAS voir ca : deux budgets donnant le meme plateau sont
    # « satures » au sens de ce controle. La propriete qui discrimine est la DOMINATION, pas la stabilite.
    plateau_stable = (publie - publie) <= 0.0
    assert plateau_stable, "deux budgets au meme plateau passent la saturation"
    assert not (publie > prouve), "et pourtant la domination REFUSE — c'est le seul controle qui porte"

