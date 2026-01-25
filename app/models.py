from pydantic import BaseModel


class DietUpdate(BaseModel):
    Name: str
    FDC_ID: int
    Quantity: float
    sort_order: int


class DietCreate(BaseModel):
    Name: str
    FDC_ID: int
    Quantity: float
    sort_order: int
