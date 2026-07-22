"""P1.1 — `AsyncLogger.stop()` ne doit JAMAIS boucler indéfiniment.

Racine mesurée (faulthandler -> `async_logger.py:80`) du hang de la suite complète : en suite, l'état
KuzuDB s'accumule sur des dizaines de tests de sim-monde ; la connexion du worker finit par échouer
(5 retries -> `return`, thread MORT) ; les événements émis restent en queue ; l'ancien `stop()` faisait
`while not queue.empty(): sleep(0.5)` SANS BORNE -> boucle infinie, la suite hangeait (~6 %,
test_main_competence_profile_smoke). Chaque smoke-test passe en ISOLATION, d'où le diagnostic tardif.

Ce test reproduit la condition (worker mort + queue non vide) et exige que `stop()` RENDE la main.
Il tourne `stop()` dans un thread avec un join borné, pour ne jamais hanger la suite lui-même.
"""
import threading

from src.graph_rag.async_logger import AsyncLogger


def test_stop_does_not_hang_when_worker_is_dead():
    lg = AsyncLogger()
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()                        # thread TERMINÉ = worker mort
    lg._thread = dead
    lg._running = True                 # emit() reste actif -> la queue peut se remplir
    lg.queue.put({"type": "X", "payload": {}, "timestamp": 0})   # jamais dépilée (worker mort)

    done = threading.Event()
    threading.Thread(target=lambda: (lg.stop(), done.set()), daemon=True).start()
    assert done.wait(timeout=15.0), \
        "stop() a HANGÉ : worker mort + queue non vide -> boucle infinie (racine du hang de suite P1.1)"


def test_stop_still_drains_when_worker_alive():
    """Non-régression : quand le worker est VIVANT, stop() attend bien qu'il draine avant de rendre —
    on ne casse pas le flush normal en bornant la boucle."""
    lg = AsyncLogger()
    drained = []

    def _fake_worker():
        # dépile jusqu'à ce que stop() mette _running à False ET que la queue soit vide
        import time as _t
        while lg._running or not lg.queue.empty():
            try:
                drained.append(lg.queue.get(timeout=0.05))
                lg.queue.task_done()
            except Exception:
                _t.sleep(0.01)

    lg._running = True
    lg._thread = threading.Thread(target=_fake_worker, daemon=True)
    lg._thread.start()
    for _ in range(5):
        lg.queue.put({"type": "X", "payload": {}, "timestamp": 0})

    done = threading.Event()
    threading.Thread(target=lambda: (lg.stop(), done.set()), daemon=True).start()
    assert done.wait(timeout=15.0), "stop() n'a pas rendu la main avec un worker vivant"
    assert len(drained) == 5, f"le flush a perdu des événements : {len(drained)}/5"
