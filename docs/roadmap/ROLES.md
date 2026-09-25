# ROLES — registre des rôles de la flotte AGAGI

**Writer unique : la session PM.** Une ligne par rôle ou lentille. Statuts : `instancié` · `candidat` · `dissous`.
Cinq colonnes obligatoires pour un rôle instancié (porte 21, `tools/check_roles_registry.py`) : une ligne creuse
est une règle documentée (E10), pas un rôle. Les compteurs VIVANTS (alertes émises / suivies 48 h / fausses,
ratio science/méthodo par chemins) sont recomputés par `python -m tools.pm.roles_counts` dans
`data/pm/ROLES_COUNTS.json` ; ce fichier ne porte en balise que les comptes structurels.
⚠️ Le point de départ 26 / 78 (2026-09-08) comptait des COMMITS ; le ratio publié ici compte des FICHIERS
modifiés sur 30 jours glissants — deux unités, non comparables.

**3 rôles instanciés** <!-- count:roles_instancies=3 --> · **7 candidats** <!-- count:roles_candidats=7 --> ·
dernier bilan : aucun (premier bilan à la première revue des rôles, 30 jours ou 20 records).
Règle 1:1 : tant que le ratio science/méthodo n'a pas franchi 1:1, aucun rôle neuf sans en réduire un autre.
Spec : `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md`.

| Rôle | Statut | Instrument | Contrôle positif | Coût mesuré | Compteurs | Dissolution / naissance |
| --- | --- | --- | --- | --- | --- | --- |
| **PM** | instancié | `tools/pm/board.py::compute`, déterministe, calibré par injection ; tick `/pm` | fixtures A1-A8 + no-op exact (`tests/sandbox/test_pm_board.py`) | tokens/tick : non mesuré au 2026-09-16, à publier au 1er bilan | `ROLES_COUNTS.json` : alertes émises / suivies 48 h / fausses ou ignorées / répétées | précision < 1/10 sur 30 j ; ou toute alerte encore émise attrapable par une porte ; ou tokens > 15 % de la fenêtre sans acte |
| **Stratège** | instancié | `.claude/workflows/strategist.js`, prompts figés, sur événement (plan 3) | candidat PÉRIMÉ connu glissé et tué à chaque passe ; sinon passe NULLE | tokens/passe : non mesuré, à publier au 1er bilan | propositions faites / acceptées par robla / amendées / réfutées par son panel (baseline : reco du 2026-09-08 tombée) | deux passes `full` sans changement de rang accepté ; ou témoin non tué deux fois (re-scellage des prompts) ; ou coût > 15 % |
| **Réfutateur** | instancié | `.claude/workflows/refutateur.js`, 8-10 prompts figés, portes 18/19/20 livrées d'abord (plan 2) | 4 témoins gelés, roster NON PUBLIÉ — `tools/refutateur_temoins.json` (les nommer ici, avec leur genre, redonnait la clé que l'anonymat de l'extraction retire) | tokens/revue : non mesuré, à publier au 1er bilan | critiques émises / confirmées / fausses ; taux de -bis après run (baseline 3/58) | < 1 confirmée sur 10 revues ; ou ≥ 80 % attrapables par une porte ; ou -bis après run ≥ 3/58 après 20 sceaux ; ou coût > 15 % |
| **Régisseur des runs** | candidat | — | — | — | — | réfuté le 2026-09-16 (compte gonflé par un apparieur faillible ; occurrences déjà closes ou déjà cliquets) ; naît sur deux runs abandonnés ou contaminés en 30 j malgré `cost_guard` et le bail |
| **Intégrateur** | candidat | — | — | — | — | condition de naissance ATTEINTE le 2026-09-24 (elle remplace le refus du 2026-09-16, dont la prémisse d1/main était périmée) ; **rôle NON créé**, réfuté par le mécanisme même de son échec — quatre collisions datées, remède à deux étages et critère de réfutation en **note 1** sous le tableau |
| **Greffier-métrologue** | candidat | — | — | — | — | réfuté le 2026-09-16 (la promotion documenté→exécutable A été appliquée, P2.25) ; naît sur deux classes restées `documenté` après deux récidives |
| **Bibliothécaire de la doctrine** | candidat | — | — | — | — | réfuté le 2026-09-16 (rare, bon marché après coup) ; naît sur deux sessions trompées par la même phrase périmée, datées |
| **Auditeur des angles morts** | candidat | — | — | — | — | → cliquet « hors motif » + lentille du stratège sur tout élargissement de détecteur (backlog) ; ne naît pas comme rôle |
| **Archiviste de l'évidence** | candidat | — | — | — | — | constat vrai (78 chemins, 18 absents, 0 non suivi -- le « 20 non suivis » de la note initiale etait un double comptage, corrige le 2026-09-23) devenu la porte 19 (plan 2) ; ne naît pas comme rôle |
| **Greffier de passage** | candidat | — | — | — | — | réfuté le 2026-09-16 (une seule occurrence) ; naît sur deux occurrences datées de travail dupliqué faute de brief |
| **Scribe des records** | dissous | témoin du panel — fonction couverte par la porte 1 | doit être TUÉ à chaque revue des rôles, sinon la passe est nulle | — | — | témoin permanent : ne renaît jamais |

## Notes

Une cellule du tableau porte un VERDICT et sa date ; quand la mesure qui le fonde ne tient pas sur une
ligne sans devenir illisible en diff, elle descend ici. La cellule renvoie, elle ne tronque pas.

**Note 1 — Intégrateur : condition de naissance ATTEINTE le 2026-09-24, rôle NON créé.**

Quatre collisions de numéro de backlog, toutes du 2026-09-24, mesurées sur les branches :

1. un bloc `P2.78-P2.84` écrasant sept numéros déjà pris sur la branche cible, invisibles depuis une
   base plus ancienne ;
2. un `P2.101` contre un autre `P2.101`, deux branches, contenus entièrement différents ;
3. un `P2.102` alloué **de mémoire** par le PM, déjà committé sur une autre branche ;
4. un `P2.107` annoncé par une session et non committé, donc invisible à tout outil.

**Le rôle n'est pas créé, et il est réfuté par le mécanisme même de son échec.** La troisième collision
s'est formée dans le message de coordination où le PM expliquait qu'un crochet mécanique rendrait ces
collisions impossibles : un coordinateur humain — exactement ce que ce rôle instancierait — a échoué
DANS L'ACTE de démontrer qu'il était nécessaire. Un refus sec n'apprendrait rien ; un candidat qui se
réfute en se démontrant est un résultat, et c'est sous cette forme qu'il est gravé. Il s'ajoute à la
règle qui fonde ce registre, et ne la remplace pas : ce qui est décidable devient un cliquet, pas un
rôle — sept candidats y sont déjà morts.

**Remède, à deux étages.** (a) Un allocateur qui lit le backlog depuis CHAQUE ref (`git for-each-ref`)
et rend `max+1` : il aurait tué les trois premières, qui naissent toutes de ce qu'on alloue depuis ce
qu'on VOIT alors qu'on ne voit que sa propre branche. (b) Le crochet de fusion en chantier chez
`agagi-d7` (P2.102 : un `commit-msg` qui relance les portes quand `MERGE_HEAD` existe, plus la garde de
copie `tools/hooks` vers `.git/hooks` sans laquelle il serait inerte), qui rattrape ce qui passe quand
même. La clé `numero-double` de `check_backlog_freshness` attrape déjà exactement ces collisions, mais
ne s'exécute pas sur une fusion : créer un rôle reviendrait à confier à quelqu'un le travail d'une garde
qu'on n'a pas branchée.

**La quatrième résiste aux deux étages**, et c'est elle qui donne la règle : **un numéro ne se réserve
pas, il s'alloue à l'écriture.** Une réservation est invisible par construction — qu'elle vive dans un
message, dans un journal de session non suivi par git, ou dans la mémoire de quelqu'un. Les trois formes
ont coûté une collision chacune le même jour.

**Ce qui le ferait renaître** (critère publié avec le refus, sans quoi ce registre ne serait pas un
instrument) : l'allocateur ET le crochet livrés, et des collisions qui continuent — la cause ne serait
alors pas structurelle, et le candidat reviendrait.

**Note 2 — Clôture du 2026-09-25, sur ordre de robla (« Go et terminons, clôturons tout cela »).**

Deux des six points remis à robla par la passation du PM n'étaient pas des actes mais des décisions ;
elles sont gravées ici pour qu'aucune session suivante ne rouvre l'enquête.

1. **Écriture dans `.git/config` le 2026-09-24 à 13:42:31** (`core.bare` true → false) : au moins trois
   sessions s'étaient vu REFUSER ce droit par le classificateur ; quelqu'un a écrit ; personne ne sait qui.
   L'hypothèse « identité posée par aa » est RÉFUTÉE (identité déjà correcte à 13:32, trois commits
   `commit-tree` sans `-c`). **Close, NON ATTRIBUÉE.** La garde est structurelle — `tests/conftest.py`
   (fixture autouse) et `tools/_git_env.py` (isolation de la famille `GIT_*`) — et le registre porte la
   classe ; une enquête de plus n'ajouterait ni garde ni fait.
2. **Le tick du PM** : la conception prévoit UNE session dédiée en `/loop` ; aucune ne le tient. Depuis le
   2026-09-24 le tableau se déclare PÉRIMÉ au-delà du TTL du bail au lieu de se présenter comme courant
   (défaut 1). L'allocation est proposée dans le prompt de reprise remis à robla ; d'ici là,
   `python -m tools.pm.board` à la main, et aucune alerte du tableau ne vaut mesure.
