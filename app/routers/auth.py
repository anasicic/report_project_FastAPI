from datetime import timedelta, datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from pydantic import EmailStr

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

# Pomoćni model za API request
class UserActivationRequest(BaseModel):
    is_active: bool


SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set!")

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

    class Config:
        orm_mode = True
        from_attributes = True
        
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def get_user_by_username(username: str, db: Session):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(username: str, password: str, db: Session):
    user = get_user_by_username(username, db)
    if user and user.is_active and bcrypt_context.verify(password, user.hashed_password):
        print(f"Authenticated user: {user.username}, Role: {user.role}")
        return user
    return None

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_bearer), db: Session = Depends(get_db)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("Decoded payload:", payload)
        user_id: int = payload.get("id")
        if user_id is None:
            raise credentials_exception

        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:  
            raise credentials_exception

        return UserResponse(  
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=user.is_active,
        )
    except JWTError:
        raise credentials_exception

@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: db_dependency):
    # Proveri da li korisnik već postoji
    existing_user = db.query(User).filter(
        (User.username == create_user_request.username) |
        (User.email == create_user_request.email)
    ).first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already registered.")

    # Hashiraj lozinku
    hashed_password = bcrypt_context.hash(create_user_request.password)
    
    # Kreiraj novog korisnika
    new_user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=hashed_password,
        role=create_user_request.role,
        is_active=True  # Aktiviraj novog korisnika
    )

    db.add(new_user)
    
    try:
        db.commit()
        db.refresh(new_user)

        # Generišite token nakon uspešne registracije
        token = create_access_token(new_user.username, new_user.id, new_user.role, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

        # Uključi token u odgovor
        return {
            **UserResponse.from_orm(new_user).dict(),  # Vraćamo sve informacije o korisniku
            "access_token": token,
            "token_type": "bearer"
        }
    except Exception as e:
        db.rollback()
       

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid credentials')
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    response = {
        'access_token': token, 
        'token_type': 'bearer',
        'username': user.username,
        'role': user.role
    }

    print("Response data:", response) 
    
    return response

# Endpoint za ažuriranje statusa korisnika (aktivacija/deaktivacija)
@router.put("/users/{user_id}/activation", status_code=status.HTTP_200_OK)
async def update_user_activation(
    user_id: int,
    activation_data: UserActivationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # Provjerava autentifikacije
):
    #  Samo admin može upravljati aktivacijom drugih korisnika
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can activate/deactivate users.")
    
    # Dohvat korisnika prema ID-u
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    # Ažuriranje statusa korisnika
    user.is_active = activation_data.is_active
    db.commit()  
    status_message = "activated" if activation_data.is_active else "deactivated"
    return {"message": f"User {user.username} has been {status_message}."}


