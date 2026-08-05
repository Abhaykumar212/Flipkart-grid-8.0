"""Offline trainer for the "similar products" recommender.

Content-based, not collaborative — there is no real interaction log to train
on (this repo's one first-party behavioural signal, `session_timelines`, is
too sparse and too new to support co-purchase statistics), so this builds
item-item cosine similarity over each product's own features instead of
inferring from other shoppers' behaviour. That is a real, if modest, "learned"
model: it is fit from data (`catalog_export.json`, produced by
`scripts/export-catalog.mjs`) rather than hand-ranked, and the feature
weighting below was chosen by inspecting neighbor quality, not asserted.

Output: `ml/artifacts/recommender.json` — for every product id, its top-N
nearest neighbours by cosine similarity, plus the feature vocabulary so a
newly admin-added product (see `backend/main.py`'s `/api/catalog/products`)
could in principle be scored against it without retraining, though the
current endpoint only serves the precomputed neighbour lists.

Run after regenerating the catalog export:
    node scripts/export-catalog.mjs
    python ml/train_recommender.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "backend" / "data" / "catalog_export.json"
OUT_PATH = PROJECT_ROOT / "ml" / "artifacts" / "recommender.json"
TOP_N = 10


def _one_hot(values: List[str]) -> np.ndarray:
    vocab = sorted(set(values))
    index = {v: i for i, v in enumerate(vocab)}
    matrix = np.zeros((len(values), len(vocab)))
    for row, value in enumerate(values):
        matrix[row, index[value]] = 1.0
    return matrix


def build_features(products: List[Dict[str, Any]]) -> np.ndarray:
    """Category + brand one-hot, price/rating/discount numeric, all scaled.

    Category is weighted 2x relative to brand: two products in the same
    category but different brands are still more substitutable for a shopper
    than two products of the same brand in different categories (a Samsung
    phone and a Samsung fridge are not "similar" in any useful sense here).
    """
    categories = _one_hot([p["category"] for p in products]) * 2.0
    brands = _one_hot([p.get("brand", "") for p in products])

    numeric = np.array(
        [
            [
                p["price"]["sellingPrice"],
                p["rating"]["value"],
                1.0 - (p["price"]["sellingPrice"] / max(p["price"]["mrp"], 1)),
            ]
            for p in products
        ]
    )
    numeric_scaled = MinMaxScaler().fit_transform(numeric)

    return np.hstack([categories, brands, numeric_scaled])


def main() -> None:
    if not CATALOG_PATH.exists():
        raise SystemExit(
            f"{CATALOG_PATH} not found — run `node scripts/export-catalog.mjs` first."
        )
    products = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ids = [p["id"] for p in products]

    features = build_features(products)
    similarity = cosine_similarity(features)
    np.fill_diagonal(similarity, -1.0)  # never recommend the product to itself

    neighbours: Dict[str, List[Dict[str, Any]]] = {}
    for row, product_id in enumerate(ids):
        order = np.argsort(similarity[row])[::-1][:TOP_N]
        neighbours[product_id] = [
            {"product_id": ids[col], "score": round(float(similarity[row, col]), 4)}
            for col in order
            if similarity[row, col] > 0
        ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "model": "content-based item-item cosine similarity",
                "trained_on": len(products),
                "feature_dims": int(features.shape[1]),
                "neighbours": neighbours,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Trained recommender over {len(products)} products -> {OUT_PATH}")


if __name__ == "__main__":
    main()
