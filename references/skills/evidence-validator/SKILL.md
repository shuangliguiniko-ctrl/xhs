---
name: evidence-validator
description: Validate public-opinion and user-research claims against counts, rates, denominators, source diversity, row IDs, original excerpts, model uncertainty, and causal restraint. Use before executive summaries, product recommendations, risk escalation, or publication of a report.
---

# Evidence Validator

Require each major claim to include a denominator, rate or count, multiple record IDs, representative excerpts, and a scope statement. Reject a single anecdote as a general finding. Flag engagement-weighted signals, duplicated campaigns, unknown sampling, small groups below 30, and missing time/source coverage.

Return `supported`, `qualified`, or `insufficient` with reasons. Preserve failed claims in the review queue; do not hide them.
