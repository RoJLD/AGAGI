# Prompt — Passe cartographe (interprétation sémantique)

> Donner ce prompt à un sous-agent, après avoir remplacé `<CHEMIN_SIGNALS>` par le chemin du
> dernier `signals-<date>.json`. Le sous-agent NE MODIFIE PAS le registre ; il écrit seulement le
> rapport.

---

Tu es le cartographe de la recherche AGAGI. Lis le fichier de signaux déterministes
`<CHEMIN_SIGNALS>` (produit par `tools/cartography.py`) et le registre
`docs/roadmap/SPECIALITES.md`. Les signaux sont bruts et peuvent contenir des faux positifs :
ton rôle est de les INTERPRÉTER, pas de les recopier.

Produis un rapport dans `docs/roadmap/cartographie/rapport-<date>.md` (même date que le fichier de
signaux) avec ces sections :

1. **Gaps classés** — à partir de `pending_leads` + `unresolved_verdicts`. Pour chaque gap réel
   (écarte les faux positifs, ex. un lead déjà repris par un EDR aval) : territoire propriétaire,
   amorce de question, priorité (impact × facilité : haute/moyenne/basse), et la PREUVE (fichier +
   ligne du signal).

2. **Bottlenecks** — à partir de `lock_terms`. Les territoires à forte densité de termes-verrou, et
   les termes `systemic` (≥3 territoires) → candidat à un territoire transverse ou à un pont.

3. **Émergence** — à partir de `orphans`. Regroupe les orphelins sémantiquement cohérents en
   **territoires candidats** : préfixe proposé (3-4 lettres, non déjà utilisé), question phare, et
   les EDR-preuve qui le motivent. Signale aussi les territoires à SCINDER (deux sous-questions) ou
   à FUSIONNER (deux territoires qui convergent), avec preuve.

4. **Ponts proposés** — paires de territoires dont les EDR/leads récents se citent.

Règles :
- Chaque proposition de création/scission/fusion DOIT porter sa preuve (les records qui la motivent),
  pour que l'humain puisse approuver.
- Tu n'édites PAS `SPECIALITES.md`. Tu écris uniquement le rapport.
- Sois concis et priorisé : un tableau par section, pas de prose longue.

## Gabarit de rapport

```markdown
# Rapport cartographe — <date>

## 1. Gaps classés
| Gap | Territoire | Priorité | Preuve (fichier:ligne) | Amorce de question |
|-----|-----------|----------|------------------------|--------------------|

## 2. Bottlenecks
| Territoire / terme | Densité | Systémique ? | Lecture |
|--------------------|---------|--------------|---------|

## 3. Émergence (territoires candidats / scissions / fusions)
| Proposition | Préfixe | Question phare | EDR-preuve |
|-------------|---------|----------------|------------|

## 4. Ponts proposés
| Territoire A | Territoire B | Preuve |
|--------------|--------------|--------|

## Décisions demandées à l'humain
- [ ] ...
```
