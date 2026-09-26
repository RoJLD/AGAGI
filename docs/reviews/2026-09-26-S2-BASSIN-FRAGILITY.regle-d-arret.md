# S2-BASSIN-FRAGILITY — règle d'arrêt des revues avant sceau

- **Écrite le** : 2026-09-26 à 18:16 (+0200), AVANT tout retour de la revue de la v8 (run `wf_62afc0f0-abc`, lancé sur
  le brouillon v8, sceau de brouillon `87f445dd…` ; au moment de l'écriture, seul l'agent « racine » avait rendu, aucune
  relecture de témoin, aucune critique).
- **Auteur** : session SCIENCE-HARNAIS (agagi-40). **Accord** : Master 2, qui en a posé les trois conditions (message
  du 2026-09-26, après la revue v7).
- **Pourquoi** : sept passes de revue ont chacune confirmé 13 à 26 critiques, et les deux dernières étaient
  INDISCRIMINANTES ou presque (le témoin cru sain rend autant de critiques recevables que les défectueux). Sans règle
  d'arrêt fixée d'avance, sceller ou re-réviser se choisirait en voyant les critiques : un choix post hoc (E11).

## La règle

1. **La v8 est scellée** si sa revue ne confirme AUCUNE critique qui change une BRANCHE ou une LECTURE au sens de la
   liste fermée ci-dessous. Toute autre critique confirmée est traitée dans l'addendum de la revue v8, sans -bis ni v9.
2. **Liste FERMÉE de ce qui « change une branche ou une lecture »** — une critique confirmée qui exige de modifier :
   - (a) le VOCABULAIRE du verdict (une issue, une lecture par bras, une lecture globale ajoutée, retirée ou renommée) ;
   - (b) un SEUIL ou une BANDE (valeur, définition ou calcul d'un seuil scellé, d'une marge, d'une bande de tirage) ;
   - (c) la TAILLE de la famille de contrôles ;
   - (d) l'INCLUSION ou l'EXCLUSION d'un contraste (dans la famille, ou dans ce que lit le verdict) ;
   - (e) le STATUT d'un contrôle (éprouvé / non éprouvé, positif / négatif, lu / hors verdict) ;
   - (f) l'UNITÉ d'appariement ;
   - (g) le SENS ATTENDU d'une issue (ce qu'une lecture affirme).
   Tout le reste — texte, chiffre cité, provenance, qualificatif publié, commentaire, docstring, borne déclarée,
   limite dite — relève de l'addendum.
3. **Une passe INDISCRIMINANTE ne compte que par la re-vérification de l'auteur, critique par critique** (sonde relancée
   ou code relu, preuve écrite dans l'addendum) ; une critique non re-vérifiée ne bloque ni ne débloque le sceau.
4. **Si une critique de la liste (a)-(g) est confirmée** : v9, nouvelle revue, même règle — et elle ne se desserre pas.
5. **Calendrier** : aucune étape n'est sacrifiée à la fenêtre de nexus. Si le sceau tombe trop tard pour la fenêtre
   (extinction à minuit), les cellules partent le LENDEMAIN sur nexus, jamais sur la batcave pour tenir l'horloge : la
   cellule témoin inter-plateforme (nexus contre batcave, au bit) est une question en soi.
