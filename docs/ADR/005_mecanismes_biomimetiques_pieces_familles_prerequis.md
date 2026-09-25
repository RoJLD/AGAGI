---
id: ADR-005
type: ADR
title: Les mecanismes biomimetiques entrent dans AGAGI comme PIECES du registre, comme FAMILLES sous controle positif, ou comme PREREQUIS a cout nul -- jamais comme architecture ; la file reformulee par la revue du 2026-09-16
status: accepted
gate: foundational
motivates: []
triggers: []
tests: []
adopts: [ADR-004, REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---
# ADR-005 — Biomimétisme : pièces, familles, prérequis — jamais une architecture

**Date** : 2026-09-16. **Décideur** : robla — design approuvé en séance, décisions déléguées (« fais ce qu'il y a de mieux, avec l'accord des autres sessions ») ; accepté avec les deux amendements de la session propriétaire du registre (agagi-c9 : billet nommé par ligne ; sham = `matched_sham`, pas une pièce). **Amont** :
[ADR-004](004_fourche_strategique_demande_generee_ou_concue.md) (harnais Task/Learner, registre de pièces, règle
d'entrée E2) et son spec `docs/superpowers/specs/2026-09-16-harness-contracts-design.md` (§2.2 registre, §2.6
« l'artificiel forme-t-il l'organique ? »). **Backlog** : P2.75–P2.77 (prérequis, livrés), P4.11–P4.15 (la file).

## Contexte (mesuré, pas raconté)

**La proposition reçue.** Une architecture hétérogène à « zones » — SNN + LNN en périphérie (réflexes), Mamba en
hippocampe (séquences), Transformer en néocortex (abstraction) — supervisée par quatre mécanismes biologiques :
dendrites multi-compartiments, hormones (hyper-réseaux modulant précision / vitesse / verrouillage), plasticité
STDP (apprentissage continu sans oubli), cellules gliales (allocation d'énergie et de calcul). Le « mur » qu'elle
nomme : rétropropagation continue vs apprentissage local discontinu.

**Ce que le dépôt dit déjà, trois fois, sur la forme « architecture ».** L'évolution n'enrichit pas le substrat
([[EDR-EVO-001]]) ; le verrou est le régime de recherche ([[EDR-EVO-016]] : 0/12 lecteurs quand lire double la
vie) ; « substrat CAPABLE, verrou = BANC » (EDR-200→202) ; la thèse « migrer torch » réfutée. ADR-004 en a tiré la
règle : une famille n'entre qu'avec son propre contrôle positif (E2). Le registre de pièces d'ADR-004 porte DÉJÀ
cinq analogues biologiques — `bilinear` (intégration dendritique), `td_critic` (RPE dopaminergique),
`state_noise_regulator` (homéostasie du sommeil), `warm_start_prior` (pré-câblage), `neuromod_plasticity`
(règle à trois facteurs, « hypothèse de robla », Task à `split="shift"`).

**La revue du 2026-09-16 — 7 lecteurs, 10 sceptiques, 1 critique de complétude (18 agents, 591 lectures, 0 run).**
Un premier tableau de lecture, bâti sur des extraits de grep, disait où chaque brique « existait déjà ». Les
sceptiques ont rendu **1 réfutation et 9 nuances** ; le critique a contesté **les cinq items** de l'ordre initial
avec des preuves du dépôt. Ce qui a changé de statut :

| brique | ce que le tableau disait | ce que le dépôt soutient (preuve) |
|---|---|---|
| LNN | « c'est déjà le substrat » | un leaky-integrator à δ_j = σ(W_jj) CONSTANT par nœud ; la propriété « liquide » (τ dépendant de l'entrée) est ABSENTE. Un seul levier, une ligne (`mamba_agent.py:533`), deux écrivains (TD et mutation) |
| SNN | « seuils spiking déjà là » | `thresholds` = biais SOUSTRACTIF sous `tanh` ; ni potentiel, ni tir, ni reset ; bytecode V6 jamais lu. « Greffer sur le substrat spiking » = greffer sur du VIDE |
| Transformer | « organe quasi jamais sélectionné » | organe legacy seulement (torch l'omet), **0/60 génomes HoF** le portent, jamais mesuré ON — ni sélection ni contre-sélection : absence |
| dendrites | « le plain est prouvablement incapable (0,389) » | **RÉFUTÉ** : le plain COMPOSE (9/9 à K=3, 16/16 à K=4, 34/36 = 0,944 > bilinéaire 0,932) ; EDR-BILINEAR est une séparation d'APPRENABILITÉ à budget fixe. Aucune borne supérieure prouvée sur la forme complète de `_step` : « une tâche où le bilinéaire est prouvablement incapable » n'est pas constructible |
| hormones | « W_router vivant, dreaming régulateur » | `W_router` = None sur tout agent frais (gain ≡ 1), absent de torch, ablation NEUTRE sign_p 1,0 (EDR-135) ; `DREAM_NOISE` = constante 0,05, organe OFF sur 60/60 HoF. Un lr modulé par l'état a DÉJÀ été mesuré en proxy : EDR-194 (LR_CLOSES sur le tronc), COG-001 (LR_INSUFFICIENT sur les readouts) — « le LIEU de la modulation décide » |
| STDP / crédit local | « Hebbien battu 10/10 » | la règle vivante du legacy est un Actor-Critic TD(0) à crédit d'ACTION (EDR-020) ; le Hebbien h·hᵀ est une branche morte. EDR-148 nomme TD(λ) comme remède jamais tenté ; NAV-005 : un modulateur BIAISÉ effondre le crédit, et le critic torch est saturé (56 % < −0,99) |
| glia | « rien » | un ALLOCATEUR DE CALCUL existe : l'organe de rêve choisit K∈[1,8] par agent (logit `do_dream` gaté par la surprise), facturé `brain_cost = base·(1+log2(1+compute_spent))` — legacy seulement, conduite de minorité, et le calcul ne coûte rien in-world (−0,1 % du drain, EDR-099) |
| lifelong / rétention | « verrou LOCK-001 » | deux rétentions : celle d'INFORMATION en état n'a plus de déficit (LOCK-002 : 12/12 à lr 0,0005) ; celle du BASSIN APPRIS sous crédit in-world est ouverte (S2-CREDIT-RETENTION : 36 → 8) — et **P4.9 est FINI** : le bras SANS signal n'érode pas (S_zero 33,25 ≈ gelé 36,0), le signe inversé érode autant que le complet, l'érosion est portée par la voie ÉPISODIQUE à 8 % du mouvement de poids |
| sommeil / élagage | « l'évolution élague et gèle » | « 60× plus sparse » compare à un frais DENSE qui n'est pas l'ancêtre (init I→O seul, densité ≈ 0,2) ; les frais sont déjà contractifs : l'évolution CONSERVE, elle ne gèle pas |

**Trois prérequis trouvés en passant, tous à coût nul, tous livrés dans la même passe** (P2.75–P2.77) :
(1) **E29** — l'activation du legacy est `generated_ops.py` (Swish), écrit par la boucle métaprog, ignoré par git,
absent de HEAD, rechargé à CHAQUE pas : tout record legacy a tourné sous une activation qu'un clone n'a pas, et un
run peut en changer en cours de route. Livré : `ACTIVATION_PIN`, `activation_provenance()` dans `regime`,
`pinned_activation()` dans `_pinned_substrate`, 13 contre-exemples. (2) **E19 occ. 7** — sous torch le pas EFFECTIF
par agent est **lr/B** (perte moyennée sur B, SGD, W disjoint) : « 0,04 » vaut 0,0033, jamais publié ; deux
backends étaient comparés « à lr égal » avec un facteur 12. Vérifié par PRÉDICTION (ΔW(B=1) = 12,000·ΔW(B=12)),
publié (`lr_effective_per_agent`). (3) sept sites hors records gravaient encore « plafond 0,389 / PROUVABLEMENT
incapable », rétracté deux fois — alignés (chiffres inchangés, lecture corrigée).

## Décision

**Règle d'admission.** Un mécanisme biologique n'entre dans AGAGI que sous UNE de trois formes :

- **(a) PIÈCE** du registre d'ADR-004 — avec son billet (une Task à réponse connue que la variante « sans » échoue et
  que la pièce réussit), sa variante « sans » qui change un logit, son sham à paramètres appariés, sa dose appariée,
  son analogue biologique avec solidité, et sa prédiction de lésion (maillon `inferred`). Nécessité énoncée « à
  l'ACQUISITION à dose D, sweep {…} », jamais nue ; « du puzzle » ssi nécessaire dans ≥ 2 familles.
- **(b) FAMILLE** — une architecture entière (SNN + STDP, SSM, transformer, `Learner` composé à zones) n'entre
  qu'avec son propre contrôle positif d'acquisition (E2) et un compteur de dose DANS sa méthode d'apprentissage.
- **(c) PRÉREQUIS à coût nul** — publier une grandeur déjà calculée (activation, pas effectif, coût de calcul) dans
  le bloc `regime` ; c'est la forme E8 : une prémisse est une mesure.

**Jamais comme architecture.** La proposition à zones est REFUSÉE comme objet d'étude — pas parce qu'elle est
fausse, mais parce que le dépôt a mesuré trois fois que le substrat n'est pas le verrou, et que quatre des cinq
« briques déjà là » sont du vide ou du legacy que ni le harnais ni les records récents n'exécutent. Elle reste
admissible comme famille (b), au prix d'un contrôle positif — papier 2.

**La file, reformulée par la revue** (ordre = coût croissant × verrou nommé) :

| # | reçu comme | entre comme | verrou / question | coût | backlog |
|---|---|---|---|---|---|
| 1 | STDP + dopamine = crédit local | **trace d'éligibilité de politique TD(λ)** dans `TorchPopulationModel._td_update` (trace sur (1{a}−π)⊗pré et sur ∇V), flag de classe `CREDIT_TRACE_LAMBDA` (0,0 = bit-identique), 4ᵉ kwarg de `count_learning_events`, calibrée à **0 simulation** (no-op exact, ΔW prédit, décroissance λ^k, lr=0 → dW=0). Les deux autres « trois facteurs » — Hebb×δ (prédit INERTE par EDR-020) et Miconi m(t) appris (la pièce `neuromod_plasticity` d'ADR-004) — sont des BRAS du même dispositif, pas des pistes | crédit DIFFÉRÉ (EDR-148 : TD(λ) nommé, jamais tenté) ; érosion P4.9 (voie épisodique coupée, η apparié en Σ\|ΔW\|) | 0 run (calibration) ; proxy D=2 ≈ 1 h CPU sans bail ; P1.6 ≈ 50 min kuzu | P4.11 |
| 2 | dendrites | **sham LINÉAIRE de même rang** pour la pièce `bilinear` (~30 lignes, 1 cas de calibration) — ferme `PARAMS_NON_APPARIES` de la cellule R1 d'ADR-004 | (contrôle, pas une pièce) | minutes | P4.12 |
| 3 | hormones | **δ_j = σ(W_jj)**, le seul levier « hormonal » à une ligne : d'abord PUBLIER la distribution de δ sur le HoF (3 entiers/nœud, 0 run) ; puis un facteur par agent piloté par un signal qui EXISTE sous torch (EMA\|δ\| ou Δénergie — jamais `surprise`, morte sous torch), flag OFF bit-identique, jugé par la garde E19 à deux réglages ; lire EDR-194 / COG-001 avant | E19 sous garde ; « le LIEU de la modulation décide » | 0 run puis 1 run | P4.13 |
| 4 | glia | **PUBLICATION** de `compute_spent` / `brain_cost` à côté de toute dose d'apprentissage — 0 ligne de moteur ; aucune pièce `compute_allocation` tant que torch ne porte pas de calcul allouable (`compute_spent = 0`) | (c) prérequis | 0 run | P4.14 |
| 5 | SNN/STDP, SSM, Transformer, zones | **FAMILLES**, hors plan : E2. Aucune greffe sur `thresholds` / `H_potentials` du legacy | — | — | — |
| 0 | — | **graver `EDR-S2-CREDIT-ABLATION`** (P4.9 fini, 12 seeds, 11,3 h, verdict lu, JSON non suivi) : son résultat MOTIVE l'item 1 (sans signal, pas d'érosion) | prérequis | 0 run | P4.15 (propriétaire : la session P4.9) |

**Ce que la première expérience NE tranche PAS, scellé d'avance.** Sur le banc P1.6 (tâche same-tick i.i.d.), une
trace n'a rien à transporter : l'issue positive n'y est pas productible ; le run y QUALIFIE l'implémentation (no-op
exact, non inerte, non dégradante — précédent EDR-130 : λ=0,7 dégrade sur du 1-pas — invariante à deux pas). L'issue
positive n'est productible que sur une tâche DIFFÉRÉE : le proxy D=2 (`tools/lang_memory_edge_run.py`, LOCK-002,
CPU pur) vient AVANT P1.6. Les deux issues sont nommées : TRACE_AIDE (sep ≥ +0,05 vs natural, ≥ 10/12, invariant
aux deux pas) et TRACE_NUIT / TRACE_NEUTRE / LEARNER_INERT.

## Ce que cette décision RÉFUTE ou SUSPEND

- « Le substrat spiking est déjà là » (NAS.md D5) : FAUX — il n'y a pas de dynamique impulsionnelle ; D5 devient une
  famille (b), pas un pivot.
- « Le plain est prouvablement incapable » comme prémisse d'une pièce dendritique : RÉTRACTÉ ; le contrôle manquant
  est le sham linéaire, pas une tâche plus dure.
- « Après P4.9 » comme séquencement : P4.9 est fini ; ce qui manque est son record.
- L'item « glia comme instrument » de la première lecture : ADR-004 `accepted` n'est plus « instrument » mais
  harnais ; et le calcul ne coûte rien in-world — rien à instrumenter avant qu'une grandeur agisse.
- MEMORY.md (« ADR-004 PROPOSÉE, non tranchée ») est périmée : tranchée le 2026-09-16.

## Conséquences

- **Lignes candidates au registre de pièces** (format `Piece` du spec, statut « attend » — et, amendement de la
  session propriétaire du registre : **pas de « attend » sans BILLET nommé**, une Task à réponse connue que la
  variante « sans » échoue et que la pièce réussit ; à porter dans `docs/REF/REF-HARNESS-PIECES.md` par la session
  qui l'écrit — pas de fichier créé ici) :

| pièce | forme artificielle | analogue (solidité) | « sans » | sham apparié | capacité servie | **billet** | in_repo_today |
|---|---|---|---|---|---|---|---|
| `eligibility_trace_credit` | trace e ← γλe + ∇logπ (et ∇V), ΔW = η·δ·e dans `_td_update` ; **à écrire** (flag `CREDIT_TRACE_LAMBDA`) | traces d'éligibilité / synaptic tagging & capture + fenêtre dopaminergique (Yagishita 2014) — **solide** comme phénomène, **moyenne** comme règle ; lésion : blocage de la DA post-STDP abolit le crédit différé, pas l'immédiat | `λ=0` (bit-identique à TD(0)) | même trace, δ PERMUTÉ dans le temps | crédit différé sans BPTT | **contingence 2-pas sous crédit TD** — `CompositionTask(K=6, same_tick=False)` (key t0, q t1, récompense t1) avec `credit="td"` : la variante « sans » (TD(0) 1-pas) ÉCHOUE — réponse connue négative **EDR-148** (« TD 1-pas différé + critique faible n'apprend pas la contingence 2-pas ») ; réponse connue positive sur la MÊME Task = `bptt_credit` (épisodique k=8, **EDR-158**). La pièce entre si λ>0 franchit la barre à dose appariée en Σ\|ΔW\| | absent ; même analogue que `bptt_credit` → **deux formes artificielles pour un analogue** (§2.6) |
| `time_constant_modulation` | facteur par agent sur δ_j = σ(W_jj) piloté par EMA\|δ\| ; **à écrire** | adaptation de la fuite membranaire / neuromodulation de τ (ACh, NE) — **moyenne** | facteur ≡ 1 | facteur PERMUTÉ entre agents | rétention sous changement de régime | **Task à `split="shift"`** (mapping key→cible remappé par bloc, réservé par le spec pour l'hypothèse neuromodulée) : DV = coups dans le bloc qui SUIT le shift ; « sans » (facteur ≡ 1) doit rester sous la barre, modulé au-dessus ; **réponse connue à PAYER** : un oracle qui remet δ à sa valeur d'init au shift (borne haute) et la référence lr=0 (borne basse) — tant que ce couple n'est pas mesuré, la ligne reste « attend » | δ_j existe (`mamba_agent.py:531-537`, `backend_torch.py:124-131`) ; distribution sur HoF non publiée (P4.13 a) |

  Le **sham linéaire de même rang** n'est PAS une pièce (amendement c9) : c'est le `matched_sham` que la ligne
  `bilinear` du spec n'a pas (`PARAMS_NON_APPARIES` permanent tant qu'il est absent). Il entre comme
  `Piece.matched_sham = {"bilinear_sham": True}` (kwargs de `build()`, forme `(H·U + H·V)·W_sh` à MÊME nombre de
  paramètres, compte asserté et non lu) sur la ligne `bilinear` — P4.12.

- Backlog : P2.75 (E29 — CLOSE : le fichier est VERSIONNÉ, `versioned` mesuré, sha normalisé CRLF→LF), P2.76 (lr/B, CLOSE), P2.77 (fixtures, CLOSE),
  P4.11–P4.15 (la file). Registre : E29 (nouvelle classe, garde exécutable, 12 contre-exemples), E19 occ. 7.
- Records : bandeau de portée sur [[EDR-CALIB-LEGACY-LEARNER]] (lr/B et activation) ; aucun verdict modifié.
- **Critère de révision — AMENDÉ le 2026-09-24** (revue de la session qui porte le harnais, réserves appliquées ; l'amendement DIT ce qu'il remplace et
  pourquoi, aucune réécriture silencieuse). *Texte remplacé* : « si l'item 1 rend TRACE_AIDE sur le proxy D=2 ET
  NEUTRE/NUIT sur P1.6, la pièce entre au registre ; si TRACE_NUIT partout, ça se grave. Sans run de l'item 1 à
  6 semaines, la file est réordonnée. » *Pourquoi il était INDÉCIDABLE — et ce n'est pas « pas encore mesuré »* :
  (i) sa jambe 1 nommait le **proxy D=2**, lieu que cet ADR a lui-même RÉTRACTÉ comme no-op le jour de sa rédaction
  (`language_memory_demand_probe` apprend par `learn_episode`, jamais par `_td_update` : une trace n'y serait jamais
  exercée) ; (ii) sa jambe 2 (NEUTRE/NUIT sur P1.6) a été REFUSÉE sur mesure — in-world le pas effectif est
  0,0033/agent, 75× sous le seul point où la trace ait jamais aidé, et `results/s2_credit_ablation_2.json` publie
  `trace_lambda: null`, `trace_updates: 0` : aucun run in-world n'a jamais posé λ>0 ; (iii) sa jambe 3
  (« TRACE_NUIT partout ») n'est pas réalisée : `tdlam_inf_td0` = 0/12 aux deux pas de R0. La conjonction n'est donc
  ni satisfaite ni réfutable. *Son échéance (~2026-10-28) n'est pas échue et son déclencheur est sans objet* : trois
  runs de l'item 1 ont eu lieu (R0 4534 s, R1 2699 s, R2 1190 s de mur).
  **NOUVEAU CRITÈRE, à DEUX issues nommées, sur le seul lieu qui exerce le mécanisme** — le pilote TD PAR PAS à
  D=1 (`tools/td_step_pilot.py`, `CompositionTask(same_tick=False)`), la qualification in-world n'étant admise
  qu'à dose RELEVÉE (jamais au pas par défaut) :
  * **La pièce ENTRE** ssi, à dose appariée en Σ|ΔW| PUBLIÉE : (1) λ>0 franchit la barre sur ≥ 11/12 seeds à
    **deux lr adjacents** (l'invariance au pas est aujourd'hui NON ÉTABLIE : 0/12 à lr 2,0, mais ce point n'a pas son contrôle de CHEMIN — `td0_d0@2` jamais mesuré — donc il ne réfute rien ; la reprise de P4.17 le mesure) **ET** (2) le sham
    **δ-PERMUTÉ** reste sous la barre au même point (sans quoi « transporte du crédit » et « fait un pas plus gros »
    restent indiscernables : γλ = 0,81).
  * **La pièce est REFUSÉE, et ça se grave comme résultat** ssi le sham δ-permuté égale la trace au point où elle
    aide (l'effet est le PAS, pas le transport) **OU** si l'aide reste confinée à un seul lr après un balayage
    complet à dose appariée (l'effet est un artefact de réglage, classe E19).
  * **Ni l'un ni l'autre** → la ligne reste « attend » avec ses manques nommés (P4.19), sans réordonner la file.
  Échéance inchangée : sans l'un des deux contrôles de P4.19 payé au 2026-10-28, la file est réordonnée par robla.
