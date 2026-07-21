"""⚠️ DÉPRÉCIÉ (2026-07-21) — remplacé par `tools/jobs/` (bail sur ressource NOMMÉE).

Ce module reste en place (arbre partagé entre sessions) mais NE DOIT PLUS être utilisé pour du code
nouveau. Son verrou fichier global est trop grossier : il sérialise TOUS les jobs, alors que seule la
ressource KuzuDB est réellement exclusive — une sim et un run de tests purs peuvent coexister. Il n'a
par ailleurs ni TTL, ni heartbeat, ni identité anti-réutilisation de PID, donc un crash laisse un verrou
orphelin qui bloque tout.

    Avant : with sim_session() as s: s.isolate(world)
    Après : from tools.jobs.run import hold
            with hold("kuzu", owner="mon-job"): ...

`sim_session()` — primitive d'ISOLATION pour toute simulation de monde.

PRINCIPE (2026-07-21) : **toute règle documentée sans application exécutable finit violée.** Les règles
d'environnement de ce dépôt sont écrites depuis longtemps ; elles ont été enfreintes TROIS fois dans une
seule journée, par trois acteurs différents :

  * moi (2×)              : sondes monde lancées en parallèle -> contention du lock KuzuDB, mesure
                            contaminée et suite de tests en timeout ;
  * le code d'instrument  : `_torch_survival_eras` laissait `memory_retriever` ACTIF pendant la boucle
                            de simulation (thread daemon vivant), alors que la règle est de l'arrêter
                            AVANT — mémoire ambiante = runs non reproductibles ;
  * la suite de tests     : état global (`async_logger`, KuzuDB) non nettoyé entre fichiers, d'où un
                            blocage de `test_behavioral_diversity` qui PASSE en isolation (26 s).

Le correctif n'est donc pas une ligne de documentation de plus, mais une primitive que le code doit
traverser. Ce module encode mécaniquement ce que la mémoire projet demandait :

  1. `memory_retriever` arrêté ET vidé AVANT toute boucle de simulation ;
  2. `async_logger` arrêté (il détient une connexion KuzuDB et bloque à l'arrêt s'il est resté actif) ;
  3. VERROU DE PROCESSUS : deux simulations ne peuvent pas tourner en même temps sur cette machine —
     c'est ce qui rend la contention KuzuDB *impossible* au lieu de simplement déconseillée ;
  4. restauration systématique, même sur exception.

Usage :
    from tools.sim_session import sim_session

    with sim_session() as s:
        world = Biosphere3D()
        s.isolate(world)          # arrête retriever + logger de CE monde
        ...  boucle de simulation ...

`SimBusyError` est levée si une autre simulation détient déjà le verrou : c'est un ÉCHEC VOULU, préférable
à une mesure silencieusement contaminée.
"""
from __future__ import annotations

import contextlib
import os
import tempfile
import time

_LOCK_PATH = os.path.join(tempfile.gettempdir(), "agagi_sim_session.lock")


class SimBusyError(RuntimeError):
    """Une autre simulation détient le verrou. Ne PAS contourner : la contention KuzuDB produit des
    mesures non reproductibles, indiscernables d'un résultat."""


def _quiet_async_logger():
    """Arrête l'`async_logger` global s'il tourne : il détient une connexion KuzuDB et son `stop()`
    bloque (`time.sleep`) quand il est resté actif à travers plusieurs mondes."""
    try:
        from src.graph_rag import async_logger as _al
    except Exception:
        return False
    for name in ("stop", "shutdown", "close"):
        fn = getattr(_al, name, None)
        if callable(fn):
            with contextlib.suppress(Exception):
                fn()
            return True
    return False


class _Session:
    def __init__(self):
        self.isolated = []

    def isolate(self, world):
        """Neutralise l'état ambiant d'UN monde : retriever arrêté + vidé AVANT la boucle de simulation.
        À appeler juste après la construction, avant d'ajouter les agents."""
        r = getattr(world, "memory_retriever", None)
        if r is not None:
            with contextlib.suppress(Exception):
                r.stop()
            with contextlib.suppress(Exception):
                r.clear()
            self.isolated.append(world)
        with contextlib.suppress(Exception):
            world.cache_enabled = getattr(world, "cache_enabled", False)
        return world

    def assert_isolated(self, world):
        """Vérifie qu'aucun retriever ne tourne — à utiliser en test de régression."""
        r = getattr(world, "memory_retriever", None)
        if r is not None and bool(getattr(r, "_running", False)):
            raise AssertionError(
                "memory_retriever ACTIF pendant la simulation : mémoire ambiante KuzuDB -> runs non "
                "reproductibles. Appeler sim_session().isolate(world) AVANT la boucle.")
        return True


@contextlib.contextmanager
def sim_session(timeout=0.0, poll=0.5):
    """Verrou exclusif de simulation + nettoyage garanti.

    `timeout=0` -> échoue IMMÉDIATEMENT si une autre simulation tourne (défaut : on préfère un échec
    bruyant à une mesure contaminée). `timeout>0` -> attend jusqu'à N secondes."""
    fd = None
    deadline = time.monotonic() + float(timeout)
    while True:
        try:
            fd = os.open(_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SimBusyError(
                    f"une autre simulation détient {_LOCK_PATH}. Ne PAS paralléliser les sondes monde "
                    "(contention KuzuDB -> non-reproductibilité). Attendre, ou supprimer le verrou "
                    "s'il est orphelin.")
            time.sleep(poll)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        fd = None
        _quiet_async_logger()
        session = _Session()
        yield session
    finally:
        if fd is not None:
            with contextlib.suppress(Exception):
                os.close(fd)
        for w in getattr(locals().get("session", None), "isolated", []) or []:
            r = getattr(w, "memory_retriever", None)
            if r is not None:
                with contextlib.suppress(Exception):
                    r.stop()
        _quiet_async_logger()
        with contextlib.suppress(Exception):
            os.unlink(_LOCK_PATH)
