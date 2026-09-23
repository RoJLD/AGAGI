# Revues adversariales à sondes propres

Un fichier par revue : `docs/reviews/<AAAA-MM-JJ>-<slug-du-record>.md`, référencé par le frontmatter `review:` du record
(exigé de tout NOUVEAU record à `gate:`/`tests:` par `tools/check_record_links.py`). Writer : la session qui a lancé la
revue. Forme : en-tête (cible, SHA, date, résultat des TÉMOINS), puis une section par prompt `P1`…`P10` de
`docs/REF/REF-REVUE-ADVERSARIALE.md` avec **Sonde** (commande rejouable) / **Constat** / **Classe** (Ex) / **Verdict**
(confirmé, non confirmé, hors périmètre). Une revue dont la phase témoins a rendu NUL ne s'écrit pas.

## Lancer une revue

1. **Extraire les témoins gelés** — quatre versions de records figées à leur SHA, trois à défaut connu et une saine :

       PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --extraire <scratchpad>/temoins

   Quatre fichiers `<nom>.md` sont écrits. `--lister` donne l'inventaire et le défaut attendu de chacun.

2. **Lancer le workflow** — les champs des témoins viennent de `tools/refutateur_temoins.json`, le script ne les invente
   pas :

       Workflow({scriptPath: '.claude/workflows/refutateur.js', args: {
         target: 'docs/EDR/<record>.md', kind: 'record', today: '<AAAA-MM-JJ>',
         temoins: [{nom, genre, attendu, fichier: '<scratchpad>/temoins/<nom>.md'}, ...]}})

3. **Lire le statut.**
   * `statut: NUL` → un défaut connu n'a pas été retrouvé (ou le témoin sain a fait crier la revue) : **rien ne
     s'écrit**. Incrémenter `témoin manqué` dans `ROLES.md` (PM). Deux fois de suite → les prompts du REF ne
     discriminent plus et sont re-scellés, par robla.
   * `statut: ECRITE` → `docs/reviews/<date>-<slug>.md` existe. La session qui GRAVE ajoute
     `review: docs/reviews/<date>-<slug>.md` au frontmatter du record, ou passe `reviewed_by=` à `preregister`.

Le plancher de fausses critiques (ce que la revue a trouvé sur le témoin **sain**) se publie dans l'en-tête de la revue :
un Réfutateur qui crie sur tout retrouverait les trois défauts et paraîtrait parfait.

Hors ligne, un texte de critiques déjà rendu se confronte à un témoin sans relancer le workflow :

    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier GRAB-COST-v09-08 <fichier>

exit 0 = défaut retrouvé, 1 = revue NULLE, 2 = témoin inconnu.
