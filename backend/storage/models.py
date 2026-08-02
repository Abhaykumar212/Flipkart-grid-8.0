from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.enums import Channel, CostLevel, Decision, RiskBand
from backend.domain.events import EventType

from .db import Base


def _values(values) -> str:
    return ",".join(f"'{value.value}'" for value in values)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("device_preference IN ('MOBILE','DESKTOP')", name="ck_users_device"),
        CheckConstraint("lifetime_orders >= 0", name="ck_users_lifetime_orders"),
        CheckConstraint("prior_abandonment_rate BETWEEN 0 AND 1", name="ck_users_abandonment_rate"),
        CheckConstraint("discount_usage_rate BETWEEN 0 AND 1", name="ck_users_discount_rate"),
        CheckConstraint("return_rate BETWEEN 0 AND 0.5", name="ck_users_return_rate"),
        Index("ix_users_persona", "persona"),
    )

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    persona: Mapped[str | None] = mapped_column(String)
    device_preference: Mapped[str | None] = mapped_column(String)
    signup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifetime_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_order_value: Mapped[float] = mapped_column(Float, default=0)
    prior_abandonment_rate: Mapped[float | None] = mapped_column(Float)
    discount_usage_rate: Mapped[float | None] = mapped_column(Float)
    return_rate: Mapped[float | None] = mapped_column(Float)
    last_purchase_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intervention_affinity: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("selling_price <= mrp", name="ck_products_price_lte_mrp"),
        CheckConstraint("selling_price > 0", name="ck_products_positive_price"),
        Index("ix_products_category", "category"),
        Index("ix_products_brand", "brand"),
    )

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    sub_category: Mapped[str] = mapped_column(String, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    rating_value: Mapped[float] = mapped_column(Float, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quantity_left: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    free_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False)
    emi_monthly: Mapped[float | None] = mapped_column(Float)
    emi_months: Mapped[int | None] = mapped_column(Integer)
    seller_name: Mapped[str] = mapped_column(String, nullable=False)
    seller_rating: Mapped[float] = mapped_column(Float, nullable=False)
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    highlights: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    offers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    specifications: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    price_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class ProductReview(Base):
    __tablename__ = "product_reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        CheckConstraint("sentiment IN ('POSITIVE','NEUTRAL','NEGATIVE')", name="ck_reviews_sentiment"),
        Index("ix_reviews_product_rating", "product_id", "rating"),
    )

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sentiment: Mapped[str] = mapped_column(String, nullable=False)
    themes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


Index("ix_reviews_product_helpful", ProductReview.product_id, ProductReview.helpful_count.desc())


class ProductReviewSummary(Base):
    __tablename__ = "product_review_summaries"
    __table_args__ = (
        UniqueConstraint("product_id", "summary_version", name="ux_review_summary_version"),
        CheckConstraint("generated_by IN ('LLM','TEMPLATE')", name="ck_summary_generated_by"),
    )

    summary_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    summary_version: Mapped[str] = mapped_column(String, nullable=False)
    pros: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    cons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    themes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_review_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ShoppingSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("outcome IN ('ABANDONED','CONVERTED','OPEN')", name="ck_sessions_outcome"),
        Index("ix_sessions_user", "user_id"),
        Index("ix_sessions_started", "started_at"),
        Index("ix_sessions_outcome", "outcome"),
    )

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_type: Mapped[str | None] = mapped_column(String)
    referral_source: Mapped[str | None] = mapped_column(String)
    is_returning_user: Mapped[bool] = mapped_column(Boolean, default=False)
    persona: Mapped[str | None] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
    outcome_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Cart(Base):
    __tablename__ = "carts"

    cart_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cart_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    mrp_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    promo_code: Mapped[str | None] = mapped_column(String)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity"),
        Index(
            "ux_cart_items_active",
            "cart_id",
            "product_id",
            "variant",
            unique=True,
            sqlite_where=text("removed_at IS NULL"),
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    cart_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.cart_id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    variant: Mapped[str | None] = mapped_column(String)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(f"event_type IN ({_values(EventType)})", name="ck_events_type"),
        UniqueConstraint("session_id", "sequence_no", name="ux_events_session_seq"),
        Index("ix_events_session_time", "session_id", "server_timestamp"),
        Index("ix_events_type_time", "event_type", "server_timestamp"),
    )

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.product_id"))
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class InterventionCatalogue(Base):
    __tablename__ = "intervention_catalogue"
    __table_args__ = (
        CheckConstraint(f"cost_level IN ({_values(CostLevel)})", name="ck_catalogue_cost"),
        CheckConstraint("intrusiveness BETWEEN 0 AND 3", name="ck_catalogue_intrusiveness"),
        CheckConstraint("prior_uplift BETWEEN 0 AND 1", name="ck_catalogue_uplift"),
    )

    intervention_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    supported_causes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    cost_level: Mapped[str] = mapped_column(String, nullable=False)
    intrusiveness: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    requires: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    prior_uplift: Mapped[float] = mapped_column(Float, nullable=False)
    max_discount_pct: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','RUNNING','STOPPED')", name="ck_experiments_status"),
        CheckConstraint("traffic_split BETWEEN 0 AND 100", name="ck_experiments_traffic"),
    )

    experiment_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False)
    control_group: Mapped[str] = mapped_column(String, nullable=False)
    treatment_group: Mapped[str] = mapped_column(String, nullable=False)
    traffic_split: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="ux_model_registry_version"),
        CheckConstraint("model_type IN ('RISK','ROOT_CAUSE')", name="ck_model_registry_type"),
        CheckConstraint("status IN ('TRAINING','SHADOW','ACTIVE','ROLLED_BACK')", name="ck_model_registry_status"),
        Index(
            "ux_model_registry_active_type",
            "model_type",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    model_id: Mapped[str] = mapped_column(String, primary_key=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    model_type: Mapped[str] = mapped_column(String, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String, nullable=False)
    training_data_version: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class DecisionTrace(Base):
    __tablename__ = "decision_traces"
    __table_args__ = (
        CheckConstraint(f"risk_band IN ({_values(RiskBand)})", name="ck_traces_risk_band"),
        CheckConstraint(f"decision IN ({_values(Decision)})", name="ck_traces_decision"),
        CheckConstraint(f"channel IS NULL OR channel IN ({_values(Channel)})", name="ck_traces_channel"),
        Index("ix_traces_session_time", "session_id", "decision_time"),
        Index("ix_traces_decision", "decision"),
        Index("ix_traces_experiment", "experiment_id"),
    )

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    decision_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    model_versions: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    abandonment_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String, nullable=False)
    root_causes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    candidate_interventions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    policy_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    utility_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    selected_intervention: Mapped[str | None] = mapped_column(ForeignKey("intervention_catalogue.intervention_id"))
    channel: Mapped[str | None] = mapped_column(String)
    recommendation_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.experiment_id"))
    experiment_group: Mapped[str | None] = mapped_column(String)
    feature_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("session_feature_snapshots.snapshot_id", use_alter=True, name="fk_trace_snapshot")
    )
    latency_ms: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)


class SessionFeatureSnapshot(Base):
    __tablename__ = "session_feature_snapshots"
    __table_args__ = (Index("ix_snapshots_session_time", "session_id", "computed_at"),)

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_traces.decision_id", use_alter=True, name="fk_snapshot_trace")
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    trigger_event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id"))


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["model_name", "model_version"],
            ["model_registry.model_name", "model_registry.model_version"],
            name="fk_predictions_model_version",
        ),
        Index("ix_predictions_model", "model_name", "model_version", "predicted_at"),
    )

    prediction_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("decision_traces.decision_id"))
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String, nullable=False)


class InterventionImpression(Base):
    __tablename__ = "intervention_impressions"

    impression_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decision_traces.decision_id"), unique=True, nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    intervention_id: Mapped[str] = mapped_column(ForeignKey("intervention_catalogue.intervention_id"), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    surface: Mapped[str] = mapped_column(String, nullable=False)


class InterventionOutcome(Base):
    __tablename__ = "intervention_outcomes"

    outcome_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decision_traces.decision_id"), unique=True, nullable=False)
    intervention_shown: Mapped[bool] = mapped_column(Boolean, nullable=False)
    clicked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    order_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_to_purchase_seconds: Mapped[float | None] = mapped_column(Float)
    discount_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    estimated_margin: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_value: Mapped[float] = mapped_column(Float, nullable=False)
    discount_applied: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    payment_method: Mapped[str] = mapped_column(String, nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    estimated_margin: Mapped[float | None] = mapped_column(Float)
    attributed_decision_id: Mapped[str | None] = mapped_column(ForeignKey("decision_traces.decision_id"))


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "session_id", name="ux_assignment_session"),
    )

    assignment_id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.experiment_id"), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    group_name: Mapped[str] = mapped_column(String, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
