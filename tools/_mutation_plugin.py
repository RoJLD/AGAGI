# -*- coding: utf-8 -*-
"""Plugin pytest — INJECTE une version MUTÉE d'un cliquet AVANT toute collecte de tests.

Compagnon de `tools/check_gate_mutation.py`. Il n'a aucun usage propre : le harnais le passe à
pytest via `-p tools._mutation_plugin` et lui transmet la spécification par la variable
d'environnement `AGAGI_MUTATION_SPEC` (chemin d'un JSON temporaire).

⚠️ POURQUOI EN MÉMOIRE, ET PAS SUR DISQUE. Muter le fichier puis le restaurer dans un `finally` est
la forme évidente — et elle est INTERDITE ici : l'arbre de travail est PARTAGÉ entre sessions
parallèles (cf. CLAUDE.md). Un `kill -9`, un plantage, une coupure de courant pendant la fenêtre de
mutation laisserait un cliquet SABOTÉ dans l'arbre de quelqu'un d'autre, et le sabotage y serait
exactement du type que ce dépôt ne sait pas voir : la garde continue de tourner, elle rend simplement
« rien à signaler ». On compile donc la source mutée en mémoire et on l'installe dans `sys.modules`
sous le nom canonique. Aucun octet n'est écrit dans le dépôt.

⚠️ LIMITE ASSUMÉE, et elle borne la portée du harnais. Un témoin qui lit le SOURCE SUR DISQUE (par
ex. « le cliquet est-il branché dans le hook ? », « la garde précède-t-elle `--update-baseline` ? »)
ne voit PAS la mutation : il relit le fichier intact. Un tel témoin ne peut donc jamais tuer un
mutant, et le harnais le comptera comme SURVIVANT s'il est le seul. C'est conservateur dans le sens
sûr — il crie au lieu de se taire — mais il faut le savoir pour lire son verdict : les mutations
déclarées visent le COMPORTEMENT D'EXÉCUTION, pas la forme du texte.
⚠️ MÊME LIMITE, SOUS UNE AUTRE FORME : un témoin qui RECHARGE le module (`importlib.reload`) relit le
disque et DÉFAIT la mutation pour TOUS les tests qui le suivent dans le fichier — pas seulement pour
lui. Mesuré le 2026-09-26 (P2.135) : deux `reload` du témoin de la porte 5 rendaient aveugles les cas
placés après eux, et la mutation de `_familles` sortait SURVIVANTE alors que deux témoins la tuaient.
Remède côté témoin : remettre les globaux explicitement, jamais recharger.

Le plugin est SILENCIEUX sans `AGAGI_MUTATION_SPEC` : le charger sur une suite ordinaire ne change
rien. C'est ce qui permet au harnais de mesurer le contrôle INTACT avec exactement la même
ligne de commande, au plugin près.
"""
import importlib
import io
import json
import os
import sys
import types

_ENV = "AGAGI_MUTATION_SPEC"


def _installer(spec):
    """Compile la source MUTÉE et l'installe sous le nom canonique du module. Lève si la mutation
    ne s'applique pas EXACTEMENT une fois — une substitution ambiguë muterait autre chose que ce
    que l'auteur croit, et le verdict porterait alors sur une mutation inconnue."""
    modname, chemin = spec["module"], spec["chemin"]
    avant, apres = spec["avant"], spec["apres"]
    src = io.open(chemin, encoding="utf-8").read()
    n = src.count(avant)
    if n != 1:
        raise RuntimeError(
            f"MUTATION INAPPLICABLE : le motif apparait {n} fois dans {chemin} (exige : exactement 1). "
            f"Motif : {avant!r}")
    mute = src.replace(avant, apres)

    mod = types.ModuleType(modname)
    mod.__file__ = chemin
    mod.__package__ = modname.rpartition(".")[0]
    mod.__spec__ = None
    mod.__loader__ = None
    # Installé AVANT l'exécution : un module qui s'importe lui-même (ou qu'un autre importe pendant
    # son exec) doit voir le MUTANT, jamais l'original.
    sys.modules[modname] = mod
    exec(compile(mute, chemin, "exec"), mod.__dict__)
    if mod.__package__:
        # `from tools import check_x` passe par l'ATTRIBUT du paquet, pas par sys.modules.
        setattr(importlib.import_module(mod.__package__), modname.rpartition(".")[2], mod)
    return mod


def pytest_configure(config):     # noqa: ARG001 — signature imposée par pytest
    chemin_spec = os.environ.get(_ENV)
    if not chemin_spec:
        return
    with io.open(chemin_spec, encoding="utf-8") as f:
        spec = json.load(f)
    _installer(spec)
