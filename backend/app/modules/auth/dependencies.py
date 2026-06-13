from uuid import UUID

from fastapi import Header, HTTPException, status


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> UUID:
    """Temporary auth boundary until a real identity provider is added."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )

    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id must be a valid UUID",
        ) from exc
