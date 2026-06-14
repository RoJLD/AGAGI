# src/seed_ai/harness.py
"""
src/seed_ai/harness.py — Socle de validité D1 (scan global, item Dev D1).

SeedManager : pose le déterminisme aux FRONTIÈRES (boot/ère/répétition) via le RNG global numpy.
Garantit l'APPARIEMENT (deux conditions au même seed partent du même monde initial) sans réécrire
les 168 sites np.random.X. Expose aussi un Generator default_rng pour le code NEUF qui veut
l'isolation par tirage. Détail : docs/superpowers/specs/2026-06-13-D1-RNG-Harness-design.md.
"""
import os
import json
import time
import logging
import numpy as np


class SeedManager:
    def __init__(self, base_seed):
        self.base_seed = int(base_seed)
        self.rng = np.random.default_rng(self.base_seed)

    def seed_boundary(self, i=0):
        """Pose np.random.seed((base_seed + i) mod 2**32) — déterministe, jamais de débordement
        (np.random.seed rejette >= 2**32). Renvoie la graine effective."""
        s = (self.base_seed + int(i)) % (2 ** 32)
        np.random.seed(s)
        return s

    @staticmethod
    def resolve(seed=None):
        """seed fourni -> int(seed). None -> graine d'entropie BORNÉE à [0, 2**31) (laisse de la
        marge pour les incréments par-ère base+i sans déborder 2**32). NOTE : le caller DOIT
        persister/logger la valeur retournée pour que le run soit rejouable a posteriori."""
        if seed is not None:
            return int(seed)
        return int(np.random.SeedSequence().generate_state(1)[0]) % (2 ** 31)


log = logging.getLogger("AGIseed.Harness")


def _git_short_commit():
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _json_default(v):
    """Sérialiseur JSON des scalaires/tableaux numpy (eval_robust renvoie des np.float)."""
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    raise TypeError(f"Non serialisable en JSON : {type(v)}")


class Harness:
    """Objet de composition (context manager) : seed + cycle async_logger + Progress + éval robuste
    appariée + I/O résultats. Absorbe le boilerplate des tools/ ; ne porte pas leur logique métier.

        with Harness(seed=0, name="robust_eval") as h:
            score = h.eval_robust(cfg, genome, run_era_fn=run_era, K=4)
            h.save({"score": score})
    """
    def __init__(self, seed=None, name="exp", robust_K=3, num_agents=20, with_db=True, db_wait=5.0):
        self.seed = SeedManager.resolve(seed)
        self.seeds = SeedManager(self.seed)
        self.name = name
        self.robust_K = int(robust_K)
        self.num_agents = int(num_agents)
        self.with_db = with_db
        self.db_wait = float(db_wait)
        self.db = None
        self._logger_started = False

    def __enter__(self):
        self.seeds.seed_boundary(0)
        log.info(f"[HARNESS] {self.name} seed={self.seed} commit={_git_short_commit()}  (rejouer : seed={self.seed})")
        if self.with_db:
            from src.graph_rag.async_logger import logger as async_logger
            async_logger.start()
            self._logger_started = True
            deadline = time.time() + self.db_wait
            while time.time() < deadline:
                self.db = async_logger.get_db()
                if self.db is not None:
                    break
                time.sleep(0.1)
            if self.db is None:
                log.warning(f"[HARNESS] {self.name}: KuzuDB indisponible -> degradation gracieuse")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._logger_started:
            from src.graph_rag.async_logger import logger as async_logger
            async_logger.stop()
            self._logger_started = False
        return False  # ne masque jamais une exception

    def eval_robust(self, config, genome, run_era_fn, K=None, num_agents=None):
        """Compétence robuste APPARIÉE : moyenne du metrics['score'] sur K ères seedées base+i.
        run_era_fn(config, genomes) -> (scored, metrics). Deux conditions au même seed Harness
        voient les mêmes mondes initiaux (block-pairing) -> variance entre-conditions effondrée."""
        K = self.robust_K if K is None else int(K)
        n = self.num_agents if num_agents is None else int(num_agents)
        scores = []
        for i in range(max(1, K)):
            self.seeds.seed_boundary(i)
            _scored, metrics = run_era_fn(config, [genome] * n)
            scores.append(float(metrics["score"]))
        return float(np.mean(scores)) if scores else 0.0

    def powered(self, conditions, run_seed_fn, seeds=(0, 1, 2)):
        """Wrap eval_harness.powered_eval en injectant le seed Harness comme base (base+s mod 2**32).
        Le Harness POSE la graine avant chaque réplicat -> run_seed_fn ne DOIT PAS seeder elle-même
        (sinon elle écrase la graine Harness et l'appariement n'est plus garanti)."""
        from src.seed_ai.eval_harness import powered_eval
        base = self.seed

        def seeded_fn(cfg, s):
            np.random.seed((base + int(s)) % (2 ** 32))
            return run_seed_fn(cfg, s)

        return powered_eval(conditions, seeded_fn, seeds=seeds)

    def progress(self, total, label=""):
        from tools.progress import Progress
        return Progress(total, label=label or self.name)

    def save(self, data):
        """Écrit results/<name>_<seed>.json (seed + commit court + données) -> provenance."""
        os.makedirs("results", exist_ok=True)
        out = {"name": self.name, "seed": self.seed, "commit": _git_short_commit(), "data": data}
        path = os.path.join("results", f"{self.name}_{self.seed}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=_json_default)
        return path
