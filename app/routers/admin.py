from typing import Annotated, Dict
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path
from starlette import status
from models import Invoice, TypeOfCost, CostCenter
from database import SessionLocal
from .auth import get_current_user

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/invoices", status_code=status.HTTP_200_OK)
async def read_all(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Invoice).all()


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user is None or user.get('user_role') != 'admin':
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
    if user is None or user.get('user_role') != 'admin':
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
