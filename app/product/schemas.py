from unicodedata import category

from pydantic import BaseModel, Field


# Category Schemas
class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int

    model_config = {"from_attributes": True}


# Product Schemas
class ProductBase(BaseModel):
    title: str
    description: str
    price: float = Field(..., gt=0)  # Ensure price is greater than 0
    stock_quantity: int = Field(..., ge=0)  # Ensure stock quantity is non-negative


class ProductCreate(ProductBase):
    category_ids: list[int] | None = (
        None  # Optional list of category IDs to associate with the product
    )


class ProductResponse(ProductBase):
    id: int
    title: str
    description: str
    slug: str
    price: float
    categories: list[CategoryResponse] = []  # List of associated categories
    image_url: str | None = None  # Optional image URL
    model_config = {"from_attributes": True}


class PaginatedProductResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[ProductResponse]


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    stock_quantity: int | None = None
    image_url: str | None = None
    category_ids: list[int] | None = None
    model_config = {"from_attributes": True}
