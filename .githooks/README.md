# Git hooks versionnés — garde-fou anti-dette CI

Ce dossier contient des hooks git **versionnés** (partagés via le repo), pour empêcher d'accumuler de
la dette CI (pousser du code qui casse le pipeline).

## Activation (une fois par clone)

Les hooks ne sont **pas** actifs tant que git ne pointe pas dessus. À faire une fois après le clone :

```bash
git config core.hooksPath .githooks
```

(Cette config est locale au clone — non poussée — d'où la nécessité de la poser une fois par machine.)

## Hooks

- **`pre-push`** — lance les tests Python du pipeline CI (`tests/test_backend.py` +
  `tests/sandbox/test_visualization.py`) avant chaque `git push`. Bloque le push s'ils échouent.
  Bypass ponctuel : `git push --no-verify`.

## Garde-fou plus fort (recommandé) : protection de branche GitHub

Le hook est local et contournable. Le **vrai** garde-fou est la **protection de la branche `main`**
exigeant que le check CI passe avant tout merge :

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -F required_status_checks.strict=true \
  -F 'required_status_checks.contexts[]=test-and-build' \
  -F enforce_admins=false \
  -F required_pull_request_reviews.required_approving_review_count=0 \
  -F restrictions=
```

À activer une fois le pipeline CI vert de bout en bout.
