from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.cart.models import CartItem
from app.product.models import Product
from app.shipping.models import ShippingAddress, ShippingStatus, ShippingStatusEnum
from app.order.models import Order, OrderItem, OrderStatusEnum

from app.payment.services import create_payment
from app.payment.schemas import PaymentCreate


async def checkout(
    session: AsyncSession,
    user_id: int,
    payment_data: PaymentCreate
) -> Order:
    # Fetch all cart item for a user, locking row for update(to prevent race conditions)
    query = select(CartItem).where(CartItem.user_id==user_id).options(selectinload(CartItem.product)).with_for_update()
    result = await session.execute(query)
    cart_items = result.scalars().all()

    # if not items found, cart is empy -> checkout not possible
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")


    # Track Total cost
    total_price = Decimal("0.0")
    # Will store OrderItem instance for bulk add
    order_items: list[OrderItem] = []

    # Validate each item
    for item in cart_items:
        if not item.product:
            continue  # skip if product no longer exists(race case)

        # Check stock availibility
        if item.product.stock_quantity < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock")

        # Ensure price consistency(prevent price manipulation on frontend)
        if item.product.price != item.price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Price mismatch")

        # Add to total price (Decimal used to prevent floting point errors)
        total_price += Decimal(str(item.price)) * item.quantity
        
        # Prepare OrderItem entry for this product
        order_items.append(
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
        )

    # Check that payment amount matches cart total (Allowing 0.01 differene due to float precision)
    if abs(total_price - Decimal(str(payment_data.amount))) > Decimal("0.01"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Payment amount does not match cart total."
        )
  

    # Validate shipping address
    address = await session.get(ShippingAddress, payment_data.shipping_address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shipping address.")

    # Create new order (status will be updated after payment success)
    order = Order(
        user_id=user_id,
        total_price=float(total_price),
        shipping_address_id=payment_data.shipping_address_id
    )
    session.add(order)
    # Ensure order.id is generated before creating payment
    await session.flush()

    # Process Payment
    payment = await create_payment(
        session=session,
        data=payment_data,
        user_id=user_id,
        order_id=order.id
    ) 

    # If payment fails, rollback transaction and abort checkout
    if not payment.is_paid:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment failed")

    # Update order status to confirmed after payment
    order.status = OrderStatusEnum.confirmed
    session.add(order)

    # Create shipping status entry (starts as pending)
    shipping_status = ShippingStatus(
        order_id=order.id,
        status=ShippingStatusEnum.pending
    )
    session.add(shipping_status)

    # Add order item to DB and updae product stock
    for order_item in order_items:
        order_item.order_id = order.id
        session.add(order_item)
        # Reduce stock quantity for each product
        product = await session.get(Product, order_item.product_id)
        if product:
            product.stock_quantity -= order_item.quantity

    # Clear the user's cart
    for item in cart_items:
        await session.delete(item)

    # Commit all changes to the database
    await session.commit()
    await session.refresh(order)

    # Fetch the order again with related entities(items, shipping address, shipping status)
    order_query = select(Order).where(Order.id==order.id).options(
        selectinload(Order.orderitems),
        selectinload(Order.shipping_address),
        selectinload(Order.shipping_status)
    )
    result = await session.execute(order_query)
    return result.scalar_one()


async def get_placed_order_for_user(
    session: AsyncSession, user_id: int
):
    query = (
        select(Order).where(Order.user_id==user_id).options(
            selectinload(Order.orderitems),
            selectinload(Order.orderitems).selectinload(OrderItem.product)
        )
    )
    result = await session.execute(query)
    return result.scalars().all()


async def get_order_by_id(session: AsyncSession, user_id: int, order_id: int):
    query = (
        select(Order).where(Order.id==order_id, Order.user_id==user_id).options(
            selectinload(Order.orderitems)
        )
    ) 
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def cancel_order(
    session: AsyncSession,
    user_id: int,
    order_id: int
):
    order = await get_order_by_id(session, user_id, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
  
    if not order.shipping_status or order.shipping_status.status != ShippingStatusEnum.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only orders with pending shipping status can be cancelled."
        )

    order.status = OrderStatusEnum.cancelled
    order.shipping_status.status = ShippingStatusEnum.cancelled
    await session.commit()
    await session.refresh(order)
    return order
    
async def all_placed_order(
    session: AsyncSession,
    shipping_status: str | None = None,
    user_id: int | None = None
):
    stmt = select(Order).where(Order.status == OrderStatusEnum.confirmed).options(
        selectinload(Order.orderitems).selectinload(OrderItem.product),
        selectinload(Order.shipping_status)
    )

    # Filter by user if provided
    if user_id:
        stmt = stmt.where(Order.user_id == user_id)

    # Filter by shipping status if provided
    if shipping_status:
        stmt = stmt.join(Order.shipping_status).where(ShippingStatus.status == shipping_status)

    result = await session.execute(stmt)
    return result.scalars().all()
