# Revues NULLES du Réfutateur — registre du compteur « témoin manqué »

Une ligne par run NUL du workflow `.claude/workflows/refutateur.js`, quelle qu'en soit la raison, avec sa **classe** :

- `témoin manqué` : un témoin à DÉFAUT connu n'a pas été retrouvé (statut NULLE) — c'est CE compte que la REF
  (`docs/REF/REF-REVUE-ADVERSARIALE.md`) fait monter : **au deuxième, les prompts sont re-scellés, par robla** ;
- `indécidable` : un témoin à défaut rendu INDÉCIDABLE (texte de critiques illisible) — la REF le distingue d'un
  témoin manqué, il ne compte pas ;
- `transport` : rien de jugeable n'a été relayé (relectures, aiguillage, témoins absents) — une absence de mesure ;
- `instrument` : un défaut de l'instrument lui-même, corrigé depuis — il ne compte pas.

Aucun témoin n'est NOMMÉ ici : le roster n'est pas publié (le nommer redonnerait la clé que l'anonymat de l'extraction
retire). Le détail d'un run se relit dans son fichier persisté (`<session>/workflows/<run>.json`).

**Témoins manqués : au moins 1** <!-- count:refutateur_temoins_manques=1 --> — compte recomputé par la porte 8 depuis
la colonne « Classe » ci-dessous. Couverture du compte initial (2026-10-14, agagi-32) : les runs PERSISTÉS des sept
dossiers de projet AGAGI, du 2026-09-24 au 2026-10-14 — 24 revues du Réfutateur (17 retrouvées, 7 nulles) ; un run
antérieur, ou dont la session a été nettoyée, est INCONNU, d'où « au moins ». La v1 de la règle d'E34, NULLE par
transport selon la session E34 (texte « (vide) », P2.133), n'apparaît pas comme NULLE dans les runs persistés : non
listée, faute de trace.

| Date (UTC) | Run | Cible | Classe | Constat |
| --- | --- | --- | --- | --- |
| 2026-09-24 08:15 | wf_8bf966fa-c7c | un fichier témoin (mise au point de l'instrument) | transport | relectures absentes : aucune relecture des témoins dans la tâche transmise |
| 2026-09-24 08:39 | wf_971a64a3-efa | un fichier témoin (mise au point de l'instrument) | transport | aiguillage incohérent (0 sur 4) |
| 2026-09-24 09:55 | wf_97132459-252 | un fichier témoin (mise au point de l'instrument) | transport | aiguillage-TRANSPORT : 0 fichier relayé |
| 2026-09-24 10:27 | wf_6ca9aa36-134 | un fichier témoin (mise au point de l'instrument) | instrument | le témoin CRU SAIN faisait barrière (« non retrouvé ») ; corrigé le même jour : il MESURE, il ne fait pas barrage (`tools/refutateur_temoins.py`) |
| 2026-09-26 12:38 | wf_847d2633-b0c | — | transport | témoins absents (aucun fichier de témoin fourni) |
| 2026-09-26 14:36 | wf_b7cd5fdc-d98 | S2-BASSIN-FRAGILITY v6 | indécidable | un témoin à défaut INDÉCIDABLE, rangé par le workflow parmi les « défauts non retrouvés » (`.claude/workflows/refutateur.js:253-254`) : la revue est sortie NUL au lieu d'indécidable — classé selon la REF (Master 2, 2026-10-14) |
| 2026-10-14 12:47 | wf_7fe5a019-982 | E34-IDENTITY-CELL (revue réduite) | témoin manqué | un témoin à défaut NON retrouvé (statut NULLE) ; dossier du run : `AGAGI_sauvegardes/e34_passation_2026-10-14/revue_nulle_wf_7fe5a019-982` (hors dépôt) |
