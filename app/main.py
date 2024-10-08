from fastapi import FastAPI
import models
from database import engine
from routers import auth, invoices, admin, users
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Dodavanje CORS middleware-a
origins = [
    "http://localhost:4200",  # URL Angular aplikacije
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],  # Omogući sve HTTP metode
    allow_headers=["*"],  # Omogući sve zaglavlja
)

# Kreiranje tablica u bazi podataka
models.Base.metadata.create_all(bind=engine)

# Uključivanje ruta
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(admin.router)
app.include_router(users.router)
