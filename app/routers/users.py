from typing import Annotated, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from models import User, Supplier, Invoice, TypeOfCost, CostCenter  
from .auth import UserResponse
from database import SessionLocal
from .auth import get_current_user



from passlib.context import CryptContext

router = APIRouter(
    prefix='/user',
    tags=['user']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6)

# Pydantic model for Supplier
class SupplierBase(BaseModel):
    id: int
    supplier_name: str

    class Config:
        orm_mode = True   # Enable ORM mode for this model


class TypeOfCostBase(BaseModel):
    id: int
    cost_name: str

    class Config:
        orm_mode = True


class CostCenterBase(BaseModel):
    id: int
    cost_center_name: str

    class Config:
        orm_mode = True

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)



@router.get("/current_user", response_model=UserResponse)
async def read_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_verification: UserVerification, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)  
):
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not bcrypt_context.verify(user_verification.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password")

    user.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.commit()

    return {"detail": "Password updated successfully"}

@router.put("/update_profile", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint za ažuriranje profila trenutno prijavljenog korisnika.
    """

    # Dohvaćamo korisnika iz baze
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Korisnik nije pronađen")

    # Ažuriranje korisničkih podataka samo ako su nova polja poslana
    if user_update.username:
        user.username = user_update.username
    if user_update.email:
        user.email = user_update.email
    if user_update.first_name:
        user.first_name = user_update.first_name
    if user_update.last_name:
        user.last_name = user_update.last_name
    if user_update.password:
        user.hashed_password = bcrypt_context.hash(user_update.password)

    # Spremamo promjene u bazu podataka
    db.commit()
    db.refresh(user)

    return user

