from typing import Annotated, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path
from starlette import status
from models import Invoice, TypeOfCost, CostCenter, User, Supplier
from database import SessionLocal
from .auth import get_current_user, UserResponse, CreateUserRequest
from database import get_db
from passlib.context import CryptContext
from .invoices import InvoiceRequest, InvoiceResponse
from datetime import datetime
from .invoices import SupplierBase, CostCenterBase, TypeOfCostBase 
from sqlalchemy.exc import IntegrityError


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

class UpdateUserResponse(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    role: str

    class Config:  
        from_attributes = True 

    

class TypeOfCostCreate(BaseModel):
    cost_code: int = Field(..., gt=0, description="Cost code must be a positive integer")
    cost_name: str = Field(..., min_length=1, max_length=40, description="Cost name must be between 1 and 40 characters long")

class CostCenterCreate(BaseModel):
    cost_center_code: int = Field(..., gt=0, description="Cost center code must be a positive integer")
    cost_center_name: str = Field(..., min_length=1, max_length=40, description="Cost center name must be between 1 and 40 characters long")

class SupplierCreate(BaseModel):
    supplier_name: str = Field(..., min_length=1, max_length=40, description="Supplier name must be between 1 and 40 characters long")



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


@router.get("/user", response_model=List[UserResponse])
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

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, db: db_dependency, current_user: UserResponse = Depends(get_current_user)):
 
    if current_user.role != 'admin' and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active
    )



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
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Dohvaćanje korisnika iz baze
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Ažuriranje samo poslanih podataka
    if update_user_request.username is not None and update_user_request.username != user.username:
        user.username = update_user_request.username

    if update_user_request.email is not None and update_user_request.email != user.email:
        # Provjera UNIQUE ograničenja za email
        existing_user = db.query(User).filter(User.email == update_user_request.email).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
        user.email = update_user_request.email

    if update_user_request.first_name is not None:
        user.first_name = update_user_request.first_name

    if update_user_request.last_name is not None:
        user.last_name = update_user_request.last_name

    if update_user_request.role is not None:
        user.role = update_user_request.role

    # Spremanje promjena u bazu
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Vraćanje ažuriranog korisnika
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active,
    )



@router.delete("/user/{user_id}", status_code=204)
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

@router.post("/type_of_cost/", response_model=TypeOfCostCreate, status_code=status.HTTP_201_CREATED)
async def create_type_of_cost(
    type_of_cost: TypeOfCostCreate, 
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can create type of cost.")
    
    new_type_of_cost = TypeOfCost(
        cost_code=type_of_cost.cost_code,
        cost_name=type_of_cost.cost_name
    )
    db.add(new_type_of_cost)
    db.commit()
    db.refresh(new_type_of_cost)
    
    return new_type_of_cost


@router.put("/update-user/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    update_user_request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Provjeravamo i ažuriramo samo izmijenjene podatke
    if update_user_request.username and update_user_request.username != user.username:
        user.username = update_user_request.username

    if update_user_request.email and update_user_request.email != user.email:
        # Provjeri postoji li korisnik s istim emailom
        existing_user = db.query(User).filter(User.email == update_user_request.email).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use by another user"
            )
        user.email = update_user_request.email

    if update_user_request.first_name and update_user_request.first_name != user.first_name:
        user.first_name = update_user_request.first_name

    if update_user_request.last_name and update_user_request.last_name != user.last_name:
        user.last_name = update_user_request.last_name

    if update_user_request.role and update_user_request.role != user.role:
        user.role = update_user_request.role

    # Sprema promjene u bazu
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating user")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active
    )

@router.delete("/type_of_cost/{cost_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type_of_cost(
    cost_type_id: int,
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    if db.query(Invoice).filter(Invoice.cost_code_id == cost_type_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete cost type associated with active invoices")
    
    type_of_cost = db.query(TypeOfCost).filter(TypeOfCost.id == cost_type_id).first()
    
    if type_of_cost:
        db.delete(type_of_cost)
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Cost type not found")
    
    return {"detail": "Cost type deleted successfully."}


@router.get("/data/type-of-cost", response_model=List[TypeOfCostBase])
async def get_type_of_costs(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return db.query(TypeOfCost).all()


@router.get("/data/type-of-cost/{type_of_cost_id}", response_model=TypeOfCostBase)
async def get_type_of_cost_by_id(
    type_of_cost_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    type_of_cost = db.query(TypeOfCost).filter(TypeOfCost.id == type_of_cost_id).first()
    if type_of_cost is None:
        raise HTTPException(status_code=404, detail="Type of cost not found")
    return type_of_cost


@router.post("/cost_center/", response_model=CostCenterCreate, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    cost_center: CostCenterCreate, 
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can create cost centers.")
    
    new_cost_center = CostCenter(
        cost_center_code=cost_center.cost_center_code,
        cost_center_name=cost_center.cost_center_name
    )
    db.add(new_cost_center)
    db.commit()
    db.refresh(new_cost_center)
    
    return new_cost_center


@router.put("/cost_center/{cost_center_id}", response_model=CostCenterBase, status_code=status.HTTP_200_OK)
async def update_cost_center(
    cost_center_id: int,
    update_cost_center_request: CostCenterCreate,  
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):

    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    cost_center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    if cost_center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost center not found"
        )

    if update_cost_center_request.cost_center_code is not None:
        cost_center.cost_center_code = update_cost_center_request.cost_center_code
    if update_cost_center_request.cost_center_name is not None:
        cost_center.cost_center_name = update_cost_center_request.cost_center_name

    db.commit()
    db.refresh(cost_center)

    return CostCenterBase(
        id=cost_center.id,
        cost_center_name=cost_center.cost_center_name
    )


@router.delete("/cost_center/{cost_center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(
    cost_center_id: int,
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    if db.query(Invoice).filter(Invoice.cost_center_id == cost_center_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete cost center associated with active invoices")
    
    cost_center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    
    if cost_center:
        db.delete(cost_center)
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Cost center not found")
    
    return {"detail": "Cost center deleted successfully."}


@router.get("/data/cost-center/{cost_center_id}", response_model=CostCenterBase)
async def get_cost_center_by_id(
    cost_center_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    cost_center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    if cost_center is None:
        raise HTTPException(status_code=404, detail="Cost Center not found")
    return cost_center


@router.get("/data/cost-center", response_model=List[CostCenterBase])
async def get_cost_centers(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return db.query(CostCenter).all()



@router.post("/supplier/", response_model=SupplierCreate, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier: SupplierCreate, 
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can create suppliers.")
    
    new_supplier = Supplier(
        supplier_name=supplier.supplier_name
    )
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    
    return new_supplier

@router.put("/supplier/{supplier_id}", response_model=SupplierBase, status_code=status.HTTP_200_OK)
async def update_supplier(
    supplier_id: int,
    update_supplier_request: SupplierCreate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )

    if update_supplier_request.supplier_name is not None:
        supplier.supplier_name = update_supplier_request.supplier_name

    db.commit()
    db.refresh(supplier)

    return SupplierBase(
        id=supplier.id,
        supplier_name=supplier.supplier_name
    )


@router.delete("/supplier/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    db: db_dependency,
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    if db.query(Invoice).filter(Invoice.supplier_id == supplier_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete supplier associated with active invoices")
    
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if supplier:
        db.delete(supplier)
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    return {"detail": "Supplier deleted successfully."}


@router.get("/data/supplier", response_model=List[SupplierBase])
async def read_suppliers(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    suppliers = db.query(Supplier).all()
    return suppliers


@router.get("/data/supplier/{supplier_id}", response_model=SupplierBase)
async def read_supplier_by_id(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier



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