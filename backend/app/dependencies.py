from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import oauth2_scheme
from app.db.session import get_db
from app.models import User
from app.services.auth_service import get_current_user_by_token

# db session dependency
SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: SessionDep
) -> User:
    """Get current authenticated active user from bearer token."""
    return get_current_user_by_token(token, db)


CurrentUser = Annotated[User, Depends(get_current_user)]
