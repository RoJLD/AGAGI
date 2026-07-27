---
id: LANG-006
type: EDR
title: "Le langage PAIE — mais SEULEMENT si la tâche exige de résoudre une asymétrie d'information (porte G3, clôt en proxy la question du BÉNÉFICE laissée ouverte par LANG-001→005). Locuteur (cible privée -> message) + auditeur (message -> action) ajustés conjointement pour survivre ; canal ablatable within-subject (méthodo S2-001). Sur monde à vérité-terrain : COORDINATION-DEMAND (action requise dépend d'une cible privée) -> ablater le canal effondre la survie (5-7×, PAIE) ; NO-COORDINATION (action fixe) -> ablation inoffensive (1.0×) ET le protocole n'émerge même pas (MI message;action = 0.000 exact). Le langage n'est pas une capacité qui s'active, c'est un investissement qui émerge SSI il paie. Corroborant MI = |W| de S2-001 : le canal est utilisé SSI il rapporte"
status: accepted
gate: G3
tests: [SDR-G3]
verdict: LANGUAGE_PAYS_IFF_TASK_DEMANDS_COORDINATION
---

# LANG-006 : le langage paie SSI la tâche exige de la coordination (porte G3)

## Contexte

Mon axe langage (LANG-001→005, [[lang-referential-capability]]) a établi la CAPACITÉ : la signalisation
référentielle émerge sous crédit épisodique, devient un protocole partagé, structurellement compositionnelle,
avec un plafond = régime d'optim pas capacité. Restait ouvert le **BÉNÉFICE** (« reste = coût signal 083 +
bénéfice in-world 087 ») : communiquer confère-t-il un avantage de survie, et QUAND ? C'est la porte **G3**
(SDR-G3 « le langage paye »). On réutilise la méthodo causale de [[s2-world-demand-thread]] (S2-001) : ablater
le CANAL de communication within-subject — si la survie s'effondre, le langage est causalement porteur.

## Méthode

`tools/language_payoff_probe.py` (pur numpy, standalone). Tâche coopérative : chaque tick une cible `t` est
PRIVÉE au locuteur ; l'action requise `a*` dépend de `t` (demanding) ou est fixe (trivial). Locuteur : `t →
message` ; auditeur : `message → action` ; récompense si action==a*, survie = ticks avant énergie≤0 (cap 200).
Locuteur + auditeur ajustés CONJOINTEMENT par hill-climb pour maximiser la survie (canal intact) → un protocole
n'émerge QUE s'il paie. Mondes à VÉRITÉ-TERRAIN :
- **COORDINATION-DEMAND** : a*(t)=t, t varie et est privée → résoudre l'asymétrie d'info EXIGE le canal.
- **NO-COORDINATION** : a*=0 fixe → l'auditeur agit sans info ; le canal est superflu.

Marqueurs : survie(canal intact) vs survie(canal RANDOMISÉ = ablation) vs survie(SANS canal) ; corroborant =
MI(message ; action) (le canal est-il utilisé ?). K∈{4,6}, M=K, 8 seeds.

## Constat

| monde (K=4) | canal intact | ablé | sans canal | MI(m;a) | PAIE(×) |
|---|---|---|---|---|---|
| COORDINATION-DEMAND | 200 | 37 | 38 | 1.040 | 5.4× |
| NO-COORDINATION | 200 | 200 | 200 | 0.000 | 1.0× |

(K=6 identique : PAIE 7.1× demand / 1.0× trivial ; MI 1.06 vs 0.000.) `VERDICT =
LANGUAGE_PAYS_IFF_TASK_DEMANDS_COORDINATION`.

## Lecture

- **Le langage PAIE causalement quand la tâche exige de résoudre une asymétrie d'information.** En
  COORDINATION-DEMAND, ablater le canal effondre la survie de 200 à 37 (≈ le niveau SANS canal, 38) : sans la
  communication, l'auditeur ne peut pas connaître la cible privée et échoue. Le canal vaut 5-7× la survie.
- **Le langage NE paie PAS quand la coordination n'est pas exigée — et alors il n'émerge même pas.** En
  NO-COORDINATION, canal intact / ablé / sans-canal survivent tous au plafond (200) ; surtout **MI(message ;
  action) = 0.000 exact** → l'auditeur IGNORE le canal. Le protocole ne se stabilise pas car il ne rapporte
  rien. Exactement l'analogue du `|W|=0.000` de S2-001 (la politique ne pèse pas une obs inutile).
- **Le langage est un INVESTISSEMENT conditionnel, pas une capacité qui s'active.** Il émerge et paie SSI la
  structure de la tâche impose une asymétrie d'information à résoudre. Ceci referme la question du bénéfice
  laissée ouverte par LANG-001→005 (qui montraient la capacité) : la capacité ne se traduit en usage que sous
  DEMANDE de coordination.

## Conséquences

- **Porte G3 franchie en proxy** : le langage PAIE (bénéfice causal, within-subject), conditionnellement à la
  demande de coordination. Complète le fil langage : capacité (001-005) + payoff (006). Le corollaire pratique
  rejoint la loi transversale [[warm-start-transversal-law]] : ce n'est pas la capacité de langage qui manque,
  c'est la DEMANDE (structure de tâche) qui décide s'il s'exprime.
- **Reco in-world pour clôre 087** : pour que le langage paie dans la biosphère, il faut une tâche à ASYMÉTRIE
  D'INFO (un agent sait quelque chose que l'autre doit utiliser — proie repérée hors du champ de l'autre,
  danger, localisation de ressource). Sans cette structure, aucun canal n'émergera (résultat NEUTRE attendu,
  pas un échec de capacité). Instrument de mesure = ablation-canal within-subject (comme S2-001 pour la
  perception).
- **Unifie ma méthodo « demande » sur deux modalités** : S2-001 (perception : ablater l'obs) et LANG-006
  (communication : ablater le canal) partagent le même témoin causal within-subject + le même corroborant «
  poids/MI = 0 quand ça ne paie pas ». Généralisable à toute question « la capacité X paie-t-elle ? ».
- Relié : `tests: SDR-G3`. Prolonge [[lang-referential-capability]] ; recoupe [[s2-world-demand-thread]]
  (même instrument) et [[vertical-world-3d-not-exploited]] (témoin within-subject).

## Caveats

1. Proxy SYNTHÉTIQUE et IDÉALISÉ (jeu locuteur-auditeur, séparation nette DEMAND/TRIVIAL) : établit la LOGIQUE
   (le langage paie SSI coordination demandée ; canal ignoré sinon), pas des magnitudes in-world.
2. Protocole ajusté SUFFISANT, pas parfait : MI ~1.04 nats < log(K) (≈1.39 à K=4) — le locuteur/auditeur
   n'est pas parfaitement injectif mais survit au plafond quand même. Le contraste robuste = MI>0.3 (utilisé)
   vs 0.000 (ignoré), pas la valeur exacte.
3. Ablation = message RANDOMISÉ (décorrélé) plutôt que masqué, pour préserver la distribution ; standard «
   canal détruit ». Le baseline SANS-canal (biais seul) confirme le même niveau d'effondrement.
4. 2 agents, canal 1-symbole, K∈{4,6} ; la composition/le multi-tour (LANG-003/004) n'est pas retestée ici —
   c'est la question du PAYOFF, orthogonale à la structure du message. Ne re-mesure pas in-world (087 reste).
