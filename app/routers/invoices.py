from fastapi import Path, HTTPException, Depends, APIRouter
from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from starlette import status
from models import TypeOfCost, CostCenter, Invoice, Supplier, User
from typing import Optional
from .auth import get_current_user
from datetime import date
from database import engine, SessionLocal
from datetime import datetime


router = APIRouter()

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




@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(db: db_dependency, user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(Invoice).filter(Invoice.user_id == user.get('id')).all()
    

@router.get("/invoices/{invoice_id}", status_code=status.HTTP_200_OK)
async def read_invoice(db: db_dependency, user: dict = Depends(get_current_user), invoice_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.get('id')).first()
    
    if invoice_model is not None:
        return invoice_model

    raise HTTPException(status_code=404, detail='Invoice not found.')



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
        user_id= user["id"]
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


@router.put("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_invoice(
    invoice_request: InvoiceRequest,
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)  
):
    
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    
    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.get('id')).first()
    
    if invoice_model is None:
        raise HTTPException(status_code=404, detail='Invoice not found or not authorized to update.')


    invoice_model.cost_code_id = invoice_request.cost_code_id
    invoice_model.cost_center_id = invoice_request.cost_center_id
    invoice_model.supplier_id = invoice_request.supplier_id
    invoice_model.netto_amount = invoice_request.netto_amount
    invoice_model.date = datetime.strptime(invoice_request.date, "%Y-%m-%d").date()
    invoice_model.invoice_number = invoice_request.invoice_number
    
    
    db.commit()


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user) 
):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    invoice_model = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.get('id')).first()
    
    if invoice_model is None:
        raise HTTPException(status_code=404, detail='Invoice not found or not authorized to delete.')


    db.delete(invoice_model)
    db.commit()

    
