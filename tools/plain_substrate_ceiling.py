"""PLAFOND DE L'INCAPABLE — ce que le substrat `plain` PEUT représenter sur `(q+key)%K` (dette P2.15).

POURQUOI cet instrument existe. Le dépôt jugeait ses nuls de composition contre une barre ABSOLUE
`1/K + 0.15 = 0.3167` (K=6). Or le substrat qu'elle est censée déclarer nul la franchit très largement :
la franchir n'établit donc AUCUNE capacité, seulement que le plancher est bas. Un seuil absolu n'est
invariant ni au PAS ni au BUDGET ; un plafond de forme fonctionnelle l'est. Tout nul revendiqué devrait
embarquer son plafond plutôt qu'un seuil.

CE QUE LA FORME CLOSE DIT, dérivé de `src/agents/backend_torch.py::_step` (vérifié ligne à ligne) :
au premier pas, `H_in = 0` donc `H = [obs, 0…0]` ; les K nœuds de readout `[N-O : N-O+K]` sont au-delà
de `I` (64..70 vs I=59 aux dims par défaut de `MambaAgent`), donc leur composante `(1-δ)·H` est NULLE et
`excitation_j` ne reçoit que les entrées one-hot. Il reste, EXACTEMENT :

    logit_j = σ(W[j,j]) · tanh( W[key, j] + W[K+q, j] )        (BILINEAR=False, un seul `_step`)

soit `c_j · tanh(a[key,j] + b[q,j])` avec `c_j > 0`.

⚠️ **L'ARGUMENT DE SÉPARABILITÉ DU DÉPÔT EST INVALIDE TEL QU'IL ÉTAIT ÉCRIT**, et c'est la deuxième
erreur que P2.15 corrige. « Transformée MONOTONE d'un score SÉPARABLE, donc prouvablement incapable » ne
tient pas : la transformée est **PAR NŒUD** (`c_j = σ(W[j,j])` diffère d'un j à l'autre), et
`argmax_j c_j·tanh(x_j)` n'égale `argmax_j x_j` QUE si tous les `c_j` sont égaux. Dès que deux diffèrent,
la courbe d'iso-score entre deux colonnes est croissante NON LINÉAIRE, deux de ses translatées se coupent
DEUX fois — on peut donc séparer une même paire de points dans les deux sens, c'est-à-dire réaliser un
XOR 2×2, impossible à tout score séparable. C'est exactement ce qui fait franchir la borne séparable.

CE QUI EST VRAIMENT PROUVÉ, et sur quelle forme :
  * **sous-forme SÉPARABLE** (`c_j` tous égaux -> `argmax_j a[k,j]+b[q,j]`) : plafond **27/36 = 0.75
    EXACTEMENT** pour K=6. La borne se démontre en trois lignes : les 36 cellules se partitionnent en
    **9 blocs 2×2 disjoints** (lignes {k, k+K/2} × colonnes {q, q+K/2}) dont la cible est un XOR exact
    entre les colonnes `k+q` et `k+q+K/2` ; sommer les deux paires d'inégalités d'un bloc donne une
    inégalité ET son inverse strict, donc **au moins une erreur par bloc**, donc au plus 36−9 = 27. Le
    MILP atteint 27 : borne et construction COÏNCIDENT.
  * **forme COMPLÈTE** (`c_j` libres) : plafond seulement MESURÉ, ≥ 29-30/36. Rien n'y est prouvé.

Ce plafond n'est en tout cas PAS `1/K` : même le sous-cas séparable représente 0.75, soit 4.5× le hasard.
Confondre « incapable de représenter » (= 1.000) et « plafonne à 0.389 » est l'erreur P2.15 elle-même.

DEUX NIVEAUX DE PREUVE, et ils ne valent pas la même chose :
  * `additive_argmax_exact_ceiling` — la sous-forme purement additive `argmax_j a[k,j]+b[q,j]` plafonne
    à **27/36 = 0.75 EXACTEMENT** pour K=6 (MILP, gap 0). C'est une borne **SUPÉRIEURE PROUVÉE**, et la
    perfection y est infaisable pour tout K de 3 à 8 (LP). Contrôle positif apparié : la MÊME formulation
    sur une cible séparable rend 36/36.
  * `measure_plain_composition_ceiling` — la forme COMPLÈTE (avec `σ(W[j,j])` et `tanh`) atteint
    **30/36 = 0.8333** par recherche. C'est un **MINORANT** : « ce que l'incapable atteint de façon
    démontrée », jamais « ce qu'il ne peut pas dépasser ». L'écart 30 − 27 chiffre ce que la saturation
    et l'échelle par nœud achètent : 3 cellules.

⚠️ **OÙ VIT LA LIMITATION — une relaxation naturelle est RÉFUTÉE (2026-09-07).** On aurait pu espérer
borner la forme complète en la relaxant : remplacer `c_j·tanh` par une fonction croissante QUELCONQUE et
par colonne, `argmax_j g_j(a[k,j]+b[q,j])`. Sous cette relaxation, seul compte l'ORDRE des scores dans
chaque colonne, ce qui se met en MILP. Résultat, PROUVÉ optimal et vérifié indépendamment (0 violation
d'ordre, argmax recompté à la main) : **la relaxation atteint la PERFECTION** — 9/9 à K=3, 16/16 à K=4.
Elle ne borne donc RIEN, et c'est instructif : ce qui limite le substrat plain n'est ni la séparabilité
de `a+b`, ni la monotonie par nœud, mais **la FORME de `tanh` elle-même** — une seule sigmoïde partagée,
seulement remise à l'échelle par nœud. Toute tentative de borne supérieure doit contraindre cette forme.

⚠️ **LA RECHERCHE EST DÉMONTRABLEMENT FAIBLE ICI, et il faut en tenir compte.** Sur la forme additive,
dont le MILP donne 0.75, la descente de gradient ne trouve que **0.3611** — un facteur 2 sur une forme
DONT ON CONNAÎT LA RÉPONSE. Le minorant 0.8333 de la forme complète est donc lui aussi probablement bas.
Conséquence pratique : `assert_bar_separates_the_incapable` adossée à un minorant est une condition
NÉCESSAIRE, pas suffisante. Aucune borne supérieure n'est établie pour la forme complète — l'établir est
la tâche ouverte, et le MILP montre qu'elle est faisable.

⚠️ **ET LA SATURATION NE SUFFIT PAS NON PLUS.** Mesuré : sur la sous-forme additive (optimum PROUVÉ
27/36), la recherche rend 13/36, puis **14/36 = 0.3889 à 15 000 pas ET à 30 000 pas**, puis 15/36.
Le chiffre publié est un PLATEAU qui tient sur un DOUBLEMENT du budget — `saturation_control`
l'aurait donc validé. Seul `dominates_proven_bound` le refuse. Un plateau de recherche est
indiscernable d'un plafond par tout contrôle sans VÉRITÉ EXACTE de référence : c'est pourquoi le
MILP est le seul contrôle qui porte ici.

⚠️ **HISTORIQUE — le `0.3889` publié le 2026-09-02 est SUPERSÉDÉ.** Sa mesure portait deux contrôles
appariés qui PASSAIENT tous les deux (table libre → 1.000 ; forme close sur cible séparable → 1.000)
alors que sa recherche n'avait pas convergé. Ces contrôles innocentent la FORME et l'OPTIMISEUR ; ni
l'un ni l'autre ne peut dire si l'on a cherché assez longtemps sur le problème DUR — la seule question
qui fixe la valeur d'un plafond. D'où le TROISIÈME contrôle, `saturation_control`. Règle transposable :
**un contrôle de CAPACITÉ ne calibre pas un contrôle de BUDGET.**

⚠️ Le terme bilinéaire lève exactement la contrainte de séparabilité (`(H·U)⊙(H·V)·W_bl` est un produit
key×q), ce qui est la thèse d'`EDR-BILINEAR` : cet instrument en donne la borne quantitative côté plain —
et la ramène de 0.543 à 0.099 de marge.

Usage : python tools/plain_substrate_ceiling.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

# MINORANT GELÉ (2026-09-07, révisé DEUX FOIS dans la journée) — **34/36**. Charnière à marge fixe,
# float64, victoire STRICTE (aucune égalité comptée juste) ; re-vérifié Python pur sans autograd
# (34/36) ET injecté dans le `W` d'un vrai `TorchPopulationModel`, lu par le VRAI `forward`
# (34/36). Témoin gelé dans `results/plain_ceiling_witness.json`.
#
# ⚠️⚠️ CE NOMBRE A MONTÉ TROIS FOIS EN UN JOUR : 14/36 (publié le 2026-09-02) -> 30/36 -> 34/36, et
# trois chercheurs indépendants du même jour ont rendu 29/36, 34/36 et 36/36 — par ordre d'EFFORT
# croissant. **Un plafond qui monte avec l'effort est le PLANCHER DE L'OPTIMISEUR.** Ne JAMAIS s'en
# servir pour fonder une affirmation « le substrat ne PEUT pas » : c'est E19 occurrence 4, et cette
# faute a été commise ICI, dans la passe même qui fermait P2.15.
#
# ⚠️ Ce nombre RÉVISE le `0.3889` publié le 2026-09-02, d'un facteur 2.1. La cause est identifiée et
# elle est instructive : la mesure d'origine portait deux contrôles appariés qui PASSAIENT tous les
# deux (table libre -> 1.000, forme close sur cible séparable -> 1.000) alors que sa recherche n'avait
# pas convergé. Ces deux contrôles innocentent la FORME et l'OPTIMISEUR ; aucun des deux ne peut dire
# si l'on a cherché assez longtemps sur le problème DUR — la seule question qui fixe la valeur d'un
# plafond. D'où `saturation_control` (moitié budget vs budget plein), ajouté ici.
#
# ⚠️ C'est un MINORANT, et il faut le lire comme tel : « ce que l'incapable atteint de façon démontrée »,
# jamais « ce que l'incapable ne peut pas dépasser ». Une recherche plus longue peut le relever encore —
# elle l'a déjà fait une fois. Toute conclusion qui s'y adosse doit rester vraie si le plafond monte.
PLAIN_COMPOSITION_CEILING = 34.0 / 36.0

# Provenance GELÉE du plafond, telle qu'exigée par `assert_bar_separates_the_incapable` : une provenance
# non écrite est une provenance non vérifiable. Citée par les sondes qui déclarent un nul de composition.
PLAIN_COMPOSITION_PROVENANCE = (
    "forme close de backend_torch._step a H_in=0 (logit_j = sigmoid(W[j,j])*tanh(W[key,j]+W[K+q,j])) ; "
    "MINORANT 34/36 par charniere a marge FIXE, float64, victoire STRICTE ; re-verifie SANS autograd "
    "(python pur) ET IN SITU dans le vrai TorchPopulationModel (34/36 aux deux). ATTENTION : c est un "
    "MINORANT qui MONTE avec l effort -- 29/36, 34/36 et 36/36 selon trois chercheurs independants du "
    "meme jour. Il ne fonde AUCUN << le substrat ne peut pas >> (E19 occ.4) : "
)


def plain_readout_ceiling(K=6, restarts=8, steps=4000, lr=0.05, temp=20.0, seed=0, free_table=False,
                          target="modular"):
    """Meilleure accuracy ATTEIGNABLE sur les K*K paires (key,q) -> cible.

    `free_table=False` : la forme close du substrat plain (séparable, transformée monotone) -> PLAFOND.
    `free_table=True`  : contrôle positif apparié, logits libres `t[key,q,j]` -> doit rendre 1.000.
    `target="modular"` : la cible qui NOUS intéresse, `(q+key)%K`, non séparable.
    `target="separable"` : contrôle de SPÉCIFICITÉ, cible `key` — séparable par construction, donc la
      forme close DOIT la rendre à 1.000. Sans ce contrôle, un plafond bas resterait indiscernable
      d'une forme mal paramétrée ou d'un optimiseur trop faible : ce serait l'instrument qui
      fabriquerait le nul, le défaut exact que ce dépôt traque chez ses sondes.

    L'accuracy est invariante par mise à l'échelle POSITIVE des logits, donc `temp` ne change PAS
    l'ensemble représentable — elle ne sert qu'à donner du gradient à la cross-entropie sur des logits
    bornés dans (-1,1). L'accuracy est relevée à CHAQUE pas et c'est le MAXIMUM qui est rendu : on
    mesure ce que la forme peut représenter, pas où l'optimiseur s'arrête.
    """
    import torch
    import torch.nn.functional as F

    keys = torch.arange(K).repeat_interleave(K)          # (K*K,)
    qs = torch.arange(K).repeat(K)                       # (K*K,)
    if target == "modular":
        tgt = (qs + keys) % K
    elif target == "separable":
        tgt = keys.clone()
    else:
        raise ValueError(f"target inconnu : {target!r} (attendu 'modular' | 'separable')")

    best = 0.0
    for r in range(restarts):
        g = torch.Generator().manual_seed(seed * 1000 + r)
        if free_table:
            t = (0.1 * torch.randn(K, K, K, generator=g)).requires_grad_(True)
            params = [t]
        else:
            a = (0.1 * torch.randn(K, K, generator=g)).requires_grad_(True)   # W[key, j]
            b = (0.1 * torch.randn(K, K, generator=g)).requires_grad_(True)   # W[K+q, j]
            d = (0.1 * torch.randn(K, generator=g)).requires_grad_(True)      # W[j, j] -> sigma(d)
            params = [a, b, d]
        opt = torch.optim.Adam(params, lr=lr)
        for _ in range(steps):
            if free_table:
                logits = t[keys, qs]                                          # (K*K, K)
            else:
                logits = torch.sigmoid(d) * torch.tanh(a[keys] + b[qs])       # (K*K, K)
            acc = float((logits.argmax(dim=1) == tgt).float().mean())
            if acc > best:
                best = acc
            loss = F.cross_entropy(temp * logits, tgt)
            opt.zero_grad(); loss.backward(); opt.step()
    return best


def additive_argmax_exact_ceiling(K=6, marge=1.0, borne=50.0, time_limit=900, target="modular",
                                  circulant=False):
    """Maximum EXACT de cellules correctes pour la forme PUREMENT ADDITIVE `argmax_j a[k,j] + b[q,j]`,
    par programmation en nombres entiers (HiGHS, gap 0). Ce n'est PAS un minorant de recherche : le
    solveur PROUVE l'optimalité, et c'est ce qui le rend bien plus fort qu'une descente multi-restart.

    -> (n_correct, K*K, accuracy). Mesuré : K=4 -> 12/16, K=5 -> 19/25, K=6 -> **27/36 = 0.75**.
    Avec `circulant=True` (a[k,j]=f[j-k], b[q,j]=g[j-q]) : **6/36 = 0.1667 a K=6, le HASARD**.

    Cette forme est le substrat plain PRIVÉ de son échelle par nœud et de sa saturation : le comparer au
    plafond mesuré de la forme COMPLÈTE (30/36) chiffre ce que `σ(W[j,j])·tanh(·)` achète — 3 cellules.
    C'est aussi le seul endroit du dossier où une borne SUPÉRIEURE est établie.

    ⚠️ La perfection est INFAISABLE pour cette forme, et pour tout K testé (3 à 8) — vérifié en LP pure
    (le système des K*K contraintes strictes n'a pas de solution). Argument, pour K pair : prendre
    k'=k+K/2, q'=q+K/2 ; alors k+q ≡ k'+q' (soit j1) et k+q' ≡ k'+q (soit j2), et les quatre cellules
    exigent à la fois `b_q[j1]+b_q'[j2] > b_q[j2]+b_q'[j1]` et son inverse strict. Une additivité ne
    peut pas porter la structure de groupe.

    `target="separable"` : CONTRÔLE POSITIF APPARIÉ — cible `k`, séparable par construction, sur laquelle
    la MÊME formulation MILP doit rendre **K*K sur K*K**. Sans lui, un `27/36` serait indiscernable d'une
    formulation fautive : un « grand M » trop petit rendrait des cellules infaisables à tort, et le
    solveur rendrait un maximum trop bas avec exactement le même air d'exactitude."""
    if target not in ("modular", "separable"):
        raise ValueError(f"target inconnu : {target!r} (attendu 'modular' | 'separable')")
    import itertools

    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    # `circulant=True` : a[k,j] = f[(j-k) mod K], b[q,j] = g[(j-q) mod K] -- 2K parametres au lieu de
    # 2K*K. C'est la forme « naturelle » qu'on ecrit spontanement pour une tache modulaire, et le MILP
    # montre qu'elle ne vaut RIEN : 6/36 = 0.1667 a K=6, soit EXACTEMENT le hasard (contre 27/36 pour
    # l'additif general). Mesure faite le 2026-09-08 pour calibrer un chemin de REPLICATION qui s'y
    # restreignait -- sans elle, on aurait accuse l'optimiseur global, qui trouvait deja 3/36 et 6/36,
    # c'est-a-dire l'optimum de cet espace. Une reference EXACTE separe « recherche faible » de
    # « forme pauvre » ; c'est tout l'enjeu de P2.15, applique ici a l'instrument de replication.
    nab = 2 * K if circulant else 2 * K * K
    nz = K * K
    nv = nab + nz
    if circulant:
        ia = lambda k, j: (j - k) % K                                    # noqa: E731
        ib = lambda q, j: K + ((j - q) % K)                              # noqa: E731
    else:
        ia = lambda k, j: k * K + j                                      # noqa: E731
        ib = lambda q, j: K * K + q * K + j                              # noqa: E731
    iz = lambda k, q: nab + k * K + q                                    # noqa: E731
    M = 4 * borne + marge
    rows, lo = [], []
    for k, q in itertools.product(range(K), repeat=2):
        t = (k + q) % K if target == "modular" else k
        for j in range(K):
            if j == t:
                continue
            r = np.zeros(nv)
            r[ia(k, t)] += 1; r[ib(q, t)] += 1
            r[ia(k, j)] -= 1; r[ib(q, j)] -= 1
            r[iz(k, q)] -= M                    # z=1 => la contrainte MORD ; z=0 => relâchée
            rows.append(r); lo.append(marge - M)
    c = np.zeros(nv); c[nab:] = -1.0            # maximiser sum(z)
    integrality = np.zeros(nv); integrality[nab:] = 1
    bounds = Bounds(np.r_[np.full(nab, -borne), np.zeros(nz)],
                    np.r_[np.full(nab, borne), np.ones(nz)])
    res = milp(c=c, constraints=LinearConstraint(np.array(rows), lo, np.inf),
               integrality=integrality, bounds=bounds,
               options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    if res.status != 0 or res.fun is None:
        raise RuntimeError(f"MILP non résolu à l'optimalité ({res.message}) — un résultat NON PROUVÉ "
                           "ne doit pas être rendu comme une borne exacte")
    n = int(round(-res.fun))
    return n, K * K, n / float(K * K)


_WITNESS = os.path.join(_ROOT, "results", "plain_ceiling_witness.json")


def verify_plain_ceiling_witness(path=None, in_situ=False):
    """Recompte le TÉMOIN GELÉ — les paramètres EXHIBÉS qui atteignent le plafond — sans AUCUNE recherche.

    Pourquoi un témoin. « Une recherche a trouvé 30/36 » est une affirmation qu'il faut refaire tourner
    pour recontrôler, et qui dépend de la chance des restarts (celui-ci est tombé au restart 19 sur 24).
    Un témoin la rend AUDITABLE à coût nul et pour toujours : les 78 coefficients sont gelés dans
    `results/plain_ceiling_witness.json`, et vérifier ne coûte plus qu'un argmax sur 36 cellules.

    `in_situ=False` : recompte sur la forme close, en Python pur, sans autograd.
    `in_situ=True`  : ⚠️ LA VÉRIFICATION QUI COMPTE — injecte les 78 coefficients dans le `W` d'un VRAI
      `TorchPopulationModel` (`BILINEAR=False`), appelle le VRAI `forward`, et lit `logits[:, :K]`,
      c'est-à-dire le chemin d'évaluation EXACT de la sonde. Si les deux nombres divergent, c'est la
      DÉRIVATION qui est fausse — et tout ce qui s'appuie sur le plafond tombe avec elle. Un plafond
      calculé sur une forme qui n'est pas celle du substrat serait exactement le défaut d'aliasing
      d'EDR-WARM-007 : une grandeur mesurée qui n'est pas celle qui agit.
    """
    import json

    with open(path or _WITNESS, encoding="utf-8") as fh:
        w = json.load(fh)
    K = int(w["K"])
    a, b, d = w["a"], w["b"], w["d"]
    if not in_situ:
        import math
        sig = lambda x: 1.0 / (1.0 + math.exp(-x))                       # noqa: E731
        ok = 0
        for k in range(K):
            for q in range(K):
                v = [sig(d[j]) * math.tanh(a[k][j] + b[q][j]) for j in range(K)]
                ok += (max(range(K), key=lambda j: v[j]) == (k + q) % K)
        return ok, K * K

    import torch

    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel as TPM
    from src.agents.mamba_agent import MambaAgent

    saved = (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR)
    TPM.CONDITION_GATE = False; TPM.GATE_TARGET = None; TPM.BILINEAR = False
    try:
        pop = make_population([MambaAgent()], backend="torch")
        I, N, O = pop.I, pop.N, pop.O
        R = N - O
        assert R >= I, f"la fenêtre de readout [{R}:{R + K}) chevauche l'observation [0:{I}) — forme close CADUQUE"
        with torch.no_grad():
            for j in range(K):
                for k in range(K):
                    pop.W[0, k, R + j] = float(a[k][j])
                    pop.W[0, K + k, R + j] = float(b[k][j])
                pop.W[0, R + j, R + j] = float(d[j])
        ok = 0
        for k in range(K):
            for q in range(K):
                obs = np.zeros((1, I), dtype=np.float32)
                obs[0, k] = 1.0; obs[0, K + q] = 1.0
                pop.H = torch.zeros((1, N))
                logits, _ = pop.forward(obs)
                ok += int(np.asarray(logits)[0, :K].argmax() == (k + q) % K)
        return ok, K * K
    finally:
        (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR) = saved


def measure_plain_composition_ceiling(K=6, restarts=8, steps=4000, seed=0, saturation_tol=0.0):
    """Plafond + ses TROIS contrôles appariés, en un seul appel. `valid` est FAUX dès qu'un contrôle
    manque sa réponse connue : le plafond n'est alors pas interprétable, et l'instrument le DIT au lieu
    de rendre un nombre (le défaut « détecté puis avalé dans un `else` » que ce dépôt traque).

      * `positive_control` (forme LIBRE, même cible, même budget) doit valoir 1.000 -> innocente
        l'OPTIMISEUR : ce qui borne la forme close n'est pas la recherche en général ;
      * `specificity_control` (MÊME forme, cible SÉPARABLE `key`) doit valoir 1.000 -> innocente la
        FORME : ce qui la borne est bien la non-séparabilité de la cible, pas une paramétrisation
        pauvre ou une dérivation fautive du code source ;
      * `saturation_control` : le plafond mesuré à MOITIÉ budget doit déjà égaler celui mesuré à budget
        plein. Sinon la recherche n'a pas convergé et le nombre rendu est un MINORANT non stabilisé.

    ⚠️ **Le troisième contrôle a été ajouté après que les deux premiers ont laissé passer un faux
    plafond** (2026-09-07, trouvé par le test de calibration, pas par l'instrument) : à 2 restarts ×
    60 pas, `positive_control` ET `specificity_control` valaient TOUS DEUX 1.000 — une table libre et
    une cible séparable se fittent en quelques dizaines de pas — pendant que le plafond lisait 0.278.
    Deux contrôles verts, un plafond faux de plus d'un facteur deux. Ils innocentent la forme et
    l'optimiseur ; NI L'UN NI L'AUTRE ne dit si on a cherché assez longtemps sur le problème DUR, et
    c'est la seule question qui décide de la valeur du plafond. C'est très probablement l'origine du
    `0.3889` publié le 2026-09-02 : une recherche non convergée, validée par des contrôles qui ne
    pouvaient pas la contredire."""
    demi = max(1, steps // 2)
    kw = dict(K=K, seed=seed)
    ceiling = plain_readout_ceiling(restarts=restarts, steps=steps, free_table=False, **kw)
    demi_c = plain_readout_ceiling(restarts=max(1, restarts // 2), steps=demi, free_table=False, **kw)
    control = plain_readout_ceiling(restarts=restarts, steps=steps, free_table=True, **kw)
    spec = plain_readout_ceiling(restarts=restarts, steps=steps, free_table=False,
                                 target="separable", **kw)
    sature = (ceiling - demi_c) <= float(saturation_tol)
    # QUATRIÈME contrôle (2026-09-07, ajouté après qu'un réfutateur eut montré que les trois autres
    # laissaient encore passer une recherche bloquée) : la forme COMPLÈTE contient la sous-forme
    # ADDITIVE, dont le MILP PROUVE l'optimum. Le plafond mesuré doit donc DOMINER cette borne — c'est
    # une condition NÉCESSAIRE, vérifiable, et la seule ancre exacte du dossier. L'ÉGALITÉ est le signal
    # qui compte : elle dit que la recherche n'a rien trouvé au-delà de ce que la sous-forme garantit
    # déjà, donc qu'elle est bloquée. Mesuré au budget « publié » (8 × 4000) : plafond 0.75 = EXACTEMENT
    # la borne additive, alors que la vérité mesurée vaut 34/36. Le contrôle mord.
    _n, _tot, prouve = additive_argmax_exact_ceiling(K=K)
    domine = ceiling > prouve
    return {"K": K, "ceiling": ceiling, "ceiling_half_budget": demi_c,
            "positive_control": control, "specificity_control": spec,
            "saturation_control": sature,
            "proven_additive_bound": prouve, "dominates_proven_bound": domine,
            "search_stalled_at_proven_bound": abs(ceiling - prouve) < 1e-9,
            # ⚠️ `valid` veut dire « cette mesure est INTERNEMENT COHÉRENTE », JAMAIS « le plafond est
            # établi ». Le nombre rendu reste un MINORANT : il a monté trois fois en une journée.
            "valid": control >= 1.0 and spec >= 1.0 and sature and domine,
            "is_minorant": True, "chance": 1.0 / K,
            "restarts": restarts, "steps": steps,
            "provenance": PLAIN_COMPOSITION_PROVENANCE}


if __name__ == "__main__":
    import json
    r = measure_plain_composition_ceiling(
        K=int(os.environ.get("PSC_K", "6")),
        restarts=int(os.environ.get("PSC_RESTARTS", "8")),
        steps=int(os.environ.get("PSC_STEPS", "4000")))
    print(json.dumps(r, ensure_ascii=False, indent=2))
