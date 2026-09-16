"""Journal des alertes PM (paths.pm_dir("alerts.jsonl"), append-only, writer = la session PM).

Cycle d'une clé d'alerte : `emise` (première apparition au tableau) -> `suivie` (elle a disparu du tableau)
-> `repetee` (elle réapparaît après avoir été suivie). Une alerte répétée est la règle du registre des erreurs
appliquée à l'organisation : deux fois -> le PM inscrit le cliquet manquant au backlog, il ne renvoie pas le
message. Les compteurs publiés (ROLES.md via roles_counts) se RECOMPUTENT d'ici, jamais recopiés.
"""
import json
import os


def charger(path):
    charger.illisibles = 0
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for ligne in fh:
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    out.append(json.loads(ligne))
                except ValueError:
                    charger.illisibles += 1
    except OSError:
        return []
    return out


charger.illisibles = 0


def ouvertes(journal):
    """Dernier état par clé : la clé est ouverte si sa dernière ligne n'est pas `suivie`."""
    dernier = {}
    for l in journal:
        dernier[l["cle"]] = l
    return {k: v for k, v in dernier.items() if v["statut"] != "suivie"}


def deja_suivies(journal):
    return {l["cle"] for l in journal if l["statut"] == "suivie"}


def _ligne(a, statut, now):
    return {"ts": now, "cle": a["cle"], "id": a["id"], "gravite": a["gravite"], "message": a["message"], "statut": statut}


def diff(board, journal, now):
    ouv, suivies = ouvertes(journal), deja_suivies(journal)
    presentes = {a["cle"]: a for a in board["alertes"]}
    nouvelles = [a for k, a in presentes.items() if k not in ouv and k not in suivies]
    repetees = [a for k, a in presentes.items() if k not in ouv and k in suivies]
    disparues = sorted(k for k in ouv if k not in presentes)
    lignes = [_ligne(a, "emise", now) for a in nouvelles] + [_ligne(a, "repetee", now) for a in repetees]
    for k in disparues:
        l = dict(ouv[k])
        l.update({"ts": now, "statut": "suivie"})
        lignes.append(l)
    return {"nouvelles": nouvelles, "disparues": disparues, "repetees": repetees, "lignes": lignes}


def ajouter(path, lignes):
    if not lignes:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for l in lignes:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")


def compteurs(journal, now, fenetre_s=30 * 86400, delai_suivi_s=48 * 3600):
    journal = [l for l in journal if l["ts"] <= now]           # un compteur évalué à `now` ne voit pas l'avenir
    debut = now - fenetre_s
    emissions = [l for l in journal if l["statut"] in ("emise", "repetee") and l["ts"] >= debut]
    suivis = {}
    for l in journal:
        if l["statut"] == "suivie":
            suivis.setdefault(l["cle"], []).append(l["ts"])
    suivies_48h = fausses = ouvertes_n = 0
    for e in emissions:
        apres = [t for t in suivis.get(e["cle"], []) if t >= e["ts"]]
        if apres and min(apres) - e["ts"] <= delai_suivi_s:
            suivies_48h += 1
        elif apres:
            fausses += 1
        elif now - e["ts"] > delai_suivi_s:
            fausses += 1
        else:
            ouvertes_n += 1
    return {"emises": len(emissions), "suivies_48h": suivies_48h, "fausses_ou_ignorees": fausses,
            "repetees": sum(1 for l in emissions if l["statut"] == "repetee"), "ouvertes": ouvertes_n}
