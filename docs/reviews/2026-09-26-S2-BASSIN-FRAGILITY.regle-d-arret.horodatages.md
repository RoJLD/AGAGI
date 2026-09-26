# S2-BASSIN-FRAGILITY — règle d'arrêt : horodatages MESURÉS (compagnon)

Le fichier de règle (`2026-09-26-S2-BASSIN-FRAGILITY.regle-d-arret.md`, sha256 `599e0074fc51…`, blob git `d493fe05`)
reste INCHANGÉ : c'est son empreinte qui a été transmise à Master 2 comme preuve. Ce compagnon, écrit à 18:18 (+0200),
toujours AVANT tout retour de critique de la revue v8 (journal : 1 seul résultat, celui de l'agent « racine »), donne les
heures MESURÉES, toutes sur la MÊME horloge (batcave, système de fichiers, +0200) :

| événement | heure mesurée | source |
|---|---|---|
| lancement du run de revue v8 `wf_62afc0f0-abc` | 18:15:07,26 | création de `journal.jsonl` du run |
| démarrage de l'agent « racine » | 18:15:07,40 | création de `agent-abc1dac1060d62103.meta.json` |
| premier résultat d'agent (« racine ») | 18:15:20,59 | dernier message du transcript de l'agent (16:15:20,589Z) |
| démarrage des relectures de témoins | 18:15:22,88 | création du premier `agent-*.meta.json` suivant |
| écriture du fichier de règle | 18:16:38,85 | date de modification du fichier |
| staging du fichier de règle | 18:16:41 | `date` lancée juste après `git add` |
| réception par Master 2 | 18:16:59 | horloge de Master 2 (son message) |

Rectification : un message de l'auteur à Master 2 annonçait la revue v8 « lancée à 18h40 ». C'était une ESTIMATION, pas
une mesure, et elle était fausse de 25 minutes. L'heure mesurée du lancement est 18:15:07. Aucun fichier de preuve ne
porte ce « 18h40 ».
