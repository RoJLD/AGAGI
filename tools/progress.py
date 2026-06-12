"""
tools/progress.py — Barre de progression + ETA pour les simulations (demande utilisateur, EDR 077).

Affiche en temps réel : barre, %, compteur, temps écoulé, ETA. Réutilisable dans tous les bancs/boucles
longues. Sans dépendance (pas de tqdm). Usage :

    from tools.progress import Progress
    p = Progress(total=600, label="BPTT seed 0")
    for i in range(600):
        ...                       # travail
        p.update()                # +1 (ou p.update(n) pour +n)
    # -> "  BPTT seed 0 [########----------]  42%  252/600  18s  ETA 25s"

ou comme wrapper d'itérable :

    for x in Progress.track(items, label="ères"):
        ...
"""
import sys
import time


class Progress:
    def __init__(self, total, label="", width=20, every=0.2, stream=None):
        self.total = max(1, int(total))
        self.label = label
        self.width = width
        self.every = every                       # délai mini (s) entre rafraîchissements
        self.stream = stream or sys.stderr       # stderr : n'encombre pas la sortie redirigée (logs)
        self.n = 0
        self.t0 = time.time()
        self._last = 0.0

    def update(self, n=1, force=False):
        self.n += n
        now = time.time()
        if not force and self.n < self.total and (now - self._last) < self.every:
            return
        self._last = now
        frac = min(1.0, self.n / self.total)
        el = now - self.t0
        eta = (el / frac - el) if frac > 1e-9 else 0.0
        filled = int(frac * self.width)
        bar = "#" * filled + "-" * (self.width - filled)
        msg = f"\r  {self.label} [{bar}] {frac*100:4.0f}%  {self.n}/{self.total}  {el:4.0f}s  ETA {eta:4.0f}s   "
        self.stream.write(msg)
        self.stream.flush()
        if self.n >= self.total:
            self.stream.write("\n")
            self.stream.flush()

    def done(self):
        self.n = self.total
        self.update(0, force=True)

    @classmethod
    def track(cls, iterable, total=None, label=""):
        if total is None:
            total = len(iterable)
        p = cls(total, label=label)
        for x in iterable:
            yield x
            p.update()
        p.done()
