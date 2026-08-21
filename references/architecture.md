# Architecture and extension guide

## Contents

1. Shared service layer
2. Project state
3. Collection adapters
4. Analysis modules
5. Storage contract
6. Extension checklist

## Shared service layer

`orchestrator.py` is the only workflow coordinator. CLI, Streamlit, and agent Skills call the same functions. UI code may build and display configuration but must not implement analytical semantics.

## Project state

Every stage writes `state.json` with running/complete status and a compact detail object. Raw data is persisted before cleaning. `manifest.json` records output paths, hashes, code/model provenance, warnings, and stage state.

## Collection adapters

`crawler/adapters.py` exposes `collect_records(config, paths)`. Each adapter returns normalized posts, comments, and failures. Add adapters without changing the cleaning/analysis layers. Keep login/verification user-operated and preserve third-party licenses.

## Analysis modules

`analysis/base.py` defines `validate_input`, `run`, and `export`. A module result contains module/version/config/metrics/tables/charts/evidence/findings/warnings/limitations. Register new outputs in the orchestrator and manifest without putting logic in UI.

`analysis/engine.py` owns transparent text coding and topic selection. `analysis/advanced.py` owns text diagnostics, comparative cohorts, experience synthesis, co-occurrence networks, and gated predictive modeling. Keep these modules callable from CLI, Streamlit, tests, and agent workflows through the orchestrator.

Topic engine and research profile are independent axes. Store `mode_requested`, `mode_used`, `profile_requested`, and `profiles_used`. Every advanced module must emit `complete` or `skipped` with an explicit reason.

## Storage contract

Use platform-safe `pathlib` paths, UTF-8, atomic JSON/YAML writes, JSONL raw records, Parquet processed records, CSV enhanced records, and self-contained HTML. Keep immutable `record_id` and original text internally; redact shared evidence.

## Extension checklist

1. Add a deterministic schema and configuration.
2. Add unit and end-to-end tests with mock data.
3. Record method/version and actual model.
4. Add evidence IDs and limitations.
5. Verify no key/cookie/token is logged or committed.
6. Update Skill references and manifest coverage.
