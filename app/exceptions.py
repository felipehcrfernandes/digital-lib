class AppError(Exception):
    """Base application exception."""


class NotFoundError(AppError):
    """Raised when a resource cannot be found."""


class BusinessRuleError(AppError):
    """Raised when a business rule is violated."""


class ConflictError(AppError):
    """Raised when a resource conflicts with existing data."""