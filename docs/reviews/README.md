# Revues adversariales à sondes propres

Un fichier par revue : `docs/reviews/<AAAA-MM-JJ>-<slug-du-record>.md`, référencé par le frontmatter `review:` du record
(exigé de tout NOUVEAU record à `gate:`/`tests:` par `tools/check_record_links.py`). Writer : la session qui a lancé la
revue. Forme : en-tête (cible, SHA, date, résultat des TÉMOINS), puis une section par prompt `P1`…`P10` de
`docs/REF/REF-REVUE-ADVERSARIALE.md` avec **Sonde** (commande rejouable) / **Constat** / **Classe** (Ex) / **Verdict**
(confirmé, non confirmé, hors périmètre). Une revue dont la phase témoins a rendu NUL ne s'écrit pas.
