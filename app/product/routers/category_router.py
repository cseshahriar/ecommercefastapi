from fastapi import APIRouter, Depends, HTTPException, status

from app.account.deps import require_admin
from app.account.models import User
from app.db.config import SessionDep
from app.product.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.product.services import (
    create_category,
    get_all_categories,
    delete_category,
    update_category,
)

router = APIRouter()


@router.post("/", response_model=CategoryResponse)
async def category_create(
    session: SessionDep,
    category: CategoryCreate,
    admin_user: User = Depends(require_admin),
):
    return await create_category(session, category)


@router.get("/", response_model=list[CategoryResponse])
async def category_list(session: SessionDep):
    return await get_all_categories(session)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def category_edit(
    session: SessionDep,
    category_id: int,
    category: CategoryUpdate,
    admin_user: User = Depends(require_admin),
):
    updated_category = await update_category(session, category_id, category)

    if not updated_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return updated_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def category_delete(
    session: SessionDep, category_id: int, admin_user: User = Depends(require_admin)
):
    success = await delete_category(session, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
