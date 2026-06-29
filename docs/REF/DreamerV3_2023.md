---
id: REF-DreamerV3-2023
type: REF
title: Mastering Diverse Domains through World Models (DreamerV3)
url: https://arxiv.org/abs/2301.04104
method: world model latent appris + planification par imagination (rollouts dans le latent)
lib: danijar/dreamerv3
maturity: production
supersedes: [EDR-095]
grounds: [SDR-G4]
adopt_for: [ADR-003]
---
# REF-DreamerV3-2023 — Hafner et al. (2023)

Planification par imagination *dans un latent appris* — exactement ce que notre « dreaming »
ne fait pas : EDR-095 montre que forcer le rêve NUIT (random-shooting latent qui n'exploite
pas le world model). DreamerV3 **dépasse** ce mécanisme.

Pont AGAGI : `supersedes EDR-095` (l'organe dreaming réfuté) ; `grounds SDR-G4` (la porte
« l'agent anticipe-t-il ? » devrait s'appuyer sur Dreamer plutôt qu'un planner depth-1 maison,
déjà réfuté). Axe 3 du plan de migration.
