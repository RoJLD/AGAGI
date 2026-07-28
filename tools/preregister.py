"""Pré-enregistrement EXÉCUTABLE d'une règle de lecture — la garde manquante de la classe E11.

Le registre des erreurs (`docs/REF/REGISTRE_ERREURS.md`) porte E11 — « choix d'analyse post-hoc, jardin
aux sentiers qui bifurquent » — avec la mention **garde : AUCUNE**, et le backlog P3.1 la réclame depuis.
Ses occurrences sont des seuils et des partitions arrêtés APRÈS avoir vu les données.

La discipline manuelle (écrire la règle dans le record avant le run) a été tenue deux fois — EVO-005 et
EVO-006 — mais rien ne l'ATTESTE : un lecteur ne peut pas distinguer une règle écrite avant d'une règle
écrite après, et l'auteur non plus, six mois plus tard. Ce module rend la chose vérifiable :

    from tools.preregister import preregister, verify
    preregister("EVO-007", {                     # AVANT de lancer le run
        "dv": "raw", "threshold": 0.5, "claim": "existence", ...
    })
    ...                                          # run
    rule = verify("EVO-007")                     # lève si le fichier a été retouché après coup

Deux propriétés, et ce sont les seules qui comptent :
  * **immuable** — ré-enregistrer un contenu DIFFÉRENT sous le même nom lève `PreregistrationConflict`.
    Un fichier de pré-inscription ne se corrige pas : on en écrit un nouveau (`EVO-007-bis`) et l'ancien
    reste, ce qui rend le changement de règle VISIBLE au lieu de le rendre invisible.
  * **scellé** — le hash du contenu est stocké AVEC lui ; `verify()` le recalcule et lève si quelqu'un a
    édité le JSON à la main. Ça ne prouve pas l'antériorité au run (rien ne le peut hors horodatage
    externe), mais ça prouve la NON-MODIFICATION après coup, qui est le mode de défaillance réel.

⚠️ Ce que cette garde NE fait PAS : elle n'empêche pas de choisir une règle stupide, ni d'ajouter APRÈS
coup un instrument que la règle ne mentionnait pas — c'est exactement ce qui est arrivé à EVO-006, dont
la sonde mécaniste a été choisie après avoir vu quelle sous-tâche avait bougé. Elle rend ce choix
DÉTECTABLE (il n'est pas dans le fichier scellé), pas impossible.
"""
import hashlib
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR = os.path.join(_ROOT, "docs", "preregistrations")


class PreregistrationConflict(Exception):
    """Tentative de ré-enregistrer un contenu DIFFÉRENT sous un nom déjà pris."""


class PreregistrationTampered(Exception):
    """Le contenu ne correspond plus à son sceau -> le fichier a été édité après coup."""


def _seal(rule: dict) -> str:
    """Hash du contenu, indépendant de l'ordre des clés et du formatage."""
    return hashlib.sha256(json.dumps(rule, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def path_for(name: str) -> str:
    return os.path.join(_DIR, f"{name}.json")


def preregister(name: str, rule: dict, *, _dir=None) -> str:
    """Scelle `rule` sous `name`. Idempotent à contenu IDENTIQUE ; lève si le contenu DIFFÈRE."""
    d = _dir or _DIR
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.json")
    payload = {"name": name, "rule": rule, "seal": _seal(rule)}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("seal") != payload["seal"]:
            raise PreregistrationConflict(
                f"« {name} » est déjà pré-enregistré avec une règle DIFFÉRENTE. Une pré-inscription ne se "
                f"corrige pas : enregistrer « {name}-bis » et garder les deux, pour que le changement de "
                f"règle soit VISIBLE.")
        return p                                     # ré-écriture à l'identique : sans effet
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
    return p


def verify(name: str, *, _dir=None) -> dict:
    """Renvoie la règle scellée, ou lève si elle a été retouchée. À appeler AVANT de lire les résultats."""
    d = _dir or _DIR
    p = os.path.join(d, f"{name}.json")
    if not os.path.exists(p):
        raise FileNotFoundError(f"aucune pré-inscription « {name} » — la règle n'a pas été scellée avant le run")
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    if _seal(payload.get("rule", {})) != payload.get("seal"):
        raise PreregistrationTampered(
            f"« {name} » ne correspond plus à son sceau : le fichier a été édité après enregistrement")
    return payload["rule"]
