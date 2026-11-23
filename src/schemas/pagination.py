from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    results: List[T]
    pagination: PaginationMeta
