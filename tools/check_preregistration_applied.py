"""Cliquet : un record MESURE-t-il les grandeurs que sa règle scellée EXIGE ?

⚠️ Né d'un échec, trouvé en revue adversariale le 2026-08-04 (classe E11, occurrence 4).

`tools/preregister.py` scelle la RÈGLE par un hash : il prouve qu'elle n'a pas été réécrite après coup.
Il ne prouve RIEN sur la fidélité de son APPLICATION. EDR-EVO-019 en est la démonstration : sa règle
exigeait littéralement « le plafond doit RÉDUIRE `|logit|` médian », le record a substitué une réduction
de FAN-IN, et a écrit « les deux conditions sont satisfaites ». Le sceau était intact. Le mot « logit »
n'apparaissait pas une seule fois dans le record.

Ce cliquet ferme cet angle mort par une intersection de vocabulaire : les GRANDEURS NOMMÉES dans les
clauses de mesure d'une règle scellée doivent apparaître dans le record qui s'en réclame. Une DV
substituée en silence ne passe plus.

⚠️ Portée honnête : c'est une vérification LEXICALE, pas sémantique. Elle attrape l'omission (le record
ne parle jamais de la grandeur) — pas le cas où le record nomme la grandeur tout en mesurant autre chose.
Elle est donc nécessaire, pas suffisante ; la revue adversariale reste la garde de dernier recours.
"""
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PREREG = os.path.join(_ROOT, "docs", "preregistrations")
_EDR = os.path.join(_ROOT, "docs", "EDR")

# Champs d'une règle qui DÉCRIVENT une mesure à faire (par opposition au contexte narratif).
# ⚠️ LISTE BLANCHE ELARGIE le 2026-09-02 -- elle SAUTAIT EN SILENCE. Mesure : sur 23 regles scellees,
# seules 8 etaient REELLEMENT inspectees ; 14 etaient sautees parce qu'aucune grandeur n'en sortait,
# faute de connaitre leurs champs. Le plus coûteux : `discrimination`, present dans 17 regles, porte la
# regle de lecture de la plupart des regles EVO. Et `instruments_autorises` est le champ que la cloture
# d'E11 avait INVENTE -- le cliquet ne le lisait pas.
# C'est la TROISIEME liste blanche silencieuse trouvee en deux jours (apres `_LIST_KEYS` du frontmatter
# et `_INSTRUMENT_PATTERNS` du nommage). Regle qui en sort : une liste blanche doit RAPPORTER ce qu'elle
# ecarte, sinon elle transforme son ignorance en succes.
_MEASURE_FIELDS = ("dv_primaire", "dv", "dv_mecaniste", "dv_survie", "dv_primaire_corrigee",
                   "dv_secondaire", "dv_sante_lignee",
                   "controle_de_manipulation_OBLIGATOIRE", "controle", "prevol_decisif",
                   "prevol_mesure", "prevol_obligatoire",
                   "regle_de_lecture_continue", "regle_existence", "regle_frequence",
                   "discrimination", "instruments_autorises", "garde_puissance",
                   "predictions_chiffrees_AVANT_le_run", "seuil")

# Tokens trop génériques pour porter une exigence de mesure.
_STOP = {"raw", "sal", "n", "p", "seed", "seeds", "bras", "age", "med", "max", "min", "w", "k"}


def _quantities(rule: dict):
    """Grandeurs NOMMÉES dans les clauses de mesure : `token` entre backticks, ou motif |token|."""
    out = set()
    for f in _MEASURE_FIELDS:
        v = rule.get(f)
        if not isinstance(v, str):
            continue
        for m in re.findall(r"`([^`]{2,40})`", v):
            out.add(m.strip())
        for m in re.findall(r"\|([A-Za-z_][A-Za-z0-9_]{1,30})\|", v):
            out.add(m.strip())
    # normalise : on ne garde que le coeur identifiant, et on jette les termes generiques
    keep = set()
    for t in out:
        # `RETAIN_intact`(`lr=0.002`) nomme la grandeur `lr` a un NIVEAU : un niveau n'est pas une
        # grandeur. Sans cette coupure, `lr=0.002` devenait le token `lr0002`, introuvable dans tout record
        # honnete -- mesure P2.28 (2026-09-06) : la famille DELAYED-COORD aurait ete flaggee A TORT sur
        # ['lr0002', 'lr005'] le jour meme de son rattachement, alors que son record ecrit `lr=0.002`.
        core = re.sub(r"[^A-Za-z0-9_\[\]]", "", re.split(r"[(=]", t)[0]).strip()
        if len(core) >= 3 and core.lower() not in _STOP:
            keep.add(core)
    return keep


_CITATION = "docs/preregistrations/{name}.json"


def _edr_texts():
    """{chemin: texte} de tous les records -- lus UNE fois par passe, pas une fois par regle."""
    out = {}
    if not os.path.isdir(_EDR):
        return out
    for fn in sorted(os.listdir(_EDR)):
        if fn.endswith(".md"):
            p = os.path.join(_EDR, fn)
            with open(p, encoding="utf-8") as f:
                out[p] = f.read()
    return out


def _declared(payload: dict, *, strict_only: bool = False):
    """Chemins (sous docs/EDR) DECLARES par la cle `record`, a DEUX niveaux qui n'ont PAS le meme contrat :
      * au niveau de l ENVELOPPE (hors sceau) -- la cle de P2.28 : une declaration CORRIGEABLE, donc
        STRICTE. Une valeur qui ne resout vers aucun fichier est un probleme VISIBLE (typo, record
        renomme), jamais avale ;
      * dans `rule` (DANS le sceau) -- ⚠️ ce champ EXISTAIT AVANT P2.28 dans 24 regles scellees, en PROSE
        (`"EDR-EVO-006 (replication directe)"`) et non en chemin. Une regle scellee ne se corrige pas :
        le lire strictement crierait a jamais sur des regles incorrigibles (mesure le 2026-09-06 : le
        test du depot reel tombait sur 13 familles, et le refutateur de ce design etait mort). Il n est
        donc utilise que s il RESOUT vers un fichier, et n est jamais signale comme pendant.
    `strict_only=True` ne renvoie que les declarations d enveloppe (pour calculer les pendantes)."""
    def _as_list(v):
        return [] if v is None else ([v] if isinstance(v, str) else list(v))
    top = _as_list(payload.get("record"))
    if strict_only:
        return top
    inner = [d for d in _as_list(payload.get("rule", {}).get("record"))
             if isinstance(d, str) and os.path.isfile(os.path.join(_EDR, d))]
    return top + inner


def _record_text_for(name: str, payload=None, texts=None):
    """Les records qui SE RECLAMENT de cette pre-inscription -- trois formes, toutes DECLAREES :
      1. `record:` dans le JSON (cf. `_declared`) -- la regle du depot : declarer, pas deviner ;
      2. le record CITE `docs/preregistrations/<name>.json` -- forme sous laquelle 13 records se
         reclamaient deja de leur regle le 2026-09-06 (une declaration PAR LE RECORD) ;
      3. le nom de fichier du record prefixe la base (`<base>_*.md`) -- l'ancien et seul appariement.
    ⚠️ P2.28 : la forme 3 seule ratait DELAYED-COORD-LR-N12 (record `EDR-DELAYED-COORD_*`) et
    S2-FLOOR-PRONOSTIC (record `S2-013_*`) : deux familles passaient toutes les portes sans etre verifiees
    par aucune. Une mention NUE du nom en prose ne rattache PAS (citer EVO-007 en passant n'est pas
    mesurer EVO-007) -- contre-exemple gele dans tests/sandbox/test_preregistration_applied.py."""
    texts = _edr_texts() if texts is None else texts
    hits = {os.path.join(_EDR, d) for d in _declared(payload or {})
            if os.path.isfile(os.path.join(_EDR, d))}
    cite, base = _CITATION.format(name=name), name.split("-bis")[0]
    for p, t in texts.items():
        if cite in t or os.path.basename(p).startswith(base + "_"):
            hits.add(p)
    return sorted(hits)


def _familles():
    """{base: [(name, payload), ...]} -- la FAMILLE = base + chaine -bis, la meme decoupe que dans
    `nouvelles_sans_grandeur`. C'est l'ASYMETRIE entre les portes (famille pour les grandeurs, fichier pour
    le record) qui a ouvert P2.28 : une seule decoupe, partagee, la ferme."""
    fam = {}
    if not os.path.isdir(_PREREG):
        return fam
    for fn in sorted(os.listdir(_PREREG)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        with open(os.path.join(_PREREG, fn), encoding="utf-8") as f:
            fam.setdefault(name.split("-bis")[0], []).append((name, json.load(f)))
    return fam


def _inspection():
    """Par famille : (base, membres, grandeurs UNION, records UNION, declarations introuvables, texte).
    Source UNIQUE de scan(), couverture() et main() -- ce qui est compte est exactement ce qui est verifie."""
    texts = _edr_texts()
    out = []
    for base, membres in sorted(_familles().items()):
        qty, recs, dangling = set(), set(), []
        for name, payload in membres:
            qty |= _quantities(payload.get("rule", {}))
            recs.update(_record_text_for(name, payload, texts))
            dangling += [d for d in _declared(payload, strict_only=True)
                         if not os.path.isfile(os.path.join(_EDR, d))]
        recs = sorted(recs)
        text = "\n".join(texts[r] if r in texts else open(r, encoding="utf-8").read() for r in recs)
        out.append((base, membres, qty, recs, dangling, text))
    return out


# Regles scellees AVANT l'adoption de la convention « backticker les grandeurs » : leurs clauses de
# mesure sont en prose (« raw = succes/essais du champion »), donc AUCUNE grandeur n'en est extractible.
# Elles sont declarees NON INSPECTABLES -- pas « verifiees ». Deviner des identifiants nus produirait des
# faux positifs ; on ne proxifie pas ce qu'on ne sait pas mesurer, on le declare.
_LEGATAIRES_SANS_BACKTICK = frozenset({
    "EVO-006-REPLICATION", "EVO-007", "EVO-007-bis", "EVO-007-bis2", "EVO-008",
    "EVO-010", "EVO-011", "EVO-012", "EVO-015", "EVO-016", "EVO-017", "EVO-017-bis", "EVO-020",
})
# ⚠️ EVO-009 a ete RETIRE de cette dette le 2026-09-02 : l'elargissement des champs de mesure a rendu
# sa grandeur extractible. C'est le test `test_the_legacy_declaration_is_STILL_REAL` qui l'a impose --
# une dette qui ne peut plus etre invalidee n'est plus une dette, c'est un commentaire.


def couverture():
    """(inspectees, sans_grandeur, sans_record, total) en FAMILLES (base + chaine -bis) -- l'unite que
    scan() verifie. ⚠️ P2.28 : compter par FICHIER quand l'extractibilite se juge par famille faisait
    tomber DELAYED-COORD-LR-N12 dans « sans grandeur » ET sa -bis dans « sans record » : deux comptes
    honnetes chacun, une famille verifiee par personne. Mesure : 32 fichiers -> 25 familles."""
    insp = sans_qty = sans_rec = 0
    for _, _, qty, recs, _, _ in _inspection():
        if not qty:
            sans_qty += 1
        elif not recs:
            sans_rec += 1
        else:
            insp += 1
    return (insp, sans_qty, sans_rec, insp + sans_qty + sans_rec)


def familles_sans_record():
    """Familles qui NOMMENT des grandeurs mais dont aucun record ne se reclame (ni declare, ni cite, ni
    prefixe). ⚠️ Ce n'est PAS « aucun record n'existe » : le distinguer sans deviner est impossible --
    on ne proxifie pas, on NOMME les familles et un humain tranche (2026-09-06 : EVO-022, EVO-028-SMOKE)."""
    return [base for base, _, qty, recs, _, _ in _inspection() if qty and not recs]


def nouvelles_sans_grandeur():
    """Regles NON legataires dont aucune grandeur n'est extractible : la convention n'a pas ete suivie.

    ⚠️ Semantique de FAMILLE (2026-09-02) : une pre-inscription ne se corrige pas -- un amendement
    passe par « -bis » et garde les deux fichiers. Juger chaque fichier ISOLEMENT rendait l'original
    ineparable a jamais (le cliquet a mordu sur S2-FLOOR-PRONOSTIC le jour meme de son scellement,
    et la voie -bis ne l'aurait pas eteint). L'extractibilite se juge donc sur l'UNION de la famille
    (base + chaine -bis) ; une famille SANS AUCUN backtick echoue toujours -- contre-exemple gele
    dans tests/sandbox/test_preregistration_applied.py."""
    if not os.path.isdir(_PREREG):
        return []
    familles = {}
    for fn in sorted(os.listdir(_PREREG)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        with open(os.path.join(_PREREG, fn), encoding="utf-8") as f:
            rule = json.load(f).get("rule", {})
        base = name.split("-bis")[0]
        familles.setdefault(base, []).append((name, bool(_quantities(rule))))
    out = []
    for base, membres in sorted(familles.items()):
        if any(qty for _, qty in membres):
            continue                              # au moins un membre est verifiable -> famille OK
        for name, _ in membres:
            if name not in _LEGATAIRES_SANS_BACKTICK:
                out.append(name)
    return out


def scan():
    """Par FAMILLE : l'UNION des grandeurs nommees par ses membres, contre l'UNION des records qui se
    reclament de N'IMPORTE QUEL membre. ⚠️ P2.28 (mesure 2026-09-02) : juge par FICHIER, la base
    DELAYED-COORD-LR-N12 (0 grandeur) et sa -bis (7 grandeurs, record non prefixe) tombaient chacune dans
    un trou different ; le record existait, citait la regle, mentionnait les grandeurs -- et n'a jamais
    ete confronte a rien. Retour : liste de (base_de_famille, record_ou_declaration, grandeurs_absentes)."""
    problems = []
    for base, _, qty, recs, dangling, text in _inspection():
        for d in dangling:
            problems.append((base, d, ["RECORD DECLARE (`record:`) INTROUVABLE sous docs/EDR"]))
        if not qty or not recs:
            continue      # rien a exiger, ou aucun record ne se reclame encore de la famille (transitoire)
        # ⚠️ Corrige le 2026-09-07 : la NORMALISATION etait ASYMETRIQUE. Les grandeurs de la regle
        # passent par `re.sub(r"[^A-Za-z0-9_\[\]]", "", ...)` (`env.big_kills` -> `envbig_kills`,
        # `W[4, o+8]` -> `W[4o8]`), mais le record etait confronte en texte BRUT. Un record ecrivant
        # honnetement `env.big_kills` ne pouvait donc JAMAIS satisfaire le cliquet : le seul moyen de
        # passer etait d'y coller le token MUTILE. On normalise les DEUX cotes, et on garde aussi le
        # texte brut (une grandeur peut etre nommee sans ponctuation).
        low = text.lower()
        low_norm = re.sub(r"[^A-Za-z0-9_\[\]]", "", text).lower()
        missing = sorted(q for q in qty if q.lower() not in low and q.lower() not in low_norm)
        if missing:
            problems.append((base, os.path.basename(recs[0]), missing))
    return problems


def main():
    problems = scan()
    insp, sans_qty, sans_rec, total = couverture()
    orphelines = nouvelles_sans_grandeur()
    # ⚠️ NE PAS SURDECLARER SA PROPRE COUVERTURE. Le message disait « {total} regles scellees, chacune
    # mesuree » alors que 8 sur 23 seulement etaient REELLEMENT inspectees : un cliquet qui annonce
    # 100 % quand il en fait 35 est un faux vert sur lui-meme.
    print(f"couverture : {insp}/{total} FAMILLES (base + chaine -bis) REELLEMENT inspectees "
          f"({sans_qty} sans grandeur nommee, {sans_rec} dont aucun record ne se reclame)")
    for base in familles_sans_record():
        print(f"    non rattachee : {base}  -- aucun record ne la declare (`record:`), ne cite "
              f"docs/preregistrations/{base}.json ni ne prefixe son nom ; transitoire si le run n'est "
              f"pas encore ecrit, sinon rattacher")
    if orphelines:
        print("ECHEC : regle(s) scellee(s) recente(s) dont AUCUNE grandeur n'est extractible :")
        for n in orphelines:
            print(f"  {n}  -> backticker les grandeurs dans les clauses de mesure, sinon la regle "
                  f"n'est pas verifiable")
        return 1
    if not problems:
        print(f"OK : aucune DV scellee absente de son record (sur les {insp} familles inspectables).")
        return 0
    for name, rec, missing in problems:
        print(f"[DV SCELLEE NON MESUREE] {name} -> {rec}")
        print(f"    grandeurs exigees par la regle et ABSENTES du record : {missing}")
    print("\nUne regle scellee nomme une grandeur que le record ne mentionne jamais : soit elle n'a pas ete")
    print("mesuree (classe E11 occ.4, cf. EDR-EVO-019), soit le record doit dire POURQUOI elle est omise.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
