"""
src/metaprog/llm_proposer_fn.py — Le dernier morceau d'armement du #8 : la fonction `llm_fn` (EDR 065).

`LLMProposer(llm_fn=...)` (EDR 059) attend une fonction `llm_fn(prompt:str) -> str`. On fournit ici :
  - `anthropic_llm_fn(...)` : LE branchement réel d'un LLM (Anthropic). >>> NON INVOQUÉ ICI <<< —
    gated sur la clé ANTHROPIC_API_KEY ; à n'exécuter QUE dans un CONTENEUR JETABLE (règle EDR 044).
  - `scripted_llm_fn` : un LLM *scripté* déterministe (sûr) — pour TESTER et DÉMONTRER la boucle armée
    de bout en bout sans aucun appel externe. Remplacer l'un par l'autre = armer/désarmer en 1 ligne.
  - `claude_code_llm_fn(...)` (P2.66) : un terminal CLAUDE CODE (`claude -p`, prompt par STDIN, outils
    désarmés) — déjà sur la machine et authentifié ; périmètre = paramètres JSON bornés (EDR 065).
    Testé contre un FAUX exécutable (tests/sandbox/test_claude_code_llm_fn.py) : aucun appel réel.
"""
import os


def anthropic_llm_fn(model="claude-opus-4-8", max_tokens=400):
    """Renvoie un `llm_fn` qui appelle un vrai LLM Anthropic. NE PAS exécuter hors d'un conteneur
    jetable (le LLM propose des *demandes de monde* dont le code tourne ensuite — règle EDR 044).
    Gated : sans ANTHROPIC_API_KEY -> lève à l'appel (jamais d'appel silencieux)."""
    def llm_fn(prompt: str) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ARMEMENT LIVE DU #8 : definir ANTHROPIC_API_KEY + executer dans un CONTENEUR "
                "JETABLE (EDR 044). Refus d'appel LLM externe sans cela.")
        import anthropic                                   # import paresseux (optionnel)
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
    return llm_fn


def local_llm_fn(base_url="http://localhost:1234/v1", model="gemma-4-12b-obliterated",
                 max_tokens=400, temperature=0.7, timeout=180):
    """Renvoie un `llm_fn` qui interroge un LLM LOCAL (LM Studio :1234 / Ollama :11434, API
    OpenAI-compatible). SÛR pour le #8 `world_demand` SANS conteneur : aucun appel externe (machine
    locale), et le LLM ne produit que du JSON de PARAMÈTRES bornés (jamais du code) -> validé par
    `sanitize_demand_params`. (Le conteneur EDR 044 ne concernait que le kind `activation`/code.)"""
    import json
    import urllib.request

    def llm_fn(prompt: str) -> str:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"})
        r = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    return llm_fn


def scripted_llm_fn(prompt: str) -> str:
    """LLM SCRIPTÉ (déterministe, sûr) pour tester/démontrer la boucle armée sans appel externe.
    Simule un générateur qui EXPLORE l'espace des demandes : à chaque appel, propose une combinaison
    différente (lecture du `prompt` pour varier). Renvoie du JSON conforme au contrat (EDR 059)."""
    # Compte les demandes déjà essayées (lignes "- nom:" dans le prompt) pour varier la proposition.
    n_tried = prompt.count("\n  - ")
    catalogue = [
        ('{"name": "lewis_ref05", "params": {"lewis": true, "referential_scale": 0.5}, '
         '"rationale": "Lewis + pression referentielle moderee"}'),
        ('{"name": "lewis_align", "params": {"lewis": true, "align_selection": 2.0}, '
         '"rationale": "Lewis + selection alignee (distinction)"}'),
        ('{"name": "lewis_combo", "params": {"lewis": true, "referential_scale": 0.3, "align_selection": 1.0}, '
         '"rationale": "combiner pression + alignement (exploration)"}'),
        ('{"name": "lewis_pure", "params": {"lewis": true}, '
         '"rationale": "demande referentielle pure (baseline forte connue)"}'),
    ]
    return catalogue[n_tried % len(catalogue)]


def claude_code_llm_fn(binary=None, timeout_s=600, allowed_tools=""):
    """Renvoie un `llm_fn(prompt) -> str` qui interroge un terminal CLAUDE CODE en mode non interactif
    (`claude -p`). Interface fixée par la session c9 (P2.66) : c'est ce que `tools/harness/propose.py`
    consomme.

    Commande : `[bin, "-p", "--output-format", "text", "--allowedTools", allowed_tools]` avec
    `bin` = `binary` si donné, sinon `AGAGI_CLAUDE_BIN` si posée, sinon `"claude"`. Le PROMPT passe par
    STDIN, jamais en argument (limite de longueur de la ligne de commande sous Windows). Sortie = stdout
    BRUT : `parse_demand_response` / `sanitize_demand_params` (`src/metaprog/rsi_loop.py`) restent seuls
    juges de ce qui en sort. Exit != 0 -> `RuntimeError` portant le stderr ; dépassement de `timeout_s`
    -> `subprocess.TimeoutExpired` REMONTÉE (jamais avalée : une réponse absente n'est pas une chaîne
    vide). Aucun secret dans le code : le terminal porte sa propre authentification.

    Sûreté : le périmètre reste des PARAMÈTRES JSON bornés par l'allow-list (`rsi_loop.py:96`,
    `ALLOWED_DEMAND_PARAMS`), aucun code n'est exécuté -> le raisonnement d'EDR-065 tient, pas de
    conteneur requis ; `--allowedTools ""` désarme en plus les outils du terminal côté proposition.
    ⚠️ Tant que l'allow-list a 5 entrées, c'est un ÉCHANTILLONNEUR D'HYPERPARAMÈTRES avec un bon prior —
    la valeur est dans P4.10 (élargir ce que le LLM peut demander)."""
    import shutil
    import subprocess

    def llm_fn(prompt: str) -> str:
        bin_ = binary or os.environ.get("AGAGI_CLAUDE_BIN") or "claude"
        # ⚠️ Résolution EXPLICITE par le PATH (PATHEXT compris). Mesuré le 2026-09-22 : sous Windows,
        # `subprocess.run(["claude", ...])` ne consulte pas PATHEXT (CreateProcess n'ajoute que `.exe`),
        # donc le shim `claude.cmd` qu'installe npm est INVISIBLE sous le nom nu -> FileNotFoundError
        # (6/8 cas rouges avec la forme littérale). `shutil.which` le trouve ; sous POSIX il rend le
        # même chemin que le shell. Un nom introuvable est laissé tel quel : l'erreur reste celle du
        # système (FileNotFoundError), jamais avalée.
        exe = shutil.which(bin_) or bin_
        cmd = [exe, "-p", "--output-format", "text", "--allowedTools", allowed_tools]
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout_s)
        if r.returncode != 0:
            raise RuntimeError(
                f"claude_code_llm_fn : {bin_} a rendu le code {r.returncode} -- "
                f"stderr : {r.stderr.strip() or '(vide)'}")
        return r.stdout
    return llm_fn
