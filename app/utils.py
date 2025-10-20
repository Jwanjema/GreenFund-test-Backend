from typing import TypeVar, Generic, Sequence
from pydantic import BaseModel
from math import ceil

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class Paginated(BaseModel, Generic[T]):
    meta: PaginationMeta
    items: Sequence[T]


def paginate(items: Sequence[T], page: int, per_page: int) -> Paginated[T]:
    """
    A utility function to paginate a list of items.
    """
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_items = items[start:end]
    total_pages = ceil(total / per_page) if per_page > 0 else 0

    meta = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
    )

    return Paginated[T](meta=meta, items=paginated_items)
