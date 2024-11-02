from fastapi import Path, HTTPException, Depends, APIRouter
from typing import Annotated, List
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from starlette import status
from models import TypeOfCost, CostCenter, Invoice, Supplier, User
from typing import Optional
from .auth import get_current_user
from datetime import date
from database import engine, SessionLocal
from datetime import datetime
from .auth import UserResponse


router = APIRouter(
    prefix='/invoices',
    tags=['invoices']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class InvoiceRequest(BaseModel):
    id: Optional[int] = Field(description = "ID is not needed on create", default=None)
    cost_code_id: int = Field(gt=0)
    cost_center_id: int = Field(gt=0)
    supplier_id: int = Field(..., gt=0)
    netto_amount: float = Field(..., description="Net amount must be greater than 0")
    date: str = Field(..., description="Date of the invoice in YYYY-MM-DD format")
    invoice_number: str = Field(..., description="Invoice number must be between 1 and 20 characters long")
    

    

    @field_validator('date')
    def validate_date(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d") 
            return value
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "cost_code_id": 1,
                "cost_center_id": 1,
                "supplier_id": 1,
                "netto_amount": 2.500,
                "date": "2022-01-01",
                "invoice_number": "70-1-77"
            }
        }

    }

class InvoiceResponse(BaseModel):

    id: int
    cost_code_id: int
    cost_center_id: int
    supplier_id: int
    netto_amount: float
    date: str
    invoice_number: str
    user_id: int
    
    
    class Config:
        
        from_attributes = True

# Pydantic model for Supplier
class SupplierBase(BaseModel):
    id: int
    supplier_name: str

    class Config:
        orm_mode = True   


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


@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(db: db_dependency, user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if user.role == 'admin':
        # Ako je korisnik admin, vrati sve račune
        return db.query(Invoice).all()
    else:
        # Ako korisnik nije admin, vrati samo njegove račune
        return db.query(Invoice).filter(Invoice.user_id == user.id).all()
    

@router.get("/{invoice_id}", status_code=status.HTTP_200_OK)
async def read_invoice(
    invoice_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user)
):
    
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")

    
    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if invoice_model is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if user.role != "admin" and invoice_model.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access this invoice.")

    
    return invoice_model




@router.post("/create-invoice", response_model=InvoiceResponse, status_code=201)
async def create_invoice(invoice_request: InvoiceRequest,  user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Pretpostavljamo da su validacije prošle i kreiramo novi račun
    new_invoice = Invoice(
        cost_code_id=invoice_request.cost_code_id,
        cost_center_id=invoice_request.cost_center_id,
        supplier_id=invoice_request.supplier_id,
        netto_amount=invoice_request.netto_amount,
        date=datetime.strptime(invoice_request.date, "%Y-%m-%d").date(),
        invoice_number=invoice_request.invoice_number,
        user_id= user.id
    )
    
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # Serijaliziramo datum prije vraćanja odgovora
    return InvoiceResponse(
        id=new_invoice.id,
        cost_code_id=new_invoice.cost_code_id,
        cost_center_id=new_invoice.cost_center_id,
        supplier_id=new_invoice.supplier_id,
        netto_amount=new_invoice.netto_amount,
        date=new_invoice.date.isoformat(),  # Konverzija datuma u string format
        invoice_number=new_invoice.invoice_number,
        user_id=new_invoice.user_id
    )


@router.put("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_invoice(
    invoice_request: InvoiceRequest,
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)  
):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    
    # Provjera da li je korisnik admin
    if user.role == "admin":
        # Ako je korisnik admin, može uređivati bilo koji račun
        invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    else:
        # Ako korisnik nije admin, može uređivati samo vlastite račune
        invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.id).first()
    
    if invoice_model is None:
        raise HTTPException(status_code=404, detail="Invoice not found or not authorized to update.")

    # Ažuriranje podataka računa
    invoice_model.cost_code_id = invoice_request.cost_code_id
    invoice_model.cost_center_id = invoice_request.cost_center_id
    invoice_model.supplier_id = invoice_request.supplier_id
    invoice_model.netto_amount = invoice_request.netto_amount
    invoice_model.date = datetime.strptime(invoice_request.date, "%Y-%m-%d").date()
    invoice_model.invoice_number = invoice_request.invoice_number

    # Spremanje promjena u bazu
    db.commit()



@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if invoice_model is None:
        raise HTTPException(status_code=404, detail='Invoice not found or not authorized to delete.')
    
    if user.role != "admin" and invoice_model.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to delete this invoice.")


    db.delete(invoice_model)
    db.commit()


    return {"detail": "Invoice deleted successfully"}

@router.get("/data/suppliers", response_model=List[SupplierBase])  
async def read_suppliers(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    suppliers = db.query(Supplier).all()
    return suppliers

@router.get("/data/cost-centers", response_model=List[CostCenterBase])  
async def get_cost_centers(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    return db.query(CostCenter).all()

@router.get("/data/type-of-costs", response_model=List[TypeOfCostBase])  
async def get_type_of_costs(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    return db.query(TypeOfCost).all()

@router.get("/supplier/{supplier_id}", response_model=SupplierBase, status_code=status.HTTP_200_OK)
async def get_supplier(
    supplier_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    return supplier


@router.get("/cost_center/{cost_center_id}", response_model=CostCenterBase, status_code=status.HTTP_200_OK)
async def get_cost_center(
    cost_center_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    cost_center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    
    if cost_center is None:
        raise HTTPException(status_code=404, detail="Cost Center not found")
    
    return cost_center


@router.get("/type_of_cost/{type_of_cost_id}", response_model=TypeOfCostBase, status_code=status.HTTP_200_OK)
async def get_type_of_cost(
    type_of_cost_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    type_of_cost = db.query(TypeOfCost).filter(TypeOfCost.id == type_of_cost_id).first()
    
    if type_of_cost is None:
        raise HTTPException(status_code=404, detail="Type of Cost not found")
    
    return type_of_cost