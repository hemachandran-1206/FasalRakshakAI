from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import ChangePasswordIn, TokenOut, UserOut
from ..services import security

router = APIRouter(prefix="/auth", tags=["auth"])

# verifying against this when the email is unknown keeps response time similar for known/unknown emails
_DUMMY_HASH = security.hash_password("not-a-real-password")


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()
    if security.too_many_failures(email):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == email))
    ok = security.verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        security.record_failure(email)
        raise HTTPException(401, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    security.clear_failures(email)
    return TokenOut(access_token=security.create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(data: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not security.verify_password(data.current_password, user.password_hash):
        raise HTTPException(401, "Current password is incorrect")
    if len(data.new_password) < security.MIN_PASSWORD_LENGTH:
        raise HTTPException(422, f"New password must be at least {security.MIN_PASSWORD_LENGTH} characters")
    user.password_hash = security.hash_password(data.new_password)
    db.commit()
