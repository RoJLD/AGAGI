---
id: REF-REVUE-ADVERSARIALE
type: REF
title: "Revue adversariale à sondes propres — les 10 prompts figés du Réfutateur, et ce qui est délégué aux portes"
status: active
---

## Règle

Rappel de `CLAUDE.md` : toute conclusion destinée au graphe de records passe par une revue qui **LANCE ses
propres sondes** — pas une relecture. Le bilan mesuré de l'arc WARM (7 revues, 7 erreurs réelles) dit que
la prudence rédactionnelle n'en aurait attrapé aucune : ce qui trouve, c'est la commande qu'on relance.

Ce document **FIGE** les prompts. Toute modification est un commit path-scopé décidé par robla, et
**re-passe les témoins**. `.claude/workflows/refutateur.js` les exécute, un contexte par prompt, après
une phase témoins que ce document ne décrit qu'en RÈGLES : ni combien de témoins il y a, ni de quels
genres, ni dans quel ordre, ni ce qu'on doit y trouver.

## Ce que le Réfutateur ne fait PLUS : le partage avec les portes

Trois portes du hook pre-commit répondent désormais, **mécaniquement et sans jugement**, à des questions
qui coûtaient une enquête à la main. Un prompt qui referait leur travail serait un doublon coûteux —
et, pire, un doublon dont la réponse peut diverger de celle du cliquet.

| porte | question qu'elle tranche | ce qu'elle NE tranche pas |
| --- | --- | --- |
| `tools/check_regime_claims.py` | un paramètre CITÉ dans la prose est-il PUBLIÉ par le `results/` (bloc `regime` ou ailleurs) ? | si le paramètre agit sur le chemin qu'on croit couper (→ P10) |
| `tools/check_evidence_provenance.py` | le `results/` cité existe-t-il, est-il suivi par git ? | si le JSON mesure la DV annoncée (→ P1) |
| `tools/check_e19_optimizer_sweep.py` | un runner scellé sous gradient appelle-t-il la garde E19 ? | si la référence à pas nul est du MÊME dispositif (→ P3) |

**Règle de partage** : un prompt marqué **DÉLÈGUE** est *une ligne* — lancer la porte, recopier son
verdict, s'arrêter. Il ne rouvre pas l'enquête que la porte a fermée ; s'il croit la porte fausse, il
ouvre une dette, pas une critique. Un prompt marqué **JUGE** est irréductible à un `grep` : il demande de
lire, de compter, ou de rejouer. `check_control_family.py` et `check_io_overlap.py` y servent de **sonde
d'entrée**, jamais de verdict — elles disent qu'une déclaration EXISTE, pas qu'elle est VRAIE.

⚠️ **Aucun chiffre de porte n'est recopié ici** (nombre de records, de discordes, de scellés). Ils se
périment en un commit. Lancer la porte, lire SA sortie.

## Contrat de chaque critique

Une SONDE obligatoire et **lancée** (`grep`, `python -c`, `git show`, lecture d'un `results/*.json`,
exécution d'une porte) · un CONSTAT · une PREUVE · une CLASSE du registre (`Ex`) ou « aucune » · un
VERDICT parmi `confirmé` / `non confirmé` / `hors périmètre`. Sortie ≤ 40 lignes.

**Trois conditions MÉCANIQUES, vérifiées sans agent** (`tools/refutateur_temoins.py::recevabilite`) ;
une critique qui en manque une est écartée avant toute lecture de fond :

1. le verdict commence par `confirmé` — un doute explicité n'est pas une trouvaille ;
2. la PREUVE a une forme vérifiable : un `fichier:ligne`, **ou** une commande (dans la sonde)
   accompagnée d'une sortie chiffrée, **ou** une valeur opposée à une autre. « aucune » n'en est pas
   une, et une phrase qui récite des noms de paramètres sans rien ouvrir non plus ;
3. le CONSTAT n'est pas une **RECOPIE** : aucune fenêtre de huit mots consécutifs du constat ne doit
   se retrouver mot pour mot dans le fichier relu. Recopier une ligne d'un record n'est pas le
   critiquer — et le mot qu'on attendait de la revue est souvent déjà dans son texte.

⚠️ Le fond — « cette critique nomme-t-elle CE défaut ? » — n'est **pas** décidable par un motif. Il est
jugé, à part, par un agent à prompt figé calibré sur des textes à réponse connue. Écrire le mot juste
n'a jamais été une découverte, et une découverte formulée autrement n'est pas une erreur.

⚠️ Le Réfutateur **ne construit aucun monde et ne prend aucun bail** (`kuzu`). Une revue est une lecture :
si une sonde exigeait une simulation, elle devient une dette au backlog, pas une critique.

## Les dix prompts

| # | rôle | prompt | sonde imposée |
| --- | --- | --- | --- |
| P1 | **JUGE** | **Prémisse porteuse.** Quelle affirmation, si elle était fausse, RENVERSE le verdict ? Est-elle mesurée dans CE run, ou héritée d'un autre dispositif, ou recopiée de mémoire ? | charger le `results/` cité (`python -c` qui imprime les clés) et montrer OÙ la prémisse y est mesurée — ou constater qu'elle n'y est pas |
| P2 | **DÉLÈGUE** | **Régime.** Chaque paramètre cité est-il publié par l'évidence ? | `python tools/check_regime_claims.py --only <record>` ; recopier le verdict, ne pas refaire le balayage |
| P3 | **DÉLÈGUE** | **Balayage du pas.** Tout nul comparatif sous gradient : la garde E19 est-elle appelée par le runner scellé ? | `python tools/check_e19_optimizer_sweep.py --only <runner>` ; recopier le verdict. *Le reste d'E19 — « la référence à pas nul sort-elle du MÊME dispositif ? » — est jugé en P5, pas ici.* |
| P4 | **JUGE** | **Famille de contrôles — taille RÉELLE.** Compter les cellules du dispositif dans le runner, et les confronter au nombre DÉCLARÉ. Le seuil est-il hérité d'un autre dispositif ? | `python tools/check_control_family.py --report` comme point de départ, puis COMPTER les cellules à la lecture du runner et de la pré-inscription |
| P5 | **JUGE** | **Les deux issues.** Le contrôle pouvait-il échouer ? Le bras testé pouvait-il réussir ? Le contrôle positif — et la référence à pas nul de P3 — sont-ils du MÊME dispositif, au MÊME régime ? Un bras est-il structurellement plus dur à optimiser que l'autre ? | `grep -n` de `assert_positive_control` / `assert_not_degenerate` / `assert_ablation_changes_something` dans le runner, PUIS les valeurs du contrôle dans le JSON : une garde appelée sur un régime facile ne calibre pas le régime dur (E19) |
| P6 | **JUGE** | **Plancher de bruit.** Tout ratio a-t-il son no-op EXACT publié à côté ? Le contraste sort-il de la bande ? Le no-op est-il celui de CE contraste ? | `grep -niE "no.?op"` dans le record et dans le JSON ; comparer le ratio publié à la bande du no-op et le DIRE, même quand il est dedans |
| P7 | **JUGE** | **Dose.** Pour tout apprenant : le nombre de mises à jour REÇUES est-il publié ? La cohorte est-elle constante (`n_agents` par bloc, `resurrections`) ? Un nul est-il un nul d'apprentissage ou un nul de létalité ? | lire le bloc d'apprentissage du JSON ; à défaut, `tools/learning_events.py::count_learning_events` est le compteur de référence |
| P8 | **JUGE** | **Corps et aliasing.** L'intervention touche-t-elle des lignes de `W` dont le monde dérive le CORPS (E26), un chevauchement entrée/sortie (E24), une VUE de l'état récurrent ? | `python tools/check_io_overlap.py` ; `grep -n "W\[" <runner>` et lire ce que les lignes touchées alimentent dans `src/agents/mamba_agent.py` |
| P9 | **DÉLÈGUE** | **Provenance.** Le `results/` cité existe-t-il et est-il suivi ? Le sceau de la pré-inscription est-il intact ? | `python tools/check_evidence_provenance.py --only <record>` ; `python -c "from tools.preregister import verify; verify('<REGLE>')"` |
| P10 | **JUGE** | **Mécanisme.** Toute affirmation sur le CODE — « TD à chaque tick », « la curiosité est active », « `W` est figé à pas nul », « ce canal est inerte » — se vérifie EN LISANT LA LIGNE. Le référent d'un paramètre publié en fait partie. | `grep -n` du symbole, puis `Read` de la ligne citée et de ce qu'elle alimente. E26 et E29 sont nées ici, à la lecture, pas au raisonnement |

**DÉLÈGUENT** : P2, P3, P9 — leur réponse est rendue par une porte, ils la recopient.
**JUGENT** : P1, P4, P5, P6, P7, P8, P10 — aucune porte ne sait quelle prémisse PORTE un verdict,
combien de cellules un dispositif a RÉELLEMENT, ni si un mécanisme affirmé existe dans le code.

## Phase témoins — avant toute revue réelle

Les prompts P1-P10 passent d'abord sur des versions GELÉES de records, tenues par le roster
`tools/refutateur_temoins.json` et extraites par `python tools/refutateur_temoins.py --extraire <dir>`.

⚠️ **La revue les lit en AVEUGLE, et ce document ne publie NI leur identité, NI leur nombre, NI leurs
genres, NI ce qu'on doit y trouver.** Les fichiers portent des noms neutres (`temoin-N.md`), déliés de
l'ordre du roster. Publier « ce que la revue doit produire » à côté du témoin ne mesurerait plus si les
prompts DISCRIMINENT, mais si l'agent sait lire un tableau ; et un plancher de fausses critiques mesuré
sous l'instruction « ce record est sain, tais-toi » n'est plus un plancher. Même un ORDINAL suffit à
tout rendre : une énumération dont le dernier est le témoin sain redonne la clé qu'on vient de retirer.
Le roster, que l'agent de revue ne lit jamais, porte les identités, les genres, les seuils et les
attendus ; le barème vit dans `tools/refutateur_temoins.py` et nulle part ailleurs.

⚠️ **Et ce document ne peut pas garantir seul ce qu'il annonce.** Le fichier extrait porte son propre
`id:` en ligne 2 : l'anonymat couvre la paire (fichier → témoin), jamais le record. **Tout document
suivi qui nomme un témoin avec son genre reconstitue la clé par simple jointure** — mesuré le
2026-09-24 sur `docs/roadmap/ROLES.md`, qui publiait le nom du no-op pendant que cette page affirmait
ne rien publier : vrai de la page, faux du dépôt. Le roster est la **seule** place d'un nom de témoin.

**Ce qui RETROUVE un témoin** — deux étages, et le second n'est pas un motif :

1. **Plancher MÉCANIQUE** : au moins une critique RECEVABLE au sens des trois conditions ci-dessus
   (confirmée, preuve de forme, pas une recopie). Pur, sans agent, rejouable par n'importe qui.
2. **JUGE** : un agent à prompt figé, qui reçoit le défaut DÉCLARÉ du témoin et les critiques
   recevables — **jamais un motif à chercher** — et répond `OUI` / `NON` / `INDECIDABLE`. Il est
   calibré sur des textes gelés à réponse connue ; s'il rate ses propres témoins, l'instrument rend
   INDÉCIDABLE plutôt que de juger.

⚠️ **Tout score de phase témoins se publie à côté de son PLANCHER DE FAUSSES RETROUVAILLES**, mesuré le
jour même par `python tools/refutateur_temoins.py --plancher <dir>` : combien de témoins une revue SANS
CONTENU peut encore faire retrouver. Un score sans son plancher est interdit — c'est la règle du dépôt
sur tout ratio, et elle est née ici : le 2026-09-23, une phrase vague identique pour tous les témoins,
écrite sans ouvrir un fichier, les passait TOUS. Le plancher valait le signal maximal ; l'instrument ne
voyait rien.

**Un témoin à DÉFAUT manqué rend la revue NULLE** : rien ne s'écrit dans `docs/reviews/`, le compteur
`témoin manqué` s'incrémente dans `ROLES.md`. **Deux fois → les prompts sont re-scellés** (ils ne
discriminent plus), et le re-scellage passe par robla. Un texte de critiques ILLISIBLE n'est pas NULLE
mais **indécidable** (code 2) : un bug de sérialisation ne doit pas devenir un verdict de fond.

⚠️ **Le témoin CRU SAIN, lui, MESURE — il ne fait pas barrage.** Il rend un NOMBRE, le compte de
critiques recevables sur un record dont aucun défaut n'est connu, et ce nombre voyage avec le score
dans la même structure. Le faire barrer revenait à **jeter une revue qui venait de retrouver trois
défauts réels parce que le plancher était haut** : supprimer la mesure au lieu de la publier, l'inverse
exact de la doctrine. Mesuré le 2026-09-24, premier passage complet : six critiques recevables sur ce
témoin, dont une confrontée aux données et **juste**. « Aucun défaut connu » n'est pas « sain », et
personne ne sait établir la seconde propriété : la revue nomme donc le témoin employé et publie son
compte. **Si ce compte est ≥ à celui des témoins à défaut retrouvés, la revue le DIT** — l'instrument
ne distingue alors pas un record sain d'un record défectueux, et c'est un verdict, pas un détail.

⚠️ **Un témoin gelé a une durée de vie.** Il mesure ce qu'on savait **au gel** ; ce qui était propre le
devient moins à mesure que le dépôt apprend. Mesuré le 2026-09-24 : le témoin cru sain porte un
phénomène — « le bras ablaté fait mieux que l'intact » — qui est la forme exacte d'un résultat établi
**depuis**. Le témoin n'avait donc pas été mal choisi. Le roster porte la **date de chaque gel** et se
confronte périodiquement à ce que le dépôt a appris ; l'ÂGE est calculé et rapporté par le CLI, la
péremption **scientifique** n'est pas décidable par motif et se déclare. Rien ne bloque sur un
calendrier : refuser un roster pour une raison qui n'est pas un fait sur ses témoins casserait un
instrument qui marche. À la revue du roster, on corrige le TEXTE d'un `defaut`, pas son SHA.

Les témoins sont figés au SHA qui porte le défaut **NU**, jamais sa rectification. Ce regard « à l'œil »
est lui-même exécutable : chaque témoin déclare une `signature` (présente dans le record à ce SHA) et une
`antisignature` (la marque de la correction, qui doit être ABSENTE), vérifiées par
`tests/sandbox/test_refutateur_temoins.py`. Déplacer un SHA pour faire passer une revue casse ce test.

## Sortie

`docs/reviews/<AAAA-MM-JJ>-<slug>.md`, selon `docs/reviews/README.md` (protocole d'invocation compris).
Tout NOUVEAU record à `gate:`/`tests:` doit porter `review:` vers ce fichier — `tools/check_record_links.py`
le vérifie ; toute NOUVELLE règle scellée déclarant un coût porte `reviewed_by`.
