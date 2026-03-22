from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists.")

    category = Category(
        name=payload.name.strip(),
        color=payload.color,
        description=payload.description,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name.asc()).all()


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        normalized_name = data["name"].strip()
        existing = (
            db.query(Category)
            .filter(Category.name == normalized_name, Category.id != category_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Another category with this name already exists.")
        category.name = normalized_name

    if "color" in data:
        category.color = data["color"]

    if "description" in data:
        category.description = data["description"]

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    db.delete(category)
    db.commit()