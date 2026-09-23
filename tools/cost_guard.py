"""Plafond de coût EXÉCUTABLE — la garde manquante de la classe E13 du registre des erreurs.

E13 (« dépassement de coût non borné au design ») était, avec E11, l'une des deux classes sans aucune
garde. Preuve accumulée : 3 runs abandonnés (8 h, 4 h projetées, 89 min), plus WARM-009 nul et un run de
1,8 h sur une question sans objet — et un **4ᵉ le 2026-07-27** (EVO-007 : 187 min pour 8 seeds sur 36,
5,6 Go, tué).

Le backlog (P3.2) formulait la garde comme « exiger un débit mesuré sur smoke + un coût projeté ». La
mesure du 4ᵉ abandon montre que **c'est insuffisant, et pourquoi** : le débit du smoke était JUSTE
(2,6 s/ère, mesuré) et le run a quand même explosé, parce que le coût de ce pipeline **dépend du seed** —
il suit le succès évolutif (`CLAUDE.md` §Coût des runs). Les seeds 0-4 coûtaient 35 s ; le seed 8 n'a pas
fini 35 ères en 10 min. Aucune projection linéaire ne borne une queue de distribution.

D'où deux gardes complémentaires, l'une AVANT et l'autre PENDANT :

    from tools.cost_guard import project_cost, CostGuard

    project_cost(unit_s=35.0, n_units=36, budget_s=3600)      # AVANT : refuse un design intenable
    g = CostGuard(budget_s=180, label="seed 8")               # PENDANT : borne CHAQUE unité
    for era in ...:
        g.tick()                                              # lève CostExceeded si dépassé
        ...

La garde PENDANT est la seule qui attrape une queue : elle abandonne l'UNITÉ coûteuse (un seed) et laisse
le run continuer, au lieu de laisser un seed pathologique tuer les 35 autres. Un abandon doit être
COMPTÉ et RAPPORTÉ — un seed silencieusement absent est un biais de sélection sur les résultats.

P2.78 (2026-09-22) — **la garde PENDANT porte sur le temps CPU du processus, pas sur le temps mur.** Mesuré
deux fois : une cellule de P4.9 a duré 33 060 s de mur (9,2 h) sans qu'on puisse dire si la machine calculait
ou dormait ; le run DECOMP de S2-BLIND-CHAMPION a publié `_cout_s` = 510 334 s (5,9 jours) pour 14 cellules que
le `-ter` avait faites en 1 039 s — la machine avait dormi six jours. Un chiffre de coût mesuré sur une machine
dont on ne connaît pas l'état est la classe E12 appliquée au coût. Désormais : `CostGuard.tick()` lève sur le
temps CPU (`time.process_time`, défaut), le temps mur est publié À CÔTÉ (`spent_wall_s`, `report()`), et
`Stopwatch` donne aux runners `elapsed_s` ET `elapsed_cpu_s`. ⚠️ Deux limites, dites : (a) `process_time` ne
compte que CE processus — un parent qui attend un pool de workers a un CPU ~0 : une telle garde ne peut PAS
échouer (E1) ; passer `clock=time.monotonic` explicitement dans ce cas ; (b) une contention (lock KuzuDB, I/O)
gonfle le mur sans le CPU : elle n'est plus attrapée par la garde de queue, elle se LIT dans `wall_over_cpu`.
Et (c), mesuré le jour même sur TD-STEP-PILOT-R2 : `process_time` somme TOUS les threads du processus — un run torch
multi-thread (BLAS) publie `_cout_cpu_s` 2 142 s pour `_cout_s` 1 191 s, donc `wall_over_cpu` < 1 ; le budget CPU d'une
unité est alors ~ (threads × mur), à connaître avant de fixer `budget_s`. Le ratio se lit dans les deux sens : ≫ 1 =
machine endormie ou contention ; < 1 = plusieurs threads. Ni l'un ni l'autre n'est un défaut : c'est ce que le mur seul cachait.
"""
import time


class CostExceeded(Exception):
    """Budget dépassé — porte l'étiquette de l'unité, le temps consommé (horloge GATÉE) et, s'il est connu, le
    temps mur à côté, pour le rapport."""

    def __init__(self, label, spent_s, budget_s, spent_wall_s=None, gated_on="cpu"):
        self.label, self.spent_s, self.budget_s = label, spent_s, budget_s
        self.spent_wall_s, self.gated_on = spent_wall_s, gated_on
        mur = f" (mur {spent_wall_s:.1f}s)" if spent_wall_s is not None else ""
        super().__init__(f"{label}: {spent_s:.1f}s {gated_on} > budget {budget_s:.1f}s{mur}")


class CostTooHighToStart(Exception):
    """Le coût PROJETÉ dépasse le budget — refus AVANT de lancer quoi que ce soit."""


def project_cost(unit_s: float, n_units: int, budget_s: float, *, safety=3.0, label="run"):
    """Refuse un design dont le coût projeté dépasse le budget. `safety` (défaut ×3) est la marge pour la
    QUEUE : le coût par unité est mesuré sur un smoke, donc sur des unités typiques, jamais sur la pire.

    Renvoie le coût projeté (avec marge) si c'est tenable ; lève `CostTooHighToStart` sinon."""
    projected = unit_s * n_units * safety
    if projected > budget_s:
        raise CostTooHighToStart(
            f"{label}: {n_units} unités × {unit_s:.1f}s × marge {safety:g} = {projected / 60:.0f} min "
            f"> budget {budget_s / 60:.0f} min. Réduire n, réduire l'unité, ou relever le budget "
            f"EXPLICITEMENT — mais ne pas lancer en espérant que ça passe.")
    return projected


def _nom_horloge(clock) -> str:
    """« cpu » / « wall » pour les horloges de la bibliothèque, « injected » pour toute autre (tests)."""
    if clock is time.process_time:
        return "cpu"
    if clock in (time.monotonic, time.time, time.perf_counter):
        return "wall"
    return "injected"


class CostGuard:
    """Borne le temps d'UNE unité de travail (un seed, un bras). `tick()` lève quand le budget est franchi.

    ⚠️ Ne remplace PAS `project_cost` : celle-ci refuse un design intenable AVANT, celle-ci attrape la
    QUEUE PENDANT. Les deux modes d'échec sont distincts et ont chacun coûté un run à ce dépôt.

    P2.78 : `clock` est l'horloge GATÉE — par défaut le temps CPU du processus (`time.process_time`) : une
    suspension de la machine ne tue plus une unité. `wall_clock` est publiée à côté (`spent_wall_s`,
    `report()`), jamais à la place. Un parent de pool de workers doit passer `clock=time.monotonic`."""

    def __init__(self, budget_s: float, label: str = "unité", clock=time.process_time, wall_clock=time.monotonic):
        self.budget_s, self.label, self._clock, self._wall = float(budget_s), label, clock, wall_clock
        self.t0 = clock()
        self.w0 = wall_clock()

    @property
    def gated_on(self) -> str:
        return _nom_horloge(self._clock)

    @property
    def spent_s(self) -> float:
        """Temps consommé sur l'horloge GATÉE (CPU par défaut)."""
        return self._clock() - self.t0

    @property
    def spent_wall_s(self) -> float:
        return self._wall() - self.w0

    def report(self) -> dict:
        """À publier avec chaque unité : le temps gaté, le temps mur, et leur rapport (une machine qui dort ou
        un lock qui attend font monter `wall_over_cpu` sans toucher au CPU)."""
        cpu, mur = self.spent_s, self.spent_wall_s
        return {"spent_s": cpu, "spent_wall_s": mur, "gated_on": self.gated_on,
                "wall_over_cpu": (mur / cpu) if (self.gated_on == "cpu" and cpu > 0) else None}

    def tick(self):
        if self.spent_s > self.budget_s:
            raise CostExceeded(self.label, self.spent_s, self.budget_s, self.spent_wall_s, self.gated_on)

    def would_exceed(self) -> bool:
        """Variante non levante, pour un abandon propre avec valeur de retour."""
        return self.spent_s > self.budget_s


class Stopwatch:
    """Le chronomètre des RUNNERS (P2.78) : `elapsed()` rend `elapsed_s` (mur) ET `elapsed_cpu_s` (CPU du processus)
    à publier côte à côte — `_cout_s` seul ne dit pas si la machine calculait ou dormait. `wall_over_cpu` ≫ 1 =
    machine endormie ou contention, à lire avant de citer un coût."""

    def __init__(self, wall_clock=time.monotonic, cpu_clock=time.process_time):
        self._wall, self._cpu = wall_clock, cpu_clock
        self.w0, self.c0 = wall_clock(), cpu_clock()

    def elapsed(self) -> dict:
        mur, cpu = self._wall() - self.w0, self._cpu() - self.c0
        return {"elapsed_s": mur, "elapsed_cpu_s": cpu, "wall_over_cpu": (mur / cpu) if cpu > 0 else None}
