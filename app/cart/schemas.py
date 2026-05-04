from pydantic import BaseModel


class CartItemBase(BaseModel):
    product_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    pass


class CartItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    product_title: str
    quantity: int
    price: float
    total: float
    model_config = {
        "form_attributes": true
    }


class CartSummary(BaseModel):
    items: list[CartItemResponse]
    total_quantity: int
    total_price: float
