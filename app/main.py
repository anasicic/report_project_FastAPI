from fastapi import FastAPI
import models
from database import engine
from routers import auth, invoices, admin, users
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Adding CORS middleware
origins = [
    "http://localhost:4200",  # URL Angular application
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  # Enable all HTTP methods
    allow_headers=["*"],  # Enable all headers
)

# Creating tables in the database
models.Base.metadata.create_all(bind=engine)

# Enabling routes
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(admin.router)
app.include_router(users.router)
