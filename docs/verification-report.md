# Verification report

Status as of 2026-08-03: **implementation complete and local release gate green**. A hosted GitHub Actions run remains a post-push release check because the current changes have not been pushed from this workspace.

## Release evidence

| Gate | Result |
|---|---|
| `./scripts/test.ps1` | Passed in 215.4 s |
| Python | 193 passed |
| Ruff | Passed |
| Oxlint | Passed with 9 non-blocking Fast Refresh warnings |
| TypeScript + production build | Passed |
| Vitest | 12 passed across 7 files |
| Playwright | 6 passed against freshly allocated backend/frontend ports |
| CI coverage slice | 124 passed; 87.87% overall |
| Policy + recommendation + feature slice | 28 passed; 92% combined |
| Scenarios A–H | 24/24 across three consecutive isolated runs |
| Secrets | No provider-key pattern in runtime source; no Groq key configured during verification |

The Python run emits one dependency deprecation warning from Starlette's legacy `TestClient` compatibility import. It does not affect runtime behavior or test results.

## Model acceptance

| Model | Verified holdout results |
|---|---|
| Risk | ROC-AUC 0.7938; PR-AUC 0.9254; ECE 0.0113; Brier 0.1468 |
| Root cause | micro-F1 0.7850; macro-F1 0.7198; Hamming loss 0.0546; top-2 recall 0.9771; `UNKNOWN` 7.55% |

Both inference paths meet the 100 ms p95 contract in the model tests, and the complete decision path meets 300 ms p95 across 100 deterministic runs. The root-cause card documents the rare trust/returns class precision limitation (0.50) without hiding it through post-hoc threshold tuning.

## Reproducibility and failure safety

- A clean test run trains missing legacy and versioned artifacts automatically.
- Browser tests allocate fresh ports and do not reuse a developer's stale servers.
- Alembic upgrades and downgrades a clean SQLite database; the metadata also compiles under the PostgreSQL dialect without SQLite-only types.
- All 21 event types validate and persist; duplicates, invalid metadata, terminal sessions, and state rebuild are covered.
- Model load failure returns `ABSTAIN`; LLM failure uses grounded templates; invalid catalogue data falls back safely; all decisions remain auditable.
- Scenario fixtures provision isolated databases, promote active model versions, and warm grounded review summaries before replay.

## External release check

After the changes are committed and pushed, confirm the `CI` workflow is green on GitHub. This is the only verification item that cannot be established solely from the local workspace.
