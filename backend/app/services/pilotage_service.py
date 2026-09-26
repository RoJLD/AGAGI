"""Service du pilotage : assemble `pilotage_v1` pour la route, en mémoire, SANS écrire un fichier.

⚠️ La flotte n'est pas recalculée sur le chemin du poll. Mesuré le 2026-09-24 (charge notée : 40 % de CPU,
9 processus python) : `tools.pm.snapshot.snapshot()` coûte 15,6 / 16,6 / 18,1 s — au-delà du timeout de
10 s du client — tandis que toute la roadmap coûte 0,70 s. Le poll sert donc le `BOARD.json` du tick PM
(dont le PM est l'unique writer) avec son ÂGE publié ; `frais=True` recalcule en mémoire, et seul un clic
explicite le déclenche.

⚠️ `frais=True` est REFUSÉ, jamais silencieusement, si le DERNIER tableau connu (`BOARD.json`, jamais un
nouveau `snapshot()` — ce serait le coût de 18 s qu'on refuse d'engager) annonce une simulation en vol
(`charge_connue.sims_en_vol > 0`, spec §5) : recalculer la flotte pendant qu'une sim tourne, c'est la
contention kuzu / le coût contaminé que l'alerte A5 du board interdit déjà côté PM. Sans tableau lisible, il
n'y a pas de mesure sur laquelle refuser : le recalcul est lancé, et la charge INCONNUE est dite (F6).
Limite connue, non corrigée ici (elle touche `snapshot.py`, qui appartient au PM) : `snapshot(racine)` lit
bulletins et registre par `paths.*`, donc depuis un worktree, sans variable d'environnement, il lit le
`data/` du WORKTREE et non celui du dépôt commun.

⚠️ Chaque bloc est validé ICI contre le modèle nommé que la route applique (`PilotageV1`), puis passé au JSON
strict comme la route le fera : `charge`, `flotte` et `roadmap.portes_agi` recopient des sources que
`pilotage.py` ne possède pas (`BOARD.json`, `ROLES_COUNTS.json`, `records_graph.json`), et un seul champ de type
inattendu donnait un 500 à la sérialisation, APRÈS le filet d'exception, sans ligne d'aveuglement (F3). Un bloc
refusé devient `None` plus une ligne qui le NOMME ; les autres restent servis. `roadmap.portes_agi` est un
SOUS-bloc (source étrangère) : il tombe seul, jamais toute la roadmap avec lui.

⚠️ Deux refus que la route ne ferait PAS, ou trop tard (re-revue de 6a062eeb) : l'ENCODAGE UTF-8 de
`JSONResponse.render` (un surrogate isolé passait tous les filets puis donnait un 500 — G2), et le float non fini
dans un champ `Any` que pydantic sert à `null` SANS le dire (G3). Le mode dégradé est lui-même rendu servable.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any

from pydantic import TypeAdapter

# ⚠️ Import GARDÉ (2026-09-26, régression du smoke docker) : `tools/` ne fait pas partie de l'image backend, il
# n'y arrive que par un volume du compose. Importé sans garde, une absence de `tools.pm` (volume manquant,
# dépendance absente de backend/requirements.txt) tuait le processus uvicorn AU DÉMARRAGE : /health tombait
# avec lui, alors que le tableau de bord n'est qu'une route parmi d'autres. Même forme que `routes/health.py`
# pour `tools.parity_check`. L'absence n'est pas tue pour autant : la route rend le mode dégradé, dont la
# ligne `pilotage: ImportError ...` NOMME le module manquant, et le smoke de la CI rougit sur ce marqueur.
try:
    from tools.pm import pilotage
    from tools.pm.snapshot import snapshot
    _IMPORT_REFUSE: Exception | None = None
except Exception as _exc:                                  # noqa: BLE001 — NOMMÉ par get_pilotage, jamais avalé
    pilotage = None
    snapshot = None
    _IMPORT_REFUSE = _exc

from ..schemas import PilotageV1, Roadmap

_SCHEMA = "pilotage_v1"   # recopie de tools.pm.pilotage.SCHEMA : le mode dégradé doit le rendre SANS ce module

_TTL_DEFAUT = 30.0
_cache: dict[str, Any] = {"at": 0.0, "valeur": None}

# Le type de chaque bloc est LU sur le modèle de la route, jamais recopié : un bloc validé ici est validé
# exactement comme `response_model=PilotageV1` le fera.
_BLOCS = ("flotte", "roadmap", "portes", "charge")
_ADAPTATEURS = {cle: TypeAdapter(PilotageV1.model_fields[cle].annotation) for cle in _BLOCS}
_PORTES_AGI = TypeAdapter(Roadmap.model_fields["portes_agi"].annotation)
_ENVELOPPE = TypeAdapter(PilotageV1)


class _NonFini(ValueError):
    """Un float non fini que pydantic, en mode json, servirait à `null` SANS le dire (G3)."""


class _EnveloppeRefusee(Exception):
    """Le filet final a refusé l'enveloppe entière : le mode dégradé le NOMME (G4)."""


def _vider_cache() -> None:
    """Réservé aux tests : le cache est un état de processus."""
    _cache["at"] = 0.0
    _cache["valeur"] = None


def _texte_servable(texte: str) -> str:
    """Une chaîne que `JSONResponse.render` peut ENCODER en UTF-8 : un surrogate isolé devient son
    échappement VISIBLE (`\\ud800`), jamais une suppression (G2). `decode("utf-8")` et non `decode("ascii")` :
    ce dernier lève sur le premier accent de ces lignes françaises."""
    return texte.encode("utf-8", "backslashreplace").decode("utf-8")


def _premier_non_fini(valeur: Any, chemin: str, _ancetres: frozenset = frozenset()) -> str | None:
    """Chemin du PREMIER float non fini (clé ou valeur, à toute profondeur, dans un dict, une liste ou un
    tuple), `None` s'il n'y en a pas. Pré-passe sur le bloc BRUT, avant pydantic : en mode json, pydantic sert
    à `null` un `nan` ou un `inf` placé dans un champ `Any`, sans ligne (G3). Une structure cyclique lève
    `ValueError` au lieu de boucler."""
    if isinstance(valeur, float):
        return None if math.isfinite(valeur) else chemin
    if not isinstance(valeur, (dict, list, tuple)):
        return None
    if id(valeur) in _ancetres:
        raise ValueError(f"structure cyclique à {chemin}")
    ancetres = _ancetres | {id(valeur)}
    if isinstance(valeur, dict):
        for cle, sous in valeur.items():
            trouve = _premier_non_fini(cle, f"{chemin}[clé {cle!r}]", ancetres)
            if trouve is None:
                trouve = _premier_non_fini(sous, f"{chemin}.{cle}" if isinstance(cle, str) else f"{chemin}[{cle!r}]",
                                           ancetres)
            if trouve is not None:
                return trouve
        return None
    for i, sous in enumerate(valeur):
        trouve = _premier_non_fini(sous, f"{chemin}[{i}]", ancetres)
        if trouve is not None:
            return trouve
    return None


def _servable(adaptateur: TypeAdapter, valeur: Any, nom: str = "pilotage") -> None:
    """Rejoue ce que fait la route (FastAPI 0.128 : `validate_python(..., from_attributes=True)`, puis
    `dump_python(mode="json", by_alias=True)`, puis `JSONResponse.render` de Starlette, c.-à-d.
    `json.dumps(..., ensure_ascii=False, allow_nan=False)` PUIS `.encode("utf-8")`) ; lève si elle refuserait.
    Le JSON strict compte (un `float('inf')` VALIDE pour pydantic fait encore un 500 au rendu), l'encodage aussi
    (un surrogate isolé passe `json.dumps` et fait un 500 à l'`encode` — G2).

    Et lève AUSSI là où la route ne refuserait RIEN : un float non fini dans un champ `Any`, qu'elle servirait
    à `null` sans le dire (G3, `_premier_non_fini`, chemin préfixé par `nom`)."""
    chemin = _premier_non_fini(valeur, nom)
    if chemin is not None:
        raise _NonFini(f"float non fini à {chemin} -- refusé AVANT la route (dans un champ libre, pydantic le "
                       "servirait à null sans le dire)")
    v = adaptateur.validate_python(valeur, from_attributes=True)
    json.dumps(adaptateur.dump_python(v, mode="json", by_alias=True), ensure_ascii=False,
               allow_nan=False).encode("utf-8")


def _resume(exc: Exception) -> str:
    """Le refus RÉSUMÉ — jamais l'erreur pydantic vidée en entier dans une ligne `aveugle`."""
    errors = getattr(exc, "errors", None)
    if callable(errors):
        try:
            liste = errors(include_url=False)
            premiere = liste[0]
            loc = ".".join(str(x) for x in premiere.get("loc", ())) or "(racine)"
            return f"{len(liste)} erreur(s) de validation, la première sur {loc} : {premiere.get('msg')}"
        except Exception:                                  # noqa: BLE001 — le résumé ne doit jamais lever
            pass
    return f"{type(exc).__name__}: {str(exc)[:160]}"


def _ligne_de_refus(nom: str, exc: Exception, suite: str) -> str:
    if isinstance(exc, _NonFini):
        return f"{nom} : bloc refusé, {exc} -- servi à null, {suite}"
    return f"{nom} : bloc refusé par le modèle de la route ({_resume(exc)}) -- servi à null, {suite}"


def _blocs_servables(out: dict) -> dict:
    """Met à `None` tout bloc que la route refuserait, avec une ligne qui le NOMME ; les autres restent.

    `roadmap.portes_agi` est jugé AVANT la roadmap, comme un sous-bloc : il recopie `records_graph.json`, source
    étrangère, et un surrogate ou un non-fini y aveuglait toute la roadmap du backlog (même règle que la couche 2
    de F3 dans `pilotage.py`). Chaque ligne est enfin rendue ENCODABLE : une ligne recopiée du board, ou un
    chemin, peut porter un surrogate — elle ne doit pas faire tomber l'enveloppe entière."""
    out = dict(out)
    aveugle = list(out.get("aveugle") or [])
    rm = out.get("roadmap")
    if isinstance(rm, dict) and rm.get("portes_agi") is not None:
        try:
            _servable(_PORTES_AGI, rm["portes_agi"], "roadmap.portes_agi")
        except Exception as exc:                           # noqa: BLE001 — refus NOMMÉ, jamais un 500
            aveugle.append(_ligne_de_refus("portes_agi", exc, "le reste de la roadmap reste servi"))
            out["roadmap"] = dict(rm, portes_agi=None)
    for cle in _BLOCS:
        if out.get(cle) is None:
            continue
        try:
            _servable(_ADAPTATEURS[cle], out[cle], cle)
        except Exception as exc:                           # noqa: BLE001 — refus NOMMÉ, jamais un 500
            aveugle.append(_ligne_de_refus(cle, exc, "les autres blocs restent servis"))
            out[cle] = None
    out["aveugle"] = [_texte_servable(a) if isinstance(a, str) else a for a in aveugle]
    return out


def _sims_en_vol_dernier_tableau(racine: str) -> float | None:
    """Lit le DERNIER `BOARD.json` connu (jamais un `snapshot()` neuf) pour juger si `frais=1` doit être
    refusé. `None` si le tableau est absent, illisible, ou ne MESURE pas `sims_en_vol` (absent, `null`,
    booléen, non fini, hors bornes) : un refus se prononce sur une mesure, jamais sur une absence —
    `get_pilotage` suit alors son chemin normal et DIT que la charge était inconnue.

    G8 : un entier JSON de plus de 309 chiffres fait lever `OverflowError` à `math.isfinite` — non attrapée,
    elle aveuglait TOUT le pilotage ; c'est une non-mesure."""
    try:
        dernier = pilotage.read_board(racine)
    except Exception:                                      # noqa: BLE001 — un tableau illisible ne bloque rien
        return None
    if not isinstance(dernier, dict):
        return None
    cc = dernier.get("charge_connue")
    if not isinstance(cc, dict):
        return None
    sims = cc.get("sims_en_vol")
    if isinstance(sims, bool) or not isinstance(sims, (int, float)):
        return None
    try:
        if not math.isfinite(sims):
            return None
    except OverflowError:
        return None
    return sims


def _mode_degrade(now: float, racine: Any, exc: Exception) -> dict:
    """Le dict du mode dégradé, lui-même SERVABLE (G2) : la ligne est rendue encodable (un message d'exception
    peut porter un surrogate isolé) et `repo_root` est une chaîne POSIX (un `racine_depot` qui rend un `Path`
    donnait un 500). Un refus de l'enveloppe est NOMMÉ comme tel (G4)."""
    if isinstance(exc, _EnveloppeRefusee):
        texte = f"pilotage: enveloppe refusée par le modèle de la route ({exc}) -- les quatre blocs servis à null"
    else:
        texte = f"pilotage: {type(exc).__name__}: {exc}"
    return {"schema": _SCHEMA, "generated_at": now,
            "repo_root": None if racine is None else _texte_servable(str(racine).replace("\\", "/")),
            "aveugle": [_texte_servable(texte)],
            "flotte": None, "roadmap": None, "portes": None, "charge": None}


def get_pilotage(ttl_s: float = _TTL_DEFAUT, frais: bool = False) -> dict:
    now = time.time()
    if not frais and _cache["valeur"] is not None and (now - _cache["at"]) < ttl_s:
        return _cache["valeur"]
    racine = None
    refus_frais = None
    sans_mesure = None
    effectif = frais
    try:                                                   # TOUT dans le filet, résolution de la racine comprise (F7)
        if _IMPORT_REFUSE is not None:
            raise ImportError(f"tools.pm indisponible dans ce processus ({type(_IMPORT_REFUSE).__name__}: "
                              f"{_IMPORT_REFUSE}) -- volume ./tools absent du conteneur, ou dépendance de "
                              "tools.pm absente de backend/requirements.txt")
        racine = pilotage.racine_depot()
        if frais:
            sims = _sims_en_vol_dernier_tableau(racine)
            if sims is None:
                sans_mesure = ("frais=1 accepté SANS mesure de charge (dernier tableau absent, illisible, ou "
                               "sims_en_vol absent ou non mesurable) -- recalcul lancé à l'aveugle")
            elif sims > 0:
                effectif = False
                refus_frais = (f"frais=1 refusé : {sims:g} simulation(s) en vol d'après le dernier tableau "
                               "connu -- recalcul de la flotte NON déclenché (charge), poll normal servi")
        snap = snapshot(racine) if effectif else None
        out = pilotage.compute_pilotage(
            snap,
            pilotage.read_backlog(racine),
            pilotage.read_records_graph(racine),
            pilotage.read_roles_counts(racine),
            pilotage.read_portes(racine),
            now,
            repo_root=racine,
            board=None if effectif else pilotage.read_board(racine),
        )
        out = _blocs_servables(out)
        try:                                               # filet final : l'enveloppe entière passe la route
            _servable(_ENVELOPPE, out)
        except Exception as exc:                           # noqa: BLE001 — NOMMÉ par le mode dégradé
            raise _EnveloppeRefusee(_resume(exc)) from exc
    except Exception as exc:                               # noqa: BLE001 — l'erreur est NOMMÉE, jamais avalée
        out = _mode_degrade(now, racine, exc)
    if not effectif:
        _cache["at"], _cache["valeur"] = now, out
    ajouts = [a for a in (refus_frais, sans_mesure) if a]
    if ajouts:
        out = dict(out)
        out["aveugle"] = list(out.get("aveugle") or []) + ajouts
    return out
