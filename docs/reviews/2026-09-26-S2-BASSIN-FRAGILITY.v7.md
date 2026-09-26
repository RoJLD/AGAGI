# Revue adversariale — S2-BASSIN-FRAGILITY v7

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v7.json` (pré-inscription, brouillon non scellé)
- **Date** : 2026-09-26
- **SHA** : `82927108f6244537bee0a35d44fa06dcf36cea03` (`git -C C:/Users/robla/VScode_Project/AGAGI/.worktrees/science rev-parse HEAD`)

## Résultat des TÉMOINS

| témoin | statut | code | critiques recevables |
|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 6 |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 7 |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 6 |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 7 |

**PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5**
**plancher mesure sur LOCK-002-286f244 : 7 critiques recevables (seuil historique 1)**
**⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux**

Commandes de vérification (fichiers de critiques dans `scratchpad/refutateur_v7/`) :

- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v7/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-1.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v7/critiques-EDR-GRAB-COST-1828371.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-3.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v7/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-4.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier LOCK-002-286f244 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v7/critiques-LOCK-002-286f244.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-2.md`

Bilan : 34 critiques, **15 confirmées**.

---

## P1

### P1.1
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p1_sonde.py`
- **Constat** : Le levier qui renverserait la lecture est la classe de greffe de b_const et b_eplr. Chacune n'érode que sur onze seeds, le douzième (2036) étant positif pour const et nul pour eplr : un seul seed de plus au-dessus de S_a ferait passer ces bras en NEUTRE, donc en PROTECTRICE/INOFFENSIF au lieu de FRAGILE/DIRECTION. Cette prémisse est MESURÉE : elle est publiée et imposée au bit par le rejeu (branche 4). Ce n'est donc pas un défaut, mais la lecture de ces deux bras n'a aucune marge au seuil sign_min. Preuve : const d_med=-12.25 neg=11/12 pos=1 (2036 : +10.5) ; eplr d_med=-19.00 neg=11/12 eq=1 (2036 : 0.0) ; zero neg=8/12 d_med=-0.75 (NEUTRE) ; S_a identique au bit entre P4.16, P4.9 et P4.4 (True).
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.2
- **Sonde** : `cd .worktrees/science && grep -n "def cold_floor\|^P44 =\|imposés au bit" tools/evo_runs/s2_bassin_fragility.py ; python scratchpad/p1_sonde2.py`
- **Constat** : La certitude que la garde E19 sera illisible repose sur la saturation, qui a S_c au dénominateur. Or le texte attribue S_c aux vérifications des branches 2 et 4, alors qu'aucune branche ne le recalcule : le runner le lit tel quel dans le JSON de P4.4, c'est une valeur héritée d'un autre dispositif. La conclusion tient (recalcul : 12/12 seeds >= 0,9), mais la justification publiée est fausse, et le runner la répète en commentaire. Preuve : S2-BASSIN-FRAGILITY.v7.json:4 et :8 disent S_c imposé par les branches 2 et 4 ; or la branche 2 (json:13) porte sur noop/a_frozen et la branche 4 (json:15) sur le rejeu des bras. Dans s2_bassin_fragility.py, :78 définit P44 = results/s2_credit_retention.json et :353-356 contient cold_floor, docstring « HÉRITÉ, pas mesuré ici » ; :835 répète l'attribution. Recalcul : sat tdoff min 0.946, médiane 1.017, >= 0.9 sur 12 seeds.
- **Classe** : E33
- **Verdict** : confirmé

### P1.3
- **Sonde** : `python scratchpad/p1_sonde2.py ; python -c "from scipy import stats; print(stats.spearmanr([-28.25,-27.75,-12.25,-19.0,-0.75,-29.0],[10,8,65.5,16.5,179,3.5]))"`
- **Constat** : La preuve la plus forte citée pour le confondant de létalité est un Spearman calculé entre six médianes de bras. Deux problèmes : son p vient de l'approximation asymptotique, sans valeur à n = 6, et ces six points ne sont pas des réplicats, puisque tous les bras sont calculés sur les mêmes douze seeds et le même S_a. Le p exact par permutation est 1,7 à 3,5 fois plus grand que celui publié. Preuve : v7.json:11 publie rho +0,943 et p 0,005. scipy rend p=0.0048 (approximation t à 4 ddl). La permutation exacte donne 6/720 = 0.0083 en unilatéral et 12/720 = 0.0167 en bilatéral. Seeds identiques pour les six bras : [2026..2037], avec S_a commun (True).
- **Classe** : E7
- **Verdict** : confirmé

### P1.4
- **Sonde** : `cd .worktrees/science && python -c "import json;a=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));L=a['arms']['b_tdoff']['2026']['learning'];print('lr_effective_per_agent' in L, L.get('lr'), a['regime']['lr_published'], a['preflight']['lr_effective'])" ; grep -n lr_published tools/evo_runs/s2_credit_ablation.py`
- **Constat** : La clause E19 affirme que le JSON de P4.9 ne publie nulle part le pas de b_tdoff, et qu'il y figure deux champs vides. Le fichier contredit les deux points. Le pas par défaut, que b_tdoff partage puisque son lr vaut None, y est publié dans le bloc regime, lu sur l'optimiseur au pré-vol. Et le second champ cité est absent du bloc d'apprentissage : il n'y vaut pas None. La prémisse sur la paire à pas ×10 a donc été recopiée sans ouvrir la source. Preuve : la sortie donne False None 0.04 {'full': 0.04, 'lr': 0.004}, alors que v7.json:4 dit le pas de b_tdoff publié par aucun JSON de P4.9. Dans s2_credit_ablation.py, :309 fait regime.lr_published = preflight.lr_effective.full, avec le commentaire « lu sur l'optimiseur ».
- **Classe** : E8
- **Verdict** : confirmé

### P1.5
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p1_eps_match.py`
- **Constat** : Si l'appariement du contrôle eps échouait après l'arrondi float32 (1e-3 de l'amplitude du crédit), la branche 6 rendrait tout le run indéterminé ; c'est donc une prémisse porteuse, et aucune survie n'était nécessaire pour la tester. Je l'ai mesurée sur les W de la sonde de conception (seed 2026, b_full, sha conforme) : l'écart de L1 effectif reste des milliers de fois sous la tolérance. La prémisse tient. Preuve : sha256 404b4c0a... identique à W_sonde_sha256 ; net L1 médiane 100.537 ; l1_rel_err_max < 5e-6 (arrondi à 0.0 à 5 décimales) sur 5 tirages pour eps, sign et sign_x2, contre une tolérance de 0.01.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.6
- **Sonde** : `cd .worktrees/science && python -c` (b_full : comparaison P4.9/P4.16, imported_full, provenance) -- voir la commande relancée plus haut dans cette revue
- **Constat** : Le texte présente la référence de rejeu de b_full comme issue de P4.16. En fait, sur onze seeds sur douze, P4.16 a importé ces valeurs de P4.9, produites par un autre runner sur un arbre sale ; P4.16 n'a recalculé lui-même que le seed 2026, le seul que la sonde a rejoué. L'identité au bit exigée par la branche 4 porte donc sur du code qu'aucun commit ne contient, et elle n'a été testée avant le sceau que sur ce seed (plus b_zero, seeds 2026 et 2027). Preuve : dW_full identiques 12/12 et âges identiques 12/12 ; imported_full = [False, True x11] ; provenance P4.9 git_sha 9de2b3b dirty=true, P4.16 16163f3 dirty=true ; alors que v7.json:27 dit « b_full [...] de P4.16 ».
- **Classe** : aucune
- **Verdict** : confirmé

## P2 (DÉLÈGUE) — Régime : chaque paramètre cité est-il publié par l'evidence ? Porte 19, `tools/check_regime_claims.py --only <cible>`

- **Sonde** : `cd .worktrees/science && python tools/check_regime_claims.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v7.json ; python -c "from tools.check_regime_claims import analyze; a=analyze('.'); print(len(a['records']), sum('S2-BASSIN-FRAGILITY' in f for f in a['records']))" ; python tools/check_regime_claims.py --only inexistant/zzz.md`
- **Constat** : Verdict recopié de la porte : OK, exit 0 (64 légataires, aucun nouveau, aucune régression). Ce vert est VIDE pour cette cible : la porte 19 ne scanne que les records docs/EDR/*.md (304 lus) et la règle pré-inscrite v7, un JSON du scratchpad, n'en fait pas partie ; le filtre --only ne retient donc aucun fichier, et un chemin inexistant rend exactement la même ligne OK. Aucune affirmation de régime de la v7 (pas 0,04 / 0,004, 2000 ticks immortels, 200 ticks mortels...) n'a été confrontée à un results/ par la porte. Hors périmètre de P2 tel que délégué ; pas de réouverture de l'enquête (règle DÉLÈGUE). Dette à ouvrir (pas une critique) : --only qui ne correspond à aucun record scanné devrait être REFUSÉ ou signalé, comme la porte 23 le fait déjà pour un --only vide -- aujourd'hui son OK est indiscernable d'une couverture réelle. Preuve : sortie 1 : 'records : 304 | SANS_PARAMETRE 227, CONCORDE 6, CONCORDE_HORS_REGIME 7, SANS_RESULTS 52, SANS_REGIME 3, SANS_VALEUR_LUE 6, DISCORDE 3' puis 'OK : 64 record(s)...', exit=0. Sortie 2 : 304 records scannés, 0 contenant la cible. Sortie 3 (témoin chemin inexistant) : même ligne OK, exit=0. Périmètre : tools/check_regime_claims.py:357 (rel = docs/EDR/{name}) et :125 (CECITES : périmètre docs/EDR/*.md seul) ; filtre --only sans refus d'ensemble vide : tools/check_regime_claims.py:425-433.
- **Classe** : E4 (vérification vide : un OK indiscernable d'un succès) -- porte sur la porte, pas sur la cible
- **Verdict** : hors périmètre

## P3 (DÉLÈGUE) — Balayage du pas : la garde E19 est-elle appelée par le runner scellé ?

- **Sonde** : `cd .worktrees/science-prep && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py` ; puis la même commande dans `.worktrees/science` ; `ls docs/preregistrations/ | grep -i bassin`
- **Constat** : Verdict de la porte 23 recopié : OK, exit 0. Le runner de P4.18 figure parmi les 3 appelants réels de la garde E19 ; il appelle lui-même la fonction d'invariance au pas, donc le balayage existe. La porte le range en regle_absente, sa pire catégorie ici, parce qu'aucun JSON S2-BASSIN-FRAGILITY n'est encore scellé dans docs/preregistrations/. La v7 est dans le scratchpad : la porte ne peut donc pas la confronter, et c'est normal avant le sceau. Le signalement est NOUVEAU mais non bloquant. Verdict identique dans les worktrees science-prep (75582d6d) et science (82927108), alors que leurs runners diffèrent (85635 contre 84342 octets). Rien de plus à enquêter en P3 ; la question de la référence au même dispositif relève de P5. Preuve : sortie de la porte (identique dans les deux worktrees) : 'runners scelles : 34 | sous gradient : 12 | nus : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19' ; '[regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; exit=0. L'appel est en tools/evo_runs/s2_bassin_fragility.py:651 (import en :632). grep bassin dans docs/preregistrations/ = 0 fichier.
- **Classe** : aucune
- **Verdict** : non confirmé -- la garde E19 est appelée par le runner ; regle_absente seulement parce que la règle n'est pas encore scellée

## P4 (JUGE)

### P4.1 — famille de contrôles, taille réelle
- **Sonde** : `python scratchpad/p4_protectrice_v7.py` (fonctions pures du runner _classer/_lecture_bras sur results/s2_credit_ablation*.json suivis, aucun monde) ; `grep -n PROTECTRICE tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : PROTECTRICE, la lecture par bras de b_zero, affirme un sens entre tirage et crédit : le crédit abîmerait moins le bassin que son tirage apparié. C'est un signe de c_zero, or ce contraste est exclu des 14 cellules et aucun test de signe ne le porte. L'étiquette se déduit seulement de l'écart entre deux classements contre S_a (tirage ERODE, greffe NEUTRE), sans seuil delta_min sur c. J'ai injecté une dose connue sur les survies publiées de b_zero : un tirage à 4,5 ticks sous la greffe sur les 12 seeds sort PROTECTRICE. Le même écart, sur un bras dont la greffe érode, sort FRAGILE, donc lu comme une équivalence. Au total, la v7 affirme 15 contrastes, dont un sans test et sans marge. Deux remèdes possibles : lire c_zero en cellule 15 (11/12 tient encore : queue 0,00317 <= 0,05/15 = 0,00333), ou ramener PROTECTRICE à un descriptif hors famille. Preuve : tools/evo_runs/s2_bassin_fragility.py:618-619 : greffe NEUTRE + tirage ERODE donne PROTECTRICE sans consulter c. v7 JSON:25 exclut c_zero de la famille, alors que v7 JSON:7 fait dire à PROTECTRICE un sens tirage/crédit. Sortie de la sonde : greffe b_zero NEUTRE (neg 8/12, med -0,75) ; tirage injecté ERODE (neg 12/12, med -5,25) ; c_zero med -4,5 (12/12 < 0, |c| < 5), lu PROTECTRICE ; le même c sur une greffe ERODE est lu FRAGILE.
- **Classe** : E23
- **Verdict** : confirmé

### P4.2 — compte des cellules contre le nombre déclaré
- **Sonde** : `python scratchpad/p4_famille_v7.py ; python tools/check_control_family.py --only tools/evo_runs/s2_bassin_fragility.py` (exit 0) ; `sed -n 465,518p` du runner
- **Constat** : J'ai recompté les contrastes que fragility_verdict consulte : pos, classe eps, contraste 9b, six classes du tirage sign contre S_a, et cinq c pour les bras à greffe érodée. Total 14, soit la valeur passée à assert_control_family. Recalculé sur les JSON publiés au seuil 11/12 et delta 5, l'ensemble des greffes érodées est full, tdonly, const, eplr, tdoff ; b_zero reste NEUTRE, et la même dose atteinte sert d'abord la ligne a_frozen de P4.9 et celle de P4.16. run_fragility_seed exécute bien 137 phases 2 par seed (1 + 6 x 21 + 10). La marge ne tient qu'à une cellule : une famille de 15 garde 11/12, une de 16 le perd. Aucun écart entre le compte et la déclaration. Preuve : full neg 12 med -28,25 · tdonly neg 12 -27,75 · const neg 11 -12,25 · eplr neg 11 -19,00 · zero NEUTRE neg 8 -0,75 · tdoff neg 12 -29,00 ; contrastes lus = 14 = FAMILLE (runner:85) ; seuil_tient : 15 donne (True, 0,00317, 0,00333), 16 donne (False, 0,00317, 0,003125) ; a_frozen P4.9 == P4.16 : True.
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.3 — seuil hérité d'un autre dispositif
- **Sonde** : python heredoc : seuils_du_runner() comparé au bloc seuils de la v7, puis verifier_seuils(v7)
- **Constat** : Trois seuils viennent d'ailleurs : delta_min = 5 et harness_min = 20 viennent de P4.4, la fermeture E19 à 2/3 est le défaut de la garde, et saturation_high = 0,9 n'a aucune dérivation. La v7 déclare chacun de ces trois points, et le seuil de signe 11/12 se déduit bien de la famille déclarée. Le bloc seuils de la v7 coïncide clé pour clé avec les constantes exécutées. Aucune hérédité cachée ; le seul effet non couvert de delta_min est son absence sur c_zero, traité dans la critique 1. Preuve : clés runner - v7 = [], v7 - runner = [], différences = {}, verifier_seuils(v7) OK ; héritages déclarés en v7 JSON:54 (delta_min, harness_min, saturation_high) et v7 JSON:4 (2/3 = défaut de la garde).
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.1
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p5_v7_9b_atteignable.py` (fragility_verdict du runner sur S_a, S_tr_full, S_c publiés, sham inerte ; eps décalé uniformément de -30 à +10, puis 16 cases mu x sigma à 400 mondes ; aucun monde construit) ; `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Le correctif v7 ne traite que l'inertie d'eps. Or, une fois la greffe complète jugée érodante (branche 8) et eps jugé non érodant (9a), le contraste 9b vaut l'écart de la branche 8 augmenté du petit écart d'eps au no-op. Pour le faire échouer, eps devrait perdre plus de 17 ticks sur deux seeds en gardant une médiane au-dessus de -5 : 3 fois sur 6400 dans le balayage, et seulement à dispersion de 12 ticks. Le témoin de DIRECTION n'a donc presque aucune issue négative propre. Le drapeau le déclare pourtant éprouvé dès qu'eps sort de sa bande, par exemple à 4 ticks du no-op, où 9b passe 12/12 par simple arithmétique ; le témoin gelé des lignes 621-628 verrouille cette lecture. Il faudrait le déclarer non éprouvé par construction, ou exiger un écart d'eps au no-op du même ordre que l'écart de greffe que 9b pourrait voir disparaître. Preuve : écarts S_a - S_tr_full par seed : minimum 9,0, deuxième 17,0, médiane 28,25. Décalage uniforme : 9b n'échoue qu'à d <= -20 (10/12), où 9a a déjà rendu CRETE ; de d = -4,5 à +10, 9b passe 12/12 (médiane +23,8 à +38,2) et le drapeau dit éprouvé pour tout d non nul. Sur 6400 mondes : 9b ECHOUE 3, LU éprouvé 989, LU non éprouvé 3212, CRETE 2196. Gardes : assert_not_degenerate seule (tools/evo_runs/s2_bassin_fragility.py:684, :763, :851), 0 appel de assert_positive_control. Témoin gelé tests/sandbox/test_s2_bassin_fragility.py:621-628 : eps à S_a - 4 exigé éprouvé.
- **Classe** : E1
- **Verdict** : confirmé

### P5.2
- **Sonde** : `grep -n '^_BASE' -A8 tools/evo_runs/s2_bassin_fragility.py` ; python -c qui lit arms/b_tdoff/2026 de results/s2_credit_ablation.json et arms/b_eplr/2026 de results/s2_credit_ablation_2.json
- **Constat** : La paire de la garde de pas ne diffère que par le pas : même base, TD coupé des deux côtés, même dose d'appels publiée. La référence sans apprentissage (no-op, W du bassin) traverse la même phase 2 sur clones frais que la greffe. Aucun écart de dispositif dans la paire ni dans la référence ; la létalité qui accompagne le pas est déjà déclarée. Preuve : tools/evo_runs/s2_bassin_fragility.py:72 (b_eplr = _BASE, td_enabled False, lr LR_LOW) et :74 (b_tdoff = _BASE, td_enabled False). JSON seed 2026 : td_updates 0, episode_updates 250, ticks 2000 des deux côtés ; lr None (P4.9) contre 0.004 (P4.16).
- **Classe** : aucune
- **Verdict** : non confirmé

## P6

### P6.1
- **Sonde** : python -c lisant results/s2_bassin_fragility_sonde_conception.json['sources']['p418_probe_net_path.py'] (lignes de run_noop) ; `grep -n compter_consensus tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Le no-op mesuré avant le sceau (seed 2026, âges égaux à a_frozen) ne passe pas par le chemin des shams. La sonde appelle la survie mortelle sur la cohorte intacte, sans affecter W, sans cast float32 et sans les deux enveloppes de classe (consensus, reconstructions) ajoutées en v6/v7. Le no-op du contraste lui-même (phase2_with_W sur apply_delta(W0, zéro)) n'a jamais tourné : la neutralité des enveloppes ne sera établie que par la branche 2, au moment du run. Le coût est borné, puisque le seed 2026 passe en premier, mais le zéro exact de CE pipeline n'est pas mesuré au moment du sceau. Preuve : source de la sonde, ligne 142 : surv = phase2_survive_mortal(_bassin_cohort(SEED, 12), SEED, 200) ; contre tools/evo_runs/s2_bassin_fragility.py:473 (noop = phase2(seed, apply_delta(W0, zero))) et :211-212 (with compter_consensus() as cons, compter_reconstructions() as reco).
- **Classe** : E6
- **Verdict** : confirmé

### P6.2
- **Sonde** : `python scratchpad/refut_p6_v7_band.py 200` (importe RF._bande_contraste, q = 0,95 puis BANDE_Q) ; lecture de scratchpad/p6_band_calib_v7.py
- **Constat** : Les chiffres de calibration de la bande (au moins 0,967 sous le nul échangeable, 0,997 à référence exacte, puissance 0,99) sont attribués à un script de scratchpad qui calcule une AUTRE bande : quantile 0,95 et entropie 4182, alors que le runner exécute 0,975 et 4181. Rejoué, le quantile 0,95 ne couvre le nul échangeable qu'entre 0,910 et 0,970. Les chiffres publiés ne se retrouvent qu'avec 0,975. La preuve citée ne produit donc pas la conclusion, et elle vit hors git. Preuve : p6_band_calib_v7.py:29 bande_ech(..., q=0.95) et :32 SeedSequence([4182, ...]) contre s2_bassin_fragility.py:111-112 BANDE_Q = 0.975, BANDE_ENTROPY = 4181 ; sortie : q=0.95 gauss ref ECH couverture 0.970 0.960 0.935 0.910 0.910 ; q=0.975 gauss ref ECH 0.995 0.980 0.970 0.970 0.965.
- **Classe** : E33
- **Verdict** : confirmé

### P6.3
- **Sonde** : `python scratchpad/refut_p6_v7_band_hi.py 1000 ; sed -n 558,563p tests/sandbox/test_s2_bassin_fragility.py`
- **Constat** : Le plancher de couverture publié est le minimum d'estimations ponctuelles, sans erreur Monte-Carlo. À 1000 répétitions, la bande EXÉCUTÉE couvre le nul échangeable à 0,962 (sigma 4) et 0,960 (sigma 8), sous le 0,967 annoncé. L'écart reste dans l'erreur : la borne n'est simplement pas établie. Avec un sigma différent par seed (x0,5 à x3, plausible pour des S_a de 17 à 50), on tombe à 0,954 et 0,948. Le runner dit sa couverture tenue par des témoins gelés sur sigma 0,5-8, mais ces témoins n'exigent que 0,95, à sigma 2 et 4 seulement. Preuve : homog sigma=4.0 962/1000 = 0.9620 (+/- 0.0119) ; homog sigma=8.0 960/1000 = 0.9600 (+/- 0.0121) ; hetero sigma=8.0 948/1000 = 0.9480 ; contre >= 0,967 publié (règle v7, discrimination branche 10 ; runner :576 « σ 0,5-8 (témoins gelés) ») ; tests/sandbox/test_s2_bassin_fragility.py:561-562 for sigma in (2.0, 4.0) ... >= 0.95.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.4
- **Sonde** : `grep -n '0,98\|0,967' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Un commentaire périmé du runner donne à la bande une couverture de 0,98 d'un nul connu, chiffre de la v6. La docstring de la même fonction et la règle v7 disent 0,967, et le rejeu mesure 0,960 sous le nul échangeable. Le même fichier porte donc deux planchers de bruit contradictoires. Preuve : tools/evo_runs/s2_bassin_fragility.py:775 (>= 0,98) contre :107 et :576 (>= 0,967) ; rejeu 0,9600 à sigma 8.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.5
- **Sonde** : `grep -o 'SANS bande...|sans plancher...'` sur la règle v7
- **Constat** : Les trois rapports sans plancher (part épargnée f, fermeture E19, saturation) sont déjà déclarés sans bande par la v7. Aucune lecture n'en dépend, puisque la garde E19 est illisible par construction. Pas de défaut neuf. Preuve : S2-BASSIN-FRAGILITY.v7.json:4 (clé clause_E19) et :54 (clé seuils_note).
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.6
- **Sonde** : python -c listant les cellules de results/s2_bassin_fragility_sonde_conception.json
- **Constat** : Aucune survie de sham n'existe encore, donc aucun contraste à confronter à sa bande. Le seul chiffre pré-sceau proche d'un seuil, la saturation de b_tdoff (1,017 contre 0,9), est déjà qualifié par la règle. Preuve : cellules : noop, p416:b_full, p49:b_zero, p416:b_const, p416:b_eplr, p416:b_tdonly — 0 cellule sign/iso/eps/pos.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7 (JUGE)

### P7.1 — dose reçue par b_zero sur la voie épisodique
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p7v7_dose_nulle.py` (lancé depuis .worktrees/science, sans monde : 3 agents du bassin, un appel learn_episode sous count_learning_events, reward_scale 0 puis 1) ; python -c sur results/s2_credit_ablation.json (b_zero : reward_scale, episode_updates)
- **Constat** : La v7 pose que chaque ligne de W reçoit une dose égale au compteur publié. Pour b_zero, c'est faux sur la voie épisodique : le retour y est multiplié par zéro, la porte conditionnelle est éteinte, la perte vaut 0 et le pas SGD ne déplace rien. Le compteur enregistre pourtant tout appel qui rend un flottant : les 250 mises à jour épisodiques publiées pour ce bras sont 250 pas nuls, et sa dose épisodique réelle est zéro. Conséquence : la borne de brassage la plus haute du tableau (0,716, b_zero) porte sur une voie qui n'écrit rien dans ΔW, et l'attribution du bruit de brassage d'abord à b_zero perd son appui épisodique ; seul le TD y bouge W. Remède : compter une mise à jour quand W bouge, ou publier par bras la part de dW_abs_sum de chaque voie. Preuve : reward_scale=0.0 -> loss=0.0, episode_updates=1, dW_abs_sum=0, max|W1-W0|=0 ; contrôle reward_scale=1.0 -> episode_updates=1, dW_abs_sum=4.12, max|W1-W0|=0.0179. tools/learning_events.py:185-186 (compte si out is not None) contre :16-17 (doc : « réellement mis à jour W ») ; src/agents/backend_torch.py:502 (gate_pen = 0 car CONDITION_GATE=False, :48) ; P4.9 b_zero : reward_scale 0.0 et episode_updates 250 sur 12/12 seeds.
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 — borne de brassage appliquée à une voie coupée (b_tdonly)
- **Sonde** : python -c sur results/s2_credit_ablation_2.json (b_tdonly : episode_calls, episode_updates, resurrections) ; `sed -n 1069,1097p src/worlds/world_1_stoneage.py` (fenêtre deque maxlen 8, appel aux multiples de 8)
- **Constat** : La borne de brassage publiée compte les fenêtres épisodiques de 8 ticks qui enjambent une mort. Elle est donnée aussi pour b_tdonly (0,032), bras dont la voie épisodique est coupée : 250 appels, 0 mise à jour sur 12/12 seeds. Ce chiffre ne borne donc rien pour ce bras ; son ΔW vient entièrement du TD, dont la contamination (transition en attente, H hérité d'un autre corps) n'a aucune borne dans la règle. Le classement des six bras par brassage place ainsi tdonly au-dessus de tdoff sur une voie qu'il n'exerce pas. Remède : borner par voie, ou retirer tdonly du tableau épisodique. Preuve : b_tdonly : episode_calls {250}, episode_updates {0}, résurrections médiane 8.0 ; world_1_stoneage.py:52 (torch_episode_k = 8) et :1078 ; tools/evo_runs/s2_credit_ablation_2.py:52 (b_tdonly episode_enabled=False) ; valeur publiée par la règle 0,032 = 8/250, opposée à 0 mise à jour épisodique.
- **Classe** : E16
- **Verdict** : confirmé

### P7.3 — cohorte constante et dose publiée
- **Sonde** : python -c sur results/s2_credit_ablation_2.json et results/s2_credit_ablation.json (num_agents, len(ages), learning.ticks)
- **Constat** : Rien à reprocher : les 84 cellules publiées des sept bras portent 12 agents, 12 âges et 2000 ticks de phase 1 ; la branche 4 exige TD, épisodique, résurrections et ticks au bit. Preuve : cellules 84, écarts 0 ; tools/evo_runs/s2_bassin_fragility.py:541-546.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGE)

### P8.1 — Corps et aliasing : vue de H
- **Sonde** : python (bassin results/warm003_dagger_genome.npz + 5 W de sonde p418_W_*.npz du scratchpad) : L1 des colonnes 77/78 du bassin, L1 attendue de pos par colonne = ||W_bassin||1/172, masse de ΔW sur les colonnes 77-78 ; python re sur la cible : `pos` à moins de 300 caractères de vote/consensus (motif validé : 'logits 13-14' = 1 occurrence)
- **Constat** : Le témoin positif de FRAGILE (pos) verse sur les deux colonnes qui déclenchent le vote social une masse égale à celle que le bassin y porte déjà, quand ΔW — donc sign et eps — y met exactement zéro. Une érosion de pos peut donc passer par l'écrivain de la vue H (toute la rangée de sorties de la case recopiée) : ce contrôle éprouve un chemin que le sham primaire n'emprunte jamais en direct. La limite annoncée pour pos ne parle que d'amplitude ; nulle part pos n'est rapproché du vote. Preuve : col 77 : bassin 12,95 contre pos 14,2 (x1,10) ; col 78 : 13,73 contre 14,2 (x1,03) ; part de ΔW sur 77-78 = 0,0 pour les 5 bras sondés (11 colonnes, 8 pour b_eplr) ; déclencheur et réécriture de toute la rangée : src/worlds/world_1_stoneage.py:963-973 ; 0 des 8 occurrences vote/consensus de la cible n'a pos à proximité (10 occurrences de pos).
- **Classe** : aucune (voisine de E5 : vue de H réécrite par le monde)
- **Verdict** : confirmé

### P8.2 — Corps (E26)
- **Sonde** : python sur results/s2_bassin_fragility_sonde_conception.json (body_rows_0_10_share) ; `grep -n phenotype|update_phenotype` sur world_1_stoneage.py, mamba_agent.py, backend_torch.py ; lecture runner :198-216 et :307-317
- **Constat** : ΔW porte 3,1 à 5,7 % de sa masse sur les rangées 0:10 qui fixent hp, inventaire et drain, mais ce corps reste celui du bassin dans toutes les conditions : attributs calculés une fois, jamais recalculés par l'apprentissage ni par la pose de W, garde avant/après munie d'un témoin qui lève, et la seule voie de recalcul du monde (HGT) est coupée par le mode benchmark. Pas de défaut E26. Preuve : body_rows_0_10_share 0,031 (zero) à 0,057 (eplr) ; mamba_agent.py:77-80 (calcul unique), backend_torch.py:509-513 (write_back sans update_phenotype), runner :209 puis garde :210/:213, témoin tests/sandbox/test_s2_bassin_fragility.py:423 ; seul recalcul monde world_1_stoneage.py:990, coupé par :1878-1879 avec benchmark_mode=True (s2_credit_retention.py:73).
- **Classe** : E26
- **Verdict** : non confirmé

### P8.3 — Chevauchement entrée/sortie (E24)
- **Sonde** : `python tools/check_io_overlap.py` ; python -c chargeant warm003_dagger_genome.npz (num_inputs, num_outputs, N)
- **Constat** : Le bassin a 59 entrées, 108 sorties, 172 nœuds : les sorties commencent au nœud 64, aucun recouvrement ; la porte 17 ne signale aucun génome nouveau ou aggravé, et load_bassin refuse un recouvrement. Pas de défaut E24. Preuve : porte 17 : 358 génomes, 10 chevauchants connus, 0 nouveau, 0 aggravé, EXIT 0 ; bassin I=59, O=108, N=172, début des sorties 64, recouvrement 0 ; assert_no_io_overlap dans load_bassin (s2_credit_retention.py:57).
- **Classe** : E24
- **Verdict** : non confirmé

### P8.4 — Vue de l'état récurrent
- **Sonde** : python -c : tranche H[:,64:172].cpu().numpy(), écriture a[0,13]=0,9 et a[0,5]-=0,1, lecture de H ; lecture des drapeaux CONDITION_GATE/GATE_TARGET(S) ; grep des écritures en place dans world_1_stoneage.py:1255-1420 ; grep d'affectation du gate dans la chaîne d'import du runner
- **Constat** : Porte de conditionnement éteinte : les logits numpy partagent bien la mémoire de H (l'écriture du logit 13 se retrouve dans H[77]). Les trois écrivains de H (vote, retrait de 0,1, remise à zéro par reconstruction) sont déjà déclarés ; aucun quatrième n'apparaît entre le forward et le choix d'action. Preuve : H[0,77]=0,90 et H[0,69]=-0,1 après écriture dans la tranche numpy ; CONDITION_GATE False, GATE_TARGET None, GATE_TARGETS None (backend_torch.py:48-51), 0 affectation dans les 10 modules de la chaîne (rc=1) ; 2 écritures seulement : vote (:1269) et retrait (:1340).
- **Classe** : E5
- **Verdict** : non confirmé

### P8.5 — Portée de la sonde imposée
- **Sonde** : Grep motif `W\[` sur tools/evo_runs/s2_bassin_fragility.py (identique hors CR dans science et science-prep : diff --strip-trailing-cr vide)
- **Constat** : La sonde imposée par P8 (motif W crochet sur le runner) ne rend que deux lignes, un commentaire et la diagonale ; l'accès aux rangées du corps passe par une autre variable et lui échappe. Faiblesse du prompt, pas de la cible. Preuve : 2 lignes : :32 (docstring) et :188 (diagonale de dW) ; l'accès aux rangées 0:10 est a[:, 0:10, :] en :190, invisible au motif.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P9 (DÉLÈGUE)

### P9.1 — provenance, porte 20 (tools/check_evidence_provenance.py)
- **Sonde** : `python tools/check_evidence_provenance.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v7.json`, lancée dans C:/Users/robla/VScode_Project/AGAGI/.worktrees/science (tmp/science 82927108) puis dans C:/Users/robla/VScode_Project/AGAGI/.worktrees/science-prep (tmp/science-prep 75582d6d) ; contrôle de vacuité : `--only docs/EDR/NEXISTE_PAS.md` dans science ; `grep -c 'P2.128 —' docs/roadmap/PRIORITES_ET_DETTES.md` (disque, index, puis git show <branche>:… sur chaque branche locale)
- **Constat** : Verdict recopié de la porte 20 corrigée (arbre science-prep) : REFUS, cible inconnue, exit 2. Une pré-inscription JSON est hors du périmètre de cette porte, qui ne lit que les records EDR ; la question de provenance reste sans réponse de porte pour la v7 (dette P2.129 déjà ouverte). Dans l'arbre science, la porte non corrigée rend OK exit 0, sortie identique à celle d'un chemin inexistant : vert vide. Le correctif P2.128 n'y est pas fusionné et son entrée manque à ce backlog alors que P2.129 en dépend. Preuve : science-prep : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte … (E4, P2.128)', exit=2. science : 'OK : 18 chemin(s) legataire(s) gele(s). Aucun nouveau, aucune regression.', exit=0, sortie identique pour docs/EDR/NEXISTE_PAS.md. La même cible reçoit donc OK/0 d'un côté, REFUS/2 de l'autre. Entrée 'P2.128 —' : 0 dans le backlog de science (disque et index), 1 sur 5 branches (feat/d1-prod-pairing, tmp/front, tmp/nexus, tmp/p2-105, tmp/science-prep) ; P2.129 cite P2.128 à PRIORITES_ET_DETTES.md:1406 et :1412 (arbre science).
- **Classe** : E4 (vert vide de la porte non corrigée, déjà inscrit en P2.128 ; le fond relève de P2.129)
- **Verdict** : hors périmètre

### P9.2 — sceau de la pré-inscription (tools.preregister.verify)
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')"` dans .worktrees/science et .worktrees/science-prep ; `ls docs/preregistrations | grep -ic bassin` ; `ls -d results/s2_bassin_fragility*`
- **Constat** : La porte de sceau refuse dans les deux arbres : aucun fichier scellé pour cette règle, donc rien à déclarer intact ni rompu. État attendu d'un brouillon revu avant sceau ; aucun JSON de run principal n'existe, seul celui de la sonde de conception. Pas un défaut à ce stade ; verify devra être rejoué après preregister avec reviewed_by. Preuve : FileNotFoundError: aucune pré-inscription « S2-BASSIN-FRAGILITY » — la règle n'a pas été scellée avant le run (tools/preregister.py:196), exit=1 dans les deux arbres ; 0 fichier 'bassin' dans docs/preregistrations ; un seul artefact results/s2_bassin_fragility* : results/s2_bassin_fragility_sonde_conception.json (aucun results/s2_bassin_fragility_genomes/ ni JSON de run).
- **Classe** : aucune
- **Verdict** : non confirmé

## P10 (JUGE)

### P10.1 — Mécanisme
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p10_consensus.py` (appelle le vrai WeightedConsensus.vote avec le critère != de compter_consensus) ; Read de src/swarm/consensus.py:47-55, de tools/evo_runs/s2_bassin_fragility.py:227-245 et de tests/sandbox/test_s2_bassin_fragility.py:885
- **Constat** : Le compteur du vote social est censé ignorer un vote entre clones dont les sorties sont identiques. Le vote réel ne rend pourtant la ligne au bit que dans un seul cas : deux votants à fitness égales. Dès trois votants, ou avec deux votants à fitness distinctes, la moyenne pondérée calculée en float32 décale la ligne d'environ 1e-7 en relatif. Ce décalage est écrit dans H par la vue, puis compté comme une réécriture. Le témoin censé calibrer le compteur remplace le vote par une lambda constante : il n'a jamais été confronté à ce cas. Preuve : 2 votants à fitness égales, 0/300 lignes changées. 3 votants à fitness égales, 300/300 (écart relatif max 1,19e-07). 12 votants, 300/300 (2,38e-07). 2 votants à fitness distinctes, 292/300 (1,49e-07). consensus.py:51 (softmax float32) et :55 (somme pondérée) ; s2_bassin_fragility.py:242 (toute ligne != avant est comptée) ; test:885 (vote=lambda preds: voted, vote simulé). L'affirmation contraire se trouve dans S2-BASSIN-FRAGILITY.v7.json:27 et dans la docstring du runner, :227-229.
- **Classe** : E8
- **Verdict** : confirmé — le compteur reste descriptif et hors verdict, mais la sémantique qu'annonce le correctif v6 P10.b est fausse. Sa fréquence in situ, notamment sous no-op où les clones sont identiques, n'est pas mesurée : il faudrait un monde, donc c'est une dette et non une sonde.

### P10.2 — référent d'une grandeur publiée
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p10_reconstructions.py` (âges publiés de P4.16 et P4.9, mécanisme lu dans world_1_stoneage.py:1254-1256 et :1060-1066, arrêt de boucle dans s2_credit_retention.py:153) ; Read de s2_bassin_fragility.py:263-275 et de test_s2_bassin_fragility.py:682-692
- **Constat** : Les médianes citées en prose (10 pour no-op/const/zero, 9 pour eplr, 5 à 5,5 pour full/tdonly/tdoff) ne comptent que les reconstructions provoquées par une mort. Or le compteur désigné pour les mesurer publie un champ « constructions » qui inclut la construction initiale de la population. Sur les mêmes âges, il rendra donc 11 / 10 / 6 à 6,5. La prose et le champ publié sont décalés de un partout, et la règle ne signale nulle part ce décalage. Preuve : (reconstructions / constructions) a_frozen 10,0 / 11,0 ; b_const 10,0 / 11,0 ; b_zero 10,0 / 11,0 ; b_eplr 9,0 / 10,0 ; b_full 5,0 / 6,0 ; b_tdoff 5,5 / 6,5. s2_bassin_fragility.py:271 incrémente de 1 à chaque make_population torch, construction initiale comprise ; :215 publie « constructions ». Le témoin test:692 rend 2 pour une construction initiale suivie d'une reconstruction. La prose correspondante est dans S2-BASSIN-FRAGILITY.v7.json:3.
- **Classe** : E8
- **Verdict** : confirmé — défaut mineur, hors verdict. Deux corrections possibles : publier constructions − 1, ou citer 11/10/6 en le disant.

### P10.3 — Mécanisme
- **Sonde** : `python .../scratchpad/p10_colonnes.py` (sha256 des W de la sonde confrontés à results/s2_bassin_fragility_sonde_conception.json) ; Read de backend_torch.py:155-210, world_1_stoneage.py:1312, :1340, :971-973, learning_events.py:190-192, s2_credit_retention.py:148, :163
- **Constat** : J'ai lu ligne par ligne le support de ΔW, l'inertie des colonnes d'entrée, la vue H, les deux écrivains du monde et le gel de phase 2 à chaque reconstruction. Tout concorde avec la règle. Preuve : dimensions I 59, O 108, N 172, premier nœud de sortie 64, donc les colonnes d'entrée pèsent 59/172 = 34,3 %. Colonnes non nulles : [64-71, 88, 89, 92] pour full, tdonly, const et zero ; [64-71] pour eplr. Couplage vers les colonnes 77/78 : L1 0,727 / 0,929, soit 8,7 % / 9,7 % de la L1 hors entrées. Rapport de norme d'opérateur crédit/sham : ×1,07 (zero) à ×1,50 (tdonly). Vue H : backend_torch.py:198 et :200. Gel de phase 2 : le patch de __init__ lr=0 est réappliqué à chaque reconstruction (learning_events.py:191).
- **Classe** : aucune
- **Verdict** : non confirmé

### P10.4 — référents chiffrés
- **Sonde** : `python .../scratchpad/p10_saturation.py ; python .../scratchpad/p10_eps_match.py` ; python -c pour les rapports de la paire E19 à partir de published()
- **Constat** : Les grandeurs annoncées comme connues d'avance, recalculées avec les fonctions du runner sans construire de monde, retombent toutes sur les valeurs publiées. L'appariement effectif en float32 tient lui aussi, y compris pour eps. Preuve : saturation de b_tdoff : médiane 1,017, minimum 0,946, 12/12 seeds à ≥ 0,9, S_tr 7,5. moins_max : 12/12 pour full, tdonly et tdoff ; 11/12 pour const et eplr ; seed 2036 : const 27,5 et eplr 17,0 contre S_a 17,0. S_tr < S_c : tdoff 7/12, full 3/12, tdonly 1/12. Rapport de chemin tdoff/eplr : médiane 1,363 (étendue 0,83 à 2,84, seed 2027 sous 1). Rapport de masse : 7,34. Résurrections : 3,5 contre 16,5. l1_rel_err_max = 0,00000 sur les 5 tirages de eps, sign, x2 et x4.
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, v7 → v8

Ce passage est sorti NUL une première fois, alors que les trois témoins avaient été retrouvés. Le vérificateur avait
écrit `refus = "(vide) Pas de refus. Étape 1 : …"`, que l'outil a lu comme un refus. C'est la 3ᵉ occurrence de P2.133
ce soir. L'auteur a relu la sortie du vérificateur : les étapes 1 à 3 passent. Le contournement local a été élargi, puis
le même run a été REPRIS, les agents rejoués depuis le cache.

⚠️ Ce passage est INDISCRIMINANT : le témoin cru sain rend 7 critiques recevables, les défectueux 6 à 7. Ses critiques
ont donc été revérifiées une à une contre le code et les JSON, et leurs chiffres recalculés, avant d'être suivies. Trois
touchaient le fond (P4.1, P5.1, P7.1) : la version soumise au sceau est la **v8**.

**Suites données aux critiques confirmées.**
- **P4.1 (E23)** — PROTECTRICE affirmait un sens (« le crédit abîme moins que son tirage ») sans aucun test sur `c`.
  Elle exige désormais le contraste PLUS : `c` < 0 sur au moins 11/12 seeds ET médiane <= −5. Sinon, avec un sham
  ERODE, la lecture est NON_TRANCHE. `c_zero` devient la 15ᵉ cellule de la famille, scellée : 11/12 tient encore
  (0,00317 <= 0,00333) et tomberait à 16. Témoin gelé sur le cas injecté par la revue.
- **P5.1 (E1)** — 9b est déclaré NON ÉPROUVÉ PAR CONSTRUCTION. C'est l'écart de la branche 8 augmenté de l'écart
  d'eps : 3 mondes sur 6400 le font échouer. Le drapeau vaut toujours vrai et le motif le dit ; l'inertie d'eps reste
  publiée. Le témoin qui déclarait le contrôle « éprouvé » à S_a − 4 est réécrit.
- **P7.1 (E8), P7.2 (E16)** — critique reproduite par la sonde de la revue : avec un retour nul, la perte épisodique
  vaut 0 et W ne bouge pas. La dose par ligne suit le compteur pour la voie TD seulement ; les 250 mises à jour
  épisodiques de b_zero sont des pas nuls. Les bornes du brassage sont réécrites PAR VOIE, pour les seules voies
  épisodiques qui écrivent : const 0,262, eplr 0,066, full 0,040, tdoff 0,014. b_zero et b_tdonly en sont retirés. La
  contamination de la voie TD est déclarée sans borne.
- **P1.2 (E33)** — S_c n'est imposé par aucune branche : c'est une constante publiée de P4.4, lue telle quelle. Corrigé
  dans clause_E19, en 10bis et dans le commentaire du runner.
- **P1.3 (E7)** — le Spearman entre les six médianes est publié avec son p EXACT par permutation (12/720 = 0,017
  bilatéral) et déclaré DESCRIPTIF : les six points ne sont pas des réplicats indépendants.
- **P1.4 (E8)** — la clause disait le pas de b_tdoff « publié par aucun JSON de P4.9 ». C'est faux :
  `regime.lr_published` = 0,04, lu sur l'optimiseur (s2_credit_ablation.py:309). La v6 avait suivi une critique sans
  ouvrir la source ; c'est reconnu ici. La mesure par cellule (`pas_optimiseur_mesure`) reste, en complément.
- **P1.6** — la provenance de la référence de b_full est dite : importée de P4.9 sur 11 seeds, arbres sales, identité
  au bit éprouvée avant le sceau sur le seul seed 2026.
- **P6.1 (E6)** — le témoin gelé du no-op passe désormais par `apply_delta(W_bassin, 0)`, soit exactement le pipeline
  des shams, enveloppes comprises. Il rend a_frozen au bit au seed 2026 (monde réel) ; la règle le déclare en (2ter).
- **P6.2 (E33), P6.3, P6.4** — la couverture est MESURÉE sur la bande exécutée par `mesurer_couverture_bande`
  (commande `calibrer-bande`, sans monde, 1000 répétitions). Elle est publiée et suivie dans
  `results/s2_bassin_fragility_calibration_bande.json`, avec son erreur Monte-Carlo et un σ hétérogène. Résultats :
  >= 0,997 à référence exacte ; 0,952-0,993 sous le nul échangeable homogène ; 0,926-0,983 hétérogène. La bande est
  donc de niveau NOMINAL, pas conservatrice, et c'est dit. Le commentaire périmé à 0,98 est retiré. Deux témoins à
  réponse connue (bande infinie, bande négative) calibrent la mesure elle-même.
- **P8.1** — la limite de pos est complétée : il charge les colonnes 77-78 du vote, où ΔW ne met rien.
- **P10.1 (E8)** — la sémantique du compteur de consensus est corrigée. Il compte les changements AU BIT, donc presque
  tous les votes, puisque l'arrondi float32 de la moyenne pondérée décale la ligne dès trois votants.
- **P10.2 (E8)** — le compteur publie `constructions`, construction initiale comprise, ET `reconstructions` =
  constructions − 1. La prose cite les reconstructions et le dit.

Non confirmées ou hors périmètre : sans suite (P1.1, P1.5, P2, P3, P4.2, P4.3, P5.2, P6.5, P6.6, P7.3, P8.2-P8.5, P9.1,
P9.2, P10.3, P10.4).
