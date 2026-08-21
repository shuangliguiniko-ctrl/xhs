---
name: predictive-modeler
description: Run gated, leakage-aware classification or regression on enriched Xiaohongshu research data with explicit targets/features, structure-aware splitting, naive/linear/nonlinear baselines, untouched holdout evaluation, and correctly named permutation or SHAP explanations. Use only when the study has enough rows and a meaningful predictive question.
---

# Predictive Modeler

Read `../../analysis-modes.md` and apply its predictive gate before fitting anything.

Require an explicit task, target, feature list, feature-availability time, ID/date/group fields, split type, positive class when relevant, and primary metric. Exclude identifiers, raw text, target-derived fields, future information, and post-outcome variables unless the user establishes their availability at prediction time.

Match holdout design to the study: chronological for future prediction, group holdout for repeated users/objects, stratified IID only for ordinary independent classification. Fit preprocessing inside the training pipeline. Compare a naive baseline, interpretable linear model, and nonlinear model using training-only cross-validation; evaluate the selected model once on the untouched holdout.

Stop and write `status: skipped` with a reason when the target, class support, total rows, split, or features are unusable. Never lower sample gates silently.

Use SHAP only when it is actually computed on validation or holdout observations with a documented explainer and background set. Otherwise report holdout permutation importance by that name. Describe all explanations as predictive associations, not causes.
