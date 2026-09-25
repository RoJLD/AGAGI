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

P2.110 (2026-09-24) — **POURQUOI le cliquet coupe, PAR LIGNE, et sur quelle charge.** Trois défauts mesurés sur
TD-STEP-PILOT-R2 : (i) deux coupes de natures OPPOSÉES portaient le même drapeau (lr 2,0 coupée à 6,4 % au-dessus de sa
bascule, lr 1,0 à 142 %), et la raison publiée de la coupe courante était celle de la LEVÉE ; (ii) une unité mesurée sur
UNE cellule appliquée à une grille hétérogène (2,8× entre familles) ; (iii) l'unité de la projection est du temps MUR.
Ajouts, sans changer une décision légitime : `NATURES_COUPE` (vocabulaire FERMÉ), `classify_cut_nature` (nature d'UNE
ligne, calibrée), `cut_geometry` / `cut_record` (les DEUX côtés du seuil : projection refusée, dépassement, unité de
bascule), `margin_to_budget`, `LoadWindow` (charge EXTÉRIEURE intégrée sur la fenêtre de la cellule, jamais un
instantané), `cost_per_arm` / `project_cost_per_arm` (unité PAR BRAS, pour les règles FUTURES — une règle déjà scellée
sur « l'unité de la première cellule neuve » n'en change pas : E11). ⚠️ La projection RESTE en temps mur : `budget_s`
est du mur, et un run torch multi-thread rend un CPU > mur (point (c) ci-dessus). Et `project_cost` refuse désormais une
unité NaN ou négative, qu'il laissait passer en silence (`nan > budget` vaut False : E1).
"""
import math
import numbers
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

    Renvoie le coût projeté (avec marge) si c'est tenable ; lève `CostTooHighToStart` sinon.

    ⚠️ P2.110 (M-M8) : une unité NaN (médiane d'un bras vide) rendait une projection NaN, et `nan > budget_s` vaut False
    — la garde ACCEPTAIT sans un mot, elle ne pouvait pas échouer (E1). NaN, unité ou n négatifs lèvent `ValueError`.
    Aucune unité légitime n'est NaN ni négative : aucune décision légitime ne change (l'unité 0 reste acceptée)."""
    projected = unit_s * n_units * safety
    if projected != projected or unit_s < 0 or n_units < 0:
        raise ValueError(f"{label}: projection indéfinie ({n_units} unités × {unit_s}s × marge {safety}) — une unité "
                         f"NaN ou négative n'est pas une mesure ; la garde refuse au lieu de laisser passer.")
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


# ---- P2.110 : nature d'une coupe, géométrie par ligne, charge extérieure, coût par bras --------------------------------
NATURES_COUPE = ("contention", "structure", "indeterminee")
"""Vocabulaire FERMÉ de la nature d'une LIGNE coupée — toute autre valeur lève `ValueError`, jamais ignorée.
  * `structure`    — la coupe tient sur une unité SANS contention : fenêtre de mesure libre, ou réplique libre de la même
                     cellule qui coupe encore, ou dépassement au-delà d'une bande de contamination DÉCLARÉE ;
  * `contention`   — unité mesurée sous une charge MESURÉE (coupe PROVISOIRE, reprise déclarée due), ou ÉTABLIE quand la
                     même cellule re-chronométrée machine libre ne coupe plus la ligne ;
  * `indeterminee` — la charge n'a pas été mesurée (ou illisible). Seul fait établi : la projection dépassait le budget.
`indeterminee` et non `budget` (le mot de la première rédaction de P2.110) : TOUTE coupe est causée par le budget, et un
libellé d'absence qui ressemble à une cause de fond est le biais « absence -> affirmation » que CLAUDE.md traque."""

COEURS_EXTERIEURS_LIBRE_MAX = 8.0
COEURS_EXTERIEURS_LIBRE_MAX_PROVENANCE = (
    "PROVISOIRE, non calibré comme certificat (2026-09-24). Cœurs occupés par les AUTRES processus, moyennés sur la "
    "fenêtre de la cellule (22 CPU logiques, 16 physiques). Mesures : flotte au repos 4,9-6,9 cœurs (sonde de revue "
    "I-A1, 8 lectures, 0 simulation, 0 bail) ; 5,5-18,5 cœurs sur six fenêtres de 5 s pendant l'écriture de ce code (six "
    "sessions Claude vivantes) ; une boucle mono-thread ralentie ~1,9× à 16,5-18,5 cœurs extérieurs (sonde de revue "
    "M-M4). 8,0 = borne haute de la flotte au repos, arrondie : « libre » veut dire « pas plus chargée que la flotte au "
    "repos », PAS « aucune contention » — torch à 16 threads subit toute charge. Ce n'est PAS le seuil A5 du PM (80 % "
    "instantané = alerte de SATURATION, 17,6 cœurs). La réponse connue reste la réplication d'une cellule bit-identique.")


def _reel(x, nom):
    """Un nombre réel (numpy compris), jamais un booléen ni une chaîne — sinon `ValueError`."""
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise ValueError(f"{nom} doit être un nombre réel, reçu {x!r}")
    return float(x)


def _charge(x, nom):
    """Une charge en cœurs : None ou non fini = « je ne sais pas » (porte 14 : None et nan DISENT l'absence)."""
    if x is None:
        return None
    v = _reel(x, nom)
    return v if math.isfinite(v) else None


def classify_cut_nature(depassement, *, coeurs_exterieurs, seuil_coeurs_libre=COEURS_EXTERIEURS_LIBRE_MAX,
                        bande_contamination=None, depassement_replique=None, coeurs_exterieurs_replique=None):
    """Nature d'UNE LIGNE coupée, dans `NATURES_COUPE`. INSTRUMENT (calibré : tests/sandbox/test_cost_guard.py).

    ⚠️ Par LIGNE, pas par mesure (revue P2.110, M-M1) : les deux lignes de la passe 1 de R2 ont été coupées sur la MÊME
    unité, donc la même charge — un classifieur de la mesure leur rend forcément la même nature, or c'est précisément
    leur confusion que P2.110 (i) reproche. Ce qui est propre à une ligne, c'est son `depassement` = projection si elle
    était gardée / budget (> 1 : elle a été coupée ; `cut_geometry`).

    Règles, dans l'ORDRE (la réponse connue d'abord) :
      1. RÉPLIQUE de la même cellule, fenêtre LIBRE (`coeurs_exterieurs_replique` <= seuil) : elle coupe encore
         (`depassement_replique` > 1) -> `structure` ; sinon la coupe venait de l'écart de chronométrage de la MÊME
         computation -> `contention` établie. Une réplique chargée ou illisible ne prouve rien : ignorée.
         (CLAUDE.md : « la charge se mesurant par la réplication d'une cellule bit-identique ». Comparer deux cellules
         DIFFÉRENTES — 217,4 s sur lam099|lr=4.0 contre 196,4 s sur lam05|lr=2.0 — n'en est pas une : E8.)
      2. fenêtre de la mesure LIBRE -> `structure` (seuil INCLUS) ;
      3. bande de contamination DÉCLARÉE et `depassement` > 1 + bande -> `structure` : la ligne tiendrait même si
         l'unité était gonflée de la bande. Sans bande déclarée (défaut), cette voie est FERMÉE — on ne devine pas ;
      4. fenêtre CHARGÉE -> `contention` (provisoire : reprise due) ;
      5. sinon -> `indeterminee`.
    Monotone : plus de dépassement ne retire jamais `structure` ; plus de charge ne l'accorde jamais.
    `ValueError` sur toute entrée dégénérée (ligne non coupée, NaN là où une mesure est exigée, booléen, bande < 0)."""
    d = _reel(depassement, "depassement")
    if not (math.isfinite(d) and d > 1.0):
        raise ValueError(f"depassement = {depassement!r} : une ligne à <= 1 × le budget n'a PAS été coupée, rien à qualifier")
    seuil = _reel(seuil_coeurs_libre, "seuil_coeurs_libre")
    if not (math.isfinite(seuil) and seuil >= 0.0):
        raise ValueError(f"seuil_coeurs_libre = {seuil_coeurs_libre!r} : un seuil fini >= 0 est exigé")
    bande = None
    if bande_contamination is not None:
        bande = _reel(bande_contamination, "bande_contamination")
        if not (math.isfinite(bande) and bande >= 0.0):
            raise ValueError(f"bande_contamination = {bande_contamination!r} : une bande finie >= 0 est exigée")
    x = _charge(coeurs_exterieurs, "coeurs_exterieurs")
    if depassement_replique is not None:
        dr = _reel(depassement_replique, "depassement_replique")
        if not (math.isfinite(dr) and dr > 0.0):
            raise ValueError(f"depassement_replique = {depassement_replique!r} : une réplique chronométrée est > 0 et finie")
        xr = _charge(coeurs_exterieurs_replique, "coeurs_exterieurs_replique")
        if xr is not None and xr <= seuil:
            return "structure" if dr > 1.0 else "contention"
    if x is not None and x <= seuil:
        return "structure"
    if bande is not None and d > 1.0 + bande:
        return "structure"
    if x is not None:
        return "contention"
    return "indeterminee"


def margin_to_budget(projected_s, budget_s) -> float:
    """(budget − projection) / budget. ⚠️ Publiée pour la projection ACCEPTÉE, elle ne mesure PAS la fragilité (revue
    M-M7 : 0,751 à la passe 1 de R2, alors que la ligne lr 2,0 avait été coupée à 6,4 % du seuil) : la fragilité se lit
    dans la marge NÉGATIVE de chaque ligne coupée (`cut_geometry`). Les deux côtés du seuil se publient ensemble."""
    p, b = _reel(projected_s, "projected_s"), _reel(budget_s, "budget_s")
    if not (math.isfinite(p) and math.isfinite(b) and b > 0.0):
        raise ValueError(f"marge indéfinie : projection {projected_s!r}, budget {budget_s!r} (budget fini > 0 exigé)")
    return (b - p) / b


def cut_geometry(unit_s, n_units, budget_s, safety) -> dict:
    """Les deux côtés du seuil pour UNE ligne : la projection qu'on aurait faite en la GARDANT (même expression que
    `project_cost`, donc bit-identique), son dépassement (> 1 = coupée), sa marge (négative si coupée) et l'unité de
    BASCULE `budget / (n × safety)` en dessous de laquelle elle aurait été gardée. Passe 1 de R2 : lr 1,0 bascule à
    89,7 s, lr 2,0 à 204,3 s, pour une unité mesurée de 217,4 s — deux lignes, deux distances au seuil."""
    u, b, s = _reel(unit_s, "unit_s"), _reel(budget_s, "budget_s"), _reel(safety, "safety")
    if isinstance(n_units, bool) or not isinstance(n_units, numbers.Integral) or n_units < 1:
        raise ValueError(f"n_units = {n_units!r} : une ligne porte au moins une unité entière")
    if not all(math.isfinite(v) and v > 0.0 for v in (u, b, s)):
        raise ValueError(f"géométrie indéfinie : unité {unit_s!r}, budget {budget_s!r}, marge {safety!r}")
    projection = unit_s * n_units * safety
    return {"n_unites": int(n_units), "projection_si_gardee_s": projection, "depassement": projection / b,
            "marge": margin_to_budget(projection, b), "unite_de_bascule_s": b / (n_units * s)}


def cut_record(*, nature, raison, lr, cles, unit_s, n_units, budget_s, safety, unite_cpu_s=None, charge=None) -> dict:
    """L'enregistrement PUBLIÉ d'une ligne coupée : sa nature (vocabulaire FERMÉ), sa raison PROPRE (P2.110 : le
    `setdefault` du runner ne gardait que celle de la PREMIÈRE ligne — celle de lr 2,0 à la passe 1 de R2, « 47 unités
    … 255 min », n'a jamais été publiée), sa géométrie, l'unité CPU à côté de l'unité mur, et la charge mesurée."""
    if nature not in NATURES_COUPE:
        raise ValueError(f"nature = {nature!r} hors du vocabulaire fermé {NATURES_COUPE}")
    if not isinstance(raison, str) or not raison.strip():
        raise ValueError("une coupe sans raison écrite n'est pas publiable")
    rec = {"lr": lr, "cles": sorted(cles), "nature": nature, "raison": raison, "unite_s": unit_s,
           "unite_cpu_s": unite_cpu_s, "charge": charge, "budget_s": budget_s, "safety": safety}
    rec.update(cut_geometry(unit_s, n_units, budget_s, safety))
    return rec


def _system_busy_cpu_s():
    """CPU-secondes occupées par TOUTE la machine depuis le démarrage, sommées sur les CPU logiques. Formule de psutil
    (`_cpu_busy_time` : total − idle − iowait, moins guest sous Linux — celle qui nourrit `cpu_percent`, donc l'A5 du PM),
    recopiée sans l'API privée. Lecture ~3 ms. None si psutil manque ou si la lecture échoue — jamais 0.0 (porte 14)."""
    try:
        import psutil
        t = psutil.cpu_times()
        total = sum(t) - getattr(t, "guest", 0.0) - getattr(t, "guest_nice", 0.0)
        return float(total - t.idle - getattr(t, "iowait", 0.0))
    except Exception:
        return None


class LoadWindow:
    """Charge EXTÉRIEURE intégrée sur une fenêtre : `(Δ CPU occupé machine − Δ CPU de ce processus) / Δ mur`, en cœurs.

    Pourquoi pas un instantané (revue P2.110, M-M3/M-M4/M-M5/I-A1) : (a) compter les processus mesure la PRÉSENCE, pas la
    charge — 13 instantanés sur 20 montraient un python transitoire d'une session voisine à 0 % CPU, donc `structure` y
    devenait une loterie (E1) ; (b) `cpu_percent(1 s)` aux bornes lisait 68-72 % pendant qu'une boucle ne recevait que 0,53
    cœur : il ne voit pas la charge PENDANT la cellule ; (c) `doctor.project_processes()` coûte 7 à 25 s — posé dans la
    fenêtre chronométrée, il gonflait l'unité scellée de 4 à 6 %, soit l'écart qui a coupé lr 2,0 (E11). Ici deux lectures
    de compteurs cumulés, ~3 ms chacune, à ouvrir AVANT le chronomètre de la cellule et à fermer APRÈS son arrêt.
    Son propre CPU (tous threads, `process_time`) est soustrait EXACTEMENT : une cellule seule sur la machine lit 0.
    Toute source illisible rend None pour CE champ, jamais 0.0 ; une fenêtre de mur nul ne fabrique aucun ratio.
    ⚠️ Ne voit pas l'I/O ni la bande mémoire, et une moyenne lisse une rafale : c'est une mesure, pas un certificat."""

    def __init__(self, *, busy_reader=None, cpu_clock=time.process_time, wall_clock=time.monotonic):
        self._busy = _system_busy_cpu_s if busy_reader is None else busy_reader
        self._cpu, self._wall = cpu_clock, wall_clock
        self.b0 = self._lire_occupation()
        self.c0, self.w0 = cpu_clock(), wall_clock()

    def _lire_occupation(self):
        try:
            v = self._busy()
        except Exception:
            return None
        if v is None or isinstance(v, bool) or not isinstance(v, numbers.Real) or not math.isfinite(v):
            return None
        return float(v)

    def close(self) -> dict:
        mur, cpu = self._wall() - self.w0, self._cpu() - self.c0
        b1 = self._lire_occupation()
        lisible = self.b0 is not None and b1 is not None and mur > 0
        return {"mur_s": mur, "cpu_propre_s": cpu, "coeurs_propres": (cpu / mur) if mur > 0 else None,
                "coeurs_exterieurs": (((b1 - self.b0) - cpu) / mur) if lisible else None}


def cost_per_arm(units_s: dict, n_units: dict, *, safety=3.0) -> dict:
    """Calcul PUR, non levant (revue M-M9 : publiable à côté d'une décision sans jamais l'interrompre) :
    `{"projection_s": Σ(unité[bras] × n[bras]) × safety, "par_bras": {bras: contribution}}`.

    P2.110 (ii) : sur la reprise de R2, `lam05` 161,9 s, `lam099` 157,6 s, `td0_d0` 56,2 s — 2,8× entre familles ;
    une unité unique prise sur la famille lente sur-estime. `ValueError` (jamais une unité par défaut, jamais 0.0) :
    `n_units` vide ; n non entier ou négatif ; bras à n > 0 sans unité mesurée, ou unité NaN / nulle / négative
    (médiane d'un bras vide). Un bras à n = 0 n'exige aucune unité et ne figure pas dans `par_bras`."""
    s = _reel(safety, "safety")
    if not (math.isfinite(s) and s > 0.0):
        raise ValueError(f"safety = {safety!r} : une marge finie > 0 est exigée")
    if not isinstance(n_units, dict) or not n_units:
        raise ValueError("n_units vide : rien à projeter — un refus, jamais une projection 0.0 fabriquée")
    if not isinstance(units_s, dict):
        raise ValueError(f"units_s doit être un dict {{bras: unité}}, reçu {type(units_s).__name__}")
    termes, par_bras = [], {}
    for bras, n in n_units.items():
        if isinstance(n, bool) or not isinstance(n, numbers.Integral) or n < 0:
            raise ValueError(f"bras {bras!r} : n = {n!r} (entier >= 0 exigé)")
        if n == 0:
            continue
        u = units_s.get(bras)
        if u is None:
            raise ValueError(f"bras {bras!r} : {n} unités à projeter SANS unité mesurée — jamais une unité par défaut")
        uf = _reel(u, f"unité du bras {bras!r}")
        if not (math.isfinite(uf) and uf > 0.0):
            raise ValueError(f"bras {bras!r} : unité {u!r} (finie > 0 exigée : NaN = médiane d'un bras vide)")
        termes.append(u * n)
        par_bras[bras] = u * n * safety
    return {"projection_s": sum(termes) * safety, "par_bras": par_bras}


def project_cost_per_arm(units_s: dict, n_units: dict, budget_s: float, *, safety=3.0, label="run") -> float:
    """`project_cost` PAR BRAS, pour les règles FUTURES dont les bras diffèrent (P2.110 (ii)). Lève `CostTooHighToStart`
    si Σ(unité × n) × safety > budget, avec la contribution de CHAQUE bras dans le message ; rend la projection sinon.
    Sur un seul bras, bit-identique à `project_cost`. ⚠️ Pas rétro-applicable à une règle scellée sur « l'unité MESURÉE
    sur la première cellule neuve » (TD-STEP-PILOT-R2) : changer de procédure après scellement est E11 — et les temps par
    cellule de R2 n'ont jamais été persistés (seulement imprimés)."""
    c = cost_per_arm(units_s, n_units, safety=safety)
    b = _reel(budget_s, "budget_s")
    if not (math.isfinite(b) and b > 0.0):
        raise ValueError(f"budget_s = {budget_s!r} : un budget fini > 0 est exigé")
    if c["projection_s"] > b:
        detail = ", ".join(f"{bras} {n_units[bras]} × {units_s[bras]:.1f}s = {p / 60:.0f} min"
                           for bras, p in sorted(c["par_bras"].items(), key=lambda kv: -kv[1]))
        raise CostTooHighToStart(
            f"{label}: projection par bras {c['projection_s'] / 60:.0f} min (marge {safety:g}) > budget {b / 60:.0f} min "
            f"— {detail}. Réduire n, réduire l'unité, ou relever le budget EXPLICITEMENT.")
    return c["projection_s"]
