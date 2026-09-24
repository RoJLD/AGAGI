# Revues adversariales à sondes propres

Un fichier par revue : `docs/reviews/<AAAA-MM-JJ>-<slug-du-record>.md`, référencé par le frontmatter `review:` du record
(exigé de tout NOUVEAU record à `gate:`/`tests:` par `tools/check_record_links.py`). Writer : la session qui a lancé la
revue. Forme : en-tête (cible, SHA, date, résultat des TÉMOINS), puis une section par prompt `P1`…`P10` de
`docs/REF/REF-REVUE-ADVERSARIALE.md` avec **Sonde** (commande rejouable) / **Constat** / **Classe** (Ex) / **Verdict**
(confirmé, non confirmé, hors périmètre). Une revue dont la phase témoins a rendu NUL ne s'écrit pas.

## Lancer une revue

1. **Extraire les témoins gelés** — quatre versions de records figées à leur SHA :

       PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --extraire <scratchpad>/temoins

   Quatre fichiers aux noms **NEUTRES** (`temoin-1.md` … `temoin-4.md`) sont écrits ; la commande imprime la
   correspondance `nom -> fichier` **à toi seul**. Ne la transmets à aucun agent de revue, et ne la copie dans aucun
   fichier du répertoire extrait : la phase témoins mesure si les prompts DISCRIMINENT, pas si un agent sait lire une
   clé de réponse. `--lister` donne l'inventaire complet (défauts attendus compris) — même précaution.

2. **Lancer le workflow** — il ne reçoit que des CHEMINS. Le roster gelé (`tools/refutateur_temoins.json`) fait foi et
   n'est jamais passé en argument : sinon un appelant pourrait affaiblir un `attendu`, ne passer que le témoin sain, ou
   pointer ailleurs.

       Workflow({scriptPath: '.claude/workflows/refutateur.js', args: {
         target: 'docs/EDR/<record>.md', kind: 'record', today: '<AAAA-MM-JJ>',
         fichiers: ['<scratchpad>/temoins/temoin-1.md', '<scratchpad>/temoins/temoin-2.md',
                    '<scratchpad>/temoins/temoin-3.md', '<scratchpad>/temoins/temoin-4.md'],
         travail: '<scratchpad>/refutateur'}})

   Le script ne juge rien : la phase **Verification** fait relire le roster et lancer
   `python tools/refutateur_temoins.py --verifier` par un agent, et ce sont les codes de sortie qui décident.

3. **Publier le plancher avec le score — jamais après.**

       PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --plancher <scratchpad>/temoins

   Le workflow le fait lui-même et recopie la ligne dans son rendu ; l'en-tête de la revue doit la porter.
   **Un score de phase témoins sans son plancher de fausses retrouvailles est interdit** — comme tout ratio du
   dépôt. Mesuré le 2026-09-23 : une phrase vague, identique pour tous les témoins et écrite sans ouvrir un
   fichier, les passait TOUS ; le plancher valait le signal maximal et l'instrument ne voyait rien.

4. **Lire le statut.**
   * `statut: NUL` → un défaut connu n'a pas été retrouvé, le roster a été refusé, la racine est invalide, ou
     l'aiguillage a cassé : **rien ne s'écrit**. Incrémenter `témoin manqué` dans `ROLES.md` (PM). Deux fois de suite
     → les prompts du REF ne discriminent plus et sont re-scellés, par robla.
     ⚠️ Le témoin **cru sain** ne rend jamais NUL : il MESURE. Son compte se publie, il n'annule rien — jeter une
     revue qui a retrouvé ses défauts parce que ce plancher est haut, c'est supprimer la mesure au lieu de la
     publier. Si `discrimine` est `false`, la revue le dit dans son en-tête : l'instrument ne sépare pas un record
     sain d'un défectueux.
   * `statut: ECRITE` → `docs/reviews/<date>-<slug>.md` existe. La session qui GRAVE ajoute
     `review: docs/reviews/<date>-<slug>.md` au frontmatter du record, ou passe `reviewed_by=` à `preregister`.

Hors ligne, une liste de critiques déjà rendue (JSON : une liste d'objets portant chacun un `verdict`, ou l'objet
`{"critiques": [...]}` que rendent les agents) se confronte à un témoin sans relancer le workflow. Le fichier relu est
obligatoire — sans lui la garde anti-recopie ne peut pas s'exécuter, et recopier une ligne du témoin suffirait à le
« retrouver » :

    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom> <critiques.json> \
        --extrait <scratchpad>/temoins/temoin-N.md --jugement OUI

exit **0** = défaut retrouvé · **1** = revue NULLE · **2** = indécidable (témoin inconnu, roster invalide, critiques
illisibles, `--extrait` absent, ou jugement de l'étage 2 manquant — aucun de ces cas n'est un verdict de fond). La
commande imprime le plancher **avec** le verdict : il n'existe pas de chemin qui rende l'un sans l'autre.

Les noms de témoins se lisent dans `tools/refutateur_temoins.json` (ou `--lister`) — jamais dans un document que l'agent
de revue est amené à lire.
