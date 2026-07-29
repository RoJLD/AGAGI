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
"""
import time


class CostExceeded(Exception):
    """Budget dépassé — porte l'étiquette de l'unité et le temps consommé, pour le rapport."""

    def __init__(self, label, spent_s, budget_s):
        self.label, self.spent_s, self.budget_s = label, spent_s, budget_s
        super().__init__(f"{label}: {spent_s:.1f}s > budget {budget_s:.1f}s")


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


class CostGuard:
    """Borne le temps d'UNE unité de travail (un seed, un bras). `tick()` lève quand le budget est franchi.

    ⚠️ Ne remplace PAS `project_cost` : celle-ci refuse un design intenable AVANT, celle-ci attrape la
    QUEUE PENDANT. Les deux modes d'échec sont distincts et ont chacun coûté un run à ce dépôt."""

    def __init__(self, budget_s: float, label: str = "unité", clock=time.monotonic):
        self.budget_s, self.label, self._clock = float(budget_s), label, clock
        self.t0 = clock()

    @property
    def spent_s(self) -> float:
        return self._clock() - self.t0

    def tick(self):
        if self.spent_s > self.budget_s:
            raise CostExceeded(self.label, self.spent_s, self.budget_s)

    def would_exceed(self) -> bool:
        """Variante non levante, pour un abandon propre avec valeur de retour."""
        return self.spent_s > self.budget_s
