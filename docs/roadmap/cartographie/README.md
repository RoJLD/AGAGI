# Cartographie de la recherche — mode d'emploi

Le cartographe repère automatiquement les **gaps, bottlenecks et territoires émergents** de la
recherche AGAGI, puis propose (sans jamais décider) des évolutions du registre
`docs/roadmap/SPECIALITES.md`. Design : `docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md`.

## Deux couches

1. **Signaux (déterministe)** — `tools/cartography.py`. Moissonne le corpus (registre + EDR +
   mémoire) en un JSON reproductible. Aucun LLM, aucun réseau.
2. **Interprétation (agent, à la demande)** — le prompt `PROMPT_CARTOGRAPHE.md`. Une session lead
   le lance sur le JSON de signaux ; il produit un `rapport-<date>.md` (gaps classés, bottlenecks,
   territoires candidats avec preuve, ponts proposés).

## Lancer les signaux

```bash
PYTHONPATH=. python tools/cartography.py
# options : --date AAAA-MM-JJ  --memory-dir <dossier mémoire>  --dormant-gap 30
```

Sortie : `docs/roadmap/cartographie/signals-<date>.json`. Les signaux sont bruts et advisory
(faux positifs attendus) — c'est la passe agent qui les affine.

## Lancer la passe agent

Ouvrir `PROMPT_CARTOGRAPHE.md`, y injecter le chemin du dernier `signals-<date>.json`, et le
donner à un sous-agent. Le rapport est écrit dans `docs/roadmap/cartographie/rapport-<date>.md`.

## Boucle d'approbation (règle d'or)

- La détection est **automatique** ; le rapport est **advisory**.
- **Création / scission / fusion** d'un territoire = une session lead (ou l'humain) approuve, puis
  **édite `SPECIALITES.md` à la main** (naissance officielle, commit path-scoped).
- **Le cartographe ne touche JAMAIS le registre.** Il lit, il propose ; il n'écrit que dans
  `cartographie/`.

## Bornage des signaux (proxys structurels)

Le script est volontairement grossier ; l'affinage sémantique revient à la passe agent :

- **Orphelins** : proxy structurel (EDR plus récent que tout `legacy_edr` mappé, ou préfixe inconnu),
  pas un matching de mots-clés contre `question_phare`/`fichiers`. L'agent fait le rattachement sémantique.
- **Leads** : le script LISTE les marqueurs de piste ; il ne vérifie PAS si un EDR aval a déjà repris la piste.
  L'agent croise avec l'aval pour écarter les leads déjà traités.
- **Verdicts ouverts** : lus dans le frontmatter (`verdict:`) et le titre uniquement — un marqueur enfoui dans
  le corps d'un EDR sans frontmatter n'est pas capté. L'agent peut relire les corps ambigus.
- **Dormance** : proxy par écart de numéro d'EDR (`legacy_edr` vide → « dormant »). Un territoire jeune ou
  suivi uniquement en mémoire apparaît dormant à tort ; le champ `statut` (présent dans la sortie) désambiguïse.

## Cadence

À la demande. Idéalement en fin de session lead, ou hebdomadaire. Pas de cron imposé (coût token
de la passe agent).
