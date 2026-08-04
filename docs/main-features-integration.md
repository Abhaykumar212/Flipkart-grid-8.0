# Main Features Integration

Integrated on `integration/main-features-into-tavish` from target `bfe09cb` after auditing source `47a384d` and every tracked file in both branch trees.

## Ported selectively

- Offline shopping companion: grounded price, offer, EMI, delivery, stock, seller, specification, review, comparison, and search-history answers; review-dwell and comparison prompts; no API key or network required.
- PDP guidance: truthful EMI estimates, stock and seller facts, canonical-event product comparison, executable product questions, catalog-derived related products, and session-derived recently viewed products.
- Governed intervention UX: `ASSISTANT_PANEL` decisions use the persistent companion while retaining Tavish impression/click/dismiss callbacks; every existing surface can disclose safe prose from Tavish's structured explanation.

Not ported: `main`'s replacement event/ML/policy/storage/explainability/experiment/dashboard/demo stacks, LLM-led decision flow, binaries/datasets/databases/environment files, hard-coded Q&A claims, unverified “No Cost” EMI labels, or decorative notification/seller actions.

## Invariants and verification

- No changes under `backend/`, `ml/`, `alembic/`, root `tests/`, `scripts/`, dashboard routes/components, event/session/cart/intervention contexts, package manifests, CI, fixtures, or environment files.
- Frontend: 32 tests pass; TypeScript/Vite production build passes; lint passes with only the target's existing Fast Refresh warnings.
- Python: 335 non-E2E tests pass, 7 artifact-dependent tests skip in the clean integration worktree.
- Offline browser smoke: PDP, companion price/review answers, question handoff, and comparison all pass with `/api/v1/**` deliberately unavailable and zero page errors.
- Existing target baseline: protected scenario tests pass 15/17; both Scenario F paths currently produce `INTERVENE / WISHLIST_REMINDER` where the frozen fixture expects `ABSTAIN / NO_ACTION`. No protected code or artifact was changed to mask this drift.

## Commits

- `ca77b2c` — offline grounded shopping assistant
- `785798a` — grounded PDP comparison and buying guidance
- `4a3d5ce` — governed interventions unified with the companion
