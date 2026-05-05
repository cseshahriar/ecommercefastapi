from fastapi import APIRouter, Depends, HTTPException, status
from typing import Union

from app.account.models import User
from app.db.config import SessionDep
from app.account.deps import get_current_user
from app.cart.schemas import CartItemCreate, CartItemResponse, CartSummary
from app.cart.services import add_to_cart, delete_cart_item, list_user_cart, chagne_cart_item_quantity_by_product


router = APIRouter()

@router.get("", response_model=CartSummary)
async def list_user_cart_item(
    session: SessionDep,
    user: User = Depends(get_current_user)
):
    return list_user_cart(session, user.id)

@router.post("/add", response_model=CartItemResponse)
async def add_item_to_cart(
    session: SessionDep,
    item: CartItemCreate,
    user: User = Depends(get_current_user)
):
    return await add_to_cart(session, user.id, item)


@router.patch("/increase/{product_id}", response_model=CartItemResponse)
async def increase_quantity_by_product(
    session: SessionDep,
    product_id: int,
    user: User = Depends(get_current_user)
):
    return await chagne_cart_item_quantity_by_product(session, product_id, user.id, delta=1)


@router.patch("/decrease/{product_id}", response_model=Union[CartItemResponse, dict])
async def decrease_quantity_by_product(
    session: SessionDep,
    product_id: int,
    user: User = Depends(get_current_user)
):
    return await chagne_cart_item_quantity_by_product(session, product_id, user.id, delta=-1)

@router.delete("/delete/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cart_item_delete(
  session: SessionDep, 
  item_id: int, 
  user: User = Depends(get_current_user)
):
  await delete_cart_item(session, item_id)