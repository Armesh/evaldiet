from pydantic import BaseModel


class DietUpdate(BaseModel):
    diet_name: str
    fdc_id: int
    quantity: float
    sort_order: int
    color: str | None = None
    original_fdc_id: int | None = None
    original_quantity: float | None = None
    original_sort_order: int | None = None


class DietCreate(BaseModel):
    diet_name: str
    fdc_id: int
    quantity: float
    sort_order: int
    color: str | None = None
