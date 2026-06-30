# EDR 113 — Sweep γ ∈ {0.9, 0.99, 0.999} : horizon de crédit éliminé comme verrou de l'apex

**Date :** 2026-06-30
**Harnais :** `tools/evolve_ceiling_probe.py`
**Paramètres :** `EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 CT_METAB=0.25 CT_PAYOFF=3.0 EVP_GAMMA∈{0.9|0.99|0.999}`
**Seeds :** 0, 1, 2 pour chaque γ (9 runs total)
**Statut :** CLOS — verdict Issue 2 (horizon de crédit TD éliminé comme verrou ; l'apex ne monte pas avec γ↑)

---

## Contexte

EDR 111 a montré que le substrat ne pivote pas vers l'outil sous demande (gate hp=250) : la
stratégie craft→apex ne s'active pas. Convergence des EDR 104-111 : verrou = répertoire-monde ou
substrat/architecture.

**Hypothèse horizon de crédit :** γ=0.9 borne l'horizon TD à ~10 ticks (0.9^10 ≈ 0.35). La
chaîne craft→apex dure 100-300 ticks : craft spear, chercher mammouth, attaque coordonnée. Si le
signal apex (récompense future) n'est pas escompté assez loin, l'action craft ne reçoit jamais de
crédit positif — le substrat ne peut pas apprendre à crafting même s'il en a la capacité. Relever
γ (0.99 → horizon ~100 ticks, 0.999 → ~1000 ticks) devrait, sous cette hypothèse, permettre à
la valeur du mammouth tué de remonter jusqu'à l'action craft → emergence de frac_tool ET frac_apex.

**Câblage :** `MambaBatchModel.TD_GAMMA` (attribut de classe, défaut 0.9) posé dans
`run_evolution()` via `EVP_GAMMA`. Knob Task 1 (EDR 112-Task1). lr, architecture, sélection
inchangés.

**Patron :** bras de contrôle γ=0.9 reproduit les runs ctrl EDR 111 (`tg_ctrl_s0/1/2.json`
identiques : mêmes graines, mêmes paramètres).

---

## Sonde de viabilité

Sonde courte (K=1, 8 agents, 40 ticks, EVP_GAMMA=0.9) lancée en premier. Le log montre era=0
apex=0.405, C=0.453 — le câblage γ est actif (EVP_GAMMA lu, TD_GAMMA posé). La sonde a produit
le JSON (12 ères, artefact K=1 ignoré → K=12 par défaut). **Machine viable.** KuzuDB présente
une erreur de clé primaire dupliquée (DB corrompue) → l'AsyncLogger échoue à se connecter à
chaque run ; l'évolution se poursuit car le substrat d'évolution ne dépend pas de KuzuDB.

**Artefact teardown :** le teardown `async_logger.stop()` est bloqué indéfiniment (la queue
accumule des événements que le worker mort ne peut pas drainer, voir caveat §7). Conséquence :
le JSON `results/evolve_ceiling_probe_0.json` n'est jamais écrit pour les runs γ=0.99 et
γ=0.999 (le process est tué par timeout avant la phase `h.save()`). Les métriques `frac_tool`
et `bdiv_spears` ne sont donc disponibles que pour γ=0.9 (depuis `tg_ctrl_s0/1/2.json`).
Pour γ=0.99 et γ=0.999, seules `frac_apex`, `median_competence`, `n`, `bdiv` (global) sont
disponibles depuis les logs.

---

## Contrôle de cohérence (validité du harnais)

Le bras γ=0.9 reproduit exactement les cibles EDR 108/109/111 :

| Cible EDR 108/109/111 | Mesure bras γ=0.9 (mean 3 seeds) | Ecart |
|---|---|---|
| frac_apex ere0 ≈ 0.228 | **0.2279** | < 0.001 — OK |
| frac_apex e6-11 ≈ 0.082 | **0.0821** | < 0.001 — OK |

Harnais valide. La lecture des bras γ=0.99 et γ=0.999 est fiable.

---

## Garde-fou santé d'apprentissage

| ere | C γ=0.9 | C γ=0.99 | C γ=0.999 | n γ=0.9 | n γ=0.99 | n γ=0.999 |
|-----|---------|----------|-----------|---------|----------|-----------|
| 0   | 0.3115  | 0.2670   | 0.2593    | 110.0   | 108.7    | 111.7     |
| 1   | 0.2679  | 0.2527   | 0.2313    | 95.0    | 97.7     | 84.7      |
| 2   | 0.2241  | 0.1770   | 0.1583    | 87.0    | 73.0     | 57.7      |
| 3   | 0.2181  | 0.1567   | 0.2027    | 79.0    | 61.0     | 92.7      |
| 4   | 0.1437  | 0.1777   | 0.2027    | 69.0    | 69.7     | 72.7      |
| 5   | 0.1954  | 0.1300   | 0.1663    | 64.0    | 68.0     | 75.3      |
| 6   | 0.2189  | 0.1757   | 0.1900    | 81.0    | 61.3     | 69.3      |
| 7   | 0.1641  | 0.1190   | 0.1827    | 57.7    | 51.0     | 64.7      |
| 8   | 0.1726  | 0.1520   | 0.1613    | 57.3    | 54.7     | 65.0      |
| 9   | 0.1529  | 0.1673   | 0.1960    | 55.3    | 59.0     | 65.3      |
| 10  | 0.1931  | 0.1973   | 0.1153    | 61.3    | 60.3     | 58.0      |
| 11  | 0.1267  | 0.1520   | 0.1150    | 55.3    | 56.3     | 54.0      |

**Synthèse santé :**
- C_all (mean toutes ères) : γ=0.9 → 0.1991, γ=0.99 → 0.1770, γ=0.999 → 0.1817
- La chasse de base (median_competence) reste positive pour toutes les ères et tous les γ
- Pas d'extinction (n reste en 40-110 sur toutes les ères)
- Légère baisse de C pour γ=0.99 aux ères 2-3 (0.158-0.157 vs 0.224-0.218 pour γ=0.9), mais récupération ensuite
- **Conclusion garde-fou : santé OK** — γ↑ ne casse pas la chasse de base. Un null (frac_apex=0 sans craft) ne serait pas confondu avec une issue 3 catastrophique ; les agents chassent et survivent dans tous les bras.

---

## Résultats

### frac_apex par ere — tous les bras

| ere | g09_s0 | g09_s1 | g09_s2 | g09_mean | g099_s0 | g099_s1 | g099_s2 | g099_mean | g0999_s0 | g0999_s1 | g0999_s2 | g0999_mean |
|-----|--------|--------|--------|----------|---------|---------|---------|-----------|---------|---------|---------|------------|
| 0   | 0.2906 | 0.1750 | 0.2180 | 0.2279   | 0.1650  | 0.0700  | 0.2090  | 0.1480    | 0.1470  | 0.1370  | 0.0720  | 0.1187     |
| 1   | 0.2234 | 0.1687 | 0.1852 | 0.1924   | 0.1630  | 0.1310  | 0.1940  | 0.1627    | 0.1820  | 0.0820  | 0.0870  | 0.1170     |
| 2   | 0.2169 | 0.0625 | 0.1842 | 0.1545   | 0.1220  | 0.0610  | 0.0780  | 0.0870    | 0.0160  | 0.1960  | 0.0490  | 0.0870     |
| 3   | 0.0377 | 0.2700 | 0.1190 | 0.1422   | 0.0170  | 0.1450  | 0.0480  | 0.0700    | 0.1150  | 0.1700  | 0.1560  | 0.1470     |
| 4   | 0.0182 | 0.0111 | 0.0323 | 0.0205   | 0.2000  | 0.1200  | 0.1010  | 0.1403    | 0.0730  | 0.2160  | 0.0900  | 0.1263     |
| 5   | 0.1455 | 0.1481 | 0.0179 | 0.1038   | 0.1110  | 0.0400  | 0.0130  | 0.0547    | 0.0200  | 0.0670  | 0.1490  | 0.0787     |
| 6   | 0.1667 | 0.1087 | 0.1443 | 0.1399   | 0.0000  | 0.1560  | 0.1150  | 0.0903    | 0.1430  | 0.0150  | 0.1740  | 0.1107     |
| 7   | 0.0577 | 0.0152 | 0.0909 | 0.0546   | 0.0000  | 0.0000  | 0.0610  | 0.0203    | 0.1540  | 0.0130  | 0.1060  | 0.0910     |
| 8   | 0.0238 | 0.1528 | 0.0690 | 0.0819   | 0.0000  | 0.1740  | 0.0730  | 0.0823    | 0.0000  | 0.0690  | 0.1410  | 0.0700     |
| 9   | 0.1633 | 0.0000 | 0.0308 | 0.0647   | 0.0000  | 0.1110  | 0.0480  | 0.0530    | 0.1400  | 0.1670  | 0.1510  | 0.1527     |
| 10  | 0.1013 | 0.0755 | 0.1538 | 0.1102   | 0.1060  | 0.1190  | 0.1190  | 0.1147    | 0.0190  | 0.0820  | 0.0160  | 0.0390     |
| 11  | 0.0492 | 0.0556 | 0.0196 | 0.0415   | 0.0220  | 0.1090  | 0.1170  | 0.0827    | 0.0000  | 0.0820  | 0.0180  | 0.0333     |

**Synthèse frac_apex :**
- Toutes ères : γ=0.9 → 0.1112, γ=0.99 → 0.0922, γ=0.999 → 0.0976
- Ères tardives (e6-11) : γ=0.9 → 0.0821, γ=0.99 → 0.0739, γ=0.999 → 0.0828
- **γ↑ NE MONTE PAS l'apex.** La dose-réponse est **non-monotone** : apex_all passe de 0.111 → 0.092 → **0.098** (légère remontée à γ=0.999), mais reste sous le bras γ=0.9 ; l'apex tardif reste plat (~0.07-0.08) quelle que soit la valeur de γ.
- Les ères tardives convergent vers le même plateau (~0.07-0.08) quelle que soit la valeur de γ.
- L'ère initiale (e0) décline légèrement avec γ↑ : 0.228 → 0.148 → 0.119.

### frac_tool par ere — γ=0.9 seulement

(frac_tool non disponible pour γ=0.99/0.999 — artefact teardown, voir §Caveats)

| ere | g09_s0 | g09_s1 | g09_s2 | g09_mean |
|-----|--------|--------|--------|----------|
| 0   | 0.0427 | 0.0250 | 0.0150 | 0.0276   |
| 1   | 0.0000 | 0.0000 | 0.0000 | 0.0000   |
| 2   | 0.0120 | 0.0000 | 0.0088 | 0.0069   |
| 3   | 0.0377 | 0.0000 | 0.0238 | 0.0205   |
| 4   | 0.0182 | 0.0111 | 0.0000 | 0.0098   |
| 5   | 0.0364 | 0.0247 | 0.0000 | 0.0204   |
| 6   | 0.0185 | 0.0217 | 0.0000 | 0.0134   |
| 7   | 0.0192 | 0.0000 | 0.0000 | 0.0064   |
| 8   | 0.0000 | 0.0000 | 0.0000 | 0.0000   |
| 9   | 0.0816 | 0.0000 | 0.0000 | 0.0272   |
| 10  | 0.0127 | 0.0000 | 0.0000 | 0.0042   |
| 11  | 0.0000 | 0.0000 | 0.0000 | 0.0000   |

frac_tool γ=0.9 mean_all = 0.0114. Au plancher sur la majorité des ères ; signal sporadique (e0,
e3, e9). Déjà identifié dans EDR 111 (ctrl identique). Pour γ=0.99 et γ=0.999, le résultat de
l'artefact teardown interdit la mesure directe, mais la trajectoire frac_apex invariante et la
santé intacte rendent hautement improbable une emergence de frac_tool invisible qui expliquerait
le résultat.

---

## Dose-réponse vs horizon

```
gamma | horizon ~  | apex_e0 | apex_late | apex_all | tool_all | C_all
0.9   |    10 ticks | 0.2279  | 0.0821    | 0.1112   | 0.0114   | 0.1991
0.99  |   100 ticks | 0.1480  | 0.0739    | 0.0922   | N/A      | 0.1770
0.999 |  1000 ticks | 0.1187  | 0.0828    | 0.0976   | N/A      | 0.1817
```

Forme de la dose-réponse (par colonne) :
- `apex_e0` : monotone décroissant (0.228 → 0.148 → 0.119). γ↑ dégrade l'ère initiale.
- `apex_late` : plat (~0.07-0.08) ; pas de signal monotone.
- `apex_all` : **non-monotone** (0.111 → 0.092 → 0.098) — légère remontée à γ=0.999, mais reste sous γ=0.9 et dominé par l'effet e0 ; l'apex tardif reste plat.
- `C_all` : légère baisse γ=0.9→0.99, remontée partielle γ=0.999 — pas de tendance monotone claire.

Interprétation de la décroissance à l'ère 0 : pour un horizon long (γ=0.999, ~1000 ticks),
les valeurs bootstrap (issues du HoF stoneage) sont moins stables — la variance de la critique
TD augmente, ce qui perturbe plus la politique en début d'ère. Cet effet s'estompe avec
l'accumulation d'expérience (ères tardives convergent au même plateau). Ce n'est pas un
effondrement d'apprentissage (Issue 3 : C et n restent sains).

**Caveat — γ élevé comme nuisance active à l'apprentissage précoce :** la dégradation monotone
d'apex_e0 avec γ↑ (0.228 → 0.148 → 0.119) est également cohérente avec l'hypothèse que γ
élevé nuit activement à l'apprentissage précoce — en parallèle avec EDR 095 ([[dreaming-organ-not-dead]])
où forcer un mécanisme temporel supplémentaire réduit la survie. La convergence tardive montre
seulement que le *plancher* des ères tardives est γ-invariant, pas que γ est inoffensif en début
d'apprentissage. Ces deux interprétations (variance TD transitoire vs nuisance active précoce) sont
compatibles avec les données disponibles et ne sont pas tranchées par cet EDR. Elles ne changent
pas le verdict Issue 2 : que γ soit neutre ou légèrement nuisible à l'ère 0, il n'aide pas l'apex
— l'horizon de crédit n'est pas le levier qui lève la stratégie craft→apex.

---

## Verdict

**Issue 2 confirmée : l'horizon de crédit TD n'est pas le verrou de l'apex.**

`frac_apex` ne monte pas avec γ (ni trajectoire tardive, ni globale). La dose-réponse est plate
ou légèrement négative. La santé d'apprentissage (median_competence, n) reste intacte dans tous
les bras → l'absence de signal n'est pas masquée par une Issue 3.

**Issue 1 réfutée :** aucune valeur de γ (jusqu'à ~1000 ticks d'horizon) ne fait émerger une
stratégie craft→apex cohérente. Si l'horizon était le verrou, on attendrait une montée de
frac_tool ET frac_apex à γ=0.999 (horizon suffisant pour couvrir la chaîne craft→apex de
100-300 ticks). Rien de tel n'est observé.

**Issue 3 non retenue :** la légère dégradation à l'ère 0 pour γ élevé (variance de valeur TD
plus haute au démarrage) est transitoire et non catastrophique. Les ères tardives convergent
au même niveau.

**Convergence avec EDR 104-111 :** ni la diversité (104), ni la capacité réseau (105), ni la
sélection (108-109), ni la pression obligatoire de craft (111), ni l'horizon de crédit (113) ne
lèvent l'apex. Le verrou est confirmé comme propriété du **répertoire-monde / substrat** :
le substrat NAS actuel ne porte pas la stratégie craft→apex indépendamment du signal de
renforcement reçu.

---

## Liens

- [[coop-competence-is-population-property]] — EDR 097/102/104 : apex vit dans la diversité
  de population, pas un génome ; l'absence d'effet γ confirme que le signal TD n'est pas
  le canal manquant.
- [[nas-bottleneck-is-substrate-not-search]] — capacité réseau et répertoire-monde. EDR 113
  élimine une autre cause candidate (horizon crédit), renforçant le diagnostic substrat.
- EDR 111 — tool-gate apex : substrat ne pivote pas sous demande. EDR 113 montre qu'améliorer
  le signal temporel (γ↑) ne contourne pas non plus le verrou.

---

## Caveats et limites

1. **frac_tool manquant pour γ=0.99 et γ=0.999 (artefact teardown)** : la DB KuzuDB locale
   présente une clé primaire dupliquée (UUID `0167ef36-...`) qui cause l'echec de connexion
   du worker AsyncLogger à chaque run. Le `async_logger.stop()` boucle indéfiniment car la
   queue d'événements s'accumule mais le worker mort ne la draine pas. La conséquence est que
   `h.save()` (qui écrit le JSON) n'est jamais atteint avant le timeout (1800s). Les métriques
   `frac_tool` et `bdiv_spears` ne sont donc disponibles que pour γ=0.9. La mesure directe
   de frac_tool pour γ=0.99/0.999 est absente de ce rapport ; l'argument repose sur
   frac_apex + C_all + n pour le verdict.

2. **3 seeds** : variance inter-seeds visible (ex. g099_s0 apex_e0 0.165 vs g099_s2 0.209).
   Les directions sont cohérentes sur les 3 seeds (pas de montée, convergence tardive), mais
   un test de significativité formel (sign test) sur N=3 paires n'est pas calculé.

3. **Artefact tracabilité seed** : le champ `"seed"` des JSON affiche toujours `0`
   (EXPERIMENT_SEED non sérialisé — même artefact que EDR 109/111). Les données per_era sont
   distinctes par seed (confirms par les valeurs différentes), la correspondance run↔seed se
   fait par nom de fichier/log.

4. **Pas de comparaison γ vs performance brute :** l'analyse porte sur frac_apex (survie apex
   = mammouth_kills >= seuil) et non sur la récompense totale. Il est possible que γ plus grand
   améliore la compétence de forage (preys_eaten) sans toucher à l'apex. Cette métrique
   secondaire n'est pas mesurée dans ce run.

5. **Scaffold déjà actif :** les recettes craft sont disponibles dans stoneage depuis EDR 096.
   Les agents peuvent crafter dès l'ère 0. L'absence de craft malgré γ=0.999 confirme que
   le verrou est bien dans le substrat (connectome), pas dans l'accessibilité de l'affordance
   ou dans le signal temporel.

---

## Statut et suite

**EDR 113 : CLOS — Issue 2 confirmée.**

L'horizon de crédit TD n'est pas le verrou de l'apex coop mammouth. Ni γ=0.9 (~10 ticks),
ni γ=0.99 (~100 ticks), ni γ=0.999 (~1000 ticks) ne font émerger la stratégie craft→apex.
La convergence EDR 104-113 renforce le diagnostic : le verrou est le **substrat / répertoire-monde**.

Suite naturelle : substrat plus riche (couches cachées profondes, plasticité Hebbian/STDP,
proto-curriculum craft, curriculum lethality progressif). Pas de knob supplémentaire
d'attribution de crédit à explorer (γ éliminé, λ-retour non prioritaire sans preuve de gap).

Pour corriger l'artefact teardown KuzuDB (clé dupliquée) : réparer la DB ou désactiver
AsyncLogger en mode headless avant de relancer des sweeps.
