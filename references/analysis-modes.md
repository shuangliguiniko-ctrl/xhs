# Analysis profiles and selection contract

## Contents

1. Two-axis selection
2. Profile matrix
3. Predictive modeling gate
4. Output contract

## Two-axis selection

Choose the topic engine and research profile independently.

- Topic engine: `fast`, `semantic`, or explicit `auto`.
- Research profile: `rapid`, `discovery`, `aspect`, `experience`, `comparative`, `network`, `predictive`, or `mixed`.

Do not infer either axis from the other. A project can use fast topics with experience synthesis, semantic topics with comparative analysis, or no predictive analysis at all.

## Profile matrix

| Profile | Best question | Required inputs | Main outputs | Stop/qualification rule |
|---|---|---|---|---|
| rapid | What is being discussed and what needs review now? | text, stable ID | volume, keywords, baseline sentiment/emotion, risk queue | label dictionary outputs as triage baselines |
| discovery | What themes exist without a fixed taxonomy? | text, stable ID | K-Means/LDA or BERTopic themes, representative records | themes remain exploratory until human review |
| aspect | What is said about known product facets? | text + aspect taxonomy | aspect × sentiment/emotion/scene matrix | unknown/unmatched remains visible |
| experience | What are users trying to do and where does experience break? | text + research objective | six-dimension extraction, journey, themes, HMW, open questions | fewer than two signals is isolated evidence, not a theme |
| comparative | How do declared cohorts differ? | group field + denominator | group counts, rates, effect sizes, uncertainty | groups under 30 are small and must be qualified |
| network | Which needs, pains, and features co-occur? | multi-label fields | node/edge graph and clusters | co-occurrence is not causation or sequence |
| predictive | Can predeclared inputs predict a target out of sample? | explicit target/features/split | audit, baselines, holdout metrics, importance | stop on leakage, unusable target, or inadequate sample |
| mixed | Which declared combination answers the decision? | profile list | merged modules with shared IDs | record every selected/skipped module |

## Predictive modeling gate

Require:

1. A named target and task type (`classification` or `regression`).
2. An explicit input feature list and any date/group/ID fields.
3. Feature availability before the predicted outcome.
4. At least the configured minimum total rows, test rows, and class rows.
5. A split matching time, group, or IID structure.
6. A naive baseline, an interpretable linear model, and a nonlinear model.
7. Cross-validation on training data and one untouched holdout evaluation.
8. Association language only. No causal claim from SHAP, permutation importance, PDP, ALE, or coefficients.

Exclude target-derived labels, post-outcome engagement, IDs, URLs, raw text, and future values unless the study explicitly defines them as available at prediction time. If SHAP is unavailable, output permutation importance and label it accurately.

## Output contract

Each module writes: module, version, config, metrics, tables, charts, evidence, findings, warnings, limitations, and status. `status` is `complete`, `skipped`, or `failed`. A skipped module must include a machine-readable reason and recommended next action.

