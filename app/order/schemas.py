from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.shipping.schemas import ShippingAddressResponse, ShippingStatusResponse


class OrderProductInfo(BaseModel):
    title: str
    description: str
    model_config = {"from_attributes": True}


class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    quantity: int
    price: float
    product: OrderProductInfo | None
    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_price: float
    status: str
    created_at: datetime
    shipping_address: ShippingAddressResponse
    shipping_status: Optional[ShippingStatusResponse] = None
    orderitems: list[OrderItemResponse]
    model_config = {"form_attributes": True}
