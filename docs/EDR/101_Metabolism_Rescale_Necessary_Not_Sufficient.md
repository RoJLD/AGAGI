# EDR 101 — PAS LE METABOLISME SEUL : le rescale aide (×5) mais sature loin du gate ; le mur résiduel est le forage

## Contexte

EDR 100 a localisé le drain intrinsèque de Lewis au **métabolisme** (`base_metabolism × phenotype_energy_drain`,
90% du drain). EDR 101 est la **première intervention** de la chaîne (après six diagnostics 090-100) : tester si
**réduire `base_metabolism` débloque la survie**. `base_metabolism` est un knob de monde (config) ; à 0, le terme
métabolisme s'annule entièrement. Pré-enregistrement :
`docs/superpowers/specs/2026-06-24-EDR101-Metabolism-Rescale-design.md`.

Variable : `base_metabolism ∈ (0.25, 0.1, 0.05, 0.025, 0.0)` à `N_APEX=0` (monde vide), reste gelé. Gate de
survie : médiane > 120.

## Le verdict : PAS LE METABOLISME SEUL

Réduire le métabolisme **aide nettement** (la survie quintuple) mais **sature à ~27 ticks** — très loin du gate.
Aucun niveau ne franchit 120, **pas même `base_metabolism = 0`**.

| `base_metabolism` | survie médiane (ticks) | famine | n |
|---|---|---|---|
| 0.25 (085) | 5.0 | 134 | 134 |
| 0.1 | 9.0 | 373 | 373 |
| 0.05 | 25.0 | 918 | 1029 |
| 0.025 | 27.0 | 1239 | 1525 |
| **0.0** (métab nul) | **27.0** | 1780 | 2230 |

Jonckheere-Terpstra z=**15.88, p<0.001** — la survie **croît monotoniquement et hautement significativement**
quand le métabolisme baisse. Combat = 0 partout (N_APEX=0) : tous meurent de **famine**.

## Le mécanisme : nécessaire mais non suffisant — un second mur à 27 ticks

Deux faits, en tension :

1. **Le métabolisme EST un vrai levier.** La survie passe de 5 (à 0.25) à 27 (à 0) — un **×5**, monotone, JT
   z=15.88. Réduire le coût de dépense prolonge la vie. EDR 100 avait raison : le métabolisme est une part réelle
   du mur.
2. **Mais il sature loin du gate.** La survie plafonne à **~27 ticks** dès `base_metabolism = 0.025`, et le
   dernier cran (0.025 → 0) **n'ajoute rien** (27 = 27). Le résidu de survie n'est donc **pas** le métabolisme.
   Même en annulant entièrement le terme métabolique, les champions meurent de famine au tick 27.

À `base_metabolism = 0`, le drain résiduel est minime (~1-2/tick : terrain + carry + brain + throw). Pourtant,
partant de E=80, les champions s'épuisent en ~27 ticks : **ils ne foragent pas assez pour couvrir même un drain
quasi-nul.** Le mur résiduel n'est plus la **dépense** d'énergie — c'est l'**acquisition** : les champions
stoneage, dans Lewis vidé d'apex, n'exploitent pas les 15 proies de forage pour rester à flot.

## Ce que cela ferme : le thread énergie-dépense (090-101)

EDR 101 clôt le fil de la **dépense énergétique** ouvert en 090. Le bilan :

| EDR | Levier (côté dépense/environnement) | Verdict |
|---|---|---|
| 090 | létalité | NÉGATIF PROFOND |
| 093 | revenu `forage_payoff` | inerte |
| 094 | densité apex `N_APEX` | inerte → MUR INTRINSÈQUE |
| 098 | `brain_cost`/surprise | inerte (clampé) |
| 099 | décomposition | phase biologie 90% |
| 100 | sous-décomposition | métabolisme (`phenotype_energy_drain≈54`) |
| **101** | **rescale `base_metabolism`** | **nécessaire mais NON suffisant (sature à 27 ≪ 120)** |

**Le mur de Lewis n'est pas réparable par un rescale d'énergie seul.** La dépense (métabolisme) compte, mais
même supprimée, un **second mur — l'acquisition (forage/comportement)** — limite la survie à ~27 ticks. Cohérent
avec le tout début (les champions stoneage ne transfèrent pas leur survie à Lewis, EDR 090) et avec la
méta-leçon NAS (le goulot est le **substrat/répertoire**, pas un paramètre).

## Le vrai levier (re-pointé) : l'acquisition, pas la dépense

Le levier suivant quitte l'énergie-dépense pour l'**énergie-acquisition** :

- **forage/comportement (prioritaire)** : à `base_metabolism=0`/`N_APEX=0`, mesurer pourquoi les champions ne
  foragent pas assez — exploitent-ils les 15 proies régulières ? (income de forage par tick, taux de capture).
  Le second mur (27 ticks) vit là.
- **substrat (EDR 102, séquence prévue)** : le finding parallèle `from_genome` aplatit l'archi est **désormais
  résolu** (`preserve_dims`, PR #55 mergée ; défaut OFF, bascule True en PR #58 ouverte). EDR 102 peut vérifier
  si `phenotype_energy_drain≈54` est un artefact d'aplatissement — mais c'est moins central depuis 101 : même le
  métabolisme nul (qui contourne le trait) ne sauve pas. Le goulot dominant est le forage, pas le trait.

## Honnêteté & méthode

- **Intervention nuancée, pas binaire.** EDR 101 n'est ni un succès ni un échec sec : il **dissocie** une vraie
  contribution du métabolisme (×5, JT z=15.88) d'un **plafond non-métabolique** (27 ticks). C'est plus
  informatif qu'un simple « inerte ».
- **Puissance réduite, verdict surdéterminé.** Le run gelé (`max_ticks=300`, R=4, n_eval=8) s'est révélé
  **impraticablement lent aux faibles `base_metabolism`** — *parce que* la survie y est longue et la population
  remplit le cap (150) → ères très lourdes (le niveau 0.05 a pris ~43 min ; 0.025/0.0 davantage). C'est un
  **signal en soi** (baisser le métabolisme prolonge nettement la vie). La table ci-dessus vient d'un run
  confirmatoire **réduit** (`max_ticks=150`, R=1, n_eval=3, seed=101). La réduction est **fidèle au gate** :
  `max_ticks=150 > 120`, donc tout franchissement de 120 serait détecté ; or les médianes (5-27) sont très en
  deçà — aucune censure n'affecte le verdict. Le verdict est **surdéterminé** : smoke (0.25→5, 0.0→27), 3/5
  niveaux du run gelé (sans franchissement), et ce run réduit concordent tous.
- **Reproductibilité.** `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; mêmes seeds entre
  niveaux (appariement). Provenance label `knob="base_metab"` (cosmétique).
- **`base_metabolism=0` = suppression complète valide.** `metab = 0 × phenotype_energy_drain = 0` quel que soit
  le trait → la survie plate-haute à 0 signifie bien « le métabolisme n'est pas le seul mur », pas un artefact du
  débat `from_genome` (lequel est contourné par le terme nul).

## Variables d'expérience

`base_metabolism` (balayé : **nécessaire non suffisant**), et — prochain levier — **le forage/comportement**
(income d'acquisition à `N_APEX=0` : taux de capture des proies régulières, énergie/tick acquise) ; en option
le **substrat** (EDR 102, `from_genome`/`preserve_dims`). Outils : `tools/lewis_survival_sweep.py` (`main_metab`,
`_verdict_metab`, param `_cfg(base_metabolism=…)`), `src/seed_ai/exp_stats.py`. Provenance :
`results/lewis_metab_sweep_101_reduced.json` (puissance réduite, surdéterminé). Lignée :
090→093→094→098→099→100→**101**.
