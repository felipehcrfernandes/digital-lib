from app.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def list_users(self, *, skip: int = 0, limit: int = 10) -> PaginatedResponse[UserResponse]:
        items = self.repository.list_all(skip=skip, limit=limit)
        total = self.repository.count_all()
        return PaginatedResponse[UserResponse](
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

    def get_user(self, user_id: int) -> User:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def create_user(self, payload: UserCreate) -> User:
        existing_user = self.repository.get_by_email(payload.email)
        if existing_user is not None:
            raise ConflictError("A user with this email already exists")

        return self.repository.create(
            name=payload.name,
            email=payload.email,
        )

    def update_user(self, user_id: int, payload: UserUpdate) -> User:
        user = self.get_user(user_id)

        changes = payload.model_dump(exclude_unset=True)

        if "email" in changes:
            existing_user = self.repository.get_by_email(changes["email"])
            if existing_user is not None and existing_user.id != user.id:
                raise ConflictError("A user with this email already exists")

        return self.repository.update(user, **changes)