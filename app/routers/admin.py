from typing import Annotated, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path
from starlette import status
from models import Invoice, TypeOfCost, CostCenter, User
from database import SessionLocal
from .auth import get_current_user, UserResponse, CreateUserRequest
from database import get_db
from passlib.context import CryptContext
from .invoices import InvoiceRequest, InvoiceResponse
from datetime import datetime



router = APIRouter(
    prefix='/admin',
    tags=['admin']
)

class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(default=None, description="Username of the user, can be updated if needed")
    email: Optional[str] = Field(default=None, description="Email of the user, can be updated if needed")
    first_name: Optional[str] = Field(default=None, description="First name of the user, can be updated if needed")
    last_name: Optional[str] = Field(default=None, description="Last name of the user, can be updated if needed")
    role: Optional[str] = Field(default=None, description="Role of the user, can be updated if needed")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/protected-route")
async def protected_route(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    # Provjera da li je korisnik admin
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"message": "Welcome, admin!"}


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: db_dependency, current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    users = db.query(User).all()
    return [UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active
    ) for user in users]


@router.post("/create-user")
async def create_user_for_admin(create_user_request: CreateUserRequest, 
                                current_user: Annotated[UserResponse, Depends(get_current_user)], 
                                db: Annotated[Session, Depends(get_db)]):

    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users."
        )
    
    
    existing_user = db.query(User).filter(
        (User.username == create_user_request.username) |
        (User.email == create_user_request.email)
    ).first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already registered.")

    hashed_password = bcrypt_context.hash(create_user_request.password)
    new_user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=hashed_password,
        role=create_user_request.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/update-user/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    update_user_request: UpdateUserRequest,
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    
    if update_user_request.username is not None:
        user.username = update_user_request.username  
    if update_user_request.email is not None:
        user.email = update_user_request.email  
    if update_user_request.first_name is not None:
        user.first_name = update_user_request.first_name  
    if update_user_request.last_name is not None:
        user.last_name = update_user_request.last_name  
    if update_user_request.role is not None:
        user.role = update_user_request.role  

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active
    )

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")

    
    if db.query(Invoice).filter(Invoice.user_id == user_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete user with active invoices")

    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        user.is_active = False
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"detail": "User deleted successfully"}



@router.get("/invoices", status_code=status.HTTP_200_OK)
async def read_all(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    if user is None or user.role != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Invoice).all()


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse, status_code=status.HTTP_200_OK)
async def update_invoice(
    invoice_request: InvoiceRequest,
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail='Access denied')

    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if invoice_model is None:
        raise HTTPException(status_code=404, detail='Invoice not found.')

    
    if invoice_request.cost_code_id:
        invoice_model.cost_code_id = invoice_request.cost_code_id
    if invoice_request.cost_center_id:
        invoice_model.cost_center_id = invoice_request.cost_center_id
    if invoice_request.supplier_id:
        invoice_model.supplier_id = invoice_request.supplier_id
    if invoice_request.netto_amount:
        invoice_model.netto_amount = invoice_request.netto_amount
    if invoice_request.date:
        invoice_model.date = datetime.strptime(invoice_request.date, "%Y-%m-%d").date()
    if invoice_request.invoice_number:
        invoice_model.invoice_number = invoice_request.invoice_number

    db.commit()
    db.refresh(invoice_model)

    return InvoiceResponse(
        id=invoice_model.id,
        cost_code_id=invoice_model.cost_code_id,
        cost_center_id=invoice_model.cost_center_id,
        supplier_id=invoice_model.supplier_id,
        netto_amount=invoice_model.netto_amount,
        date=invoice_model.date.isoformat(),
        invoice_number=invoice_model.invoice_number,
        user_id=invoice_model.user_id
    )



@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user is None or user.role != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail='Invoice not found.')
    
    db.query(Invoice).filter(Invoice.id == invoice_id).delete()
    db.commit()
    
    return {"detail": "Invoice deleted successfully."}

@router.get("/report", status_code=status.HTTP_200_OK)
async def generate_report(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user is None or user.role != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')

    types_of_cost = db.query(TypeOfCost).all()
    cost_centers = db.query(CostCenter).all()

    expenses_by_type_and_center: Dict[str, Dict[str, float]] = {}

    for type_of_cost in types_of_cost:
        expenses_by_center = {}
        for cost_center in cost_centers:
            expenses = db.query(Invoice).filter(
                Invoice.cost_code_id == type_of_cost.id,
                Invoice.cost_center_id == cost_center.id
            ).all()

            total_amount = sum(expense.netto_amount for expense in expenses)
            expenses_by_center[cost_center.cost_center_name] = total_amount if total_amount else 0

        expenses_by_type_and_center[type_of_cost.cost_name] = expenses_by_center

    return {"report": expenses_by_type_and_center}
