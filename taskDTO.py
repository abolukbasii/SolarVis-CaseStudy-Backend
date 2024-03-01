from pydantic import BaseModel
from datetime import datetime


class DeleteTaskDTO(BaseModel):
    task_id: int


class UserCreateTask(BaseModel):
    detail: str
    dueDate: datetime
    status: str


class SuperAdminCreateTask(BaseModel):
    assignedTo: int
    detail: str
    dueDate: datetime
    status: str


class SuperAdminUpdateTask(BaseModel):
    assigned_to: int
    detail: str
    due_date: datetime
    status: str
    task_id: int


class UpdateTask(BaseModel):
    detail: str
    due_date: datetime
    status: str
    task_id: int