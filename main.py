
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, Request
import logging
import Enums
import auth
import models
import userDTO
from sqlalchemy.orm import Session
from database import get_db, engine
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import taskDTO
from datetime import datetime
from logging.handlers import RotatingFileHandler
import time

app = FastAPI()
models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


file_handler = RotatingFileHandler("log.txt", maxBytes=10000, backupCount=1)
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

def get_db_dependency(db: Session = Depends(get_db())) -> Session:
    return db

def get_user_dependency(user: dict = Depends(auth.get_current_user)) -> dict:
    return user

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    end_time = time.time()

    if request.method != "GET" and request.method != "OPTIONS":
        elapsed_time = end_time - start_time
        username = await auth.get_username_from_request(request)
        if username:
            logger.info(f"Received request: {request.method} {request.url} - Username: {username} - Elapsed Time: {elapsed_time:.4f} seconds")

    return response


app.middleware("http")(log_requests)


@app.post("/login", response_model=dict, status_code=status.HTTP_200_OK)
async def login(login_data: userDTO.LoginDTO, db: Session = Depends(auth.get_db)):

    expires_date = 60 # minutes
    authentication = auth.authenticate_user(login_data.username, login_data.password, db)
    if not authentication['success']:
        return {'success': False, 'detail': authentication['detail']}
    user = db.query(models.Users).filter(models.Users.username == login_data.username).first()
    organization = db.query(models.Organization).first()
    token = auth.create_access_token(username=user.username, user_id=user.id, expires_date=timedelta(minutes=expires_date))
    return {'success': True, "access_token": token, "expires_date": expires_date, "token_type": "bearer", "user_id": user.id, "role": user.role, "first_name": user.first_name, "last_name": user.last_name, "username": user.username, "suspended": organization.suspended}

@app.get("/getUserTasks", response_model=dict, status_code=status.HTTP_200_OK)
async def getUserTasks(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):

    tasks = db.query(models.Tasks).filter(models.Tasks.asigned_to == user['id']).all()
    tasks_with_assign_user_name = []
    for task in tasks:
        assign_user = db.query(models.Users).filter(models.Users.id == task.asigned_by).first()
        task_dict = {
            'id': task.id,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'asigned_to': task.asigned_to,
            'asigned_by': task.asigned_by,
            'detail': task.detail,
            'due_date': task.due_date,
            'status': task.status,
            'assign_user_name': f"{assign_user.first_name} {assign_user.last_name}",
        }
        tasks_with_assign_user_name.append(task_dict)
    users = db.query(models.Users).all()
    return {'success': True, 'tasks': tasks_with_assign_user_name, 'users': users}

@app.delete("/deleteTask", response_model=dict, status_code=status.HTTP_200_OK)
async def deleteTask(deleteTask: taskDTO.DeleteTaskDTO, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    task = db.query(models.Tasks).filter(models.Tasks.id == deleteTask.task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.asigned_to != userData.id and userData.role != Enums.UserRoleEnum.superadmin:
        raise HTTPException(status_code=403, detail="You cannot delete a task that is not assigned to you")
    db.delete(task)
    db.commit()
    return {'success': True, 'detail': "Successfully deleted the task."}


@app.post("/userCreateTask", response_model=dict, status_code=status.HTTP_200_OK)
async def userCreateTask(userCreateTask: taskDTO.UserCreateTask, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    try:
        create_user_task = models.Tasks(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            asigned_to=user['id'],
            asigned_by=user['id'],
            detail=userCreateTask.detail,
            due_date=userCreateTask.dueDate,
            status=userCreateTask.status
        )
        db.add(create_user_task)
        db.commit()
        return {'success': True, 'detail': "Successfully created the task."}
    except:
        return {'success': False, 'detail': "Error creating the task."}

@app.post("/superAdminCreateTask", response_model=dict, status_code=status.HTTP_200_OK)
async def userCreateTask(superadminCreateTask: taskDTO.SuperAdminCreateTask, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    try:
        userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
        if userData.role == Enums.UserRoleEnum.superadmin:
            create_user_task = models.Tasks(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                asigned_to=superadminCreateTask.assignedTo,
                asigned_by=user['id'],
                detail=superadminCreateTask.detail,
                due_date=superadminCreateTask.dueDate,
                status=superadminCreateTask.status
            )
            db.add(create_user_task)
            db.commit()
            return {'success': True, 'detail': "Successfully created the task."}
        else:
            return {'success': False, 'detail': "You are not autherized to assign a task."}
    except:
        return {'success': False, 'detail': "Error creating the task."}

@app.put("/superAdminUpdateTask", response_model=dict, status_code=status.HTTP_200_OK)
async def superAdminUpdateTask(superAdminUpdateTask: taskDTO.SuperAdminUpdateTask, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    try:
        userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
        if userData.role != Enums.UserRoleEnum.user:
            task = db.query(models.Tasks).filter(models.Tasks.id == superAdminUpdateTask.task_id).first()
            task.detail = superAdminUpdateTask.detail
            task.asigned_to = superAdminUpdateTask.assigned_to
            task.status = superAdminUpdateTask.status
            task.due_date = superAdminUpdateTask.due_date
            task.updated_at = datetime.now()
            db.commit()
            return {'success': True, 'detail': "Successfully edited the task."}
        else:
            return {'success': False, 'detail': "You are not autherized to edit a task."}
    except:
        return {'success': False, 'detail': "Error editting the task."}

@app.put("/updateTask", response_model=dict, status_code=status.HTTP_200_OK)
async def updateTask(updateTask: taskDTO.UpdateTask, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    try:
        userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
        task = db.query(models.Tasks).filter(models.Tasks.id == updateTask.task_id).first()
        if task.asigned_to == userData.id:
            task.detail = updateTask.detail
            task.status = updateTask.status
            task.due_date = updateTask.due_date
            task.updated_at = datetime.now()
            db.commit()
            return {'success': True, 'detail': "Successfully edited the task."}
        else:
            return {'success': False, 'detail': "You are not autherized to edit this task."}
    except:
        return {'success': False, 'detail': "Error edittinh the task."}

@app.get("/getUserInfo", response_model=dict, status_code=status.HTTP_200_OK)
async def getUserInfo(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    userInfo = {
        'first_name': userData.first_name,
        'last_name': userData.last_name,
        'username': userData.username,
        'role': userData.role,
    }
    return {'success': True, 'object': userInfo}

@app.put("/updateUser", response_model=dict, status_code=status.HTTP_200_OK)
async def updateUser(updateUserData: userDTO.UpdateUserData, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()

    if userData is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    userData.first_name = updateUserData.first_name
    userData.last_name = updateUserData.last_name
    db.commit()
    return {'success': True, 'detail': 'Updated the user data'}

@app.get("/getAllTasks", response_model=dict, status_code=status.HTTP_200_OK)
async def getAllTasks(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if userData.role == Enums.UserRoleEnum.user:
        return {'success': False, 'detail': 'You are not allowed to see all tasks'}
    tasks = db.query(models.Tasks).all()
    tasks_with_assign_user_name = []

    for task in tasks:
        assign_user = db.query(models.Users).filter(models.Users.id == task.asigned_by).first()
        assigned_user = db.query(models.Users).filter(models.Users.id == task.asigned_to).first()
        task_dict = {
            'id': task.id,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'asigned_to': task.asigned_to,
            'asigned_by': task.asigned_by,
            'detail': task.detail,
            'due_date': task.due_date,
            'status': task.status,
            'assign_user_name': f"{assign_user.first_name} {assign_user.last_name}",
            'assigned_user_name': f"{assigned_user.first_name} {assigned_user.last_name}",
        }
        tasks_with_assign_user_name.append(task_dict)
    users = db.query(models.Users).all()
    return {'success': True, 'tasks': tasks_with_assign_user_name, 'users': users, 'userRole': userData.role}

@app.get("/getAllUsers", response_model=dict, status_code=status.HTTP_200_OK)
async def getAllUsers(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if userData.role == Enums.UserRoleEnum.user:
        return {'success': False, 'detail': 'You are not allowed to see all tasks'}
    elif userData.role == Enums.UserRoleEnum.admin:
        users = db.query(models.Users).filter(models.Users.role == Enums.UserRoleEnum.user).all()
        return {'success': True, 'users': users, 'userId': userData.id, 'userRole': userData.role}
    else:
        users = db.query(models.Users).all()
        return {'success': True, 'users': users, 'userId': userData.id, 'userRole': userData.role}

@app.post("/addUser", response_model=dict, status_code=status.HTTP_200_OK)
async def addUser(addUser: userDTO.AddUser, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):

    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if userData.role != Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'You are not allowed to add a user!'}

    email_user = db.query(models.DeletedUsers).filter(models.DeletedUsers.username == addUser.username.lower()).first()

    if email_user is not None and userData.role != Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'The user is deleted before. It can only added by Superadmin!'}

    email_user = db.query(models.Users).filter(models.Users.username == addUser.username.lower()).first()
    if email_user is not None:
        return {'success': False, 'detail': 'There is already an account with this email!'}
    if addUser.role == Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'Not allowed!'}
    create_user_model = models.Users(
        created_at=datetime.now(),
        updated_at=datetime.now(),
        username=addUser.username.lower(),
        password=auth.bcrypt_content.hash(addUser.password),
        first_name=addUser.first_name,
        last_name=addUser.last_name,
        role=addUser.role,
        suspended=False,
        last_edited_by=user['id']
    )
    email_user = db.query(models.DeletedUsers).filter(models.DeletedUsers.username == addUser.username).first()
    if email_user is not None:
        db.delete(email_user)
    db.add(create_user_model)
    db.commit()
    return {'success': True, 'detail': 'User is created!'}

@app.delete("/deleteUser", response_model=dict, status_code=status.HTTP_200_OK)
async def deleteUser(deleteUser: userDTO.DeleteUser, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    userId = deleteUser.userId
    userInfo = db.query(models.Users).filter(models.Users.id == user['id']).first()
    if userInfo.role != Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'You are not allowed to delete a user!'}
    else:
        userTasks = db.query(models.Tasks).filter(models.Tasks.asigned_to == userId).all()
        for task in userTasks:
            db.delete(task)
        db.commit()
        userData = db.query(models.Users).filter(models.Users.id == userId).first()
        deletedUserId = userData.id

        db.query(models.Tasks).filter(models.Tasks.asigned_to == deletedUserId).update({"asigned_to": userInfo.id}, synchronize_session=False)
        db.query(models.Tasks).filter(models.Tasks.asigned_by == deletedUserId).update({"asigned_by": userInfo.id},synchronize_session=False)
        db.query(models.Users).filter(models.Users.suspended_by == deletedUserId).update({"suspended_by": userInfo.id}, synchronize_session=False)
        db.query(models.Users).filter(models.Users.last_edited_by == deletedUserId).update({"last_edited_by": userInfo.id}, synchronize_session=False)

        username_deleted = userData.username
        db.delete(userData)
        db.commit()
        deletedUsersAdd = models.DeletedUsers(
            username=username_deleted
        )
        db.add(deletedUsersAdd)
        db.commit()
        return {'success': True, 'detail': 'The user has been deleted successfully. All the items about the user are set to superadmin!'}

@app.put("/suspendUser", response_model=dict, status_code=status.HTTP_200_OK)
async def suspendUser(suspendUser: userDTO.SuspendUser, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    suspendedUserId = suspendUser.userId
    userInfo = db.query(models.Users).filter(models.Users.id == user['id']).first()

    suspendedUserData = db.query(models.Users).filter(models.Users.id == suspendedUserId).first()
    suspendedUserRole = suspendedUserData.role

    if suspendedUserRole == Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'Superadmin cannot be suspended!'}
    if suspendedUserRole == Enums.UserRoleEnum.admin and userInfo.role == Enums.UserRoleEnum.admin:
        return {'success': False, 'detail': 'Admins cannot suspend another admin!'}

    suspendedUserData.suspended = True
    suspendedUserData.suspended_by = userInfo.id
    db.commit()
    return {'success': True, 'detail': 'The user has been suspended successfully!'}

@app.put("/unsuspendUser", response_model=dict, status_code=status.HTTP_200_OK)
async def unsuspendUser(unsuspendUser: userDTO.SuspendUser, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    unsuspendedUserId = unsuspendUser.userId
    userInfo = db.query(models.Users).filter(models.Users.id == user['id']).first()

    unsuspendedUserData = db.query(models.Users).filter(models.Users.id == unsuspendedUserId).first()

    if userInfo.role == Enums.UserRoleEnum.user:
        return {'success': False, 'detail': 'You are not autharized to unsuspend a user!'}
    if userInfo.role == Enums.UserRoleEnum.admin and unsuspendedUserData.suspended_by != userInfo.id:
        return {'success': False, 'detail': 'The user is unsuspended by another user. You cannot unsuspend!'}
    if userInfo.role == Enums.UserRoleEnum.admin and unsuspendedUserData.suspended_by != userInfo.id and unsuspendedUserData.last_edited_by != userInfo.id:
        return {'success': False, 'detail': 'You are not the person to make any modifications. You cannot unsuspend!'}

    unsuspendedUserData.suspended = False
    unsuspendedUserData.suspended_by = None
    db.commit()
    return {'success': True, 'detail': 'The user has been unsuspended successfully!'}

@app.put("/updateUserbyAdmin", response_model=dict, status_code=status.HTTP_200_OK)
async def updateUserbyAdmin(updatedUser: userDTO.UpdateUserbyAdmin, user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()
    updatedUserData = db.query(models.Users).filter(models.Users.username == updatedUser.username).first()

    if updatedUserData.suspended:
        return {'success': False, 'detail': 'You cannot update a suspended user!'}

    if userData.role != Enums.UserRoleEnum.superadmin and updatedUserData.role == Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'You cannot update the Superadmin!'}

    if userData.role == Enums.UserRoleEnum.user and updatedUserData.id != userData.id:
        return {'success': False, 'detail': 'You cannot update another user!'}

    if userData.role == Enums.UserRoleEnum.admin and updatedUserData.role == Enums.UserRoleEnum.admin and updatedUserData.id != userData.id:
        return {'success': False, 'detail': 'You cannot update another admin!'}

    updatedUserData.first_name = updatedUser.first_name
    updatedUserData.last_name = updatedUser.last_name
    updatedUserData.last_edited_by = userData.id
    db.commit()
    return {'success': True, 'detail': 'Updated the user data'}

@app.put("/suspendOrganization", response_model=dict, status_code=status.HTTP_200_OK)
async def suspendOrganization(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()

    if userData.role != Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'You cannot suspend organization!'}

    organization = db.query(models.Organization).first()
    organization.suspended = True
    db.commit()
    return {'success': True, 'detail': 'Succesfully suspended the organization!'}


@app.put("/unsuspendOrganization", response_model=dict, status_code=status.HTTP_200_OK)
async def unsuspendOrganization(user: models.Users = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    userData = db.query(models.Users).filter(models.Users.id == user['id']).first()

    if userData.role != Enums.UserRoleEnum.superadmin:
        return {'success': False, 'detail': 'You cannot unsuspend organization!'}

    organization = db.query(models.Organization).first()
    organization.suspended = False
    db.commit()
    return {'success': True, 'detail': 'Succesfully unsuspended the organization!'}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)