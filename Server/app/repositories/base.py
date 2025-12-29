"""
Base repository class with common database operations.
"""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Generic repository that can be inherited for specific model types.
    """

    def __init__(self, model: Type[ModelType], session: Session):
        """
        Initialize repository.

        Args:
            model: The SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def create(self, obj: ModelType) -> ModelType:
        """Create a new record."""
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get_by_id(self, id: any) -> Optional[ModelType]:
        """Get record by ID."""
        return self.session.query(self.model).filter_by(id=id).first()

    def get_all(self, limit: Optional[int] = None) -> List[ModelType]:
        """Get all records with optional limit."""
        query = self.session.query(self.model)
        if limit:
            query = query.limit(limit)
        return query.all()

    def update(self, obj: ModelType) -> ModelType:
        """Update existing record."""
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Delete a record."""
        self.session.delete(obj)
        self.session.commit()

    def delete_by_id(self, id: any) -> bool:
        """Delete record by ID. Returns True if deleted, False if not found."""
        obj = self.get_by_id(id)
        if obj:
            self.delete(obj)
            return True
        return False

    def count(self) -> int:
        """Count total records."""
        return self.session.query(self.model).count()

    def exists(self, id: any) -> bool:
        """Check if record exists by ID."""
        return self.session.query(self.model).filter_by(id=id).first() is not None
