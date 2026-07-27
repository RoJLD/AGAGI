# Contributing to AGAGI

Thank you for considering a contribution. Please read this page before opening a pull request — this
repository has stricter-than-usual rules, and they exist for a measured reason.

AGAGI produces **empirical claims**, not just software. Most of its conclusions come from long,
irreversible runs, and a bug in a measurement instrument does not announce itself: it produces a coherent,
plausible, wrong result. The rules below are the apparatus that keeps that from happening again. Nearly all
of them are executable, so you will meet them as failing checks rather than as etiquette.

**Negative results, refutations and self-corrections are first-class contributions.** A run that measured
null, recorded honestly with its method and absolute values, is worth more here than a positive result
without a control.

---

## 1. Setup

```bash
git clone https://github.com/RoJLD/AGAGI.git && cd AGAGI
pip install -r requirements.txt          # NumPy core
pip install -r requirements-torch.txt    # optional: torch backend
python -m pytest --collect-only -q | tail -1     # sanity: should collect ~1310 tests
```

Python 3.13 is what CI runs.

### Install the ratchet hook — do this first

```bash
cp tools/hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

This hook runs two **blocking** checks, each scoped to the files you actually staged:

1. **Record graph hygiene** — refuses a commit that introduces a new orphan record or a new id collision.
2. **Instrument calibration** — refuses a commit touching `tools/` or `src/seed_ai/` while a new
   uncalibrated instrument exists in the tree.

Emergency bypass is `git commit --no-verify`. Using it means you owe the repository a follow-up.

> ⚠️ **Three hook directories exist and they compete.** `tools/hooks/` holds the blocking ratchets,
> `hooks/` holds a non-blocking frontend/record parity warning (`make hooks`), and `.githooks/` holds a
> pre-push hook running the CI Python tests. Git resolves only **one** `core.hooksPath`, so `make hooks`
> or `git config core.hooksPath .githooks` will silently **disable the ratchets**. Recommended setup: leave
> `core.hooksPath` unset and install the ratchet hook into `.git/hooks/` as above. If you want the others
> too, merge their bodies into that single file.

---

## 2. The experimental protocol

### One variable at a time

Never introduce more than **one** experimental variable between two versions of the simulation. Every
innovation causes a temporary regression; two at once make both uninterpretable.

1. **Baseline** — run the unmodified version for at least 30 eras.
2. **Intervention** — change exactly one thing.
3. **Observation** — run the modified version for at least 30 eras, same seeds.
4. **Analysis** — compare with a paired sign test, not by eyeballing curves.
5. **Decision** — accept only if performance is superior or statistically equivalent. Otherwise revert.

### Preflight before any expensive run

```bash
python tools/experiment_preflight.py
```

Reference: [`docs/REF/REF-EXPERIMENT-PREFLIGHT.md`](docs/REF/REF-EXPERIMENT-PREFLIGHT.md). Four questions,
two of them with executable assertions:

```python
from tools.experiment_preflight import (
    assert_ablation_changes_something, assert_positive_control, assert_not_degenerate,
    assert_selection_nonempty, assert_no_aliasing, assert_predictor_measured_in_situ, declare_design)

spec = declare_design(
    question="does ablating X improve survival?",
    replication_unit="era",          # NOT "agent" — agents in a seed share training, optimiser and world
    n_independent=12,
    links={"X changes behaviour": "measured", "survival gain": "measured"})
assert spec["warning"] is None       # an 'inferred' link raises an explicit warning

assert_no_aliasing(logits, pop.H)                 # the output must not share memory with the state
assert_positive_control(lambda: gain_oracle(), expect_better_than=0.0)
assert_not_degenerate(surv_intact)                # not pinned at floor or ceiling
assert_ablation_changes_something(intact, ablated)
```

**Four rules that follow, and are not negotiable:**

- **A negative control that cannot fail is not a control.** If your ablation targets an action the subject
  never performs, the no-op is analytic. The informative control is the **inverse** manipulation — force
  the action in subjects that do not perform it.
- **A sham must reproduce the PATHWAY of the suspected artefact**, not merely "do nothing".
- **Reduce n, never remove the link.** A causal chain carries its sign, not its amplitude. Inferring the
  final link to save compute has already produced a published claim that measured null in 28 minutes.
- **Read the number of units actually executed**, not the absence of failure. `pytest -k` deselecting 1034
  tests once passed for a clean regression check.

⚠️ **Aliasing is the trap this repository falls into most often.** `forward` returns **views** of the
recurrent state: writing to an output mutates the state. Structural aliasing is caught by
`assert_no_aliasing` (`np.shares_memory`); *functional* aliasing — where ablating input X degrades an
unrelated control capability Y through shared representations — is caught by
`assert_no_functional_aliasing`. Run both.

### Bound the cost in the design

The pipeline is slow, and **cost scales with success**: as survival rises, episodes lengthen and everything
slows. Three long runs have already been abandoned (8 h, 4 h projected, 89 min).

- Cap `max_ticks` for trace runs; reserve the full `n` for the final verdict.
- **Persist trained genomes.** Losing them once cost a complete retraining.
- Measure throughput on a smoke run before committing to a long one — but never extrapolate a trend from
  a short prefix. A learning transient looks exactly like one.

---

## 3. Calibrating a new instrument

An **instrument** is any function producing a scientific claim: a verdict, a ratio, a survival figure, a
rate. If you write one, you must calibrate it in the same pass.

> **Why this is enforced rather than encouraged:** an uncalibrated instrument does not simply fail — it
> **produces** a result. The `EDR-WARM-007` aliasing bug generated a dose-response curve, correlations and
> a coherent negative control, all mutually consistent, all artefacts, and they survived a full review pass.

### Procedure

1. Build or reuse a toy world whose answer is **known**: [`tools/ground_truth_worlds.py`](tools/ground_truth_worlds.py).
2. Add cases to [`tests/sandbox/test_instrument_calibration.py`](tests/sandbox/test_instrument_calibration.py),
   declaring the `(function, branch)` pair. Branch matters — a function whose `grab_off` branch is
   calibrated is **not** calibrated for its `perception` branch.
3. Cover at least one of the three admissible forms:

   | Form | What it establishes |
   | --- | --- |
   | **Exact no-op** | specificity — the instrument reports nothing when nothing was done |
   | **Prediction** | linearity in an imposed dose, measured at a *different* operating point |
   | **Monotonicity** | direction — the verdict moves the right way as the dose grows |

4. Verify: `python tools/check_instrument_calibration.py`

**Prefer calibration by prediction over calibration by absolute value.** Identify nuisances at one operating
point, then predict at another. Absolute-value calibration has been wrong before — replacing `_resolve_biology`
does not control the energy budget, because the `action` phase weighs 5× more, and the reference standard
was wrong before the instrument was.

**Watch the operating window.** Ground-truth standards have one. Too little income and the zero-dose cell
sits at the floor, so inertia cannot be demonstrated; too much and the high-dose cell sits at the ceiling,
so collapse is invisible. Any ratio whose intact arm approaches `max_ticks` is a **compressed lower bound**,
not an amplitude — that is what the `censored` field reports.

Legacy debt is frozen; only **new** uncalibrated instruments fail the check. To declare debt deliberately:
`python tools/check_instrument_calibration.py --update-baseline`.

---

## 4. Writing a record

Every conclusion destined for the knowledge graph gets a record in `docs/EDR/`.

### Frontmatter

```yaml
---
id: EDR-THEME-NNN                  # thematic prefix: LANG- PLAN- MEM- S2- WARM- EVO- …
type: EDR
title: "Quote the title — an unquoted ':' breaks the YAML"
status: accepted | validated | active | legacy | open | refuted
gate: G0 | G1 | G2 | G3 | G4 | foundational
tests: [SDR-G0]                    # which hypothesis this tests
adopts: [REF-DEMAND-MARKER]        # which method it applies
corrects: [EDR-095]                # what it overturns, if anything
verdict: SOME_UPPERCASE_CONSTANT
---
```

A record is attached to the graph if it carries `gate:`, **or** `tests: [SDR-Gx]`, **or** is adopted by a
REF. Use `foundational` for infrastructure, NAS, architecture or methodology that legitimately belongs to
no gate. Anything else is an orphan, and the hook will block it.

**Use a thematic prefix, never a bare sequential number.** Global `NNN_` numbering caused eight id
collisions between parallel sessions and is frozen.

### Body

State, in this order: the **question**; the **method** (exact tool, exact parameters, seeds); the
**measurement with absolute values**; and — mandatory — the **caveats** and the scope beyond which the
conclusion does not travel.

**Publish absolute values, not only ratios.** This is not a style preference. When an instrument bug was
later fixed, `EDR-095` could be re-run and shown to still hold on its own arms (0.547 against 0.543
published) *only because it had published them*.

**Never delete a superseded record.** Declare `corrects:` in the new one and leave the old file in place.

### Adversarial review

Any conclusion headed for the record graph goes through a review that **runs its own probes**, not a
re-reading. Measured over one arc: **7 reviews, 7 real errors found**. None would have been caught by
cautious writing.

---

## 5. The error registry ritual

Every error found in review, and every null or contaminated run, must land in
[`docs/REF/REGISTRE_ERREURS.md`](docs/REF/REGISTRE_ERREURS.md):

1. Attach it to an existing class, or open a new one.
2. Give it a guard status: `executable`, `documented`, or `not automatable`.
3. If `executable` — write **and test** the guard in the same pass.
4. If `not automatable` — say so explicitly. That is what justifies mandatory review.

An error recurring twice as `documented` gets promoted or reclassified. There is no third time.

This registry is the counterpart, for error classes, of the calibration ratchet for instruments. Without it
the same class returned **three times** in a single arc — including once inside the record that denounced it.

---

## 6. Exclusive resources

Two concurrent world probes fight over the KuzuDB lock and **silently contaminate each other's
measurements** (measured 2026-07-21), while timing out the test suite. Any world simulation must hold the
lease:

```python
from tools.jobs.run import hold, run

with hold("kuzu", owner="my-job"):
    ...                                                    # another sim raises ResourceBusy

run("name", cmd, resources=["kuzu"], timeout_s=3600)       # on timeout, kills the process TREE
```

```bash
python -m tools.jobs.doctor        # lease and process state — read-only by default
python -m tools.jobs.doctor --kill # explicit; never the current process nor its ancestors,
                                   # never a lease whose holder is alive
```

Distinct resources do not block each other — a global concurrency cap of 1 would serialise independent
jobs for no reason. Leases are crash-recoverable via TTL, heartbeat and PID/`create_time` identity.

⚠️ `tools/sim_session.py` is **deprecated** in favour of `tools/jobs/`.

⚠️ Stop `memory_retriever` and call `_disable_kuzu()` before simulation loops. Ambient graph memory makes
runs non-reproducible; every survival measurement in one arc ran with the retriever live before this was
caught.

---

## 7. Code conventions

1. **No hard-coded physics or mutation parameters.** Inject them through `WorldConfig` or configuration
   files.
2. **Vectorise.** Population networks propagate through NumPy over the whole population at once. Avoid
   `for` loops on hot paths.
3. **Sandbox generated code.** Anything produced by the metaprogramming agent passes an AST validator
   (`secure_sandbox.py`) and runs in an isolated subprocess.
4. **Path-scoped commits.** The working tree is shared between parallel sessions — commit
   `git commit path/to/file.py`, never `git commit -a`.
5. **Never push a red suite.**

### The two forward passes

There are **two** inference paths, and testing the wrong one produces a confident, meaningless result:

| Path | Where | Used by |
| --- | --- | --- |
| `MambaBatchModel.forward` | `src/agents/mamba_agent.py` | production — excitability thresholds, contextual neuromodulation, QKV attention |
| `recurrent_forward` | `src/seed_ai/rl_evolution.py` | legacy, still used by some historical benches |

If you change agent behaviour, either reconcile both paths or state explicitly which engine your test
targets.

The torch backend is optional and **off by default** (`use_torch_inworld = False`, `ADR-003`). Note the
known asymmetry: world writes into the recurrent state are **not inert** on torch benches. Production runs
`LegacyPopulationModel` and is unaffected.

---

## 8. Tests and CI

```bash
pytest -m "not slow"        # fast suite — per-test timeout of 120 s (pytest.ini)
pytest -m slow --timeout=0  # heavy smokes
make e2e                    # Playwright E2E against docker compose
make api-types              # regenerate OpenAPI → TypeScript after changing backend schemas
```

A test legitimately exceeding ~120 s must be marked `@pytest.mark.slow`. The per-test timeout exists
because two mismarked tests once hung the whole suite, each costing ~13 minutes to find by hand.

CI (`.github/workflows/ci.yml`) runs a fast Python subset, the record/frontend parity gate, an OpenAPI
codegen drift check (`git diff --exit-code` on generated types), frontend unit tests and build, both Docker
images, and a compose smoke test. Run `make api-types` and commit the result whenever you touch a backend
schema, or CI will fail on drift.

---

## 9. Pull requests

- Branch from `main`. Keep the diff scoped to one concern.
- **Never commit without an explicit request** if you are working as an agent in someone else's session.
- Describe **what you measured**, not what you expect. If a claim is inferred rather than measured, say so
  in those words.
- Link the record your change produces or modifies.
- Confirm in the PR body: preflight run · new instruments calibrated · records attached · registry updated
  if a new error class appeared.
- Never bypass hooks (`--no-verify`) or skip signing unless you say why in the PR.

## Reporting a problem

Open an issue. Measurement problems are especially welcome: if you believe a published record is wrong,
the best report is a probe that shows it, and it will be recorded as a correction with your name on it.

That is how this repository is supposed to work.
