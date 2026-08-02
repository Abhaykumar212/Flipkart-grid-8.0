from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from uuid import UUID

import numpy as np
from numpy.random import Generator

from .catalog import SimProduct, delivery_estimate, pick_product
from .personas import Persona, PersonaName


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
REFERRALS = ("DIRECT", "SEARCH", "SOCIAL", "EMAIL")
REFERRAL_PROBABILITIES = (0.35, 0.38, 0.17, 0.10)
PAYMENT_METHODS = ("UPI", "CARD", "NET_BANKING", "COD")


def _deterministic_uuid4(namespace: str) -> str:
    digest = hashlib.blake2b(namespace.encode("utf-8"), digest_size=16).digest()
    return str(UUID(bytes=digest, version=4))


@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: str
    persona: str
    device_type: str
    referral_source: str
    is_returning_user: bool
    lifetime_orders: int
    prior_abandonment_rate: float
    avg_order_value: float
    discount_usage_rate: float
    category_order_counts: dict[str, int]
    days_since_last_purchase: float
    avg_session_to_purchase_s: float
    return_rate: float
    affinity_informational: float
    affinity_incentive: float
    payment_method_on_file: bool

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["category_order_counts_json"] = json.dumps(
            row.pop("category_order_counts"), sort_keys=True, separators=(",", ":")
        )
        row["is_synthetic"] = True
        return row


@dataclass(frozen=True, slots=True)
class SimulatedEvent:
    event_id: str
    event_type: str
    session_id: str
    user_id: str
    product_id: str | None
    sequence_no: int
    client_timestamp: datetime
    metadata: dict[str, Any]

    def to_row(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "sequence_no": self.sequence_no,
            "client_timestamp": self.client_timestamp.isoformat(),
            "metadata_json": json.dumps(
                self.metadata, sort_keys=True, separators=(",", ":")
            ),
        }


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    user: UserProfile
    persona: Persona
    events: tuple[SimulatedEvent, ...]
    primary_product: SimProduct
    cart_value: float
    converted: bool

    @property
    def outcome(self) -> str:
        return "CONVERTED" if self.converted else "ABANDONED"

    def to_row(self) -> dict[str, Any]:
        started = self.events[0].client_timestamp
        ended = self.events[-1].client_timestamp
        return {
            "session_id": self.session_id,
            "user_id": self.user.user_id,
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "device_type": self.user.device_type,
            "referral_source": self.user.referral_source,
            "is_returning_user": self.user.is_returning_user,
            "persona": self.persona.name.value,
            "outcome": self.outcome,
            "outcome_resolved_at": ended.isoformat(),
            "is_synthetic": True,
            "primary_product_id": self.primary_product.product_id,
            "cart_value": self.cart_value,
            "event_count": len(self.events),
        }


@dataclass(slots=True)
class SimClock:
    current: datetime
    started_at: datetime

    def advance(self, rng: Generator, persona: Persona) -> None:
        mean = persona.behavior.inter_event_seconds_mean
        seconds = max(0.25, float(rng.gamma(shape=2.0, scale=mean / 2.0)))
        if rng.random() < persona.behavior.idle_gap_probability:
            seconds += float(rng.uniform(60, 420))
        self.current += timedelta(seconds=seconds)


def make_user_profile(
    *,
    user_index: int,
    persona: Persona,
    rng: Generator,
) -> UserProfile:
    behavior = persona.behavior
    is_returning = persona.name == PersonaName.HIGH_INTENT_REPEAT or rng.random() < 0.68
    lifetime_orders = int(rng.integers(1, 18)) if is_returning else 0
    avg_order_value = float(np.clip(rng.lognormal(np.log(8_000), 0.75), 500, 120_000))
    if persona.name == PersonaName.PAYMENT_CONSTRAINED:
        avg_order_value *= 0.62
    discount_rate = float(rng.beta(2.0, 4.0))
    if persona.name == PersonaName.PRICE_SENSITIVE:
        discount_rate = float(rng.beta(7.0, 2.0))
    return_rate = (
        float(rng.uniform(0.27, 0.42))
        if rng.random() < 0.15
        else float(rng.beta(1.5, 14.0))
    )
    categories = {
        name: int(rng.integers(0, lifetime_orders + 1))
        for name in ("mobiles", "electronics", "appliances", "audio", "fashion")
    }
    informational = float(rng.beta(3, 3))
    if persona.name in {PersonaName.QUALITY_CONSCIOUS, PersonaName.COMPARISON_HEAVY}:
        informational = float(rng.beta(7, 2))
    incentive = float(rng.beta(3, 3))
    if persona.name == PersonaName.PRICE_SENSITIVE:
        incentive = float(rng.beta(7, 2))
    device = "MOBILE" if rng.random() < behavior.mobile_probability else "DESKTOP"
    referral = str(rng.choice(REFERRALS, p=REFERRAL_PROBABILITIES))
    return UserProfile(
        user_id=f"sim-u-{user_index:05d}",
        persona=persona.name.value,
        device_type=device,
        referral_source=referral,
        is_returning_user=is_returning,
        lifetime_orders=lifetime_orders,
        prior_abandonment_rate=float(
            np.clip(rng.normal(persona.base_abandonment, 0.09), 0.02, 0.98)
        ),
        avg_order_value=round(avg_order_value, 2),
        discount_usage_rate=discount_rate,
        category_order_counts=categories,
        days_since_last_purchase=(
            float(rng.uniform(1, 180)) if is_returning else 365.0
        ),
        avg_session_to_purchase_s=float(np.clip(rng.normal(850, 260), 120, 2_400)),
        return_rate=return_rate,
        affinity_informational=informational,
        affinity_incentive=incentive,
        payment_method_on_file=(
            persona.name == PersonaName.HIGH_INTENT_REPEAT
            or (is_returning and rng.random() < 0.64)
        ),
    )


def _session_start(rng: Generator, persona: Persona, user_index: int) -> datetime:
    day = int(rng.integers(0, 180))
    if rng.random() < persona.behavior.late_night_probability:
        hour = int(rng.choice([0, 1, 2, 3, 4, 23]))
    else:
        hour = int(rng.integers(7, 23))
    minute = int(rng.integers(0, 60))
    # The user offset avoids timestamp ties without affecting behavior.
    return BASE_TIME + timedelta(
        days=day, hours=hour, minutes=minute, microseconds=user_index
    )


def _persona_product(
    products: tuple[SimProduct, ...], persona: Persona, rng: Generator
) -> SimProduct:
    if persona.name == PersonaName.PAYMENT_CONSTRAINED:
        candidates = tuple(
            product for product in products if product.facts.selling_price >= 5_000
        )
        if candidates:
            return pick_product(candidates, rng)
    return pick_product(products, rng)


def simulate_session(
    *,
    rng: Generator,
    user: UserProfile,
    persona: Persona,
    products: tuple[SimProduct, ...],
    session_number: int,
    user_index: int,
) -> SessionRecord:
    """Generate one causal event stream through the shopping state machine."""

    session_id = f"sim-s-{user_index:05d}-{session_number:02d}"
    clock = SimClock(
        current=_session_start(rng, persona, user_index),
        started_at=BASE_TIME,
    )
    events: list[SimulatedEvent] = []

    def emit(
        event_type: str,
        *,
        product: SimProduct | None = None,
        **metadata: Any,
    ) -> None:
        sequence_no = len(events) + 1
        events.append(SimulatedEvent(
            event_id=_deterministic_uuid4(f"{session_id}:{sequence_no}"),
            event_type=event_type,
            session_id=session_id,
            user_id=user.user_id,
            product_id=product.product_id if product else None,
            sequence_no=sequence_no,
            client_timestamp=clock.current,
            metadata=metadata,
        ))
        clock.advance(rng, persona)

    emit(
        "SESSION_STARTED",
        device_type=user.device_type,
        referral_source=user.referral_source,
        viewport_width=390 if user.device_type == "MOBILE" else 1440,
    )

    behavior = persona.behavior
    search_count = int(rng.poisson(behavior.searches_mean))
    for _ in range(search_count):
        is_price_sort = rng.random() < behavior.price_sort_probability
        emit(
            "SEARCH_PERFORMED",
            query=str(rng.choice(("phone", "headphones", "shoes", "washing machine"))),
            result_count=int(rng.integers(8, 51)),
            sort_order="PRICE_LOW_TO_HIGH" if is_price_sort else "RELEVANCE",
        )

    view_count = max(1, int(rng.poisson(max(0.0, behavior.product_views_mean - 1))) + 1)
    viewed: list[SimProduct] = []
    for index in range(view_count):
        product = _persona_product(products, persona, rng)
        viewed.append(product)
        emit(
            "PRODUCT_VIEWED",
            product=product,
            source="DIRECT" if index == 0 and not search_count else "SEARCH",
        )
    product = viewed[-1]

    review_count = int(rng.poisson(behavior.review_opens_mean))
    for _ in range(review_count):
        emit("REVIEW_OPENED", product=product, source="PRODUCT_PAGE")
        dwell_seconds = max(1.0, float(rng.gamma(2, behavior.review_dwell_seconds_mean / 2)))
        emit(
            "REVIEW_DWELL_RECORDED",
            product=product,
            dwell_ms=int(min(300_000, dwell_seconds * 1_000)),
        )

    for _ in range(int(rng.poisson(behavior.similar_views_mean))):
        similar = pick_product(products, rng)
        emit(
            "SIMILAR_PRODUCT_VIEWED",
            product=similar,
            origin_product_id=product.product_id,
        )

    for _ in range(int(rng.poisson(behavior.comparisons_mean))):
        compared = pick_product(products, rng)
        if compared.product_id == product.product_id:
            compared = products[(products.index(compared) + 1) % len(products)]
        emit(
            "PRODUCT_COMPARED",
            product=product,
            compared_with=[compared.product_id],
        )

    for _ in range(int(rng.poisson(behavior.delivery_checks_mean))):
        emit(
            "DELIVERY_CHECKED",
            product=product,
            pincode=f"{int(rng.integers(100_000, 999_999)):06d}",
            estimated_days=delivery_estimate(product, rng),
            available=product.facts.in_stock,
        )

    cart_value = product.facts.selling_price
    emit(
        "ITEM_ADDED_TO_CART",
        product=product,
        quantity=1,
        unit_price=cart_value,
        variant=None,
    )
    emit("CART_VIEWED", cart_value=cart_value, item_count=1)

    if rng.random() < behavior.coupon_search_probability:
        emit("COUPON_SEARCHED", code="SAVE10", applied=False)

    if rng.random() < behavior.cart_churn_probability:
        emit("ITEM_REMOVED_FROM_CART", product=product, quantity=1)
        replacement = pick_product(products, rng)
        emit("PRODUCT_VIEWED", product=replacement, source="RAIL")
        product = replacement
        cart_value = product.facts.selling_price
        emit(
            "ITEM_ADDED_TO_CART",
            product=product,
            quantity=1,
            unit_price=cart_value,
            variant=None,
        )
        emit("CART_VIEWED", cart_value=cart_value, item_count=1)

    converted = False
    if rng.random() < behavior.start_checkout_probability:
        emit("CHECKOUT_STARTED", cart_value=cart_value, item_count=1)
        aborted = False
        method = str(rng.choice(PAYMENT_METHODS))
        for step, step_name in ((1, "ADDRESS"), (2, "SUMMARY"), (3, "PAYMENT")):
            emit("CHECKOUT_STEP_VIEWED", step=step, step_name=step_name)
            if step == 2 and rng.random() < behavior.back_from_checkout_probability:
                emit("CART_VIEWED", cart_value=cart_value, item_count=1)
                aborted = True
                break
            if step == 3 and rng.random() < behavior.payment_failure_probability:
                emit(
                    "PAYMENT_FAILED",
                    method=method,
                    reason_code="INSUFFICIENT_FUNDS",
                    attempt_no=1,
                )
                if rng.random() < behavior.change_method_probability:
                    new_method = "UPI" if method != "UPI" else "CARD"
                    emit(
                        "PAYMENT_METHOD_CHANGED",
                        from_method=method,
                        to_method=new_method,
                    )
                    method = new_method
                else:
                    aborted = True
                    break
        if not aborted and rng.random() < behavior.checkout_completion_probability:
            emit(
                "ORDER_COMPLETED",
                order_id=f"ord-{session_id}",
                order_value=cart_value,
                payment_method=method,
            )
            converted = True

    # ORDER_COMPLETED is terminal. This satisfies realism check 8 and avoids
    # contaminating post-purchase ordering with a synthetic SESSION_ENDED row.
    if not converted:
        emit("SESSION_ENDED", reason="TIMEOUT")

    return SessionRecord(
        session_id=session_id,
        user=user,
        persona=persona,
        events=tuple(events),
        primary_product=product,
        cart_value=cart_value,
        converted=converted,
    )
