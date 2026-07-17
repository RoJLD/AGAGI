---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-035
type: EDR
title: "Sandbox sécurisée — colmater la faille RCE avant la RSI (Vague 2 #7)"
status: legacy
gate: foundational
---

# EDR 035 : Sandbox sécurisée — colmater la faille RCE avant la RSI (Vague 2 #7)

## Contexte

La roadmap impose **la sécurité d'abord** : isoler l'exécution du code auto-généré AVANT de
brancher un vrai LLM (qui générerait du code arbitraire). Scan du metaprog → **3 failles RCE** :

1. **Live (la pire)** : `mamba_agent._get_activation_function` chargeait `generated_ops.py` via
   `exec_module` **directement dans le process principal** — aucune isolation.
2. **Subprocess sans capacités** : `compiler.validate_and_install_mutation` / `sandbox.inject_and_test`
   lançaient `pytest` (timeout 5 s) mais avec **FS/réseau/env complets** (le timeout limite le temps,
   pas les capacités).
3. **Pollution du repo** : `inject_and_test` écrivait dans `tests/sandbox/` — et ces fichiers
   (`generated_op.py`, `test_generated_op.py`) étaient **committés** → notre non-régression
   `pytest tests/sandbox/` les *exécutait*.

## Décision (V18.22) — défense en deux temps, portable (Windows inclus)

`src/metaprog/secure_sandbox.py` :
1. **Gate statique AST** (`validate_code`) : rejette le code dangereux *avant* toute écriture/exécution.
   **Allowlist** d'imports (`numpy`, `math` ; deny-by-default), blocage des **appels de capacités**
   (`exec`/`eval`/`compile`/`__import__`/`open`/`getattr`…) et des **accès dunder** (`__globals__`,
   `__class__`… = vecteurs d'évasion).
2. **Exécution isolée** (`run_sandboxed`) : valide PUIS exécute dans un **dossier temporaire
   hors-repo**, subprocess `python -I` (ignore env & user-site), **env scrubé**, **timeout**, nettoyage.
3. `first_def_name` : détecte le nom de la fonction générée (Swish, custom_activation…) pour la
   tester sans coder le nom en dur.

Câblage aux **3 points** : `compiler` (gate AST + test isolé AVANT d'écrire le fichier live),
`sandbox.inject_and_test` (délègue au runner isolé, ne touche plus `tests/sandbox/`), `mamba_agent`
(re-valide le fichier AVANT `exec_module` — défense en profondeur). Artefacts générés **retirés du
suivi git + gitignorés**.

## Résultat

- **Code malveillant** (`import os; os.system(...)`) → **rejeté par le gate AST** (False), sans
  exécution. **Code généré sûr** (Swish, bytecode tanh/relu) → validé, testé isolé, accepté.
- Le **closed-loop metaprog fonctionne AVEC la sécurité** (`test_metaprog_closed_loop` passe :
  génère Swish → AST → isolé → installé).
- Pollution du repo éliminée (`test_generated_op.py` retiré). **114 tests verts** (+6 sécurité).

## Limites

- L'isolation OS-complète (conteneur / seccomp / cgroups) reste la **cible long terme** ; sur
  Windows sans conteneur, la **digue est l'AST gate** (deny-by-default), le subprocess `-I` est la
  ceinture. Un LLM adversarial déterminé reste un risque résiduel → exécuter la RSI réelle (item 8)
  dans un conteneur jetable quand on y arrivera.
- Allowlist d'imports volontairement étroite (`numpy`/`math`) : à élargir prudemment si besoin.

## Suites (Vague 2)

- **#8 Vraie RSI** : brancher un vrai LLM dans la boucle metaprog, code **réellement réinjecté**
  après passage par ce sandbox — désormais possible *en sécurité*.
- **#9 Supervisor réflexif** : remplacer l'`analyze_metrics` if/else par un nœud LLM lisant la
  tendance multi-ères dans KuzuDB (l'ontologie EDR 032/034 est prête).

## Variables d'expérience

Allowlist d'imports, ensemble d'appels/dunders interdits, timeout, niveau d'isolation (subprocess
`-I` vs conteneur).
