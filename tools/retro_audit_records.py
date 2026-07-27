"""RÉTRO-AUDIT des records — applique les générateurs d'erreur du pré-vol aux conclusions DÉJÀ GRAVÉES.

Classe **E14** du registre des erreurs, ouverte le 2026-07-21 : *un cliquet ne regarde jamais en arrière.*
`assert_not_degenerate` était `exécutable` quand EDR-WARM-002 a été gravé, relu et cité par 4 records — et
n'a rien attrapé, parce qu'aucun dispositif ne repasse les CHIFFRES DÉJÀ PUBLIÉS. Le cliquet bloque le
prochain instrument non calibré ; il ne relit pas les verdicts. Conséquence mesurée : un verdict sur la
STRUCTURE DU MONDE (« paysage de fitness PLAT ») a tenu et s'est propagé, alors que le contrôle positif
qui l'a réfuté coûtait **6 secondes** et était disponible depuis des semaines (EDR-WARM-010).

CE QUE CET OUTIL EST : un **TRIAGE**, pas un verdict. Il ratisse large exprès et signale des CANDIDATS à
examiner à la main. Il ne lit pas les chiffres — il lit la STRUCTURE ARGUMENTATIVE.

CE QUE LE CODE NE SAIT PAS FAIRE — mesuré, pas supposé. Le signal que je VOULAIS automatiser était :
« verdict nul publié SANS contrôle positif », soit le générateur A du pré-vol. Calibré sur la seule
réponse connue (WARM-002 avant sa correction, qui DOIT sortir au risque maximal), il a **échoué deux
fois** :
  1. en cherchant « oracle » dans tout le fichier — le mot est dans la section `## Question`, où le
     record CITE S2-009 en cadrage ; faux vert sur l'archétype. Même faute de portée que le bug
     substring du cliquet de calibration, commise le même jour dans l'outil censé la rattraper ;
  2. en restreignant aux sections de dispositif — le mot revient dans les Résultats sous la forme
     « oracle intact ≈ 200 (S2-009) », qui est une **valeur de référence citée**, pas un contrôle
     exécuté. Textuellement indiscernables.

Conclusion assumée : **distinguer « a lancé un contrôle positif » de « cite un contrôle positif fait
ailleurs » demande de comprendre la phrase, pas de la matcher.** Le rétro-audit n'est donc PAS
automatisable de bout en bout — même partage que la classe E9. Le code ÉNUMÈRE et PRIORISE ; le jugement
tranche. Poursuivre le raffinage des motifs reviendrait à les ajuster sur l'unique exemple disponible,
ce qui est la classe E11.

SIGNAL EFFECTIVEMENT RETENU (robuste, sans détection de contrôle) :

    verdict NEUTRE/NUL  ×  conclusion portant sur LE MONDE  ×  plancher avoué

C'est la signature exacte de WARM-002, et elle ne dépend d'aucune lecture fine.

⚠️ DISTINCTION QUI DÉCIDE DE TOUT — un négatif au plancher n'est PAS toujours une faute :
  * WARM-002 lisait un **ratio d'ablation** sur un bras au sol et concluait sur **le MONDE** → INVALIDE :
    le ratio vaut 1.0 par construction, il ne mesure rien.
  * S2-010 (« le crédit ne bootstrappe pas ») conclut sur **l'APPRENANT**, et rester au plancher EST le
    résultat observé → VALIDE.
La différence est l'OBJET de la conclusion, pas la valeur mesurée. Le triage la marque via `portee`, et
c'est le point qui exige un œil humain : sans lui, l'outil crie au loup sur la moitié du corpus.

Usage :
  python tools/retro_audit_records.py                 # candidats parmi les records `status: active`
  python tools/retro_audit_records.py --all           # tout le corpus
  python tools/retro_audit_records.py --verbose       # + le motif déclencheur de chaque signalement
"""
from __future__ import annotations

import argparse
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EDR = os.path.join(_ROOT, "docs", "EDR")

# Verdict sans effet — ce qui rend un contrôle positif OBLIGATOIRE pour être interprétable.
_NULL_VERDICT = re.compile(
    r"NEUTRAL|NEUTRE|_NO_?OP\b|NO_?OP\b|\bINERTE?\b|\bNUL(?:LE|S)?\b|ratio\s*[≈~=]?\s*1\.0"
    r"|aucun effet|sans effet|n'améliore pas|ne change (?:rien|pas)|INCONCLUSIVE|INDETERMINATE",
    re.I)

# Trace d'un contrôle positif : un bras dont on SAIT qu'il doit réussir.
_POSITIVE_CONTROL = re.compile(
    r"contr[ôo]le\s+positif|positive\s+control|t[ée]moin\s+positif|oracle|borne\s+haute"
    r"|plafond\s+atteignable|contr[ôo]le\s+de\s+capacit[ée]|assert_positive_control",
    re.I)

# Aveu de plancher/plafond : le record dit lui-même que ses bras sont collés au bord.
_FLOOR = re.compile(r"plancher|au\s+sol|floor|plafond|ceiling|satur[ée]|d[ée]g[ée]n[ée]r", re.I)

# Objet de la conclusion : sur le MONDE (invalide au plancher) vs sur l'APPRENANT (légitime).
_ABOUT_WORLD = re.compile(
    r"paysage de fitness|le monde (?:n'|ne )|structure de (?:la )?t[âa]che|gradient (?:de fitness|cognitif)"
    r"|l'?[ée]cologie|la t[âa]che n'exige|monde PLAT|fitness PLAT", re.I)


def _frontmatter(src):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", src, re.S)
    return m.group(1) if m else ""


def _section(src, *names):
    """Extrait une section `## <nom>` (jusqu'au prochain `##`)."""
    for n in names:
        m = re.search(rf"^##\s*{n}.*?\n(.*?)(?=^##\s|\Z)", src, re.M | re.S | re.I)
        if m:
            return m.group(1)
    return ""


def classify_record(path):
    """Renvoie un dict de triage pour UN record, ou None s'il est illisible."""
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    fm = _frontmatter(src)
    ident = (re.search(r"^id:\s*(\S+)", fm, re.M) or [None, os.path.basename(path)])[1]
    status = (re.search(r"^status:\s*(\S+)", fm, re.M) or [None, "?"])[1]
    verdict = _section(src, "Verdict") or src
    body = _section(src, "R[ée]sultats?", "Verdict") or src

    dispositif = _section(src, "M[ée]thode", "Protocole") + _section(src, "R[ée]sultats?") + verdict
    null = bool(_NULL_VERDICT.search(verdict))
    floor = bool(_FLOOR.search(body))
    world = bool(_ABOUT_WORLD.search(verdict))
    # ⚠️ INDICATION SEULEMENT, JAMAIS UN SCORE — voir la note « ce que le code ne sait pas faire ».
    mentionne_ctl = bool(_POSITIVE_CONTROL.search(dispositif or src))

    # SCORE = verdict nul × portée de la conclusion × aveu de plancher. La détection du contrôle
    # positif est VOLONTAIREMENT exclue du score : mesurée non fiable (elle rendait `risque=1` sur
    # l'archétype WARM-002, deux fois de suite). Mieux vaut un triage franc et large qu'un tri fin
    # et faux — un faux vert ici reproduirait exactement l'erreur qu'on chasse.
    if not null:
        risque, motif = 0, "verdict non nul"
    elif world and floor:
        risque, motif = 4, "verdict NUL + conclut sur le MONDE + plancher avoué (signature WARM-002)"
    elif world:
        risque, motif = 3, "verdict NUL + conclut sur le MONDE"
    elif floor:
        risque, motif = 2, "verdict NUL + plancher avoué"
    else:
        risque, motif = 2, "verdict NUL"

    return {"id": ident, "status": status, "file": os.path.basename(path),
            "risque": risque, "motif": motif, "mentionne_ctl": mentionne_ctl,
            "portee": "MONDE" if world else "apprenant/instrument"}


def audit_records(actifs_seulement=True):
    rows = []
    for fn in sorted(os.listdir(_EDR)):
        if not fn.endswith(".md"):
            continue
        r = classify_record(os.path.join(_EDR, fn))
        if r is None or (actifs_seulement and r["status"] != "active"):
            continue
        rows.append(r)
    return sorted(rows, key=lambda r: (-r["risque"], r["id"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="Tout le corpus, pas seulement `status: active`.")
    ap.add_argument("--verbose", action="store_true", help="Affiche le motif de chaque signalement.")
    args = ap.parse_args(argv)

    rows = audit_records(actifs_seulement=not args.all)
    flag = [r for r in rows if r["risque"] >= 2]
    print(f"records examinés : {len(rows)} | à EXAMINER (risque >= 2) : {len(flag)}")
    print("\nRAPPEL : triage heuristique, PAS un verdict. Un négatif au plancher est légitime quand la")
    print("conclusion porte sur l'APPRENANT ; il ne l'est pas quand elle porte sur le MONDE.\n")
    for r in rows:
        if r["risque"] < 2 and not args.verbose:
            continue
        mark = "!!!" if r["risque"] >= 4 else ("!! " if r["risque"] == 3 else "!  ")
        ctl = "ctl?" if r["mentionne_ctl"] else "    "
        print(f"  {mark} [{r['risque']}] {ctl} {r['id']:<14} portée={r['portee']:<20} {r['file']}")
        if args.verbose:
            print(f"        motif : {r['motif']}")
    print("\n`ctl?` = le record mentionne un vocabulaire de contrôle positif — INDICATION seulement,")
    print("non fiable (elle rendait un faux vert sur l'archétype). À vérifier à la main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
