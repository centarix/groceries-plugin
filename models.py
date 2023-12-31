from datetime import date
from typing import Optional
from pydantic import BaseModel

class ItemPayLoad(BaseModel):
    item_id: Optional[int]
    item_name: str
    quantity: int

class BillPayLoad(BaseModel):
    bill_id: Optional[int]
    bill_name: str
    bill_duedate: date
    bill_totalamt: float
    bill_mindue: float