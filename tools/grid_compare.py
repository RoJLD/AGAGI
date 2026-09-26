"""Comparaison SUR LA GRILLE d'une grandeur de compte — et déclaration explicite du continu (classe E30, P2.105).

Le fait. Une accuracy est un COMPTE k/N (40 lots × 16 agents = 640 évaluations) : ses valeurs sont des multiples
exacts de 1/N, et une marge scellée à 0,05 vaut EXACTEMENT 32 pas. Or k/640 n'est pas représentable en binaire
(640 = 2^7 · 5) : float32 décale chaque valeur de ~2e-6 (0,184375 revient 0,18437500298023224), et une ÉGALITÉ
exacte comparée en flottants devient un DÉPASSEMENT ou un ÉCHEC — toujours du côté qui refuse. Cas fondateur
(E30 occ. 1, BILINEAR-SHAM-R1, seed 3) : plain 178/640, sham 210/640, marge 32 pas → `210 <= 178 + 32` est VRAI ;
en flottants `0,328125 > 0,27812498807907104 + 0,05` de 1,19e-08 → compté échec, **8/12 publié pour 9/12 exact**,
à trois endroits. Un critère à seuil comme « ≥ 10/12 » peut donc basculer sur une seule égalité perdue.

Ce module est l'UNIQUE endroit du dépôt où cette comparaison s'écrit (l'ancien `_cmp_grille` de
`tools/td_step_pilot.py` vit ici depuis le 2026-09-26) ; la porte 24 (`tools/check_grid_threshold.py`) refuse toute
NOUVELLE comparaison « a OP b ± marge » écrite en flottants nus dans un runner, et tient pour DÉCLARÉ tout site
qui passe par l'une des deux fonctions ci-dessous :

  * `cmp_grille(x, y, marge, n_grille, sens)` — la grandeur EST un compte sur `n_grille` : comparaison en unités
    de grille, repli DÉCLARÉ (comparaison ordinaire) si une valeur ou la marge n'est pas commensurable au pas ;
  * `cmp_continu(x, y, marge, sens)` — la grandeur N'EST PAS un compte (moyenne, ratio, probabilité) : la même
    comparaison, mais DÉCLARÉE telle. La porte ne sait pas lire la nature d'une grandeur ; elle fait déclarer
    l'auteur, elle ne devine pas (même règle que `_degeneracy` et que la porte 3).

L'étage des MÉDIANES (P2.105 (i)) : la médiane de 12 comptes est un DEMI-ENTIER sur N, donc un entier sur 2N —
comparer deux médianes se fait avec `n_grille = 2 * N` (0,05 y vaut 64 pas, la barre 0,5 en vaut 640) ; sur N,
elles ne sont pas commensurables et le repli s'applique (dit par `sur_grille`, jamais en silence).
La marge 0,0 (P2.105 (ii)) est trivialement commensurable (0 pas) : `cmp_grille(x, x, 0.0, N)` rend False dans
les deux sens, une égalité n'est ni un dépassement ni un déficit.

`marge_en_pas(marge, n_grille)` rend la marge EN PAS DE GRILLE (32 pour 0,05 sur 640) ou None : c'est le chiffre
à PUBLIER à côté de tout compte comparé à un seuil (« tout ratio se publie avec son plancher de bruit », appliqué
au bruit de REPRÉSENTATION). Calibré sur réponses connues dans `tests/sandbox/test_grid_compare.py` — dont le
contre-exemple gelé de la porte 24 : 126/640 contre 94/640 + 32, une égalité que float32 lit comme un dépassement.
"""

_TOL_PAS = 1e-3     # tolérance en PAS de grille : float32 décale k/640 de ~2e-6, soit ~1,3e-3 pas -- un millième de pas


def sur_grille(x, n_grille, tol=_TOL_PAS):
    """Position ENTIÈRE de `x` sur la grille de pas 1/`n_grille`, ou None si `x` n'est pas commensurable au pas
    (à `tol` pas près). Fonction PURE ; `None` DIT « pas sur cette grille », jamais 0."""
    a = float(x) * float(n_grille)
    r = round(a)
    return int(r) if abs(r - a) <= tol else None


def marge_en_pas(marge, n_grille, tol=_TOL_PAS):
    """La marge EN PAS DE GRILLE (0,05 sur 640 → 32 ; sur 1280 → 64 ; 0,0 → 0), ou None si elle n'est pas un
    multiple du pas (0,03 sur 640 = 19,2 pas → None). À publier à côté de chaque compte comparé à un seuil."""
    return sur_grille(marge, n_grille, tol)


def cmp_continu(x, y, marge, sens=1):
    """`x > y + marge` (sens=+1) ou `x < y − marge` (sens=−1), comparaison ORDINAIRE — pour une grandeur DÉCLARÉE
    continue (moyenne, ratio, probabilité). L'appeler plutôt qu'écrire la comparaison nue DIT à la porte 24 que
    la grandeur n'est pas un compte sur une grille."""
    return (x > y + marge) if sens > 0 else (x < y - marge)


def cmp_grille(x, y, marge, n_grille, sens=1, tol=_TOL_PAS):
    """`x > y + marge` (sens=+1) ou `x < y − marge` (sens=−1), comparé en UNITÉS DE GRILLE de pas 1/`n_grille`.

    Repli DÉCLARÉ : si `x`, `y` ou `marge` n'est pas commensurable au pas (à `tol` pas près), la comparaison
    ordinaire s'applique — c'est le comportement de l'ancien `_cmp_grille` de `td_step_pilot.py`, conservé tel
    quel (vérifié par la revue d'agagi-52 : les 17 comptes publiés de TD-STEP-PILOT R0/R1/R2 sont IDENTIQUES dans
    les deux arithmétiques ; le défaut y était LATENT, et il se réalise sur toute égalité exacte)."""
    a, b, m = sur_grille(x, n_grille, tol), sur_grille(y, n_grille, tol), sur_grille(marge, n_grille, tol)
    if a is None or b is None or m is None:
        return cmp_continu(x, y, marge, sens)
    return (a > b + m) if sens > 0 else (a < b - m)
