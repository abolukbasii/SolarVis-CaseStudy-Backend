from pydantic import BaseModel

class LoginDTO(BaseModel):
    username: str
    password: str


class UpdateUserData(BaseModel):
    username: str
    first_name: str
    last_name: str
    role: str


class UpdateUserbyAdmin(BaseModel):
    username: str
    first_name: str
    last_name: str
    role: str


class AddUser(BaseModel):
    username: str
    first_name: str
    last_name: str
    role: str
    password: str


class DeleteUser(BaseModel):
    userId: int


class SuspendUser(BaseModel):
    userId: int


class UnsuspendUser(BaseModel):
    userId: int