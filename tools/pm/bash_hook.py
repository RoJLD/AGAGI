"""Hook PostToolUse `Bash` du PM (P2.118) : COMPTE les écritures POSSIBLES d'une commande Bash, n'en capture RIEN.

    python -m tools.pm.bash_hook      # appelé par .claude/settings.json (matcher "Bash"), JSON du hook sur stdin

Pourquoi. Le tableau PM ne voyait que les écritures des outils d'ÉDITION (hook `tool`, matcher Edit|Write|…) : un
script lancé par Bash qui réécrit un fichier n'y laissait AUCUNE trace — la forme d'écriture la plus dangereuse de ce
dépôt (l'anéantissement du backlog du 2026-09-09 était un script). A1 et les P-items inférés en dépendent.

Ce que ce hook NE fait PAS, délibérément (contrat de `.claude/skills/pm/SKILL.md`) : il n'enregistre ni le texte de la
commande, ni un diff de `git status` autour d'elle — sur l'arbre PARTAGÉ, un diff attribuerait à la session les
écritures d'AUTRUI, ce qui est pire que la cécité. Il INCRÉMENTE `bash_ecritures_possibles` dans le bulletin quand la
commande porte un MARQUEUR d'écriture (liste fermée ci-dessous) ; le tableau publie ce nombre à côté des fichiers en
vol, comme une incertitude chiffrée — jamais comme une liste de fichiers, jamais comme une certitude.

Coût (mesuré le 2026-09-26) : il tourne après CHAQUE commande Bash de chaque session. Le cas commun — aucun marqueur —
sort ici sans importer le bulletin ni toucher au disque, au prix d'un démarrage de Python ; seul un marqueur paie le
chemin complet (ancrage de la racine de données, lecture et écriture du bulletin).
"""
import json
import re
import sys

# Mots de commande qui écrivent par nature (en position de commande : début, après ; && || | ( $( ou un saut de ligne).
_ECRIVAINS = frozenset({"tee", "cp", "mv", "rm", "touch", "truncate", "dd", "ln", "mkdir", "install", "pytest",
                        "patch", "unzip", "tar"})
_GIT_ECRIT = frozenset({"apply", "checkout", "restore", "reset", "merge", "rebase", "cherry-pick", "am", "stash",
                        "pull", "switch", "worktree", "clean", "mv", "rm"})
_NPM_ECRIT = frozenset({"install", "i", "ci", "update", "run", "uninstall"})
_SEPARATEURS = re.compile(r"&&|\|\||[;|\n(]|\$\(")
_AFFECTATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
# Une redirection vers un FICHIER : « > » ou « >> » (fd optionnel), jamais un doublage de descripteur (« 2>&1 »,
# « >&2 ») ni /dev/null ; « -> » et « => » ne sont pas des redirections.
_REDIRECTION = re.compile(r"(?<![-=>&])(?:\d)?>>?(?!&)\s*(?!/dev/null\b)(?=[^\s&])")


def _mots(segment):
    mots = segment.strip().split()
    while mots and _AFFECTATION.match(mots[0]):          # PYTHONIOENCODING=utf-8 python …
        mots = mots[1:]
    return mots


def _nom(mot):
    """`/usr/bin/python3.13.exe` -> `python3.13` : le nom de la commande, sans chemin ni extension .exe."""
    base = mot.replace("\\", "/").rsplit("/", 1)[-1].strip("'\"")
    return base[:-4] if base.lower().endswith(".exe") else base


_ENVELOPPES = frozenset({"timeout", "nice", "nohup", "time", "command", "exec", "env", "xargs", "then", "do", "else",
                         "elif", "if", "while", "until", "!", "{"})
_ARG_ENVELOPPE = re.compile(r"^(-\S*|\d+(\.\d+)?[smhd]?|[A-Za-z_][A-Za-z0-9_]*=\S*)$")


def _segment_ecrit(mots):
    # « timeout 1500 python … », « then python … », « env X=1 python … » : l'enveloppe et ses arguments tombent,
    # la commande qu'elle lance est jugée
    while mots and _nom(mots[0]) in _ENVELOPPES:
        mots = mots[1:]
        while mots and _ARG_ENVELOPPE.match(mots[0]):
            mots = mots[1:]
    if not mots:
        return False
    nom = _nom(mots[0])
    reste = mots[1:]
    if nom in _ECRIVAINS:
        return True
    if re.fullmatch(r"python[0-9.]*|py", nom):
        return bool(reste) and reste[0] not in ("--version", "-V", "-VV")
    if nom in ("sh", "bash"):
        return bool(reste)                                # un script, ou -c : n'importe quoi
    if nom == "sed":
        return any(m == "--in-place" or m.startswith("--in-place=") or re.fullmatch(r"-[A-Za-z]*i\S*", m)
                   for m in reste)
    if nom == "perl":
        return any(re.fullmatch(r"-[A-Za-z]*i\S*", m) for m in reste)
    if nom == "git":
        i = 0
        while i < len(reste) and reste[i].startswith("-"):   # git -C <chemin> -c k=v --no-pager <sous-commande>
            i += 2 if reste[i] in ("-C", "-c") else 1
        return i < len(reste) and reste[i] in _GIT_ECRIT
    if nom == "npm":
        return bool(reste) and reste[0] in _NPM_ECRIT
    return False


# --- P2.136 (2026-09-26, promotion d'E21) : le CANAL SHELL transforme le texte qu'on lui confie --------------------
# Trois occurrences documentées, la règle du registre impose la garde (« pas de troisième fois ») : un fragment backtické
# d'un `git commit -m` parti VIDE, une pré-inscription scellée MUTILÉE par un `python -c` (2026-09-07), et un script
# écrit par heredoc dont les continuations de ligne sont arrivées en « \n » LITTÉRAUX — pytest n'a reçu aucun chemin
# et a lancé ZÉRO test (2026-09-26, agagi-32 : un vert qui ne mesurait rien). En PostToolUse la mutilation a déjà eu
# lieu : le hook ne bloque pas, il le DIT à l'agent et dit quoi faire. Signal, pas preuve : il marque les commandes
# dont le canal a PU transformer le texte.
_HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)^[ \t]*\2[ \t]*$", re.S | re.M)
_ECHAPPEMENT = re.compile(r"\\[nrt0\\'\"`$]")
# Entre guillemets doubles, bash résout lui-même \` \" \$ \\ (le caractère voulu arrive) ; il laisse en revanche \n \t \r
# \0 tels quels : git reçoit une barre oblique et une lettre, jamais le saut de ligne qu'on croyait écrire.
_ECHAPPEMENT_NON_RESOLU = re.compile(r"\\[nrt0]")
_GUILLEMETS_DOUBLES = re.compile(r'"((?:[^"\\]|\\.)*)"', re.S)
_BACKTICK_NU = re.compile(r"(?<!\\)`")
_MESSAGE = re.compile(r"(?:^|\s)(?:-m|--message)(?:\s+|=)\"((?:[^\"\\]|\\.)*)\"", re.S)


def mutilation_possible(commande):
    """P2.136 — les raisons pour lesquelles le canal shell a PU transformer le texte de `commande` ; [] si aucune.
    « heredoc » : le corps d'un heredoc porte une séquence d'échappement ou un backtick (mesuré : le canal les
    réinterprète même sous un délimiteur entre apostrophes) ; « substitution » : un backtick NON échappé dans une
    chaîne entre guillemets DOUBLES, que bash remplace par la sortie d'une commande ; « message » : un `-m`/`--message`
    entre guillemets doubles qui porte \\n, \\t, \\r ou \\0, que bash laisse tels quels. Fonction PURE."""
    if not isinstance(commande, str) or not commande:
        return []
    raisons = []
    if any(_ECHAPPEMENT.search(m.group(3)) or "`" in m.group(3) for m in _HEREDOC.finditer(commande)):
        raisons.append("heredoc")
    hors_heredoc = _HEREDOC.sub("", commande)
    if any(_BACKTICK_NU.search(s) for s in _GUILLEMETS_DOUBLES.findall(hors_heredoc)):
        raisons.append("substitution")
    if any(_ECHAPPEMENT_NON_RESOLU.search(s) for s in _MESSAGE.findall(hors_heredoc)):
        raisons.append("message")
    return raisons


def avertissement_mutilation(raisons):
    """Le texte injecté dans le contexte de l'agent : ce qui a pu se passer, et quoi faire."""
    return ("[E21] le canal shell a pu TRANSFORMER le texte de cette commande (" + ", ".join(raisons) + ") : "
            "vérifier le RÉSULTAT, pas la commande — relire le fichier ou le message produit, lire le COMPTE de tests "
            "exécutés (0 test n'est pas un vert). Pour un contenu qui porte des backslashs ou des backticks : écrire le "
            "script avec l'outil Write et l'exécuter par son chemin, jamais par heredoc, -c ou -m (CLAUDE.md, "
            "§Environnement ; P2.136).")


def ecriture_possible(commande):
    """Vrai si la commande PEUT écrire dans l'arbre : une redirection vers un fichier, ou un mot de commande de la
    liste fermée (tee, cp, mv, rm, sed -i, perl -i, git apply/checkout/…, npm install/run, python <script>, sh/bash
    <script>…). Fonction PURE. Une commande vide ou non textuelle rend False. Faux positifs assumés (une comparaison
    « a > b » dans une chaîne compte) : le nombre publié est celui des commandes QUI PEUVENT avoir écrit."""
    if not isinstance(commande, str) or not commande.strip():
        return False
    if _REDIRECTION.search(commande):
        return True
    return any(_segment_ecrit(_mots(s)) for s in _SEPARATEURS.split(commande))


def main(stdin=None):
    brut = (sys.stdin.read() if stdin is None else stdin) or "{}"
    try:
        payload = json.loads(brut)
        commande = (payload.get("tool_input") or {}).get("command")
    except (ValueError, AttributeError):
        payload = None
    raisons = mutilation_possible(commande) if payload is not None else []
    if raisons:
        # P2.136 : la SEULE forme documentée par laquelle un hook PostToolUse avertit l'agent sans bloquer — un JSON
        # hookSpecificOutput.additionalContext, seul sur stdout, code 0. ASCII échappé : une console cp1252 ne doit
        # jamais faire lever le hook sur un accent.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": avertissement_mutilation(raisons)}}))
        sys.stdout.flush()
    if payload is not None and not ecriture_possible(commande):
        return 0                                          # le cas commun : rien à compter, rien à écrire
    from tools.pm import bulletin                         # chemin complet : ancrage, bulletin, journal des erreurs
    return bulletin.main(["bash"], brut=brut)


if __name__ == "__main__":
    sys.exit(main())
