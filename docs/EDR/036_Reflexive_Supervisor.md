# EDR 036 : Supervisor réflexif (tendance multi-ères) + positionnement MiroFish (Vague 2 #9)

## Contexte

Vague 2 #9 : rendre le superviseur **réflexif**. L'`analyze_metrics` était un if/else **myope**
(commentaire « Mock LLM Call ») : famine cognitive détectée sur un *snapshot* (`std<0.02 and
mean<0.95` de l'historique en mémoire). Le #8 (vrai LLM dans la boucle) est **différé** par
décision utilisateur (à armer à la prochaine impasse, dans un conteneur jetable).

## Décision (V18.23)

`src/graph_rag/reflexive_supervisor.py` :
- `read_recent_scores(db)` : historique **multi-ères** depuis KuzuDB (`Result.mean_score`).
- `compute_trend(scores)` : régression linéaire → **direction** (improving / plateau / declining)
  + pente + stats.
- `reflexive_decision(trend)` : décision fondée sur la **tendance**, pas l'instantané. **>>> SEAM
  LLM (#8) <<<** clairement marqué : il suffira de remplacer ce corps heuristique par un nœud LLM
  lisant `trend` + le contexte (ontologie KuzuDB EDR 032/034).

Câblé dans `supervisor.analyze_metrics` : lit la tendance KuzuDB (fallback historique mémoire si
pas de DB), remplace la détection de famine snapshot, et gère un nouveau cas : **déclin → ↑
exploration** (que le snapshot myope manquait).

## Résultat

- Décisions tendance-conscientes (`test_reflexive_supervisor`) : plateau bas → famine ; plateau
  haut → rien ; hausse → rester le cap ; **déclin → boost mutation**. Le closed-loop metaprog
  fonctionne toujours. **120 tests verts**.
- Le superviseur n'est plus aveugle au *sens* de l'évolution sur plusieurs ères.

## Positionnement lointain — MiroFish (référence, Arc 5+)

[MiroFish](https://github.com/666ghj/MiroFish) : moteur d'**intelligence d'essaim** LLM (graines du
réel → monde parallèle → milliers d'agents à personnalités/mémoire → émergence sociale &
prédiction). **Inverse paradigmatique d'AGIseed** : top-down (intelligence *donnée* par LLM) vs
bottom-up (intelligence *trouvée* par évolution). Noté dans la roadmap (Vague 4 / référence
lointaine) comme **point de synthèse possible à l'Arc 5** : réutiliser son infra (monde parallèle,
orchestration, UI/prédiction) comme substrat d'application, ou s'inspirer de son modèle social.
**Étude différée** — à ne pas toucher avant que la coopération émergée (EDR 028) mûrisse.

## Suites

- **#8 Vraie RSI** : remplacer le seam (`reflexive_decision`) par un vrai LLM + réinjection du code
  via le sandbox sécurisé (EDR 035), dans un conteneur jetable. À armer à la prochaine impasse.
- Enrichir le contexte lu par le superviseur (ontologie : hypothèses réfutées, axes sous-explorés).

## Variables d'expérience

Fenêtre de tendance (n ères), seuils de pente (improving/declining), source du score (mean vs max),
heuristique vs LLM pour `reflexive_decision`.
