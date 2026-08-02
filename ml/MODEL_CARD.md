# Cart Abandonment Prediction — Model Card

Phase 1 of the intelligent cart-recovery system. Predicts, in real time, the
probability that an active cart will be abandoned, and attributes that
prediction to specific session signals so Phase 2 can choose an intervention.

---

## 1. Headline results

Evaluated on a 40,000-row holdout the model never saw during training or
early stopping.

| Metric | Model | Bayes-optimal ceiling | Gap |
|---|---|---|---|
| ROC-AUC | **0.8072** | 0.8107 | 0.0035 |
| PR-AUC | **0.8956** | 0.8982 | 0.0026 |
| Accuracy | **0.7609** | 0.7631 | 0.0022 |
| Log loss | **0.4874** | 0.4836 | 0.0038 |
| Brier score | **0.1613** | 0.1600 | 0.0013 |

ROC-AUC 95% CI (200-round bootstrap): **[0.8037, 0.8122]**
Expected Calibration Error: **0.0070**

### Why we report a ceiling instead of just an AUC

The training data is synthetic, generated from a known stochastic process with
an irreducible noise term (σ = 0.55) representing the part of a purchase
decision no tracker can observe — a phone call, a partner's opinion, payday
timing.

Because that process is known, we can compute the **Bayes-optimal predictor**:
`P(abandon | observable features)`, obtained by integrating the noise out of the
signal with Gauss-Hermite quadrature. No model, however sophisticated, can beat
it.

Our model reaches **99.57% of that ceiling**. That number is the honest measure
of model quality here. A raw AUC of 0.81 in isolation says very little; "0.0035
away from the theoretical maximum" says the modelling is essentially done and
further gains must come from *better features*, not better hyperparameters.

> **Important caveat for reviewers:** these figures describe performance on
> synthetic data. They demonstrate that the pipeline is sound and that the model
> extracts nearly all available signal. They are *not* a claim about live
> Flipkart traffic, which would require real logged sessions to validate.

---

## 2. Feature set — and why each feature is here

22 raw features, all observable by a live session, grouped by the abandonment
driver they target. Effect directions follow the recurring Baymard Institute
checkout-abandonment survey, whose most-cited reasons are: extra costs too high
(~48%), forced account creation (~26%), didn't trust the site with card details
(~25%), delivery too slow (~23%), checkout too long/complex (~18%).

### A. Cart engagement — how invested is this shopper?

| Feature | Why it's here |
|---|---|
| `seconds_spent_in_cart` | Long dwell without checkout indicates deliberation, not intent. |
| `times_returned_to_product_page` | Re-opening the product signals unresolved doubt about the item. |
| `product_reviews_read` | Heavy review reading *late* in the funnel correlates with uncertainty. |
| `seconds_idle_before_checkout` | The classic hesitation window immediately before committing. |
| `delivery_pincode_checks` | Repeated checks reveal anxiety about whether delivery works for them. |
| `saved_items_in_wishlist` | Proxies platform engagement; engaged shoppers abandon less. |

### B. Cost friction — the single most-cited driver (~48%)

| Feature | Why it's here |
|---|---|
| `cart_value_vs_typical_order` | Basket size **relative to this shopper's own average** — captures sticker shock personally, not absolutely. ₹5,000 is routine for one shopper and alarming for another. |
| `delivery_fee_percent_of_cart` | Shipping cost as a share of basket — the literal "extra costs" complaint. |
| `price_dropped_since_first_view` | A recent drop creates urgency and *reduces* abandonment. |
| `discount_seeking_tendency` | Deal-driven shoppers abandon more when no deal materialises. |
| `failed_coupon_attempts` | "Couldn't find a working coupon" is a documented trigger — and directly fixable by Phase 2. |

### C. Delivery friction (~23%)

| Feature | Why it's here |
|---|---|
| `estimated_delivery_days` | Promised speed. Slow delivery is cited by roughly a quarter of abandoners. |

### D. Checkout & trust friction (~26% account, ~25% card trust, ~18% complexity)

| Feature | Why it's here |
|---|---|
| `payment_method_on_file` | Removes the highest-friction checkout step. **Highest-gain feature in the model.** |
| `checkout_steps_completed` | Depth into the 3-step funnel — the best available proxy for commitment. |
| `payment_attempts_failed` | A declined payment is a *hard blocker*, not a preference. Highly actionable. |
| `is_guest_checkout` | Checking out without an account relationship. |

### E. Customer history (RFM)

| Feature | Why it's here |
|---|---|
| `past_abandonment_rate` | This shopper's own historical behaviour — the strongest available prior. |
| `past_order_return_rate` | High returns indicate prior dissatisfaction and lower conviction. |
| `lifetime_orders_placed` | Frequency (F in RFM). Loyal buyers convert more reliably. |
| `days_since_last_purchase` | Recency (R in RFM). Lapsed shoppers complete materially less often. |

### F. Session context

| Feature | Why it's here |
|---|---|
| `is_mobile_session` | Mobile converts worse across the industry — smaller screens, more interruption, fiddlier payment entry. |
| `is_late_night_session` | Late-night sessions skew toward low-intent browsing. |

### Engineered features (10)

Each expresses a hypothesis about how two frictions **compound**, as a smooth
product of normalised quantities. Crucially, none of them hardcode a threshold:

| Feature | Hypothesis |
|---|---|
| `extra_cost_burden_score` | A 10% delivery fee hurts far more on an unusually large basket. |
| `product_research_intensity` | Revisiting the product *and* reading reviews together indicate an unresolved decision. |
| `checkout_friction_events` | Count of concrete blockers hit (failed payments, failed coupons, no saved card, guest flow). |
| `delivery_concern_index` | Slow delivery matters more when the shopper is actively re-checking their pincode. |
| `dwell_per_return_visit` | Separates one long considered session from rapid comparison loops. |
| `hesitation_ratio` | Share of cart time spent idle — scale-free, works for short and long sessions alike. |
| `price_sensitivity_exposure` | Deal-seeker facing an above-average basket: the classic discount-abandonment profile. |
| `customer_loyalty_score` | Frequency damped by recency — a compact RFM summary. |
| `checkout_progress_ratio` | Fraction of the funnel completed. |
| `trust_barrier_score` | Spending significant money without an account relationship. |

---

## 3. A design flaw we found and removed

An earlier version of the feature set contained indicator columns like:

```python
price_shock_flag = (cart_value_to_aov_ratio > 1.8) & (delivery_fee_percentage > 5.0)
```

Those constants — `1.8`, `5.0`, and three more like them — were **copied from the
data generator's own hidden signal**. The feature set was therefore an answer
key rather than a hypothesis, and the reported score partly measured our
knowledge of the simulator rather than the model's ability to learn.

It also had no production analogue: nobody can justify the number `1.8` to a
reviewer, because in a real deployment nobody knows it.

All five such features were removed. Where a threshold genuinely matters, the
gradient-boosted trees now discover it from data — which is precisely what they
are good at. **The model's score is lower than it would have been with the flags
in place, and that is the point:** the current number is one we can defend.

---

## 4. Calibration — and why we deliberately do *not* reweight classes

Phase 2 fires interventions at probability thresholds, so a predicted 0.70 must
actually mean 70%. Ranking quality (AUC) is not sufficient.

Two decisions follow:

**We removed `scale_pos_weight`.** The previous model used it. With a mild 68/32
split it buys no discriminative power, and it systematically inflates predicted
probabilities away from the true rate — corrupting exactly the property Phase 2
depends on. Class balance is handled at the decision threshold, where it
belongs, not in the loss function.

**We tested post-hoc calibration rather than assuming it.** `train_model.py`
fits an isotonic calibrator on one half of the calibration split and evaluates
it on the other half. On the current model, isotonic made log-loss *worse*
(0.4876 → 0.4882), because removing `scale_pos_weight` already left the model
well calibrated (ECE 0.0070). The script therefore ships raw probabilities and
reports that decision. Should future changes degrade calibration, the same check
will automatically switch isotonic back on. **The test set plays no part in this
choice.**

---

## 5. Operating points for Phase 2

Precision/recall/coverage at each candidate trigger threshold, on the holdout.
Base abandonment rate is 68.1%, so "lift" is precision relative to blanket
targeting.

| Threshold | Coverage | Precision | Recall | Lift |
|---|---|---|---|---|
| 0.50 | 75.9% | 0.791 | 0.882 | 1.16x |
| 0.60 | 66.2% | 0.827 | 0.804 | 1.21x |
| 0.70 | 54.6% | 0.865 | 0.693 | 1.27x |
| 0.75 | 47.8% | 0.885 | 0.621 | 1.30x |
| 0.80 | 40.2% | 0.904 | 0.533 | 1.33x |
| 0.85 | 31.5% | 0.926 | 0.428 | 1.36x |
| 0.90 | 21.5% | 0.951 | 0.300 | 1.40x |

The served API exposes a `risk_tier` field using **high ≥ 0.80**, **medium ≥ 0.60**,
low below. At 0.80, an intervention reaches 40% of sessions and is correct 90% of
the time. The right threshold ultimately depends on intervention cost versus
recovered margin — the table exists so that decision can be made with numbers
rather than intuition.

---

## 6. Reproducing

```bash
python ml/generate_dataset.py    # writes ml/data/cart_abandonment_dataset.csv
python ml/train_model.py         # writes ml/artifacts/{model,explainer,calibrator}.joblib
python -m unittest tests.test_phase1_pipeline -v
python -m uvicorn backend.main:app --port 8000 --reload
```

Everything is seeded (`RANDOM_SEED = 42`) and reproducible.

---

## 7. Known limitations

1. **Synthetic data.** Metrics validate the pipeline, not live performance. The
   feature *directions* are grounded in published research, but the effect
   *magnitudes* are our modelling assumptions.
2. **Shopper-history features are placeholders in the live demo.**
   `past_abandonment_rate`, `lifetime_orders_placed`, `days_since_last_purchase`
   and `payment_method_on_file` require an account system that the storefront
   does not yet have; the tracker currently sends neutral defaults. The model
   uses them correctly, but in the demo they do not vary per session.
3. **`is_mobile_session` is inferred from viewport width**, not a parsed user
   agent — coarse, but it is the signal genuinely available client-side without
   an extra dependency.
4. **No temporal validation.** Real cart-abandonment models need out-of-time
   testing to catch seasonality and drift; a synthetic dataset has no meaningful
   time axis to split on.
5. **SHAP explains the uncalibrated log-odds.** When a calibrator is active,
   attributions still describe the ranking correctly (isotonic is monotone), but
   they do not decompose the calibrated probability itself.
