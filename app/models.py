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

class DietNameUpdate(BaseModel):
    diet_name_old: str
    diet_name_new: str

class DietCreate(BaseModel):
    diet_name: str
    fdc_id: int
    quantity: float
    sort_order: int
    color: str | None = None

class DietDelete(BaseModel):
    diet_name: str
    fdc_id: int | None = None
    quantity: float | None = None
    sort_order: int | None = None
    delete_all: bool = False

class ULUpdate(BaseModel):
    nutrient: str | None = None
    value: float

class RDAUpdate(BaseModel):
    nutrient: str | None = None
    value: float
