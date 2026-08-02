"""Persist simulator-fitted prior uplift values in the intervention catalogue."""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


# Means fitted from the Phase 7 counterfactual response profiles and rounded to
# two decimals. These values are also the frozen Phase 11 worked-example inputs.
FITTED_PRIOR_UPLIFTS = {
    "REVIEW_SUMMARY": 0.28,
    "PRODUCT_COMPARISON": 0.26,
    "DELIVERY_REASSURANCE": 0.27,
    "RETURN_POLICY_REASSURANCE": 0.19,
    "PRICE_DROP_ALERT": 0.24,
    "SIMILAR_PRODUCT_RECOMMENDATION": 0.21,
    "EMI_SUGGESTION": 0.25,
    "ALTERNATE_PAYMENT_METHOD": 0.33,
    "CHECKOUT_ASSISTANCE": 0.22,
    "WISHLIST_REMINDER": 0.14,
    "LIMITED_TIME_DISCOUNT": 0.38,
    "NO_ACTION": 0.0,
}


def _write(values: dict[str, float]) -> None:
    table = sa.table(
        "intervention_catalogue",
        sa.column("intervention_id", sa.String()),
        sa.column("prior_uplift", sa.Float()),
    )
    for intervention_id, prior_uplift in values.items():
        op.execute(
            table.update()
            .where(table.c.intervention_id == intervention_id)
            .values(prior_uplift=prior_uplift)
        )


def upgrade() -> None:
    _write(FITTED_PRIOR_UPLIFTS)


def downgrade() -> None:
    # Phase 5 catalogue defaults were the same rounded values; restoring them
    # keeps downgrade deterministic while removing the migration provenance.
    _write(FITTED_PRIOR_UPLIFTS)

