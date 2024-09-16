from database import Base
from sqlalchemy import Column, Integer, Float, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TypeOfCost(Base):
    __tablename__ = 'type_of_cost'
    
    id = Column(Integer, primary_key=True, index=True)
    cost_code = Column(Integer, nullable=False)
    cost_name = Column(String(40), nullable=False)
    
    
    invoices = relationship("Invoice", back_populates="type_of_cost")


class CostCenter(Base):
    __tablename__ = 'cost_center'
    
    id = Column(Integer, primary_key=True, index=True)
    cost_center_code = Column(Integer, nullable=False)
    cost_center_name = Column(String(40), nullable=False)
    
   
    invoices = relationship("Invoice", back_populates="cost_center")


class Supplier(Base):
    __tablename__ = 'supplier'
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_name = Column(String(40), nullable=False)
    
    
    invoices = relationship("Invoice", back_populates="supplier")


class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(40), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)  
    first_name = Column(String(50), nullable=False)            
    last_name = Column(String(50), nullable=False)            
    hashed_password = Column(String(255), nullable=False)      
    role = Column(String(20), nullable=False)                  
    is_active = Column(Boolean, default=True, nullable=True)                  

    
    invoices = relationship("Invoice", back_populates="user")


class Invoice(Base):
    __tablename__ = 'invoice'
    
    id = Column(Integer, primary_key=True, index=True)
    cost_code_id = Column(Integer, ForeignKey('type_of_cost.id'), nullable=False)
    cost_center_id = Column(Integer, ForeignKey('cost_center.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('supplier.id'), nullable=False)
    netto_amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    invoice_number = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    
    
    type_of_cost = relationship("TypeOfCost", back_populates="invoices")
    cost_center = relationship("CostCenter", back_populates="invoices")
    supplier = relationship("Supplier", back_populates="invoices")
    user = relationship("User", back_populates="invoices")