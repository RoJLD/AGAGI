# -*- coding: utf-8 -*-
"""LE helper d'isolation git du depot -- un seul, partage. Ne depend que de `os` : le cliquet des
cliquets (porte 15) l'importe, et il ne doit pas pouvoir mourir d'une erreur dans une porte.

Pendant un hook, git exporte `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`, `GIT_PREFIX`... a TOUS ses
sous-processus. Mesure le 2026-09-24 : un `git init -q` lance ailleurs sous `GIT_DIR` herite rend 0,
n'imprime RIEN, ne cree aucun `.git` la ou il tourne, et pose `core.bare = true` dans le depot vise.
(2026-09-23, porte 20 : un `GIT_INDEX_FILE` herite faisait echouer le commit d'un depot jetable.)

ISOLER (appeler `env_isole`) : (a) un appel git sur un depot TIERS -- jetable de test, clone ;
(b) un lanceur de TEMOINS (porte 15) -- un temoin tourne hermetique, jamais contre l'index du commit.
HERITER (ne PAS l'appeler) : pour JUGER l'index du commit courant, que `GIT_INDEX_FILE` designe --
c'est ce que fait `check_evidence_provenance._env_pour` sur le depot courant."""
import os


def env_isole():
    """Copie de l'environnement SANS AUCUNE variable `GIT_*` : la famille entiere, jamais une
    enumeration -- l'enumeration a oublie une variable deux fois le 2026-09-24."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
