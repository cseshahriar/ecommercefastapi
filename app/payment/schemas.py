from pydantic import BaseModel, Field
from typing import Literal

from app.payment.models import PaymentGatewayEnum


class PaymentCreate(BaseModel):
    amount: int
    shipping_address_id: int
    gateway: Literal["mock", "razorpay", "bkash"] = Field(default="mock")
    simulate_success: bool | None = None
    """
    simulate_success is only for testing purpose when gateway is mock.
    If True, the payment will be marked as success, otherwise it will be marked as failed.
    """


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: int
    status: str
    is_paid: bool
    payment_gateway: PaymentGatewayEnum
    model_config = {"from_attributes": True}
