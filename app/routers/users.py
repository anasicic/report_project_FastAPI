from typing import Annotated, List
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

