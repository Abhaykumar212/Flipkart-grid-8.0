from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.random import Generator

from backend.feature_engine.schema import ProductFacts


CATALOG_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "catalog.json"
ZONE_DELTAS = np.array([-1, 0, 1, 2], dtype=int)
ZONE_PROBABILITIES = np.array([0.15, 0.55, 0.20, 0.10])


@dataclass(frozen=True, slots=True)
class SimProduct:
    facts: ProductFacts
    title: str
    brand: str
    seller_rating: float

    @property
    def product_id(self) -> str:
        return self.facts.product_id


def _price_history(seed_price: float, rng: Generator) -> tuple[float, ...]:
    floor = seed_price * 0.8
    ceiling = seed_price * 1.2
    price = seed_price
    values: list[float] = []
    for _ in range(5):
        price = float(np.clip(price * (1 + rng.normal(-0.008, 0.03)), floor, ceiling))
        values.append(round(price, 2))
    values.append(round(seed_price, 2))
    return tuple(values)


def load_catalog(
    *,
    seed: int,
    path: str | Path = CATALOG_PATH,
) -> tuple[SimProduct, ...]:
    raw_products = json.loads(Path(path).read_text(encoding="utf-8"))
    seed_streams = np.random.SeedSequence([seed, 8_013]).spawn(len(raw_products))
    products: list[SimProduct] = []
    for raw, seed_stream in zip(raw_products, seed_streams, strict=True):
        rng = np.random.default_rng(seed_stream)
        selling_price = float(raw["price"]["sellingPrice"])
        products.append(SimProduct(
            facts=ProductFacts(
                product_id=str(raw["id"]),
                category=str(raw["category"]),
                mrp=float(raw["price"]["mrp"]),
                selling_price=selling_price,
                rating=float(raw["rating"]["value"]),
                rating_count=int(raw["rating"]["count"]),
                in_stock=bool(raw["stock"]["inStock"]),
                quantity_left=int(raw["stock"]["quantityLeft"]),
                estimated_delivery_days=int(raw["delivery"]["estimatedDays"]),
                emi_eligible=bool(raw.get("emi")),
                price_history=_price_history(selling_price, rng),
            ),
            title=str(raw["title"]),
            brand=str(raw["brand"]),
            seller_rating=float(raw["seller"]["rating"]),
        ))
    return tuple(products)


def product_facts_by_id(
    products: Iterable[SimProduct],
) -> dict[str, ProductFacts]:
    return {product.product_id: product.facts for product in products}


def pick_product(products: tuple[SimProduct, ...], rng: Generator) -> SimProduct:
    """Choose a real fixture product, modestly oversampling scarce stock context."""

    weights = np.array([
        3.0 if (not product.facts.in_stock or product.facts.quantity_left <= 5) else 1.0
        for product in products
    ])
    weights /= weights.sum()
    return products[int(rng.choice(len(products), p=weights))]


def delivery_estimate(product: SimProduct, rng: Generator) -> int:
    delta = int(rng.choice(ZONE_DELTAS, p=ZONE_PROBABILITIES))
    return max(1, min(10, product.facts.estimated_delivery_days + delta))
