# Revue adversariale — S2-BASSIN-FRAGILITY

* **Cible** : `docs/EDR/S2-BASSIN-FRAGILITY_The_Positive_Control_Of_FRAGILE_Misses_By_One_Seed_The_Instrument_Cannot_Return_FRAGILE.md`
* **Date** : 2026-09-28
* **SHA** : `afa4dac6f759d55439653573129a896480f4f52c` (branche tmp/science-prep)
* **Témoins** :
  * S2-BLIND-CHAMPION-42e9357 : RETROUVE (code 0, 9 critiques recevables)
  * LOCK-002-286f244 (cru sain) : MESURE (code 0, 6 critiques recevables)
  * EDR-GRAB-COST-1828371 : RETROUVE (code 0, 6 critiques recevables)
  * EDR-RETAIN-COMPOSE-4204f8f : RETROUVE (code 0, 5 critiques recevables)
* **Planchers** : PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
* ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
* Commandes de vérification : `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom> <scratchpad>/refutateur_p418rec/critiques-<nom>.json --extrait <scratchpad>/temoins_p418rec/temoin-N.md [--jugement OUI]` (N = 1..4 dans l'ordre ci-dessus ; `--jugement OUI` sauf pour LOCK-002).

---

## P1 (JUGE) — prémisse porteuse

### P1.a
* **Sonde** : `python -c "import json,statistics as st; d=json.load(open('results/s2_bassin_fragility.json',encoding='utf-8')); R=d['rows']; [print(b, sum(r['S_sign_'+b]-r['S_a']<0 for r in R), st.median([r['S_sign_'+b]-r['S_a'] for r in R]), d['verdict']['par_bras'][b]['sign']['lecture']) for b in ['full','tdonly','const','eplr','zero','tdoff']]"`
* **Constat** : L'interprétation portée par le titre, l.70 et la Leçon l.209-210 (dispositif aveugle à toute dégradation par bruit, donc FRAGILE hors d'atteinte, pré-vol Q1 = NON) est démentie par le JSON de CE run : le sham primaire sign, lui aussi un tirage aléatoire, fait chuter la survie contre S_a sur 12/12 seeds pour full, tdonly, tdoff (médianes -26,25 / -24,5 / -26,0) et 11/12 pour const et eplr, et reste NEUTRE sur zero. L'instrument a donc rendu les deux issues ; seul le gaussien diffus plein support (pos, qui touche aussi les colonnes 77-78) a manqué d'un seed. Ériger l'échec d'UN contrôle en propriété de l'instrument ne tient pas ; le record porte lui-même la contradiction (l.113-114 : sign érode presque autant que le crédit). Et il tait la valeur des lectures bloquées : verdict.par_bras.<bras>.sign.lecture = FRAGILE sur 5 bras sur 6 (INOFFENSIF sur zero), si bien que la question n'est pas symétriquement ouverte. Le verdict mécanique INDETERMINE_INSTRUMENT reste, lui, conforme à la branche 7 scellée.
* **Preuve** : sortie : full 12/12 med -26.25 FRAGILE ; tdonly 12/12 -24.5 FRAGILE ; const 11/12 -10.75 FRAGILE ; eplr 11/12 -14.5 FRAGILE ; zero 7/12 -0.5 INOFFENSIF ; tdoff 12/12 -26.0 FRAGILE — opposés à record:70 et :209-210 (titre :4) ; grep -n FRAGILE du record = lignes 4, 57, 70, 131 seulement, aucune ne publie la lecture FRAGILE des bras.
* **Classe** : E9
* **Verdict** : confirmé

### P1.b
* **Sonde** : `python -c "import json,statistics as st; d=json.load(open('results/s2_bassin_fragility.json',encoding='utf-8')); df=[r['S_pos']-r['S_a'] for r in d['rows']]; print(sum(x<0 for x in df), sum(x==0 for x in df), st.median(df), d['verdict']['thresholds']['sign_min'], d['verdict']['controles']['pos'])"`
* **Constat** : La prémisse qui porte le verdict MÉCANIQUE (pos non ERODE : 10 négatifs < seuil 11, médiane -8,75) est bien mesurée dans CE run, contre le no-op du même run (noop_identical vrai sur 12 seeds), au seuil publié par le JSON (sign_min 11) identique à la branche 7 de la règle scellée ; aucun ex aequo. S_c est hérité de P4.4 mais n'entre pas dans la branche 7. Remarque sans effet sur le verdict : 2 des 10 négatifs (2027 -4,0 ; 2031 -3,0) sont dans la bande de tirage de pos publiée (bande_vs_S_a 4,5), que le record ne cite pas ; la corriger ne ferait que baisser le compte.
* **Preuve** : sortie : neg 10, zero 0, médiane -8.75, sign_min 11, pos = {classe NEUTRE, négatifs 10/12, bande_vs_S_a 4.5} ; règle docs/preregistrations/S2-BASSIN-FRAGILITY.json /rule/discrimination/7 : ERODE = < 0 sur >= 11/12 ET médiane <= -5.
* **Classe** : aucune
* **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — Régime

### P2.a
* **Sonde** : `python tools/check_regime_claims.py --only docs/EDR/S2-BASSIN-FRAGILITY_The_Positive_Control_Of_FRAGILE_Misses_By_One_Seed_The_Instrument_Cannot_Return_FRAGILE.md` ; puis python -c qui appelle c.claims / c.cited_results / c.evaluer sur ce texte
* **Constat** : Porte 19 : OK, rc 0 ; le record sort SANS_PARAMETRE (claims() n'extrait aucune paire paramètre=valeur, donc rien à confronter aux cinq results cités). Verdict recopié, enquête non rouverte.
* **Preuve** : sortie : 'OK : 64 record(s) sans regime concordant [...] Aucun nouveau, aucune regression.' rc=0 ; evaluer -> statut=SANS_PARAMETRE, params={}, claims={}, 5 chemins results/s2_bassin_fragility*.json cités ; retour SANS_PARAMETRE à tools/check_regime_claims.py:257.
* **Classe** : aucune
* **Verdict** : non confirmé

### P2.b — note de cécité, pas une critique
* **Sonde** : `grep -n '_CLAIM = re.compile' tools/check_regime_claims.py` ; `grep -n '200 ticks'` sur le record
* **Constat** : SANS_PARAMETRE signifie seulement qu'aucune forme 'nom = nombre' n'a été trouvée : le motif de la porte exige le signe égal, alors que ce record énonce ses durées et effectifs sous la forme 'nombre puis nom' (phase 1 à 2000, phase 2 à 200, cohortes de 12). Si cette cécité doit être traitée, c'est une dette de la porte au backlog (règle REF l.32-33), pas une critique du record.
* **Preuve** : tools/check_regime_claims.py:97 (motif PARAMS + `\s*=\s*` + nombre) contre record:42 (durée de phase 2 écrite sans '=') ; claims() rend {} sur ce texte.
* **Classe** : aucune
* **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas

* **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py` ; puis `python tools/check_e19_optimizer_sweep.py --report | grep -n -i bassin`
* **Constat** : La porte 23 range le runner scellé de P4.18 dans la classe couvert et ne bloque rien : aucun défaut E19 de sa compétence. Verdict recopié, enquête non rouverte ; la question de la référence à pas nul du même dispositif relève de P5.
* **Preuve** : --only : rc=0, sortie 'OK : aucun nouveau runner sous gradient sans garde E19, aucune regression, aucune perte d'appelant' (34 scellés, 12 sous gradient, 3 appelants de la garde) ; --report ligne 14 : '[couvert] tools/evo_runs/s2_bassin_fragility.py : S2-BASSIN-FRAGILITY : clause_E19 declaree'.
* **Classe** : E19
* **Verdict** : non confirmé

## P4 (JUGE) — famille de contrôles

### P4.a — taille réelle de la famille
* **Sonde** : `python tools/check_control_family.py --report` ; lecture de tools/evo_runs/s2_bassin_fragility.py:792-910 ; python -c qui lit verdict.famille et rows dans results/s2_bassin_fragility.json
* **Constat** : Le nombre de cellules lues par fragility_verdict égale le nombre déclaré : contrôle pos (1), eps en 9a (1), 9b (1), classe du sham sign par bras (6), puis par bras UN seul des deux contrastes sham − greffe, MOINS ou PLUS selon la classe de la greffe (6), soit 15. Le runner (FAMILLE=15), la règle scellée (seuils.famille=15) et le JSON (verdict.famille=15) concordent. iso, sign_commun, x2/x4 et les bandes sont marqués hors_famille dans le code. La porte 11 ne signale rien. Côté dispositif : 167 phases 2 par seed × 12 = 2004, le compte que le record donne pour le vote social.
* **Preuve** : porte 11 : 32 runners scellés, 0 sans design, rc 0 ; s2_bassin_fragility.py:86 FAMILLE = 15, :829-857 (sign lu, iso passé en lecture_hors_famille à :866) ; JSON famille 15, 12 lignes ; design.cost_estimate donne 167 phases 2 par seed.
* **Classe** : aucune
* **Verdict** : non confirmé — aucun écart entre le compté et le déclaré

### P4.b — exclusion des 6 classes de greffe
* **Sonde** : python -c qui compare r['S_tr_<bras>'] à tools.evo_runs.s2_bassin_fragility.published(bras, seed)['S'] et S_a à published('a_frozen')
* **Constat** : La famille laisse dehors les classes des six greffes, au motif qu'elles répliquent un résultat déjà publié. Si ce n'était pas le cas, la famille compterait 21 cellules, et 11/12 (queue 0,00317) dépasserait 0,05/21 = 0,00238 : le seuil tomberait. J'ai rejoué la comparaison contre les JSON sources suivis : S_tr et S_a sont identiques au publié, seed par seed. L'exclusion tient.
* **Preuve** : S_tr égal au publié sur 72/72 (seed, bras), S_a sur 12/12, repl_* et transplant_ok_* vrais partout.
* **Classe** : aucune
* **Verdict** : non confirmé

### P4.c — le seuil du contrôle positif est-il hérité ?
* **Sonde** : python -c avec math.comb : queues P(X>=k | 12, 1/2) et P(X>=11 | 12, p=10/12)
* **Constat** : Le 11/12 qui décide la branche 7 vient de la correction de Bonferroni de CETTE famille. Il n'est pas importé d'un autre dispositif. Le verdict ne dépend pas de la façon dont la famille est comptée : retirer pos (14 cellules, alpha 0,00357) laisse l'exigence à 11/12, et 10/12 (queue 0,0193) ne passerait qu'avec une famille de 2 cellules ou moins (0,05/3 = 0,0167). Chiffre que le record ne donne pas : avec une probabilité de 10/12 par seed (l'effet observé), pos franchit 11/12 environ 38 fois sur 100. Le contrôle avait plus de chances d'échouer que de passer.
* **Preuve** : q11 = 0,003174 ; q10 = 0,019287 ; 0,05/15 = 0,003333 ; 0,05/14 = 0,003571 ; 0,05/3 = 0,016667 ; puissance au p observé = 0,381.
* **Classe** : aucune
* **Verdict** : non confirmé — l'inférence du record tient ; la puissance chiffrée relève de P5

### P4.d — δmin hérité, provenance absente du record
* **Sonde** : `grep -n -i 'hérit' <record>` (motif validé sur un cas positif, la ligne 107) ; `grep -n 'δmin' <record>` ; `grep -c 'HÉRITÉ de P4.4' docs/preregistrations/S2-BASSIN-FRAGILITY.json` ; python -c qui recalcule c/S_tr et δmin/S_tr depuis les lignes du JSON
* **Constat** : La règle scellée dit que δmin = 5 ticks vient de P4.4, où il valait environ 15 % du bassin. Le record emploie δmin quatre fois sans jamais dire d'où il vient : le seul héritage qu'il nomme est celui de S_c. Pour pos, l'échelle est la bonne (5/36 = 14 % de S_a) et le verdict n'est pas touché. Mais l'hypothèse descriptive s'appuie sur ce seuil pour dire que le sham érode presque autant que la greffe. Or, sur les bras au plancher, δmin vaut 59 à 67 % de la survie sous greffe. Et sur full, tdonly et tdoff, le sham survit 31 à 47 % plus longtemps que la greffe, sur 12 seeds sur 12. En perte rapportée à S_a, en revanche, le sham reproduit 86 à 89 % de celle de la greffe. Le lecteur ne peut pas arbitrer entre les deux lectures s'il ignore que la marge est importée d'une autre échelle.
* **Preuve** : record:107, seule occurrence de « hérit » (S_c) ; δmin aux lignes 47, 68, 115 et 206 sans provenance ; la règle (seuils_note) contient 1 fois « HÉRITÉ de P4.4 » ; c/S_tr : full 0,31, tdonly 0,41, tdoff 0,47, eplr 0,21 ; δmin/S_tr : 0,62, 0,59, 0,67, 0,29 ; c > 0 sur 12/12 pour ces quatre bras.
* **Classe** : aucune
* **Verdict** : confirmé — mineur : le verdict scellé n'est pas touché ; l'hypothèse hors famille, elle, se lit à travers une marge importée sans le dire

### P4.e — seuils comparés en flottants (E30)
* **Sonde** : `python tools/check_grid_threshold.py --only tools/evo_runs/s2_bassin_fragility.py` ; python -c qui vérifie que v*4 est entier pour les 84 contrastes pos − a et sign − tr
* **Constat** : Les comparaisons à δmin portent sur des médianes de demi-ticks, qui tombent toutes sur une grille de pas 0,25, représentable exactement en float64. La perte d'égalité qui définit E30 ne peut donc pas se produire ici. La porte 24 ne voit aucun site nouveau.
* **Preuve** : porte 24 : 0 site nouveau, rc 0 ; 84/84 contrastes multiples de 0,25.
* **Classe** : E30
* **Verdict** : non confirmé

### P4.f — observation en passant (relève de P9 / porte 20)
* **Sonde** : `git ls-files results/ | grep bassin` ; `git status --short docs/EDR/`
* **Constat** : Aux lignes 224 à 226, le record annonce SUIVIS l'agrégat, l'agrégat de la coupe 1 et le témoin de lieu. Dans ce worktree, aucun des trois n'est dans l'index, pas plus que le record lui-même. Tant que ce n'est pas corrigé, un clone ne peut pas rouvrir le verdict.
* **Preuve** : git ls-files ne rend que s2_bassin_fragility_calibration_bande.json et s2_bassin_fragility_sonde_conception.json ; le record est en ?? (non suivi).
* **Classe** : E27
* **Verdict** : hors périmètre — à trancher par P9 (check_evidence_provenance), qui juge l'index au moment du commit

## P5 — le contrôle positif

### P5.a
* **Sonde** : `python -c "import json;d=json.load(open('results/s2_bassin_fragility.json',encoding='utf-8'));v=d['verdict'];print(v['controles']['pos']);[print(k,b['sign']['classe_vs_S_a'],b['sign']['negatifs_vs_S_a'],b['sign']['mediane_vs_S_a'],v['secondaire_iso'][k]['classe_vs_S_a'],v['secondaire_iso'][k]['negatifs_vs_S_a'],v['secondaire_iso'][k]['mediane_vs_S_a']) for k,b in v['par_bras'].items()]"` ; `sed -n 517p,536p tools/evo_runs/s2_bassin_fragility.py`
* **Constat** : Le contrôle pos ne sonde pas la perturbation que lit FRAGILE. C'est un gaussien étalé sur toutes les coordonnées de W, alors que le bras lu est un tirage de signes restreint au support de ΔW. Le même JSON montre que le gaussien est la géométrie qui érode le moins (iso, à la dose des bras : médiane 0,0 et 1 à 4 seeds négatifs sur les six bras). Le tirage de signes, lui, érode sous le critère scellé sur cinq bras (12/12 pour full, tdonly et tdoff ; 11/12 pour const et eplr). Le dispositif détecte donc une érosion causée par une perturbation. L'échec de pos mesure la faiblesse d'un bruit diffus, pas une cécité de l'instrument. Le titre, la raison du verdict reprise l.69-70 et la Leçon 1 (qui ne met en cause que la puissance) tirent sur l'instrument une conclusion que ses propres lignes réfutent. Le défaut porte sur le RÉGIME (support et géométrie) : calibrer seulement la puissance de pos dans la règle suivante laisserait le contrôle hors du régime qu'il protège.
* **Preuve** : tools/evo_runs/s2_bassin_fragility.py:536 (pos = sham_delta(zero + 1.0, 'iso', ...) : support plein) contre :517 (sign tiré sur dW). Sortie : pos NEUTRE 10/12, -8,75. Sign contre S_a : full ERODE 12/12 -26,25 ; tdonly 12/12 -24,5 ; const 11/12 -10,75 ; eplr 11/12 -14,5 ; tdoff 12/12 -26,0. Iso : NEUTRE sur les six bras, 1/12 à 4/12, médiane 0,0.
* **Classe** : E6
* **Verdict** : confirmé

### P5.b
* **Sonde** : `python -c "import json,copy;from tools.evo_runs.s2_bassin_fragility import fragility_verdict as f;rows=json.load(open('results/s2_bassin_fragility.json',encoding='utf-8'))['rows'];print(f(rows)['verdict']);r2=copy.deepcopy(rows);[r.__setitem__('S_pos',r['S_a']-5.0) for r in r2 if r['seed'] in (2036,2037)];v=f(r2);print(v['verdict'],v.get('lecture_globale'),{k:b['sign']['lecture'] for k,b in v['par_bras'].items()})"`
* **Constat** : Le bras testé pouvait réussir, et il a réussi : un seul seed de pos sépare ce run d'un verdict scellé FRAGILE. J'ai rejoué la fonction scellée sur les lignes publiées (par injection, sans aucun monde). Elle rend INDETERMINE_INSTRUMENT à l'identique et franchit déjà 9b (eps moins érodé que la greffe complète sur 12/12). Si je force seulement 2036 et 2037 à S_a - 5 pour pos, elle rend LU / FRAGILE : FRAGILE sur cinq bras, INOFFENSIF sur b_zero. Le record déclare l'issue impossible à obtenir et classe les lectures par bras en non lu sans publier leur valeur. Le lecteur ne peut donc pas savoir que l'issue bloquée est exactement celle que protégeait le contrôle défaillant. Il n'est pas question d'autoriser une lecture (la règle s'arrête à la branche 7). Mais le mot inatteignable décrit la porte, pas les données, et cette donnée conditionne la conception de la règle neuve.
* **Preuve** : Sortie : « INDETERMINE_INSTRUMENT | eps moins True 12/12 », puis « LU FRAGILE | full FRAGILE, tdonly FRAGILE, const FRAGILE, eplr FRAGILE, zero INOFFENSIF, tdoff FRAGILE ». Le record, l.131, met non lu en face de FRAGILE.
* **Classe** : E2 (invoquée à tort : l'issue est déclarée inatteignable alors que le bras l'atteint sous la fonction scellée)
* **Verdict** : confirmé

### P5.c
* **Sonde** : `python -c "import json;d=json.load(open('results/s2_bassin_fragility.json',encoding='utf-8'));l1=2442.805;rs=[l1/r['net_'+k] for r in d['rows'] for k in ('full','tdonly','const','eplr','zero','tdoff')];print(min(rs),max(rs))"` ; recherche de 718 dans docs/preregistrations/S2-BASSIN-FRAGILITY.json
* **Constat** : Le rapport d'amplitude entre le contrôle et les bras (l.85 et l.205) est une estimation de conception recopiée de la règle (revue P5.b), pas une mesure de ce run. Recalculé depuis le JSON, avec ‖W_bassin‖₁ = 2442,8 : il va de 25,5 à 826,7 sur les médianes par bras, et de 21,5 à 1018,1 par seed et par bras. L'ordre de grandeur ne change pas. Mais la distance au régime testé est présentée comme mesurée alors qu'elle ne l'est pas.
* **Preuve** : Sortie : min 21,5, max 1018,1 (par seed et par bras) ; 25,5 à 826,7 sur les médianes. La pré-inscription contient « 24 à 718 fois le déplacement des bras (revue P5.b) », donc un chiffre antérieur au sceau, contre 21,5-1018,1 mesuré.
* **Classe** : E8
* **Verdict** : confirmé

### P5.d
* **Sonde** : python -c (load_bassin, puis l1_per_agent_median des 60 tirages controls/pos divisé par ‖W0‖₁)
* **Constat** : J'ai vérifié la dose réelle de pos : L1 par agent égale à ‖W_bassin‖₁ sur les 60 tirages (ratio 1,0000 partout). Le contrôle a bien reçu la dose annoncée : aucun défaut de dose.
* **Preuve** : Sortie : « pos l1/agent / l1_W0 : min 1.0000 max 1.0000 n 60 ».
* **Classe** : aucune
* **Verdict** : non confirmé

### P5.e
* **Sonde** : `git status --porcelain -- results/s2_bassin_fragility.json` ; `git ls-files --error-unmatch results/s2_bassin_fragility.json`
* **Constat** : Le record (l.224) dit l'agrégat SUIVI, mais dans ce worktree le JSON et le record sont tous deux hors index. C'est une question de provenance, déléguée à la porte 20 (P9), qui n'est pas du ressort de P5.
* **Preuve** : Sortie : « ?? results/s2_bassin_fragility.json » et « Did you forget to 'git add'? ».
* **Classe** : E27
* **Verdict** : hors périmètre

## P6 — plancher de bruit

### P6.a
* **Sonde** : `python -c "import json;v=json.load(open('results/s2_bassin_fragility.json'))['verdict'];[print(k,b['sign']['contraste_vs_transplant_mediane'],round(b['sign']['bande_contraste'],3),b['sign']['dans_la_bande']) for k,b in v['par_bras'].items()]"` ; `grep -c bande docs/EDR/S2-BASSIN-FRAGILITY_*.md`
* **Constat** : Les contrastes descriptifs signe-moins-greffe sont publiés sans le plancher de tirage que le JSON calcule pour chacun d'eux. Trois des six (const, eplr, zero) restent sous leur bande, donc ne se distinguent pas de zéro ; eplr passe à 0,006 tick près bien que 12/12 seeds soient positifs. La fourchette de +2,5 à +3,5 que l'hypothèse hors famille attribue à cinq bras mêle ainsi deux contrastes hors bande avec deux autres dedans. La cause est mécanique : le runner n'ajoute la mention de bande qu'au chemin de lecture LU, que la branche 7 a coupé, et le record a recalculé ses médianes depuis les lignes, sans la bande.
* **Preuve** : Sortie : full 2,5 / bande 1,5 / hors ; tdonly 3,5 / 1,75 / hors ; const 2,5 / 3,75 / DEDANS ; eplr 3,5 / 3,506 / DEDANS ; zero 1,25 / 1,75 / DEDANS ; tdoff 3,5 / 1,25 / hors. Le record contient 2 occurrences de « bande », aux lignes 207 et 227, et aucune ne porte sur ces contrastes (tableau record:100-105, hypothèse record:113-116). Mention réservée au chemin LU : tools/evo_runs/s2_bassin_fragility.py:1045.
* **Classe** : E10
* **Verdict** : confirmé

### P6.b
* **Sonde** : `python -c "import json;print(json.load(open('results/s2_bassin_fragility.json'))['verdict']['controles']['pos'])"` ; `grep -n bande docs/EDR/S2-BASSIN-FRAGILITY_*.md`
* **Constat** : Le contraste qui porte le verdict (pos contre S_a) a lui aussi une bande dans le JSON, et le record ne la publie pas. Elle vaut 4,5 ticks, et la médiane de −8,75 en sort presque du double. L'érosion médiane dépasse donc le bruit de tirage : l'échec de pos tient au seul compte de signes (10/12), pas au bruit. La règle de dépôt veut que ce chiffre figure à côté du ratio.
* **Preuve** : Le JSON rend {'classe':'NEUTRE','mediane':-8.75,'negatifs':'10/12','bande_vs_S_a':4.5,'dans_la_bande_vs_S_a':False}. Les lignes record:57-71 et record:128 ne donnent pas cette bande ; grep bande ne ressort qu'aux lignes 207 et 227.
* **Classe** : E10
* **Verdict** : confirmé

### P6.c
* **Sonde** : `python -c "import json,numpy as np;from tools.evo_runs.s2_bassin_fragility import _bande_contraste as B;R={int(r['seed']):r for r in json.load(open('results/s2_bassin_fragility.json'))['rows']};[print(s,float(np.median(R[s]['S_pos_draws']))-R[s]['S_a'],B([R[s]['S_pos_draws']],[R[s]['S_a']])) for s in (2036,2037,2026)]"`
* **Constat** : L'argument (ii) contre le plancher lit comme une hausse, sur les deux seeds où S_a est le plus bas, un écart qui reste dans le bruit des cinq perturbations de chaque seed. Avec la bande propre au seed (même fonction, un seul seed), +6,5 et +5,5 ne se distinguent pas de zéro. Même le −9,5 du seed 2026 tombe dans sa bande de 9,5. Un signe lu seed par seed ne peut donc départager ni plancher ni resserrement.
* **Preuve** : Sortie : 2036 contraste +6,5 contre bande 7,5 (dedans) ; 2037 +5,5 contre 8,0 (dedans) ; 2026 −9,5 contre 9,5 (dedans). L'affirmation « il la MONTE » est à record:75-76.
* **Classe** : E9
* **Verdict** : confirmé

### P6.d
* **Sonde** : `python -c "import json;c=json.load(open('results/s2_bassin_fragility_calibration_bande.json'));t=[v['taux'] for k,d in c['couverture'].items() if k.startswith('echangeable') for v in d.values()];print(sum(x<0.975 for x in t),len(t),min(t))"`
* **Constat** : Le record renvoie à la calibration de la bande comme à une chose acquise, sans donner ses chiffres. Or la bande appliquée (bootstrap échangeable, q = 0,975) couvre moins que son quantile nominal dans 8 des 10 régimes mesurés, jusqu'à 0,926. Elle est donc un peu trop étroite : on la franchit à tort 4 à 7 % du temps au lieu de 2,5 %. Cela ne change pas pos, dont la marge est de 8,75 contre 4,5, mais aucune lecture « hors bande » ne le mentionne.
* **Preuve** : Sortie : 8 10 0.926, pour q = 0,975 (regime.bande du JSON). La calibration est citée sans chiffre à record:207-208.
* **Classe** : aucune
* **Verdict** : confirmé

### P6.e
* **Sonde** : `grep -n "sham_rng(" tools/evo_runs/s2_bassin_fragility.py` ; `sed -n 125,128p tools/evo_runs/s2_bassin_fragility.py`
* **Constat** : Question : le no-op est-il bien celui de CE contraste, c'est-à-dire le tirage gaussien de pos pourrait-il désynchroniser la bande RNG du monde, comme run_ablation_map ? Écarté par lecture du code : eps et pos tirent d'un flux privé SeedSequence, jamais de l'état global, et eps rend S_a au bit sur 12/12 seeds.
* **Preuve** : tools/evo_runs/s2_bassin_fragility.py:128 construit default_rng(SeedSequence([SHAM_ENTROPY,...])) ; pos l'utilise en :536 ; seeds_eps_egal_noop vaut 12/12 dans le JSON.
* **Classe** : aucune
* **Verdict** : non confirmé

### P6.f
* **Sonde** : `git status --porcelain -- docs/EDR/S2-BASSIN-FRAGILITY* results/s2_bassin_fragility*.json`
* **Constat** : Relevé en passant, hors du périmètre de P6 (cela relève de P9 et de la porte 20) : trois JSON d'évidence sont déclarés SUIVIS alors que git ne les voit pas, pas plus que le record lui-même. Ce sera à régler dans le même commit que la citation.
* **Preuve** : La sortie marque ?? le record, results/s2_bassin_fragility.json, _coupe1.json et _temoin_lieu.json, qui sont déclarés SUIVIS à record:224-226.
* **Classe** : E27
* **Verdict** : hors périmètre

## P7 (JUGE) — dose

### P7.a — les mises à jour reçues sont-elles comptées, et un nul serait-il un nul de létalité ?
* **Sonde** : `python -c "import json;c=json.load(open('results/s2_bassin_fragility.json'))['cells'];[print(a,{c[s]['arms'][a]['learning']['td_updates'] for s in c},{c[s]['arms'][a]['learning']['episode_updates'] for s in c},[c[s]['arms'][a]['learning']['resurrections'] for s in sorted(c)]) for a in c['2026']['arms']]"`
* **Constat** : Le JSON chiffre bien la dose pour chaque bras et chaque graine : 1999 mises à jour TD ou zéro, 250 épisodiques ou zéro, sur 2000 ticks. Ces comptes ne varient pas d'une graine à l'autre, alors que les morts de phase 1 vont de 2 à 380. La cohorte immortelle sépare donc la quantité d'apprentissage de la létalité. Un nul de b_zero, s'il était lu, viendrait d'un signal de récompense coupé (reward_scale 0,0), à dose égale à celle de b_full, et non d'une dose tronquée. Le texte ne donne pas ces comptes : il n'emploie le mot « dose » que comme critère de rejeu au bit.
* **Preuve** : Sortie : b_full {1999} {250}, b_tdonly {1999} {0}, b_eplr {0} {250}, b_zero {1999} {250}, morts de b_zero 5 à 380, ticks {2000} partout. Dans le record, « dose » n'apparaît qu'aux lignes 41 et 198 (grep).
* **Classe** : aucune
* **Verdict** : non confirmé

### P7.b — la cohorte est-elle constante ? Morts de phase 1 et brassage (P2.132) selon le bras
* **Sonde** : `python <scratchpad>/p7_dose.py` (lit results/s2_bassin_fragility.json -> rows, calcule les rangs de Spearman et compte n_agents) ; `grep -n -iE 'résurrection|corrél'` sur le record, motif validé par sa correspondance ligne 78
* **Constat** : Le nombre de corps reste à 12 par construction, mais leur appariement avec les slots de W change à chaque mort. Or le nombre médian de morts en phase 1 va de 3,5 (b_tdoff) à 179 (b_zero), soit un facteur 51, et de 5 à 380 à l'intérieur de b_zero. Le brassage contenu dans chaque ΔW dépend donc fortement du bras. Le seul bras dont la greffe n'érode pas est aussi le plus brassé. Entre bras, l'érosion suit le nombre de morts presque exactement (rang 0,943 sur 6 points), plus fidèlement que l'amplitude nette (−0,771). Sur les 72 points, les deux se valent (0,609 contre −0,652) : c'est une confusion, pas une cause. Le texte donne la colonne des morts mais ne relève jamais qu'elle est rangée comme l'effet comparé. Le JSON ne publie ni n_agents ni de profil par bloc : impossible de dater le brassage. Aucun effet sur la branche 7, puisque pos et S_a n'utilisent pas ΔW. La portée se limite à l'hypothèse descriptive des lignes 113-122.
* **Preuve** : Sortie : médianes des morts 10/8/65,5/16,5/179/3,5 ; rapport max/min 51,14 ; ρ inter-bras (morts, S_tr−S_a) = 0,943 ; ρ (net, S_tr−S_a) = −0,771 ; ρ sur 72 points 0,609 contre −0,652 ; 0 occurrence de n_agents, 0 de bloc. Dans le record, « résurrection » n'apparaît qu'aux lignes 15 et 98, « corrél » qu'aux lignes 78-79, qui portent sur pos.
* **Classe** : E15
* **Verdict** : confirmé (portée limitée à la section descriptive hors verdict ; ne touche pas INDETERMINE_INSTRUMENT)

### P7.c — la dose en amplitude : le pas effectivement appliqué à chaque agent est-il publié pour chaque apprenant ?
* **Sonde** : `grep -n 'optim.SGD\|loss = -(R \* total_logp).mean()' src/agents/backend_torch.py` ; `python -c "import json;c=json.load(open('results/s2_bassin_fragility.json'))['cells'];[print(a,sum(c[s]['arms'][a]['learning']['lr_effective_per_agent'] is None for s in c),{tuple(c[s]['arms'][a]['learning']['pas_optimiseur_mesure']) for s in c}) for a in ('b_eplr','b_tdoff')]"`
* **Constat** : La mise à jour épisodique passe par le même SGD que la TD, avec une perte moyennée sur B. Chaque agent reçoit donc lr/B sur cette voie aussi. Pour les deux bras sans TD (b_eplr, b_tdoff), le bloc learning laisse pourtant lr_effective_per_agent et son unité à None sur les 12 graines. Seul le pas nominal de l'optimiseur est publié (0,004 et 0,04). Les pas réels par agent valent 0,00033 et 0,0033. Le runner connaît cette lacune (docstring ligne 306) et le record ne cite aucun pas effectif. Le rapport entre les deux bras reste de 10 : la garde E19 déclarée illisible n'en est pas faussée. Mais ce champ, que la garde lr/B exige dans tout bloc learning, manque sur un tiers des bras.
* **Preuve** : src/agents/backend_torch.py:141 (torch.optim.SGD) et :502 (perte REINFORCE .mean() sur B) ; tools/evo_runs/s2_bassin_fragility.py:306 ; sortie : b_eplr None sur 12/12, pas {(0.004,)} ; b_tdoff None sur 12/12, pas {(0.04,)}.
* **Classe** : E19
* **Verdict** : confirmé (défaut de publication mineur, sans effet sur le verdict)

### P7.d — le nul qui porte le verdict (pos NEUTRE, 10/12) est-il un nul d'apprentissage ou de létalité ?
* **Sonde** : `python -c "import json;s=json.load(open('results/s2_bassin_fragility.json'))['cells']['2036'];print(s['controls']['pos']['draws'][:400]);print(s['noop']['reconstructions'])"`
* **Constat** : Le verdict repose sur pos : un bruit appliqué à W_bassin, puis une phase 2 mortelle à poids gelés. Aucun apprenant n'intervient, donc la question de la dose ne s'y pose pas. La cohorte de phase 2 est reconstruite à chaque mort, et ce comptage est publié tirage par tirage (B de 12 à 1, zéro censuré au seed 2036). Le puits de létalité est donc visible, et il est le même pour pos et pour le no-op.
* **Preuve** : Sortie : tirage pos S 25,0, ages de 6 à 61, censored 0, reconstructions B [12, 11, …, 1] ; no-op reconstructions B [12, 11, 10, 9, 7, …, 1].
* **Classe** : aucune
* **Verdict** : hors périmètre

### P7.e — hors dose, vu en passant : l'évidence que le texte annonce SUIVIE
* **Sonde** : `git status --short results/s2_bassin_fragility.json results/s2_bassin_fragility_coupe1.json results/s2_bassin_fragility_temoin_lieu.json` ; `grep -c E34 docs/REF/REGISTRE_ERREURS.md`
* **Constat** : La section Évidence déclare suivis trois agrégats que git ne suit pas encore à ce HEAD. De même, le bandeau cite une classe E34 absente du registre de ce worktree : zéro occurrence, alors que la classe E33 y figure bien (motif validé). Ces deux points relèvent de P9 (porte 20) et de P10, pas de P7. À vérifier au commit, qui doit emporter le record et ses artefacts ensemble.
* **Preuve** : Les trois fichiers ressortent en « ?? » (non suivis) ; grep -c E34 rend 0. Lignes 224-226 du record contre git status.
* **Classe** : E27
* **Verdict** : hors périmètre

## P8 (JUGE) — corps, aliasing, chevauchement

### P8.a — dose réelle du contrôle positif pos
* **Sonde** : python -c : m.sham_delta(zero+1.0,'iso',m.sham_rng(seed,None,'pos',r),l1_target=POS_REL*l1_W0) puis m.delta_structure, seeds 2026 et 2036, r=0..4 ; lecture de src/agents/backend_torch.py:155-210 et :113-128 ; lecture JSON cells/*/arms/b_full/structure et cells/*/controls/pos (clés)
* **Constat** : Environ un tiers du bruit de pos tombe dans des poids qui ne touchent jamais la politique : les colonnes qui alimentent les 59 nœuds d'entrée. L'état de ces nœuds est remplacé par l'observation au pas suivant, avant toute lecture (les logits ne lisent que les nœuds 64-171, et le gate ne dépend pas de H puisque w_gate vaut zéro). La dose qui agit vaut donc environ 0,66 fois la L1 du bassin, pas 1,0, alors que les bras de crédit ne mettent RIEN dans ces colonnes (part 0,0). La leçon (1) compare une dose en partie morte à une dose entièrement active. Le runner publie la structure du déplacement pour chaque bras, mais pas pour pos (sa L1 seulement), donc le JSON ne permet pas de voir cette part inerte. Le verdict INDETERMINE_INSTRUMENT n'est pas renversé. En revanche, la règle suivante doit calibrer la puissance de son contrôle positif sur la dose ACTIVE.
* **Preuve** : backend_torch.py:159 H[:, :self.I] = obs_t ; :200 logits = H_new[:, N-O:N] ; input_cols_share(pos) = 0,3422 à 0,3437 sur 10 tirages (W_bassin lui-même : 0,332) ; b_full input_cols_share médiane 0,0 ; s2_bassin_fragility.py:505 publie structure pour les bras, :536-540 n'en publie pas pour pos (clés pos : rel_l1, draws, S).
* **Classe** : E8
* **Verdict** : confirmé

### P8.b — chevauchement entrée/sortie (E24)
* **Sonde** : `python tools/check_io_overlap.py` ; python -c sur les 72 .npz (num_inputs + num_outputs − W_final.shape[-1])
* **Constat** : Aucun chevauchement dans les génomes du run (59 entrées et 108 sorties sur 172 nœuds, marge de 5). Mais le « OK » de la porte 17 ne couvre pas ce record : elle balaie data/genomes et les Hall of Fame (358 sujets), jamais results/s2_bassin_fragility_genomes/. C'est ma mesure directe qui écarte E24, pas la porte.
* **Preuve** : porte : 358 génomes, 10 chevauchants connus, rc 0 ; 72/72 .npz : chevauchement = −5 (min = max) ; check_io_overlap.py:51 root = genomes().
* **Classe** : E32 (périmètre de la porte, pas le record)
* **Verdict** : non confirmé

### P8.c — corps dérivé de W[0:10] (E26)
* **Sonde** : delta_structure (body_rows_share) sur pos et lecture JSON b_full ; `grep -n update_phenotype tests/sandbox/test_s2_bassin_fragility.py`
* **Constat** : pos place 5,8 % de sa L1 sur les lignes du corps (b_full 3,4 %). Le corps n'est jamais recalculé et reste celui du bassin dans toutes les conditions : il est vérifié avant et après chaque phase 2, et un témoin gelé lève sur un recalcul. Aucune contamination du corps.
* **Preuve** : body_rows_share pos 0,0578-0,0583 contre b_full 0,034 ; s2_bassin_fragility.py:228 et :231 (_assert_body_is_bassin) ; test_s2_bassin_fragility.py:438.
* **Classe** : E26
* **Verdict** : non confirmé

### P8.d — aliasing / vue de l'état récurrent (E5)
* **Sonde** : Read s2_bassin_fragility.py:226-227 ; Read backend_torch.py:108-109 ; `grep -n 'last_action.*0.1' world_1_stoneage.py`
* **Constat** : Le runner n'ajoute aucun alias : W est copié à la pose, et la population torch copie la pile de génomes. L'écriture du monde dans la vue des logits est déjà déclarée en tête du record. Pour chiffrer son effet par condition, il faudrait une simulation : c'est une dette, pas une critique.
* **Preuve** : s2_bassin_fragility.py:227 np.array(w, copy=True) ; backend_torch.py:109 torch.tensor(W) (copie) ; world_1_stoneage.py:1340 logits[last_action] -= 0.1.
* **Classe** : E5
* **Verdict** : hors périmètre

### P8.e — constat annexe (relève de P1)
* **Sonde** : python -c : médianes de cells/*/arms/{b_full,b_zero}/net_l1_median_agent et de controls/pos/draws/l1_per_agent_median
* **Constat** : Le facteur « 24 à 718 » de la leçon reprend les mesures de pré-scellement du seul seed 2026 (nets 100,5 et 3,4). Les médianes des 12 seeds que le record publie lui-même (95,78 et 2,95) donnent 25,5 à 826,7, et 16,8 à 543,1 sur la dose active.
* **Preuve** : pos 2442,8 par agent ; 2442,8/95,78 = 25,5 ; 2442,8/2,95 = 826,7 ; règle : full 100,5 et zero 3,4 (pré-scellement).
* **Classe** : E8
* **Verdict** : hors périmètre

## P9 (DÉLÉGUÉ) — Provenance

### P9.a — le results/ cité existe-t-il et est-il suivi ?
* **Sonde** : `python tools/check_evidence_provenance.py --only docs/EDR/S2-BASSIN-FRAGILITY_The_Positive_Control_Of_FRAGILE_Misses_By_One_Seed_The_Instrument_Cannot_Return_FRAGILE.md ; echo rc=$?` (HEAD afa4dac6, branche tmp/science-prep)
* **Constat** : La porte 20 rend ECHEC, code 1. Elle classe non_suivi (cause E27, nouvelle ou régressée hors baseline) les trois agrégats JSON que ce record invoque comme évidence : la reprise, la première tentative coupée et le témoin de lieu. Or la section Évidence les annonce tous trois comme suivis. Un clone ne pourrait donc rouvrir ni le verdict INDETERMINE_INSTRUMENT ni les tableaux recalculés. Verdict de la porte recopié tel quel, enquête non rouverte.
* **Preuve** : Sortie de la porte : 'non suivis : 3', rc=1, '[NOUVEAU/REGRESSE] ... results/s2_bassin_fragility.json [non_suivi], results/s2_bassin_fragility_coupe1.json [non_suivi], results/s2_bassin_fragility_temoin_lieu.json [non_suivi]'. Le record affirme le contraire : record:224-226 (mention SUIVI sur chacun des trois).
* **Classe** : E27
* **Verdict** : confirmé

### P9.b — le sceau de la pré-inscription est-il intact ?
* **Sonde** : `python -c "from tools.preregister import verify; print(verify('S2-BASSIN-FRAGILITY'))"` ; lecture du champ seal de docs/preregistrations/S2-BASSIN-FRAGILITY.json ; `grep -c d29d7934b3a252b10c9e3bb4e6b459d538a9fb30440515db4bc092d183ff5bd4 <record>`
* **Constat** : verify() rend la règle sans lever PreregistrationTampered. Le hash stocké dans la pré-inscription est identique à celui que cite le record. Aucune altération de la règle après le sceau n'est détectée.
* **Preuve** : verify : rc=0, retourne le dict de la règle (tools/preregister.py:199-202 : lève si _seal(rule) != seal). Sceau stocké d29d7934...5bd4 = sceau cité au record (grep -c = 1, record:33).
* **Classe** : aucune
* **Verdict** : non confirmé

## P10 (JUGE) — Mécanisme

### P10.a — référent de l'amplitude de pos
* **Sonde** : `python <scratchpad>/p10_probe.py` ; `PYTHONPATH=. python <scratchpad>/p10_pos.py` (régénération PURE, par sham_rng, des 60 tirages pos, sans aucun monde)
* **Constat** : Le rapport d'amplitude pos/bras, présenté comme la limite du contrôle positif dans le verdict et dans la leçon, ne vient pas de ce run. C'est le chiffre du seul seed 2026 mesuré avant le scellement, repris tel quel de la règle. Sur les 12 seeds (médiane par bras), il va de 25,5 à 826,7. Son référent, la L1 de la matrice W entière, compte aussi les colonnes 0-58, que l'observation réécrit à chaque pas. pos y place 34 % de sa masse, le crédit 0 %. Rapporté à la seule masse qui agit, le rapport descend à environ 17-545.
* **Preuve** : Le record (l.85 et l.205) reprend « 24 à 718 » de la pré-inscription (l.21 et l.27, sonde de conception du seed 2026). Sortie de la sonde : seed 2026 -> 24,3 / 716,4 ; 12 seeds -> 25,5 (b_full, net 95,78) à 826,7 (b_zero, net 2,95). Part de la L1 de pos sur les colonnes 0..58 : 0,341-0,3445. input_cols_share du crédit : 0,0 sur les six bras. backend_torch.py:159 : H[:, :self.I] = obs_t (I=59, N=172, O=108, aucun chevauchement).
* **Classe** : E8
* **Verdict** : confirmé — limite descriptive, la branche 7 n'en dépend pas

### P10.b — où le vote social a tiré
* **Sonde** : `python <scratchpad>/p10_probe.py` (somme par condition de consensus.ticks_avec_reecriture) ; python -c qui imprime le vote de pos par seed et par tirage ; `sed -n 947,976p src/worlds/world_1_stoneage.py`
* **Constat** : Le vote n'a pas été silencieux « presque partout » : il n'a tiré que sous pos, dans 2 phases sur 60 (seed 2030, tirage 2 : 1 tick ; seed 2034, tirage 4 : 3 ticks). Il n'a jamais tiré dans les 1944 autres phases 2. La règle l'avait désigné comme un chemin propre à pos : pos met de la masse sur les nœuds 77-78, qui déclenchent le vote, et ΔW ne les touche pas. Le record ne le relie qu'au biais DIRECTION. Le verdict n'est pas touché : les seeds 2036 et 2037 n'ont aucun vote.
* **Preuve** : Sortie : 2004 phases, 4 ticks, 8 lignes. Par condition : pos [60 phases, 4 ticks], toutes les autres [n, 0]. world_1_stoneage.py:964-966 : le vote se déclenche si logits[13]>0,5 et logits[14]>0, soit les nœuds 77-78. pos verse 1,16 % de sa L1 sur 77-78 (p10_pos.py). Pré-inscription l.21 (revue v7 P8.1), contre record l.110-111.
* **Classe** : E5
* **Verdict** : confirmé — erreur de localisation, sans effet sur la branche 7

### P10.c — affirmations de code de l'en-tête et du dispositif
* **Sonde** : sed/grep sur backend_torch.py, world_1_stoneage.py, s2_credit_retention.py, s2_bassin_fragility.py, cost_guard.py, preregister.py et runs/p418/p418_reprise.py ; `git status --porcelain --untracked-files=no` (0 ligne) ; `git check-ignore -v results/s2_bassin_fragility*.json` (.gitignore:19, négation)
* **Constat** : Relues à la ligne, les affirmations tiennent. forward rend une vue, pas un clone, puisque la porte est coupée. Le monde retranche 0,1 dans cette vue, et le vote écrase toutes les lignes d'une case. Un corps ressuscité revient en fin de liste, sans reconstruction, dès que B retombe à 12. Les définitions sign/iso/pos/eps, le critère ERODE, la marge x3, les 8,0 cœurs et le « sale » de provenance() sont conformes. Même chose pour les refus de la reprise.
* **Preuve** : backend_torch.py:48, :198-200, :210 ; world_1_stoneage.py:1312, :1340, :971-972, :1060-1066 ; s2_credit_retention.py:108-111 ; s2_bassin_fragility.py:151-164, :536, :659-667, :967 ; cost_guard.py:75 (safety=3.0) et :174 (8.0) ; preregister.py:162 ; p418_reprise.py:56-66 ; max match_* = 2,095e-5 (le record annonce 2,1e-5).
* **Classe** : aucune
* **Verdict** : non confirmé

### P10.d — troisième écrivain de l'état H
* **Sonde** : python -c qui compte reconstructions.reconstructions par condition dans results/s2_bassin_fragility.json ; `sed -n 1050,1075p src/worlds/world_1_stoneage.py`
* **Constat** : L'en-tête annonce deux défauts qui écrivent dans l'état. Il en existe un troisième : chaque mort reconstruit la population torch et remet H à zéro pour tous les survivants. Mais il ne sépare pas les deux bras de la branche 7 : médiane de 10 reconstructions sous noop comme sous pos.
* **Preuve** : backend_torch.py:111 (self.H = zeros) ; world_1_stoneage.py:1060-1066 (reconstruction dès que B change) ; sortie : 17 883 reconstructions sur 2004 phases, médiane 10,0 sous noop et 10,0 sous pos.
* **Classe** : E5
* **Verdict** : non confirmé — mécanisme omis, mais pas différentiel entre les bras

---

**Bilan** : 38 critiques, dont 15 confirmées, 15 non confirmées, 8 hors périmètre. Aucune ne renverse le verdict mécanique INDETERMINE_INSTRUMENT (branche 7) ; les confirmées portent sur l'interprétation (titre, Leçons), les planchers non publiés et la provenance (porte 20 en ECHEC).

---

## Addendum de l'auteur (2026-09-28)

**Passage INDISCRIMINANT** : le témoin cru sain (LOCK-002) rend 6 critiques recevables, autant que les défectueux.
Une critique confirmée n'y compte donc qu'une fois RE-MESURÉE par l'auteur. Les quinze l'ont été, par des sondes qui
ne construisent aucun monde : lecture de `results/s2_bassin_fragility.json`, fonctions pures du runner scellé
(`fragility_verdict`, `_bande_contraste`, `sham_delta`, `delta_structure`), recomptage du vote social par condition.
**Les quinze sont retenues** ; aucune ne touche le verdict mécanique INDETERMINE_INSTRUMENT (branche 7), toutes
portent sur la glose, les leçons, les planchers non publiés et la provenance. Mesures de charge et de coût : 19 agents,
2 517 719 jetons de sous-agents, 29 min 47 s de mur.

**Le record a été RENOMMÉ** après cette revue, parce que son titre était l'objet de P1.a et P5.b : le chemin relu
ci-dessus (`…_Misses_By_One_Seed_The_Instrument_Cannot_Return_FRAGILE.md`) est devenu
`docs/EDR/S2-BASSIN-FRAGILITY_A_Diffuse_Positive_Control_Misses_By_One_Seed_And_Blocks_The_Reading.md`. Le corps de
cette revue n'est pas retouché.

**Re-mesure et correction, critique par critique.**
- **P1.a (E9) et P5.a (E6)** — re-mesuré : `sign` ERODE contre S_a sur full, tdonly, tdoff (12/12 ; −26,25, −24,5,
  −26,0), const et eplr (11/12 ; −10,75, −14,5), NEUTRE sur zero ; `iso` NEUTRE partout (1/12 à 4/12, médiane 0,0) ;
  `pos` tiré par `sham_delta(zero + 1.0, "iso", …)` sur toute la matrice. Corrigé : le titre ne dit plus que
  l'instrument est aveugle ; une section « Ce que ce verdict ne dit PAS » dément la glose de la branche 7 par les
  données du run ; la Leçon 1 nomme le défaut de RÉGIME avant celui de puissance.
- **P5.b (E2)** — re-mesuré : `fragility_verdict(rows)` rend INDETERMINE_INSTRUMENT ; avec `S_pos` = `S_a` − 5 aux
  seeds 2036 et 2037, LU / FRAGILE (FRAGILE sur cinq bras, INOFFENSIF sur b_zero). Corrigé : la lecture bloquée est
  publiée, avec la mention qu'elle n'a aucune valeur de verdict ; « inatteignable » ne décrit plus que la porte.
- **P4.d** — re-mesuré : rapport des pertes sham/greffe (médiane par seed) 0,93 / 0,87 / 0,84 / 0,79 / 0,89 ; c/S_tr
  0,30 / 0,44 / 0,47 sur full, tdonly, tdoff (12/12). Corrigé : δmin est dit hérité de P4.4 (≈ 15 % du bassin), les deux
  échelles sont publiées, « presque autant » n'est plus affirmé sans échelle.
- **P5.c, P10.a (E8), et P8.e (hors périmètre, même fait)** — re-mesuré : ‖W_bassin‖₁ = 2442,8, rapport pos/bras 25,5 à
  826,7 sur les médianes. Corrigé : le « 24 à 718 » de conception est remplacé par la mesure, et la dose active est
  donnée (≈ 17 à 545).
- **P8.a (E8)** — re-mesuré : `input_cols_share` de `pos` 0,343-0,344 sur quatre tirages rejoués (W_bassin lui-même :
  0,332). Corrigé : dose active ≈ 0,66 × ‖W_bassin‖₁, dans le verdict et dans la Leçon 1.
- **P6.a, P6.b (E10)** — re-mesuré : bandes de `c` 1,50 / 1,75 / 3,75 / 3,51 / 1,75 / 1,25, const, eplr et zero DEDANS ;
  bande de `pos` 4,5, médiane −8,75 hors. Corrigé : colonne « bande de c » au tableau, bande de `pos` dans le verdict.
- **P6.c (E9)** — re-mesuré : bandes par seed 7,5 (2036, écart +6,5), 8,0 (2037, +5,5), 9,5 (2026, −9,5), tous dedans.
  Corrigé : l'argument « pos la MONTE » est retiré ; le signe par seed est dit indécidable.
- **P6.d** — re-mesuré : 8/10 régimes échangeables sous 0,975, minimum 0,926. Corrigé : chiffres publiés.
- **P7.b (E15)** — re-mesuré : ρ(résurrections, S_tr − S_a) = 0,943 ; ρ(net, S_tr − S_a) = −0,771 (six bras). Corrigé :
  réserve (iv) de l'hypothèse descriptive.
- **P7.c (E19, publication)** — re-mesuré : `lr_effective_per_agent` vide sur 12/12 seeds pour b_eplr et b_tdoff.
  Corrigé : pas effectifs donnés au record ; dette au backlog (le runner ne publie pas le pas effectif de la voie
  épisodique seule).
- **P10.b (E5)** — re-compté : 4 ticks de vote, tous sous `pos` (60 phases), 0 dans les 1944 autres phases. Corrigé :
  le vote est dit propre à `pos`, comme la règle l'attribuait.
- **P9.a (E27)** — juste au HEAD relu : les trois JSON cités n'étaient pas suivis. Résolu par le commit qui porte le
  record et ses trois JSON ensemble (porte 20 relancée à ce commit). La mention « SUIVI » par fichier est remplacée par
  une phrase qui nomme ce commit.

**Hors périmètre, suites données.** P2.b (la porte 19 ne lit que « nom = nombre ») et P8.b (la porte 17 ne balaie pas
`results/*_genomes/`) : deux dettes de porte, inscrites au backlog. P4.f, P5.e, P6.f, P7.e (E27, évidence non suivie) :
résolus par le même commit. P7.e (E34 absente du registre de CE worktree) : E34 existe dans d1 ; la branche est
fusionnée avec d1 avant le commit. P8.d (écrivain du monde dans la vue de H) : déjà en tête du record.
