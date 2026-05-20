from os import name


from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile, status

from app.product.models import Product, Category
from app.product.schemas import (
    CategoryCreate,
    CategoryResponse,
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.product.utils import generate_slug, save_upload_file


# Category Services
async def create_category(
    session: AsyncSession, category: CategoryCreate
) -> CategoryResponse:
    """Create a new category."""
    new_category = Category(name=category.name)
    session.add(new_category)
    await session.commit()
    await session.refresh(new_category)
    return new_category


async def get_all_categories(session: AsyncSession) -> list[CategoryResponse]:
    """Get all categories."""
    stmt = select(Category)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_category(session, category_id: int, data):
    query = select(Category).where(Category.id == category_id)
    result = await session.execute(query)

    category = result.scalar_one_or_none()

    if not category:
        return None

    category.name = data.name

    await session.commit()
    await session.refresh(category)

    return category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    """Delete a category by ID."""
    category = await session.get(Category, category_id)
    if not category:
        return False
    await session.delete(category)
    await session.commit()
    return True


# Product Services
async def create_product(
    session: AsyncSession, data: ProductCreate, image_url: UploadFile | None = None
) -> ProductResponse:
    """Create a new product."""
    if data.stock_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock quantity cannot be negative.",
        )

    image_path = await save_upload_file(image_url, "images")

    categories = []
    if data.category_ids:
        category_stmt = select(Category).where(Category.id.in_(data.category_ids))
        category_result = await session.execute(category_stmt)
        categories = category_result.scalars().all()

    product_dict = data.model_dump(exclude={"category_ids"})

    # Generate slug if not provided
    if not product_dict.get("slug"):
        product_dict["slug"] = generate_slug(product_dict["title"])

    # Check if slug already exists
    existing = await session.execute(
        select(Product.id).where(Product.slug == product_dict["slug"])
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Slug already exists. Please use a different title or slug.",
        )

    new_product = Product(**product_dict, image_url=image_path, categories=categories)
    session.add(new_product)
    await session.commit()
    return new_product


async def get_all_products(
    session: AsyncSession,
    category_names: list[str] | None = None,
    limit: int = 5,
    page: int = 1,
) -> dict:
    stmt = select(Product).options(selectinload(Product.categories))
    if category_names:
        stmt = (
            stmt.join(Product.categories)
            .where(Category.name.in_(category_names))
            .distinct()
        )

    count_stmt = stmt.with_only_columns(func.count(Product.id)).order_by(None)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    stmt = stmt.limit(limit).offset((page - 1) * limit)

    result = await session.execute(stmt)
    products = result.scalars().all()

    return {"total": total, "page": page, "limit": limit, "items": products}


async def search_products(
    session: AsyncSession,
    category_names: list[str] | None = None,
    title: str | None = None,
    description: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 5,
    page: int = 1,
) -> dict:
    stmt = select(Product).options(selectinload(Product.categories))

    if category_names:
        stmt = (
            stmt.join(Product.categories)
            .where(Category.name.in_(category_names))
            .distinct()
        )

    filters = []

    if title:
        filters.append(Product.title.like(f"%{title}%"))

    if description:
        filters.append(Product.description.like(f"%{description}%"))

    if min_price is not None:
        filters.append(Product.price >= min_price)

    if max_price is not None:
        filters.append(Product.price <= max_price)

    if filters:
        stmt = stmt.where(and_(*filters))

    count_stmt = stmt.with_only_columns(func.count(Product.id)).order_by(None)
    result = await session.execute(count_stmt)
    total = result.scalar_one()

    stmt = stmt.limit(limit).offset((page - 1) * limit)
    result = await session.execute(stmt)
    products = result.scalars().all()
    return {"total": total, "page": page, "limit": limit, "items": products}


async def get_product_by_slug(
    session: AsyncSession, slug: str
) -> ProductResponse | None:
    stmt = (
        select(Product)
        .options(selectinload(Product.categories))
        .where(Product.slug == slug)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_product_by_id(
    session: AsyncSession,
    product_id: int,
    data: ProductUpdate,
    image_url: UploadFile | None = None,
) -> ProductResponse:
    query = (
        select(Product)
        .options(selectinload(Product.categories))
        .where(Product.id == product_id)
    )
    result = await session.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        return None

    if data.category_ids is not None:
        category_query = select(Category).where(Category.id.in_(data.category_ids))
        category_result = await session.execute(category_query)
        product.categories = category_result.scalars().all()

    for key, value in data.model_dump(
        exclude={"category_id"}, exclude_none=True
    ).items():
        setattr(product, key, value)

    if image_url is not None:
        image_path = await save_upload_file(image_url, "images")
        product.image_url = image_path

    await session.commit()
    await session.refresh(product)
    return product


async def delete_product(session: AsyncSession, product_id: int) -> bool:
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)

    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await session.delete(product)
    await session.commit()

    return True
