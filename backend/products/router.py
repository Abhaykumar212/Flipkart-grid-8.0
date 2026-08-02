from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.storage.db import get_db
from backend.storage.repositories import get_product_by_slug, list_products

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("")
def products(
    category: str | None = Query(default=None),
    session: Session = Depends(get_db),
) -> list[dict]:
    return list_products(session, category)


@router.get("/{slug}")
def product(slug: str, session: Session = Depends(get_db)) -> dict:
    result = get_product_by_slug(session, slug)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result
