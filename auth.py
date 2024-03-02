
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
import models
from database import get_db
from models import Users, Organization
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from Enums import UserRoleEnum

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRET_KEY = 'a35gdsujkglufut5784dyd58g987g5466su7rrd8o8r90f'
ALGORITHM = 'HS256'

bcrypt_content = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class Token(BaseModel):
    access_token: str
    token_type: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    role: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: Session = Depends(get_db)):

    email_user = db.query(models.DeletedUsers).filter(models.DeletedUsers.username == create_user_request.username).first()
    if email_user is not None:
        return jsonable_encoder({'success': False, 'detail': 'The user is deleted. It can only added by superadmin!'})

    email_user = db.query(Users).filter(Users.username == create_user_request.username).first()
    if email_user is not None:
        return jsonable_encoder({'success': False, 'detail': 'There is already an account with this email!'})
    if create_user_request.role == UserRoleEnum.superadmin:
        superadmins = db.query(Users).filter(Users.role == UserRoleEnum.superadmin).first()
        if superadmins is not None:
            return jsonable_encoder({'success': False, 'detail': 'There is already a Super Admin in the organization!'})
    create_user_model = Users(
        created_at=datetime.now(),
        updated_at=datetime.now(),
        username=create_user_request.username.lower(),
        password=bcrypt_content.hash(create_user_request.password),
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        suspended=False
    )
    db.add(create_user_model)
    db.commit()
    return jsonable_encoder({'success': True, 'detail': 'User is created!'})
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    response = authenticate_user(form_data.username, form_data.password, db)
    if not response['success']:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    token = create_access_token(response['user'].username, response['user'].id, timedelta(minutes=60))
    return jsonable_encoder({'access_token': token, 'token_type': 'bearer'})


def authenticate_user(username: str, password: str, db: Session):
    organization = db.query(Organization).filter(Organization.id == 1).first()
    email_user = db.query(models.DeletedUsers).filter(models.DeletedUsers.username == username).first()
    if email_user is not None:
        return jsonable_encoder({'success': False, 'detail': 'The user is deleted before. It can only added by Superadmin!'})

    user = db.query(Users).filter(Users.username == username.lower()).first()

    if not user:
        return jsonable_encoder({'success': False, 'detail': "Username not found!"})
    if not bcrypt_content.verify(password, user.password):
        return jsonable_encoder({'success': False, 'detail': "Wrong password!"})
    if user.suspended:
        return jsonable_encoder({'success': False, 'detail': "The user is suspended!"})
    if user and user.role != UserRoleEnum.superadmin and organization.suspended:
        return jsonable_encoder({'success': False, 'detail': "Organization is suspended!"})
    return jsonable_encoder({'success': True, 'detail': "Succesfull", 'user': user})

def create_access_token(username: str, user_id: int, expires_date: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.utcnow() + expires_date
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')
        return jsonable_encoder({'username': username, 'id': user_id})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')

async def get_username_from_request(request: Request) -> str:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        user = await get_current_user(token)
        return user['username']
    else:
        return None