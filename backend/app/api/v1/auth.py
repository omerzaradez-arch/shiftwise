from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import jwt, JWTError

from app.database import get_db
from app.models import Employee
from app.config import settings
from app.security import verify_password

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {**data, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        emp_id: str = payload.get("sub")
        if not emp_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    emp = await db.get(Employee, emp_id)
    if not emp or not emp.is_active:
        raise credentials_exc
    return emp


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee).where(Employee.phone == data.phone)
    )
    emp = result.scalar_one_or_none()

    if not emp or not verify_password(data.password, emp.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="פרטי התחברות שגויים",
        )

    token = create_access_token({"sub": emp.id, "org_id": emp.org_id})

    # Load org name
    from app.models import Organization
    org = await db.get(Organization, emp.org_id)

    return TokenResponse(
        access_token=token,
        user={
            "id": emp.id,
            "name": emp.name,
            "phone": emp.phone,
            "email": emp.email,
            "role": emp.role,
            "org_id": emp.org_id,
            "org_name": org.name if org else "",
        },
    )


@router.get("/me")
async def get_me(current_user: Employee = Depends(get_current_user)):
    from app.models import Organization
    return {
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "org_id": current_user.org_id,
    }


@router.post("/logout")
async def logout():
    return {"ok": True}
