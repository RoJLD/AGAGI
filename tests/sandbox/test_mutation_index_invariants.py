"""Défaut ÉPINGLÉ : `add_node` ne met à jour ni `num_inputs` ni `num_outputs`.

⚠️ **Ces tests NE PROTÈGENT PAS le code — ils protègent les CONCLUSIONS.**

`src/seed_ai/mutation.py:54-73` insère une ligne et une colonne à l'indice `j` ; tous les nœuds ≥ `j`
glissent, mais les bornes des blocs d'entrée et de sortie restent figées. Insérer DANS le bloc de sortie
re-mappe donc quelle décision chaque nœud pilote : une arête câblée survit intacte et pilote autre chose.

Mesuré : **56 % des insertions désalignent** une arête câblée ([[EDR-EVO-021]],
`tools/evo_runs/probe_output_block_shift.py`). C'est ce qui explique qu'UN `add_node` détruise un lecteur
~65 % du temps — et non le mécanisme initialement proposé (nœud inséré sans diagonale), **réfuté par
intervention** en [[EDR-EVO-022]].

**Pourquoi épingler au lieu de corriger** : ce comportement porte les chiffres de TOUT l'arc EVO-005→022.
Le réparer rendrait les runs d'avant et d'après incomparables. La migration devra donc s'accompagner d'une
RE-MESURE des records concernés. Ces tests deviennent alors ROUGES — et cette rougeur est exactement la
liste de ce qu'il faut refaire. Les laisser passer silencieusement serait pire que le bug.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.mutation import add_node, MutationConfig, Genome  # noqa: E402

I, O, N = 59, 108, 172
SIG, OUT_IDX = 5, 8
J0 = N - O + OUT_IDX


def _wired():
    """Génome RÉFLEXE (diagonale pleine) portant UNE arête sémantique : SIG -> sortie n°8."""
    W = np.zeros((N, N), dtype=np.float32)
    np.fill_diagonal(W, 10.0)
    W[SIG, J0] = 3.0
    return Genome(W, I, O)


def _edge_column(g):
    """Colonne réellement pointée par l'arête du signal (hors auto-boucle)."""
    nz = [c for c in np.nonzero(g.W[SIG])[0] if c != SIG]
    return int(nz[-1]) if nz else None


def test_add_node_does_not_update_the_block_bounds():
    """Le fait BRUT : N grandit, les bornes déclarées ne bougent pas."""
    g = _wired()
    n0, i0, o0 = g.num_nodes, g.num_inputs, g.num_outputs
    np.random.seed(0)
    add_node(g, MutationConfig())
    assert g.num_nodes == n0 + 1, "add_node doit bien ajouter un nœud"
    assert g.num_inputs == i0 and g.num_outputs == o0, (
        "DÉFAUT ÉPINGLÉ : si ce test tombe, `add_node` met désormais à jour les bornes de bloc. "
        "C'est la MIGRATION attendue — il faut alors RE-MESURER les records EVO-005 à EVO-022, "
        "dont les chiffres reposent sur l'ancien comportement.")


def test_output_semantics_shift_on_insertion_inside_the_output_block():
    """⚠️ CONTRE-EXEMPLE GELÉ — une arête câblée cesse de piloter la même sortie.

    Le taux mesuré est ~56 % sur 200 insertions ; on l'épingle ici dans une fourchette large pour ne pas
    dépendre du RNG, tout en garantissant que le phénomène est MAJEUR et non marginal."""
    desaligne = 0
    TRIALS = 200
    for s in range(TRIALS):
        np.random.seed(1000 + s)
        g = _wired().clone()
        add_node(g, MutationConfig())
        col = _edge_column(g)
        attendu = g.num_nodes - g.num_outputs + OUT_IDX
        if col is None or col != attendu:
            desaligne += 1
    taux = desaligne / TRIALS
    assert 0.35 < taux < 0.75, (
        f"taux de désalignement mesuré {taux:.2f}, attendu ~0.56. "
        "S'il s'effondre vers 0, `add_node` a été corrigé -> MIGRATION : re-mesurer EVO-005..022. "
        "S'il explose vers 1, le régime de génome a changé et les records doivent être relus.")


def test_a_fresh_soup_genome_hides_the_defect():
    """⚠️ Le piège qui m'a eu (classe E9, dans une RÉFUTATION).

    Sur une SOUPE FRAÎCHE les arêtes vont d'une entrée vers une sortie (`i < 59`, `j ≥ 64`), donc `j` ne
    tombe JAMAIS dans le bloc d'entrée et le défaut y semble inexistant — j'avais mesuré 0/3000 et conclu
    « ne se produit jamais en pratique ». Un génome à AUTO-BOUCLES a un `j` uniforme sur tous les nœuds.

    **Règle** : une propriété de l'opérateur de mutation doit être mesurée sur PLUSIEURS régimes de
    génome — au minimum soupe fraîche ET génome à auto-boucles."""
    # regime 1 : arêtes entree -> sortie uniquement (pas d'auto-boucle)
    W = np.zeros((N, N), dtype=np.float32)
    W[SIG, J0] = 3.0
    W[7, J0 + 1] = 1.0
    fresh = Genome(W, I, O)
    js_fresh = []
    for s in range(300):
        np.random.seed(s)
        nzi, nzj = np.nonzero(fresh.W)
        js_fresh.append(int(nzj[np.random.randint(len(nzi))]))
    assert min(js_fresh) >= I, "sur ce régime, j ne tombe jamais dans le bloc d'entrée (d'où le faux négatif)"

    # regime 2 : auto-boucles -> j uniforme sur TOUS les noeuds, le bloc d'entree est atteignable
    js_reflex = []
    for s in range(300):
        np.random.seed(s)
        nzi, nzj = np.nonzero(_wired().W)
        js_reflex.append(int(nzj[np.random.randint(len(nzi))]))
    assert min(js_reflex) < I, (
        "sur un génome à auto-boucles, j DOIT pouvoir tomber dans le bloc d'entrée — "
        "c'est ce que la mesure sur soupe fraîche masquait")
