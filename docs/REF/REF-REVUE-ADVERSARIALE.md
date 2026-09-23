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
**re-passe les témoins** (`tools/refutateur_temoins.json`). `.claude/workflows/refutateur.js` les exécute,
un contexte par prompt, après avoir retrouvé le défaut connu de trois témoins gelés et être resté
silencieux sur un quatrième, sain.

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
exécution d'une porte) · un CONSTAT avec `fichier:ligne` ou sortie de commande · une CLASSE du registre
(`Ex`) ou « aucune » · un VERDICT parmi `confirmé` / `non confirmé` / `hors périmètre`. Sortie ≤ 40
lignes. **Une critique sans sonde lancée est rejetée à la consolidation** — c'est la différence entre
une revue et une relecture.

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

Les prompts P1-P10 passent d'abord sur quatre versions GELÉES de records, gelées dans le roster
`tools/refutateur_temoins.json` et extraites par `python tools/refutateur_temoins.py --extraire <dir>`.
Le roster gèle `GRAB-COST-v09-08`, `S2-BLIND-v1`, `RETAIN-COMPOSE-pre-retractation` et `LOCK-002-sain`.

⚠️ **La revue les lit en AVEUGLE, et ce document ne publie aucun attendu.** Les témoins sont extraits sous
des noms NEUTRES (`temoin-N.md`, délié de l'ordre du roster) ; ni leur nom, ni leur genre, ni ce qu'on
doit y trouver ne parviennent à l'agent qui relit. Publier « ce que la revue doit produire » à côté du
témoin ne mesurerait plus si les prompts DISCRIMINENT, mais si l'agent sait lire un tableau — et un
plancher de fausses critiques mesuré sous l'instruction « ce record est sain, tais-toi » n'est plus un
plancher. Les attendus vivent dans le roster, que l'agent de revue ne lit jamais ; le barème vit dans
`tools/refutateur_temoins.py` et nulle part ailleurs — deux implémentations d'un même barème divergent.

**Ce qui RETROUVE un témoin** : une critique **CONFIRMÉE**, dont le fond vit dans son CONSTAT ou sa
PREUVE. Jamais la sonde — recopier la commande qui nomme un paramètre n'est pas une découverte, et un
record dit souvent lui-même, dans sa section « ce qui n'est pas mesuré », le mot qu'on attendait de la
revue. Pour le témoin sain : **au plus UNE critique confirmée**, et ce chiffre se publie dans l'en-tête de
toute revue. Il vaut autant que les trois défauts — sans lui, un Réfutateur qui crie sur tout retrouverait
les trois et paraîtrait parfait, exactement comme un instrument de contraste sans no-op EXACT ne sait pas
ce qu'il ne peut pas voir.

**Un témoin manqué rend la revue NULLE** : rien ne s'écrit dans `docs/reviews/`, le compteur
`témoin manqué` s'incrémente dans `ROLES.md`. **Deux fois → les prompts sont re-scellés** (ils ne
discriminent plus), et le re-scellage passe par robla. Un texte de critiques ILLISIBLE n'est pas NULLE
mais **indécidable** (code 2) : un bug de sérialisation ne doit pas devenir un verdict de fond.

Les témoins sont figés au SHA qui porte le défaut **NU**, jamais sa rectification. Ce regard « à l'œil »
est lui-même exécutable : chaque témoin déclare une `signature` (présente dans le record à ce SHA) et une
`antisignature` (la marque de la correction, qui doit être ABSENTE), vérifiées par
`tests/sandbox/test_refutateur_temoins.py`. Déplacer un SHA pour faire passer une revue casse ce test.

## Sortie

`docs/reviews/<AAAA-MM-JJ>-<slug>.md`, selon `docs/reviews/README.md` (protocole d'invocation compris).
Tout NOUVEAU record à `gate:`/`tests:` doit porter `review:` vers ce fichier — `tools/check_record_links.py`
le vérifie ; toute NOUVELLE règle scellée déclarant un coût porte `reviewed_by`.
