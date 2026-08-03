# Demo script

Start the frontend and API with `./scripts/dev.ps1`. Keep the storefront and `/dashboard` side by side. Every fixture command resets, migrates, seeds, promotes both models, warms review summaries, replays the event stream, prints the full trace, and fails if the frozen expectation changes.

## Three-minute judge run-of-show

1. **Problem (20 seconds).** “Cart abandonment is not one problem. A worried buyer, a failed payment, and a low-intent browser should not receive the same coupon.”
2. **Live shopper evidence (35 seconds).** Keep the storefront and `/dashboard` side by side. Reopen reviews, browse similar products, and return to cart.
3. **Architecture proof (55 seconds).** Select the new session in the Command Center. Let the session architecture resolve automatically: validated events → 67 versioned features → calibrated risk → supported root cause → policy → utility ranking → explanation → customer action.
4. **Helpful action (35 seconds).** Show `PRODUCT_QUALITY_UNCERTAINTY → REVIEW_SUMMARY`. Select Policy to show why the discount was rejected, then show the dismissible inline card in the storefront.
5. **Safety (25 seconds).** In `/dashboard/proof/scenarios`, run F for `UNKNOWN → ABSTAIN` and G for fatigue suppression. Say: “The safest recommendation is sometimes silence.”
6. **System proof (10 seconds).** Open `/dashboard/architecture` to show the full online path, persistence, feedback loop, and guardrails in one diagram.

Close with: “This is not a coupon popup. It is an auditable decision system that knows when to help, what evidence supports the help, and when to leave the customer alone.”

If time is cut to 90 seconds, show A, F, and G. Together they demonstrate value, honest uncertainty, and governance.

```powershell
foreach ($scenario in 'A','B','C','D','E','F','G','H') {
    ./scripts/run_scenario.ps1 $scenario
}
```

| Scenario | Expected result | Point demonstrated |
|---|---|---|
| A | `PRODUCT_QUALITY_UNCERTAINTY` → `REVIEW_SUMMARY` | Grounded help instead of a discount |
| B | `DELIVERY_CONCERN` → `DELIVERY_REASSURANCE` | Context-specific delivery answer |
| C | `PRICE_SENSITIVITY` → `PRICE_DROP_ALERT` | Discount protection preserves margin |
| D | `CHECKOUT_OR_PAYMENT_FAILURE` → `ALTERNATE_PAYMENT_METHOD` | Urgent checkout help beside the CTA |
| E | `NO_ACTION` | Low-risk silence is still audited |
| F | `UNKNOWN` → `ABSTAIN` | Honest uncertainty; never invent a cause |
| G | two dismissals → `NO_ACTION` | Policy overrides confident ML for fatigue |
| H | control `WISHLIST_REMINDER`; treatment `REVIEW_SUMMARY` | Deterministic A/B arms and complete traces |

Use `-NoReset` only while developing a fixture against an already-clean database. Normal presentation commands should retain the reset for order independence.

## Demo resilience

- Keep `GROQ_API_KEY` unset to prove the deterministic offline path.
- If venue Wi-Fi fails, nothing changes; models, review summaries, database, and UI are local.
- If a model artifact is missing before judging, run `./scripts/train_all.ps1 -Scale full` once. `./scripts/test.ps1` also detects and rebuilds missing artifacts.
- Use `./scripts/reset_demo.ps1` before the presentation. It is idempotent and restores the catalogue, experiment, active models, and grounded review cache.
