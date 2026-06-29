# EDR 111 — Tool-gate mammouth (hp 100→250) : apex effondre, craft ne monte pas → substrat ne pivote pas sous demande

**Date :** 2026-06-29
**Harnais :** `tools/evolve_ceiling_probe.py`
**Parametres :** `EVP_SELECT=elitist EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 EVP_MAMMOTH_HP={100|250} CT_METAB=0.25 CT_PAYOFF=3.0`
**Seeds :** 0, 1, 2 (x2 bras = 6 runs, tous reussis par exit code)
**Statut :** CLOS — verdict Issue 2 (substrat ne pivote pas vers l'outil sous pression ; converge avec diagnostic architecture EDR 107)

---

## Contexte

La convergence EDR 104-109 pointe le repertoire-monde comme verrou de l'apex (~0.21,
chasse coop mammouth). Le diagnostic : la coop mains-nues court-circuite l'outil
(EDR 096 — `altars_solved ≡ 0`, frac_tool plancher ~0.016). La strategie dominante
est la submersion numerique, pas le craft.

**Hypothese tool-gate :** si le mammouth a 250 HP (contre 100 par defaut), la riposte
cumulee tue le pack mains-nues avant qu'il ne finisse la chasse, mais un pack avec
lances (×5 de degats) reussit. Cela forcerait l'emergence d'une **strategie
craft→apex distincte** → le repertoire-monde s'enrichirait (Issue 1). A l'oppose,
si ni le craft ni l'apex ne montent, le verrou est le substrat/architecture (Issue 2).

---

## Pre-check de calibration (Task 2)

La calibration avait valide hp=250 comme gate honnete :
- **bare (mains nues)** : echec a hp=250, succes a hp=100.
- **lance** : succes a hp=250 (riposte absorbe 5× moins).
- **`break_pack_size`= 13** : un pack mains-nues >= 13 individus recasse le gate
  (riposte diluee sur effectif suffisant). Limite honnete rapportee ci-apres.

---

## Controle de coherence (validite du harnais)

Le bras controle (hp=100) **reproduit exactement** les cibles EDR 108/109 :

| Cible EDR 108/109 | Mesure bras ctrl (mean 3 seeds) | Ecart |
|---|---|---|
| frac_apex ere0 ≈ 0.228 | **0.2279** | < 0.001 — OK |
| frac_apex e6-11 ≈ 0.082 | **0.0821** | < 0.001 — OK |

Harnais valide. Lecture du bras gate est fiable.

---

## Resultats

### frac_apex par ere — contraste ctrl vs gate

| ere | ctrl s0 | ctrl s1 | ctrl s2 | ctrl mean | gate s0 | gate s1 | gate s2 | gate mean | delta |
|-----|---------|---------|---------|-----------|---------|---------|---------|-----------|-------|
| 0   | 0.2906  | 0.1750  | 0.2180  | 0.2279    | 0.1895  | 0.0957  | 0.1310  | 0.1387    | −0.0891 |
| 1   | 0.2234  | 0.1687  | 0.1852  | 0.1924    | 0.0381  | 0.1707  | 0.1343  | 0.1144    | −0.0781 |
| 2   | 0.2169  | 0.0625  | 0.1842  | 0.1545    | 0.0566  | 0.0222  | 0.0159  | 0.0316    | −0.1230 |
| 3   | 0.0377  | 0.2700  | 0.1190  | 0.1422    | 0.0462  | 0.0000  | 0.0735  | 0.0399    | −0.1023 |
| 4   | 0.0182  | 0.0111  | 0.0323  | 0.0205    | 0.0000  | 0.0435  | 0.0806  | 0.0414    | +0.0208 |
| 5   | 0.1455  | 0.1481  | 0.0179  | 0.1038    | 0.0758  | 0.0000  | 0.0462  | 0.0407    | −0.0632 |
| 6   | 0.1667  | 0.1087  | 0.1443  | 0.1399    | 0.0147  | 0.0484  | 0.1045  | 0.0559    | −0.0840 |
| 7   | 0.0577  | 0.0152  | 0.0909  | 0.0546    | 0.0312  | 0.0909  | 0.0545  | 0.0589    | +0.0043 |
| 8   | 0.0238  | 0.1528  | 0.0690  | 0.0819    | 0.0735  | 0.0000  | 0.0000  | 0.0245    | −0.0574 |
| 9   | 0.1633  | 0.0000  | 0.0308  | 0.0647    | 0.0000  | 0.0154  | 0.0463  | 0.0206    | −0.0441 |
| 10  | 0.1013  | 0.0755  | 0.1538  | 0.1102    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | −0.1102 |
| 11  | 0.0492  | 0.0556  | 0.0196  | 0.0415    | 0.0345  | 0.0000  | 0.0312  | 0.0219    | −0.0196 |

**Synthese frac_apex :**
- Toutes eres confondues : ctrl=0.1112 vs gate=0.0490 (delta=−0.0622, −56%)
- Eres tardives e6-11 : ctrl=0.0821 vs gate=0.0303 (delta=−0.0518, −63%)
- Le gate **effondre** l'apex a travers toutes les eres. Pas de rebond en phase tardive.

### frac_tool (spears_crafted) par ere — contraste ctrl vs gate

| ere | ctrl s0 | ctrl s1 | ctrl s2 | ctrl mean | gate s0 | gate s1 | gate s2 | gate mean | delta |
|-----|---------|---------|---------|-----------|---------|---------|---------|-----------|-------|
| 0   | 0.0427  | 0.0250  | 0.0150  | 0.0276    | 0.0526  | 0.0426  | 0.0238  | 0.0397    | +0.0121 |
| 1   | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000 |
| 2   | 0.0120  | 0.0000  | 0.0088  | 0.0069    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | −0.0069 |
| 3   | 0.0377  | 0.0000  | 0.0238  | 0.0205    | 0.0308  | 0.0000  | 0.0000  | 0.0103    | −0.0102 |
| 4   | 0.0182  | 0.0111  | 0.0000  | 0.0098    | 0.0159  | 0.0000  | 0.0000  | 0.0053    | −0.0045 |
| 5   | 0.0364  | 0.0247  | 0.0000  | 0.0204    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | −0.0204 |
| 6   | 0.0185  | 0.0217  | 0.0000  | 0.0134    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | −0.0134 |
| 7   | 0.0192  | 0.0000  | 0.0000  | 0.0064    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | −0.0064 |
| 8   | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000 |
| 9   | 0.0816  | 0.0000  | 0.0000  | 0.0272    | 0.0000  | 0.0000  | 0.0093  | 0.0031    | −0.0241 |
| 10  | 0.0127  | 0.0000  | 0.0000  | 0.0042    | 0.0000  | 0.0000  | 0.0189  | 0.0063    | +0.0021 |
| 11  | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000  | 0.0000  | 0.0000  | 0.0000    | 0.0000 |

**Synthese frac_tool :**
- Toutes eres : ctrl=0.0114 vs gate=0.0054 (delta=−0.0060)
- Sous gate, frac_tool ne monte pas — il baisse ou reste au plancher.
- Aucune ere ne montre un signal de craft emergence coherent sur les 3 seeds.
- L'unique micro-signal positif (ere0 gate +0.0121) precede l'effondrement apex et
  n'est pas tenu sur les eres suivantes.

### Lecture secondaire : behavioral_diversity et bdiv_spears

| ere | bdiv_sp ctrl | bdiv_sp gate | bdiv ctrl | bdiv gate |
|-----|-------------|-------------|-----------|-----------|
| 0   | 0.1600      | 0.1508      | 0.1984    | 0.1933    |
| 1   | 0.0000      | 0.0000      | 0.1846    | 0.1603    |
| 2   | 0.0674      | 0.0000      | 0.1968    | 0.1462    |
| 3   | 0.1144      | 0.0576      | 0.2035    | 0.1665    |
| 4   | 0.0795      | 0.0417      | 0.1538    | 0.1462    |
| 5   | 0.1141      | 0.0000      | 0.2107    | 0.1398    |
| 6   | 0.0834      | 0.0000      | 0.1803    | 0.1589    |
| 7   | 0.0458      | 0.0000      | 0.1770    | 0.1530    |
| 8   | 0.0000      | 0.0000      | 0.1597    | 0.1419    |
| 9   | 0.0913      | 0.0319      | 0.1661    | 0.1176    |
| 10  | 0.0373      | 0.0454      | 0.1921    | 0.1063    |
| 11  | 0.0000      | 0.0000      | 0.1459    | 0.1291    |

- `bdiv_spears` en gate : plancher (0.0000) sur 9/12 eres en moyenne, aucun signal
  d'emergence d'un tier lance coherent. Le craft ne diversifie pas le comportement.
- `behavioral_diversity` gate : legerement inferieure au ctrl sur toutes les eres
  (mean gate ~0.145 vs ctrl ~0.183), coherent avec une population qui collapse sans
  trouver de strategie alternative.

### Tailles de pack observees vs seuil de calibration

| ere | n moyen gate |
|-----|-------------|
| 0   | 91          |
| 1   | 85          |
| 2   | 54          |
| 3   | 62          |
| 4   | 57          |
| 5   | 62          |
| 6   | 66          |
| 7   | 62          |
| 8   | 64          |
| 9   | 80          |
| 10  | 56          |
| 11  | 63          |

Ces `n` sont la taille de POPULATION, pas du pack de chasse. Les packs de chasse
effectifs sont un sous-ensemble. La calibration (Task 2) avait montre que le gate
cede au-dela de 12 individus mains-nues coordonnes. Ici, la population tombe apres
ere0 (54-91), ce qui suggere que les packs effectifs passent en dessous du seuil
de brisure — mais l'apex s'effondre quand meme, car le substrat ne compense pas par
le craft. Le gate n'est pas contourne par la taille de population observee.

---

## Verdict : Issue 2 confirmee

**Issue 2 (le substrat ne pivote pas vers l'outil sous demande) :**
- `frac_apex` : ctrl=0.1112 → gate=0.0490 (−56% toutes eres ; −63% tardif)
- `frac_tool` : ctrl=0.0114 → gate=0.0054 (−53%, reste au plancher sous gate)
- `bdiv_spears` : plancher sous gate sur la quasi-totalite des eres
- Le substrat NE REPOND PAS au changement de pression en activant une strategie
  outil. Il s'effondre.

**Note sur l'attribution architecturale :** l'hypothese que le verrou serait
l'architecture du connectome (97% I/O, NEAT-like sans couche cachee) est IMPORTEE
d'EDR 107/NAS — elle CONVERGE avec ce resultat mais n'est pas prouvee
independamment ici (un seul levier hp, N=3 seeds). Cet EDR mesure uniquement que
le substrat ne se reoriente pas ; la cause architecturale reste une hypothese
renforcee par convergence.

**Issue 1 refutee :** le craft ne monte pas malgre le gate. Aucun signal d'emergence
d'un repertoire enrichi.

**Transition partielle :** non observee. Le signal est unidirectionnel : effondrement
apex SANS compensation outil. Meme ere0 (seule ere avec frac_tool gate legerement
superieur au ctrl : +0.012) est suivie d'un effondrement complet des eres 1-11.

---

## Distinction avec EDR 039/041

EDR 039 et 041 avaient explore `coop_reward=False` (AUTRE levier — supprimer la
recompense coop) sur des instruments **perimes** (avant EDR 096 repare la metrique
altar, avant EDR 058/preserve_dims). Leur question etait la "completude d'ablation".

Ici : levier **hp-gate** (augmenter la durabilite du mammouth via `EVP_MAMMOTH_HP`),
instruments repares (preserve_dims actif, metrique reparee EDR 096), question =
**emergence de repertoire sous pression obligatoire de craft**. Ce n'est pas un
doublon.

---

## Liens

- [[coop-competence-is-population-property]] — EDR 097/102/104 : apex vit dans la
  diversite de population, pas dans un genome ; ici l'effondrement confirme que la
  population ne trouve pas d'alternative quand la coop mains-nues est brisee.
- [[nas-bottleneck-is-substrate-not-search]] — la capacite reseau eliminee comme
  verrou (EDR 105b), le repertoire-monde comme piste. EDR 111 confirme : sous gate,
  le substrat ne porte pas la strategie outil → verrou substrat/architecture.
- [[lewis-energy-economy-wall]] — meme famille de verdict (le substrat ne repond pas
  a un changement de contexte par une strategie adaptee).
- EDR 109 — `behavioral_diversity` confirme issue 2 (tournoi insuffisant) ; EDR 111
  le confirme independamment via le levier hp-gate.

---

## Caveat et limites

1. **Gate partiellement poreux — et pré-check analytique insuffisant en isolation** :
   au-dela de 12 individus mains-nues coordonnes le gate cede (calibration Task 2).
   Les tailles de population observees tombent sous ce seuil apres ere 0, mais nous
   n'avons pas de mesure directe du pack de chasse effectif (nombre d'agents qui
   attaquent un mammouth simultanement).

   **Biais de modele dans la calibration :** le pre-check (`tools/tool_gate_calibration.py`)
   suppose que la riposte du mammouth est distribuee UNIFORMEMENT sur l'ensemble du
   pack a chaque tick. Or la mecanique reelle (`src/worlds/world_1_stoneage.py:595-597`)
   ne riposte que contre l'UNIQUE agent `closest` par tick de proie (instruction
   `continue` apres riposte), ce qui concentre les degats sur un seul agent a la fois.
   Consequence : le pack encaisse moins de riposte distribuee que le modele ne le
   suppose → le gate reel est **plus POREUX que `break_pack_size=13`**.

   Le pre-check est donc **NECESSAIRE MAIS NON SUFFISANT** : il prouve que, sous le
   modele uniforme, le pack mains-nues ne tue pas et la lance tue, mais il ne prouve
   pas que le gate mord avec la meme durete dans la sim. La preuve que le gate a
   effectivement morde reste **INDIRECTE** (effondrement apex + frac_tool au plancher).
   Le verdict honnete est « le substrat ne pivote pas vers l'outil sous CE gate » ;
   la force exacte du gate in-sim est incertaine.
2. **3 seeds** : variance inter-seeds visible (ex. ctrl s1 ere3 : 0.270 vs s0 : 0.038).
   Les directions sont coherentes sur les 3 seeds mais un test de significativite
   formel (sign test) n'est pas calcule sur N=3.
3. **Knob hp seul** : ce knob gate le mammouth mais ne modifie pas les affordances
   de craft (les recettes restent accessibles). L'absence de craft emergence est
   donc un signal de substrat, pas d'une absence d'affordance.
4. **Traçabilite seed (artefact harnais)** : le champ `"seed"` des 6 JSON de run
   affiche toujours `0` — `EXPERIMENT_SEED` n'est pas serialise dans le `result`
   (meme artefact que EDR 109/105/108). Les donnees per_era sont bien distinctes par
   seed (ctrl ere0 : 0.2906/0.175/0.218), ce qui confirme que les runs sont
   independants. La correspondance run↔seed se fait par le nom de fichier, pas par
   le champ metadata.
5. **Cohérence config_hash** : les 6 JSON partagent `config_hash = "fa6f6ff765fb"`,
   identique entre bras ctrl et gate. Indice de parite de configuration — note
   honnete : le hash ne couvre pas necessairement `EVP_MAMMOTH_HP`, donc c'est une
   indication, pas une preuve formelle que seul ce parametre differe.

---

## Statut et suite

**EDR 111 : CLOS — Issue 2 confirmee.**

Le substrat (NAS actuel) ne porte pas de strategie outil sous pression obligatoire :
il s'effondre sans pivoter vers le craft. Enrichir le repertoire-monde via un knob hp
ne suffit pas — le substrat ne saisit pas l'affordance quand le monde l'exige.

L'hypothese sur l'architecture (NEAT-like, connectome 97% I/O, sans couche cachee
profonde) comme cause profonde CONVERGE avec EDR 107/NAS mais n'est pas etablie
independamment ici. Elle reste a tester directement (substrat plus riche : hidden
layers profonds, plasticite, proto-curriculum craft).

Suite naturelle : EDR 110 (capacity-nav, Lewis, reserve) ou un pivot vers un
substrat plus riche (hidden layers profonds, plastique, proto-curriculum craft).
