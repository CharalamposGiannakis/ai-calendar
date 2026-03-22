from sqlalchemy.orm import Session

from app.models import Category


DEFAULT_CATEGORIES = [
    {"name": "Uni", "color": "#7c3aed", "description": "University-related events"},
    {"name": "Work", "color": "#2563eb", "description": "Work-related events"},
    {"name": "Other", "color": "#16a34a", "description": "Other personal events"},
]


def seed_default_categories(db: Session) -> None:
    existing_names = {
        category.name
        for category in db.query(Category).all()
    }

    for item in DEFAULT_CATEGORIES:
        if item["name"] not in existing_names:
            db.add(Category(**item))

    db.commit()