from sqlalchemy import select
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.models import CartItem
from app.cart.schemas import CartItemCreate, CartItemResponse, CartSummary
from app.product.models import Product
from sqlalchemy.orm import selectinload


async def list_user_cart(session: AsyncSession, user_id: int) -> CartSummary:
    query = select(CartItem).where(CartItem.user_id==user_id).options(selectinload(CartItem.product))
    # selectinload: Fetch all related products in ONE extra query like select_related
    result = await session.execute(query)
    cart_items = result.scalars().all() 

    cart_data: list[CartItemResponse] = []
    total_quantity = 0
    total_price = 0

    for item in cart_items:
        if not item.product:
            continue
        price = item.price
        quantity = item.quantity
        total = price * quantity

        total_price += total
        total_quantity += quantity
        cart_data.append(
            CartItemResponse(
                id=item.id,
                product_id=item.product.id,
                user_id=user_id,
                product_title=item.product.title,
                quantity=quantity,
                price=price,
                total=total
            )
        )
    return CartSummary(
        items=cart_data,
        total_quantity=total_quantity,
        total_price=total_price
    )


async def add_to_cart(session: AsyncSession, user_id: int, data: CartItemCreate):
    product = await session.get(Product, data.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.stock_quantity < data.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    # if cartitem exists by user and product
    query = select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == data.product_id)
    result = await session.execute(query)
    item = result.scalar_one_or_none()

    if item:  # increase qty
        item.quantity += data.quantity
        item.price = product.price
    else:
        item = CartItem(
            user_id=user_id,
            product_id=data.product_id,
            quantity=data.quantity,
            price=product.price
        )
        session.add(item)
    
    await session.commit()
    await session.refresh(item)
    return CartItemResponse(
        id=item.id,
        user_id=item.user_id,
        product_id=item.product_id,
        product_title=product.title,
        quantity=item.quantity,
        price=product.price,
        total=round(product.price * item.quantity, 2)
    )


async def chagne_cart_item_quantity_by_product(
    session: AsyncSession, 
    product_id: int,
    user_id: int, 
    delta: int
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NO_FOUND, detail="Product not found")
    
    # get cart item by product and user
    query = select(CartItem).where(CartItem.user_id==user_id, CartItem.product_id == product_id)
    result = await session.execute(query)
    cart_item = result.scalar_one_or_none() 

    if not cart_item:
        if delta < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item not in cart")
        
        if product.stock_quantity < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

        new_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=1,
            price=product.price
        )
        session.add(new_item)
        await session.commit()
        await session.refresh(new_item)
        return CartItemResponse(
            id=new_item.id,
            product_id=product.id,
            user_id=user_id,
            product_title=product.title,
            quantity=new_item.quantity,
            price=new_item.price,
            total=round(product.price * new_item.quantity, 2)
        )

    new_quantity = cart_item.quantity + delta
    if new_quantity <= 0:
        await session.delete(cart_item)
        await session.commit()
        return {"message": "Item remove from cart"}
    
    if product.stock_quantity < new_quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    # update cart_item
    cart_item.quantity = new_quantity
    cart_item.price = product.price
    await session.commit()
    await session.refresh(cart_item)

    return CartItemResponse(
        id=cart_item.id,
        product_id=cart_item.product_id,
        user_id=user_id,
        product_title=product.title,
        quantity=cart_item.quantity,
        price=cart_item.price,
        total=round(product.price * cart_item.quantity, 2)
    )


async def delete_cart_item(session: AsyncSession, cart_item_id: int):
    item = await session.get(CartItem, cart_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NO_FOUND, detail="Item not found")
    await session.delete(item)
    await session.commit()
    return item


