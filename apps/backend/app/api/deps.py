import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import read_session_token
from app.db.session import get_db

DBSession = Annotated[Session, Depends(get_db)]


def get_current_user_id(
    session_cookie: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> uuid.UUID:
    if session_cookie is not None:
        user_id = read_session_token(session_cookie)
        if user_id is not None:
            return user_id

    if settings.allow_dev_user_header and x_user_id is not None:
        try:
            return uuid.UUID(x_user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-User-Id header",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
