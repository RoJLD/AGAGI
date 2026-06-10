# EDR 038 : Portée du signal — la communication brise l'impasse (Vague 3, levier B)

## Contexte

L'EDR 037 a trouvé l'impasse (chaîne qui plafonne) ET que le canal de langage *activé* ne créait
que du bruit. Hypothèse (levier B, le plus doux) : le signal était inutile car **sans portée** —
on n'entend les alliés (`in_hear`) qu'une fois **déjà sur la même case**, donc trop tard pour
coordonner. On donne au signal une **portée** physique, sans scripter son *sens*.

## Décision (V18.24)

`world.hear_radius` (défaut 0 = legacy same-cell). Si > 0, `in_hear` perçoit les agents proches
(distance Manhattan ≤ radius), **atténué** par la distance. Capacité physique de **recruter** le
pack vers l'apex. La *pression* existe déjà (la coopération paie, EDR 028) ; le *sens* (quel token
= « Mammouth ici ») reste à émerger par sélection — **non scripté**.

## Résultat — l'impasse est brisée

Évolution longue (rareté 12, LANGUAGE on), tendance 2ᵉ moitié, `hear_radius=3` vs EDR 037 (radius 0) :

| Métrique | radius 0 (EDR 037) | **radius 3 (B)** |
|---|---|---|
| `mammouth` | déclin −0.048, **moy 0.90** | **improving +0.021, moy 1.47** |
| `proies_moy` | plateau ~1.0 | **improving +0.014, moy 1.31** |
| `crafts` | déclin −0.029 | déclin −0.029, moy 1.07 |

> **L'apex-hunting passe de *déclinant à 0.90* à *croissant à 1.47* (+63 %)** rien qu'en ajoutant
> la portée. Le signal, désormais audible à distance, permet de **recruter le pack** ; la coopération
> (EDR 028) récompense ce recrutement → la sélection le fixe. **L'addition minimale (portée) a suffi
> là où l'activation seule (EDR 037) ne faisait que du bruit.** Communication instrumentale naissante,
> non scriptée.

## Conséquences

- **Le levier doux (B) a brisé l'impasse** → le **#8 (vraie RSI)** n'est pas (encore) nécessaire :
  un enabler structurel minimal a relancé la progression. Bonne nouvelle pour la discipline
  « addition minimale > LLM ».
- Premier pas vers l'**Arc 5 (Tribu)** : la coopération (EDR 028) devient *communicante*.

## Limites (honnêteté)

- **Comparaison inter-runs** (vs EDR 037), pas un A/B simultané (mêmes ères, même HoF de départ,
  radius 0 vs 3) → résultat **prometteur, à confirmer** par un A/B propre.
- « Recrutement émergé » est inféré du gain de chasse coopérative ; l'alignement référentiel du
  *token* n'est pas encore mesuré finement.
- Bord du scripting : la portée est une *capacité* (physique), pas un *sens* (sémantique) — on reste
  du bon côté, mais c'est de l'addition (à anneler/justifier comme les scaffolds).

## Variables d'expérience

`hear_radius`, atténuation (Manhattan vs Chebyshev), coût du signal, A/B propre radius 0 vs 3,
mesure d'alignement référentiel.
