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
| **Réfutateur** | instancié | `.claude/workflows/refutateur.js`, 8-10 prompts figés, portes 18/19/20 livrées d'abord (plan 2) | trois records-témoins gelés (GRAB-COST 09-09, S2-BLIND v1, RETAIN-COMPOSE pré-rétractation) + no-op LOCK-002 | tokens/revue : non mesuré, à publier au 1er bilan | critiques émises / confirmées / fausses ; taux de -bis après run (baseline 3/58) | < 1 confirmée sur 10 revues ; ou ≥ 80 % attrapables par une porte ; ou -bis après run ≥ 3/58 après 20 sceaux ; ou coût > 15 % |
| **Régisseur des runs** | candidat | — | — | — | — | réfuté le 2026-09-16 (compte gonflé par un apparieur faillible ; occurrences déjà closes ou déjà cliquets) ; naît sur deux runs abandonnés ou contaminés en 30 j malgré `cost_guard` et le bail |
| **Intégrateur** | candidat | — | — | — | — | réfuté le 2026-09-16 (prémisse périmée : d1/main résolu le 07-28) ; naît sur deux collisions de numéro ou deux merges perdus en 30 j |
| **Greffier-métrologue** | candidat | — | — | — | — | réfuté le 2026-09-16 (la promotion documenté→exécutable A été appliquée, P2.25) ; naît sur deux classes restées `documenté` après deux récidives |
| **Bibliothécaire de la doctrine** | candidat | — | — | — | — | réfuté le 2026-09-16 (rare, bon marché après coup) ; naît sur deux sessions trompées par la même phrase périmée, datées |
| **Auditeur des angles morts** | candidat | — | — | — | — | → cliquet « hors motif » + lentille du stratège sur tout élargissement de détecteur (backlog) ; ne naît pas comme rôle |
| **Archiviste de l'évidence** | candidat | — | — | — | — | constat vrai (69/20/18) devenu la porte 19 (plan 2) ; ne naît pas comme rôle |
| **Greffier de passage** | candidat | — | — | — | — | réfuté le 2026-09-16 (une seule occurrence) ; naît sur deux occurrences datées de travail dupliqué faute de brief |
| **Scribe des records** | dissous | témoin du panel — fonction couverte par la porte 1 | doit être TUÉ à chaque revue des rôles, sinon la passe est nulle | — | — | témoin permanent : ne renaît jamais |
