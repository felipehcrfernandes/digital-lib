from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, *, skip: int = 0, limit: int = 10) -> list[User]:
        statement = select(User).order_by(User.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def count_all(self) -> int:
        statement = select(func.count()).select_from(User)
        return self.db.scalar(statement) or 0

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def create(self, *, name: str, email: str) -> User:
        user = User(name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, **changes: object) -> User:
        for field, value in changes.items():
            setattr(user, field, value)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user