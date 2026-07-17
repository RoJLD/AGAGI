---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-009
type: EDR
title: "Falsifiabilité & Observabilité du Curriculum"
status: legacy
gate: foundational
---

# EDR 009 : Falsifiabilité & Observabilité du Curriculum

## Contexte

L'EDR 008 a posé le *mécanisme* ontogénétique (enchaîner les mondes par portes de maîtrise) et `main_curriculum.py` l'a branché sur la simulation. Mais un mécanisme n'est pas une preuve. Le curriculum learning **suppose** que « maîtriser simple → apprendre complexe plus vite » ; or le **transfert négatif** existe aussi : un cerveau sur-spécialisé sur le monde N peut apprendre le monde N+1 *plus lentement* qu'un naïf (entrenchment, déjà signalé dans l'EDR 008).

Sans groupe de contrôle, on ne peut pas distinguer les deux. L'axe ontogénétique resterait une croyance — ce qui viole le Commandement 15 (valide ou revert sur preuve).

## Décision (V17.1)

L'axe ontogénétique n'a de valeur que **mesuré contre son absence**. On instrumente sa falsifiabilité.

### 1. Métrique-mère : le Ratio de Transfert

```
Ratio = eras_to_master(cible | tabula rasa)
        ─────────────────────────────────────────────
        eras_to_master(cible | a gradué le prédécesseur)
```

- **Ratio > 1** : transfert positif → le curriculum accélère. **Axe validé.**
- **Ratio < 1** : transfert négatif → l'entrenchment domine. **Revert**, ou abaisser `C_floor` (« assez bon puis on avance »).
- **Ratio ≈ 1** : la progression choisie n'apporte rien sur cette paire de mondes.

Implémenté dans `tools/transfer_ratio.py`. Le **groupe de contrôle est gratuit** : c'est le même `CurriculumRunner`, avec vs sans `import_agent_id`. L'architecture découplée (injection de `run_era_fn`) rend A/B trivial — l'architecture testable et l'architecture falsifiable sont la même.

### 2. Trois instruments dérivés

| Instrument | Mesure | Réutilise |
|---|---|---|
| **Carte de rétention** | Re-tester le monde N *après* graduation vers N+1 → quantifie l'**oubli catastrophique**. Décide quelle parade (périodes critiques / rehearsal / progressif) on garde. | `competence_for(N)` |
| **Courbe de croissance** | Le `transcript` du runner EST la timeline ontogénétique : ères-par-monde + compétence par lignée. À tracer comme une *courbe de croissance pédiatrique* (X = âge développemental cumulé, Y = compétence, rupture de pente à chaque transition). | `results/curriculum_transcript.json`, axe Frontend |
| **Localisation des skills** | Sonder *quels neurones* encodent *quel monde* après curriculum → teste l'hypothèse des périodes critiques (le skill du monde N a-t-il gelé dans un sous-réseau stable ?). | `tools/skinner_box.py` |

### 3. L'ordre du curriculum comme objet de recherche

`0→1→2→3` n'est pas forcément optimal. Comme le langage humain a une *fenêtre critique*, certains skills pourraient n'être apprenables que dans un certain ordre. L'ordre développemental devient une **méta-search** (lien axe 4.3, méta-méta-programmation) ; le Sociologue Prédictif pourrait anticiper l'ordre qui minimise les ères totales.

## Conséquences

- Le verdict sur l'axe ontogénétique devient **chiffré et reproductible** (Ratio), expliqué (rétention, localisation), et visualisable (courbe de croissance).
- La courbe de croissance matérialise enfin la **2ᵉ échelle de temps** : la phylogénèse avait ses courbes (Hall of Fame) ; l'ontogénèse a les siennes.
- **Coût** : chaque mesure de Ratio = 2 bras de simulation (curriculum + control), × répétitions pour dompter le bruit (pas de seed fixe). À budgéter.

## Questions ouvertes

- Quel `C_floor` / `eps_plateau` rend le Ratio le plus discriminant sans exploser le coût ?
- Le carry-over NTM (`KEEP_MEMORY`) déplace-t-il le Ratio ? (Mesurer avec vs sans.)
- Faut-il un seed déterministe pour réduire la variance des bras, au risque de sur-ajuster à un monde particulier ?
